import pytest
from hbo_bench.oracle import Oracle

TPCH_ORACLE = Oracle("data/processed/tpch_10gb")


@pytest.fixture
def tpch_oracle() -> "Oracle":
    return TPCH_ORACLE
