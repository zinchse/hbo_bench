from oracle import Oracle, OracleRequest
from vectorization import extract_vertices_and_edges, ALL_OPERATIONS
import math
import torch


def test_vertices_and_edges(tpch_oracle: "Oracle"):
    plan = tpch_oracle.get_explain_plan(OracleRequest(query_name="q01", hintset=0, dop=1))
    (vertices, edges) = extract_vertices_and_edges(plan)
    sort_index = ALL_OPERATIONS.index("Sort")
    assert torch.all(vertices[0][0:sort_index] == 0) and torch.all(vertices[0][sort_index + 1 : -2] == 0)
    assert vertices[0][sort_index] == 1.0
    assert vertices[0][-1] == 1.0
    assert vertices[0][-2] == math.log(6.0)
    assert torch.allclose(edges[0], torch.tensor([1, 2, 0], dtype=torch.long))
