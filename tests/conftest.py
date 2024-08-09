import sys
import os
import pytest

sys.path.insert(0, os.getcwd())

from oracle import Oracle

TPCH_ORACLE = Oracle("data/processed/tpch_10gb")


@pytest.fixture
def tpch_oracle() -> "Oracle":
    return TPCH_ORACLE
