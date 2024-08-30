from hbo_bench.oracle import Oracle
from hbo_bench.query_explorer import QueryExplorer, SearchingState
from hbo_bench.data_config import DEFAULT_DOP, DEFAULT_HINTSET
from hbo_bench.local_search_settings import LOCAL_SS, LOCAL_DEF_DOP_SS


def test_boost(tpch_oracle: "Oracle"):
    for ss in [LOCAL_SS, LOCAL_DEF_DOP_SS]:
        explorer = QueryExplorer(tpch_oracle, "q11", ss)
        def_state, best_state = SearchingState(DEFAULT_HINTSET, DEFAULT_DOP), explorer.run()
        assert explorer.get_e2e_time(def_state) > explorer.get_e2e_time(best_state)
