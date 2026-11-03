"""Compare both ILP objectives with full enumeration."""

import time
from decimal import Decimal
from unittest.mock import patch

from skypilot_bench.adapter import load_capacity_optimizer
from skypilot_bench.metrics import evaluate_plan
from skypilot_bench.oracle import enumerate_plans
from skypilot_bench.sky_bridge import build_problem

from . import require
from .cli import execute
from .fixtures import capacity_cases


def run(args):
    import pulp

    optimizer, metadata = load_capacity_optimizer(args.source)
    rows = []
    real_solve = pulp.LpProblem.solve
    for case in capacity_cases():
        problem = build_problem(case.data)
        oracle = min(
            enumerate_plans(case.data, allow_partial=True),
            key=lambda plan: (-len(plan), sum(Decimal(row["cost_usd"]) for row in plan)),
        )
        expected = evaluate_plan(case.data, oracle)
        solver_calls = []

        def solve(model, *args, **kwargs):
            solver_calls.append(1)
            return real_solve(model, *args, **kwargs)

        started = time.perf_counter()
        with patch.object(pulp.LpProblem, "solve", solve):
            best, objective, status = optimizer._optimize_by_ilp(
                *problem.arguments, resource_capacities=problem.capacities
            )
        seconds = time.perf_counter() - started
        require(status == "optimal", f"{case.name}: expected optimal, got {status}")
        plan = problem.plan(best, allow_partial=True)
        actual = evaluate_plan(case.data, plan)
        require(actual == expected, f"{case.name}: ILP differs from enumeration")
        require(abs(objective - float(actual["cost_usd"])) < 1e-7, "Objective mismatch")
        require(len(solver_calls) == (2 if actual["placed"] else 1), "Unexpected solver calls")
        rows.append(
            {
                "case": case.name,
                "status": status,
                **actual,
                "solver_calls": len(solver_calls),
                "oracle": expected,
                "plan": plan,
                "wall_seconds": seconds,
            }
        )
    return {
        **metadata,
        "cases": rows,
        "scope": "Maximize placed tasks, then minimize cost; checked by enumeration",
    }


def main():
    return execute("capacity-ilp", run, source=True, offline=True)


if __name__ == "__main__":
    raise SystemExit(main())
