"""Translate validated benchmark inputs to SkyPilot task and resource objects."""

import math
from copy import deepcopy
from dataclasses import dataclass

from .model import decimal, validate_input


@dataclass
class Problem:
    data: dict
    graph: object
    nodes: list
    costs: dict
    capacities: dict
    resources: dict

    @property
    def arguments(self):
        return self.graph, self.nodes, self.costs

    def plan(self, assignments, *, allow_partial=False):
        if not isinstance(assignments, dict) or not set(assignments) <= set(self.nodes):
            raise ValueError("Solver assignments must refer to input tasks")
        if not allow_partial and set(assignments) != set(self.nodes):
            raise ValueError("Solver must assign exactly the input tasks")
        ids = {id(resource): rid for rid, resource in self.resources.items()}
        offerings = {resource["id"]: resource for resource in self.data["offerings"]}
        plan = []
        for node, job in zip(self.nodes, self.data["jobs"], strict=True):
            if node not in assignments:
                if node.best_resources is not None:
                    raise ValueError("Unassigned task has stale resources")
                continue
            selected = assignments[node]
            if node.best_resources is not selected or selected not in self.costs[node]:
                raise ValueError("Solver returned a resource outside the candidate set")
            rid = ids[id(selected)]
            cost = decimal(offerings[rid]["price_usd_h"]) * decimal(job["duration_h"])
            plan.append({"job_id": job["id"], "offering_id": rid, "cost_usd": str(cost)})
        return plan


def build_problem(data):
    validate_input(data)
    data = deepcopy(data)
    import networkx as nx
    import sky

    resources = {
        r["id"]: sky.Resources(cpus=r["cpus"], labels={"benchmark-offering": str(i)})
        for i, r in enumerate(data["offerings"])
    }
    capacities = {resources[r["id"]]: r["capacity"] for r in data["offerings"]}
    nodes, costs = [], {}
    for job in data["jobs"]:
        candidates = {}
        for resource in data["offerings"]:
            if (
                resource["cpus"] < job["required_cpus"]
                or [resource["provider"], resource["region"]] not in job["allowed_locations"]
                or decimal(job["duration_h"]) > decimal(job["deadline_h"])
            ):
                continue
            cost = float(decimal(resource["price_usd_h"]) * decimal(job["duration_h"]))
            if not math.isfinite(cost):
                raise ValueError("Cost is too large for the solver")
            candidates[resources[resource["id"]]] = cost
        node = sky.Task(name=job["id"], resources=set(candidates) if candidates else None)
        nodes.append(node)
        costs[node] = candidates
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    return Problem(data, graph, nodes, costs, capacities, resources)
