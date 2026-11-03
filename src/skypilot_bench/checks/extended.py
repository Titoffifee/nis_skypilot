"""Check author DP against enumeration and verify cost/time calculations."""

import random
from dataclasses import dataclass
from itertools import product

from skypilot_bench.author import extract_methods

from . import require
from .cli import execute


@dataclass(frozen=True)
class Resource:
    name: str
    price_h: float
    runtime_s: float

    def get_cost(self, seconds):
        return self.price_h * seconds / 3600


@dataclass(eq=False)
class Task:
    name: str
    resources: tuple
    num_nodes: int = 1
    best_resources: object = None
    time_estimator_func: bool = True

    def estimate_runtime(self, resource):
        return resource.runtime_s


class Graph:
    def __init__(self, edges):
        self.edges = edges

    def predecessors(self, node):
        return [parent for parent, child in self.edges if child is node]


def chain_fixture(resources):
    dummy = Resource("dummy", 0, 0)
    source = Task("skypilot-dummy-source", (dummy,))
    sink = Task("skypilot-dummy-sink", (dummy,))
    nodes = [source] + [Task(f"job{i}", tuple(rs)) for i, rs in enumerate(resources)] + [sink]
    return nodes, Graph(list(zip(nodes, nodes[1:])))


def compare(optimizer, nodes, graph, transfers, minimize_cost):
    def transfer(is_cost, parent, r_parent, child, r_child):
        return transfers.get((is_cost, parent.name, r_parent.name, child.name, r_child.name), 0)

    optimizer._egress_cost_or_time = staticmethod(transfer)
    cost_map = {
        n: {r: r.get_cost(r.runtime_s) if minimize_cost else r.runtime_s for r in n.resources}
        for n in nodes
    }
    plan, actual = optimizer._optimize_by_dp(nodes, cost_map, minimize_cost)
    # Direct Cartesian enumeration, independent of the author recurrence.
    expected = min(
        sum(cost_map[n][r] for n, r in zip(nodes, assignment))
        + sum(
            transfer(minimize_cost, u, ru, v, rv)
            for u, ru, v, rv in zip(nodes, assignment, nodes[1:], assignment[1:])
        )
        for assignment in product(*(n.resources for n in nodes))
    )
    require(abs(actual - expected) < 1e-7, f"Oracle mismatch: {actual} != {expected}")
    total_cost = optimizer._compute_total_cost(graph, nodes, plan)
    total_time = optimizer._compute_total_time(graph, nodes, plan)
    direct_cost = sum(plan[n].get_cost(plan[n].runtime_s) for n in nodes) + sum(
        transfer(True, u, plan[u], v, plan[v]) for u, v in graph.edges
    )
    direct_time = sum(plan[n].runtime_s for n in nodes) + sum(
        transfer(False, u, plan[u], v, plan[v]) for u, v in graph.edges
    )
    require(abs(total_cost - direct_cost) < 1e-7, "Author cost mismatch")
    require(abs(total_time - direct_time) < 1e-7, "Author time mismatch")
    return plan, actual


def run(args):
    optimizer, metadata = extract_methods(
        args.source, {"_optimize_by_dp", "_compute_total_cost", "_compute_total_time"}
    )
    for seed in range(100):
        rng = random.Random(seed)
        resources = [
            [
                Resource(f"r{k}", rng.randint(1, 5), rng.randint(1, 6) * 3600)
                for k in range(rng.randint(1, 3))
            ]
            for _ in range(rng.randint(1, 5))
        ]
        nodes, graph = chain_fixture(resources)
        transfers = {}
        for u, v in graph.edges:
            if u is nodes[0] or v is nodes[-1]:
                continue
            for a, b in product(u.resources, v.resources):
                transfers[True, u.name, a.name, v.name, b.name] = rng.randint(0, 9)
                transfers[False, u.name, a.name, v.name, b.name] = rng.randint(0, 900)
        for minimize in (True, False):
            compare(optimizer, nodes, graph, transfers, minimize)
    # A local compute minimum can lose after transfer costs are included.
    nodes, graph = chain_fixture(
        [
            [Resource("A", 1, 3600), Resource("B", 2, 3600)],
            [Resource("A", 1, 36000), Resource("B", 2, 1800)],
        ]
    )
    transfer = {(True, "job0", a, "job1", b): 20 for a, b in [("A", "B"), ("B", "A")]}
    plan, objective = compare(optimizer, nodes, graph, transfer, True)
    chosen = [plan[n].name for n in nodes[1:-1]]
    require(chosen == ["B", "B"] and objective == 3, "Unexpected transfer tradeoff")
    # Parallel branches: total time is the critical path, not sum of runtimes.
    dummy = Resource("dummy", 0, 0)
    source = Task("skypilot-dummy-source", (dummy,))
    root = Task("root", (Resource("root", 1, 3600),))
    left = Task("left", (Resource("left", 1, 7200),))
    right = Task("right", (Resource("right", 1, 14400),))
    sink = Task("sink", (dummy,))
    dag = Graph([(source, root), (root, left), (root, right), (left, sink), (right, sink)])
    nodes = [source, root, left, right, sink]
    optimizer._egress_cost_or_time = staticmethod(lambda *unused: 0)
    plan = {n: n.resources[0] for n in nodes}
    runtime = optimizer._compute_total_time(dag, nodes, plan)
    cost = optimizer._compute_total_cost(dag, nodes, plan)
    require(runtime == 18000 and cost == 7, "Parallel DAG calculation mismatch")
    root.num_nodes = 3
    multinode_cost = optimizer._compute_total_cost(dag, nodes, plan)
    require(multinode_cost == 9, "num_nodes cost multiplier mismatch")
    report = {
        **metadata,
        "scope": "Extracted author DP and cost/time calculations; synthetic transfers",
        "randomized": {
            "seeds": "0..99",
            "chains": 100,
            "optimization_checks": 200,
            "total_cost_checks": 200,
            "total_time_checks": 200,
        },
        "transfer_tradeoff": {
            "status": "passed",
            "chosen": chosen,
            "cost": objective,
            "local_compute_first_choice": "A",
        },
        "parallel_dag": {
            "status": "passed",
            "runtime_s": runtime,
            "cost": cost,
            "multinode_cost": multinode_cost,
        },
    }
    return report


def main():
    return execute("extended", run, source=True)


if __name__ == "__main__":
    raise SystemExit(main())
