from typing import Dict
from hbo_bench.oracle import Oracle, OracleRequest
from hbo_bench.data_config import BENCH_NAME_TO_SIZE
from hbo_bench.data_types import ExplainAnalyzePlan, ExplainPlan, Time, QueryName, Cost


PATH_TO_DATA: "str" = "src/hbo_bench/data/processed"
BENCH_NAME_TO_EXAMPLE_QUERY: "Dict[str, QueryName]" = {
    "JOB": "1b",
    "sample_queries": "q10_2a265",
    "tpch_10gb": "q01",
}


def test_types_and_sizes():
    for bench_name, query_name in BENCH_NAME_TO_EXAMPLE_QUERY.items():
        oracle = Oracle(f"{PATH_TO_DATA}/{bench_name}")
        oracle_request = OracleRequest(query_name=query_name, dop=1, hintset=42)
        assert isinstance(oracle.get_query_names(), list)
        assert len(oracle.get_query_names()) == BENCH_NAME_TO_SIZE[bench_name]
        assert isinstance(oracle.get_planning_time(request=oracle_request), Time)
        assert isinstance(oracle.get_execution_time(request=oracle_request), Time)
        assert isinstance(oracle.get_explain_analyze_plan(request=oracle_request), (type(None), ExplainAnalyzePlan))
        assert isinstance(oracle.get_explain_plan(request=oracle_request), ExplainPlan)
        assert isinstance(oracle.get_cost(request=oracle_request), Cost)
