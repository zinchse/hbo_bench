from oracle import Oracle, OracleRequest
from vectorization import extract_vertices_and_edges
from dataset import WeightedBinaryTreeDataset, weighted_binary_tree_collate
import torch
from utils import preprocess, MAX_TREE_LENGTH
from torch.utils.data import DataLoader


def test_dataset(tpch_oracle: "Oracle"):
    freq = 42
    plan = tpch_oracle.get_explain_plan(OracleRequest(query_name="q01", hintset=0, dop=1))
    (vertices, edges), time = extract_vertices_and_edges(plan), torch.Tensor([1.0])
    dataset = WeightedBinaryTreeDataset([vertices] * freq, [edges] * freq, [time] * freq, torch.device("cpu"))
    assert len(dataset) == 1

    dataloader = DataLoader(
        dataset=dataset,
        batch_size=1,
        shuffle=False,
        collate_fn=lambda el: weighted_binary_tree_collate(el, MAX_TREE_LENGTH),
        drop_last=False,
    )

    vertices, edges = preprocess(vertices, edges)
    for (v, e, f), t in dataloader:
        assert torch.all(v[0] - vertices == 0)
        assert torch.all(e[0] - edges == 0)
        assert torch.all(t[0] - time == 0)
        assert torch.all(f[0] - torch.Tensor([freq]) == 0)
