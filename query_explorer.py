from typing import Set, List, Tuple
from collections import namedtuple
from oracle import Oracle, OracleRequest
from data_types import QueryName, Time, ExplainPlan
from data_config import DEFAULT_DOP, DEFAULT_HINTSET, DOPS, HINTS


OFF_INL_HINT = 64 | 8 | 2
N_SCANS = 4
N_JOINS = 3
NL_POS = 2
assert N_SCANS + N_JOINS == len(HINTS)


SearchingState = namedtuple("SearchingState", ["hintset", "dop"], defaults=[DEFAULT_HINTSET, DEFAULT_DOP])

SearchingSettings = namedtuple(
    "SearchingSettings",
    [
        "disable_joins",
        "disable_scans",
        "decrease_dop",
        "disable_inl",
        "relative_boost_threshold",
        "max_iter",
        "use_joined_search",
        "default_hintset",
        "default_dop",
        "hardcoded_hintsets",
        "hardcoded_dops",
    ],
    defaults=[
        False,
        False,
        False,
        False,
        1.0,
        1,
        False,
        DEFAULT_HINTSET,
        DEFAULT_DOP,
        None,
        None,
    ],
)


class QueryExplorer:
    def __init__(
        self,
        oracle: "Oracle",
        query_name: "QueryName",
        settings: "SearchingSettings",
    ):
        self.oracle = oracle
        self.query_name = query_name
        self.settings = settings

        self.tried_states: "Set[SearchingState]" = set()
        self.explored_states: "Set[SearchingState]" = set()

        self.parallel_planning_time = 0.0
        self.parallel_e2e_time = 0.0

    def _prepare_request(self, state: "SearchingState") -> "OracleRequest":
        return OracleRequest(query_name=self.query_name, hintset=state.hintset, dop=state.dop)

    def get_execution_time(self, state: "SearchingState") -> "Time":
        request = OracleRequest(query_name=self.query_name, hintset=state.hintset, dop=state.dop)
        return self.oracle.get_execution_time(request) / 1000

    def get_planning_time(self, state: "SearchingState") -> "Time":
        return self.oracle.get_planning_time(self._prepare_request(state)) / 1000

    def get_e2e_time(self, state: "SearchingState") -> "Time":
        return self.get_execution_time(state) + self.get_planning_time(state)

    def _get_explain_plan(self, state: "SearchingState") -> "ExplainPlan":
        return self.oracle.get_explain_plan(self._prepare_request(state))  # pragma: no cover

    def explore_in_parallel(self, neighbors: "List[SearchingState]", timeout: "Time") -> "Tuple[Time, SearchingState]":
        self.tried_states |= set(neighbors)
        min_e2e_time, best_st = min((self.get_planning_time(st) + self.get_execution_time(st), st) for st in neighbors)
        timeout = min(timeout, min_e2e_time)
        plan_times = [self.get_planning_time(st) for st in neighbors]
        e2e_times = [self.get_planning_time(st) + self.get_execution_time(st) for st in neighbors]
        self.parallel_planning_time += max(min(plan_time, timeout) for plan_time in plan_times)
        self.parallel_e2e_time += min(min(e2e_time, timeout) for e2e_time in e2e_times)
        if min_e2e_time <= timeout:
            self.explored_states.add(best_st)
        return min_e2e_time, best_st

    def run(self) -> "SearchingState":
        def_state = SearchingState(self.settings.default_hintset, self.settings.default_dop)
        prev_state, record_state, record_time = None, def_state, float("inf")
        it = 0
        while it < self.settings.max_iter and prev_state != record_state:
            timeout, prev_state = record_time / self.settings.relative_boost_threshold, record_state
            neighbors = list(filter(lambda st: st not in self.tried_states, self.get_neighbors(state=record_state)))
            if not neighbors:
                break  # pragma: no cover
            best_ngb_time, best_ngb = self.explore_in_parallel(neighbors, timeout)
            if record_time / best_ngb_time > self.settings.relative_boost_threshold:
                record_state, record_time = best_ngb, best_ngb_time
            it += 1

        return record_state

    def get_neighbors(self, state: "SearchingState") -> "List[SearchingState]":
        current_dop, current_hintset = state.dop, state.hintset
        neighbors = set()

        if self.settings.use_joined_search and self.settings.decrease_dop:
            to_try_dops = DOPS
        else:
            to_try_dops = [current_dop]

        for dop in to_try_dops:
            if self.settings.disable_scans:
                for op_num in range(N_SCANS):
                    neighbors.add(SearchingState(dop=dop, hintset=current_hintset | (1 << op_num)))

            if self.settings.disable_joins:
                for op_num in range(N_SCANS, N_SCANS + N_JOINS):
                    neighbors.add(SearchingState(dop=dop, hintset=current_hintset | (1 << op_num)))

            if self.settings.disable_inl:
                neighbors.add(SearchingState(dop=dop, hintset=current_hintset | (OFF_INL_HINT)))

            if self.settings.decrease_dop:
                for new_dop in [new_dop for new_dop in DOPS if new_dop < dop]:
                    neighbors.add(SearchingState(dop=new_dop, hintset=current_hintset))

        return [state] + list(neighbors)
