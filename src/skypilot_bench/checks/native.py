"""Check the original ILP using real SkyPilot objects and synthetic inputs."""

import time
from decimal import Decimal

from skypilot_bench.author import installed_optimizer
from skypilot_bench.model import validate_plan
from skypilot_bench.sky_bridge import build_problem

from . import require
from .cli import execute
from .fixtures import original_cases


def run(args):
    optimizer, metadata = installed_optimizer(args.source)
    rows = []
    expected = [
        ("1.40", ["capacity"]),
        ("1.40", []),
        ("1.70", []),
        ("9.60", ["capacity"]),
        ("10.80", ["capacity"]),
        ("10.80", []),
    ]
    for case, (expected_cost, expected_errors) in zip(original_cases(), expected, strict=True):
        problem = build_problem(case.data)
        started = time.perf_counter()
        best, objective = optimizer._optimize_by_ilp(*problem.arguments, minimize_cost=True)
        seconds = time.perf_counter() - started
        plan = problem.plan(best)
        errors, placed, cost = validate_plan(case.data, plan)
        require(errors == expected_errors, f"{case.name}: unexpected errors {errors}")
        require(placed == len(case.data["jobs"]), f"{case.name}: incomplete plan")
        require(
            cost == Decimal(expected_cost) and abs(objective - float(cost)) < 1e-8,
            f"{case.name}: unexpected cost",
        )
        rows.append(
            {
                "case": case.name,
                "cost_usd": str(cost),
                "plan": plan,
                "validator_errors": errors,
                "wall_seconds": seconds,
            }
        )
    return {
        **metadata,
        "cases": rows,
        "scope": "Original private ILP; real SkyPilot objects and synthetic CPU candidates",
    }


def main():
    return execute("original-ilp", run, source=True, offline=True)


if __name__ == "__main__":
    raise SystemExit(main())
