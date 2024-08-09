from collections import defaultdict
from typing import List, Tuple, TypedDict
import torch
from torch import Tensor
from data_types import ExplainPlan, ExplainNode, Cardinality, Selectivity, QueryName, HintsetCode, QueryDop
from dataset import paddify_sequences
from oracle import Oracle, OracleRequest, TIMEOUT
from vectorization import extract_vertices_and_edges
from data_config import HINTSETS, DOPS, DEFAULT_HINTSET


# hardcoded constant
MAX_TREE_LENGTH = 66


def get_logical_tree(plan: "ExplainPlan", with_rels: "bool" = True) -> "str":
    res = []

    def recurse(node: "ExplainNode") -> "None":
        if with_rels:
            res.append(f"{node.node_type} (Rel={node.relation_name}|Index={node.index_name})")
        else:
            res.append(f"{node.node_type}")
        res.append("[")
        for child in node.plans:
            recurse(child)
        res.append("]")

    recurse(node=plan.plan)
    return " ".join(res)


def get_full_plan(plan: "ExplainPlan", with_rels: "bool" = True) -> "str":
    res = []

    def recurse(node: "ExplainNode") -> "None":
        node_type, cardinalities = node.node_type, node.estimated_cardinality
        if with_rels:
            rel_name, index_name = node.relation_name, node.index_name
            res.append(f"{node_type} (Rel={rel_name}|Index={index_name}|Cards={cardinalities})")
        else:
            res.append(f"{node_type} (Cards={cardinalities})")
        res.append("[")
        for child in node.plans:
            recurse(child)
        res.append("]")

    recurse(node=plan.plan)
    return " ".join(res)


def get_selectivities(plan: "ExplainPlan") -> "List[Selectivity]":
    res = []

    def recurse(node: "ExplainNode") -> "None":
        max_possible_size = 1
        current_size = node.estimated_cardinality
        for child in node.plans:
            max_possible_size *= child.estimated_cardinality
        res.append(current_size / max_possible_size)

        for child in node.plans:
            recurse(child)

    recurse(node=plan.plan)
    return res


def get_cardinalities(plan: "ExplainPlan") -> "List[Cardinality]":
    res = []

    def recurse(node: "ExplainNode") -> "None":
        res.append(node.estimated_cardinality)
        for child in node.plans:
            recurse(child)

    recurse(node=plan.plan)
    return res


class QueryInfo(TypedDict):
    query_name: "QueryName"
    hintset: "HintsetCode"
    dop: "QueryDop"
    vertices: "Tensor"
    edges: "Tensor"
    time: "Tensor"


def preprocess(v: "Tensor", e: "Tensor") -> "Tuple[Tensor, Tensor]":
    """unifies tensors from dataset with tensors from dataloader; see `weighted_binary_tree_collate`"""
    v, e = v.clone(), e.clone()
    v = torch.stack(paddify_sequences([v], MAX_TREE_LENGTH)).transpose(1, 2)[0]
    e = torch.stack(paddify_sequences([e], MAX_TREE_LENGTH)).unsqueeze(1)[0]
    return v, e


def extract_list_info(oracle: "Oracle", query_names: "List[QueryName]") -> "List[QueryInfo]":
    """initial plan processing and T/O handling with search for maximum lower bound of execution time"""
    list_info = []

    for query_name in query_names:
        seen_logical_plans = set()
        timeouted_logical_plans_to_dops = defaultdict(set)
        timeouted_logical_plans_to_settings = defaultdict(list)
        logical_plan_to_times = defaultdict(list)

        for dop in DOPS:
            for hintset in HINTSETS:
                custom_request = OracleRequest(query_name=query_name, hintset=hintset, dop=dop)
                custom_logical_plan = get_logical_tree(oracle.get_explain_plan(custom_request))
                custom_time = oracle.get_execution_time(custom_request)
                if custom_time != TIMEOUT:
                    time = torch.tensor(custom_time / 1000, dtype=torch.float32)
                    vertices, edges = extract_vertices_and_edges(oracle.get_explain_plan(request=custom_request))
                    seen_logical_plans.add(custom_logical_plan)
                    info: "QueryInfo" = {
                        "query_name": query_name,
                        "hintset": hintset,
                        "dop": dop,
                        "time": time,
                        "vertices": vertices,
                        "edges": edges,
                    }
                    list_info.append(info)
                    logical_plan_to_times[custom_logical_plan].append(time)
                else:
                    timeouted_logical_plans_to_dops[custom_logical_plan].add(dop)
                    timeouted_logical_plans_to_settings[custom_logical_plan].append((dop, hintset))

        for custom_logical_plan in timeouted_logical_plans_to_settings:
            if custom_logical_plan in logical_plan_to_times:
                time = torch.mean(torch.stack(logical_plan_to_times[custom_logical_plan]))
            else:
                max_def_time = 0.0
                for dop in timeouted_logical_plans_to_dops[custom_logical_plan]:
                    def_request = OracleRequest(query_name=query_name, hintset=DEFAULT_HINTSET, dop=dop)
                    def_time = oracle.get_execution_time(request=def_request)
                    max_def_time = max(max_def_time, def_time)
                time = torch.tensor(2 * max_def_time / 1000, dtype=torch.float32)

            for dop, hintset in timeouted_logical_plans_to_settings[custom_logical_plan]:
                custom_request = OracleRequest(query_name=query_name, hintset=hintset, dop=dop)
                vertices, edges = extract_vertices_and_edges(oracle.get_explain_plan(request=custom_request))
                timeouted_info: "QueryInfo" = {
                    "query_name": query_name,
                    "hintset": hintset,
                    "dop": dop,
                    "time": time,
                    "vertices": vertices,
                    "edges": edges,
                }

                list_info.append(timeouted_info)

    return list_info
