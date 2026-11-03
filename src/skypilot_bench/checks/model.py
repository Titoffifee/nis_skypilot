"""Check the small model and deliberately invalid plans."""

from copy import deepcopy
from decimal import Decimal

from skypilot_bench.model import validate_plan
from skypilot_bench.oracle import enumerate_plans

from . import require
from .cli import execute
from .fixtures import small_cases


def run(args):
    data = small_cases()[0].data
    best = min(enumerate_plans(data), key=lambda plan: sum(Decimal(e["cost_usd"]) for e in plan))
    errors, placed, cost = validate_plan(data, best)
    require(not errors and placed == 2 and cost == Decimal("1.70"), "Wrong optimum")
    checks = []
    for label in (
        "cpu",
        "region",
        "deadline",
        "capacity",
        "cost",
        "job_coverage",
        "unknown_offering",
        "unassigned",
    ):
        changed, plan = deepcopy(data), deepcopy(best)
        if label == "cpu":
            changed["jobs"][0]["required_cpus"] = 8
        elif label == "region":
            changed["jobs"][0]["allowed_locations"] = [["A", "east"]]
        elif label == "deadline":
            changed["jobs"][0]["deadline_h"] = "0.5"
        elif label == "capacity":
            changed["offerings"][1]["capacity"] = 0
        elif label == "cost":
            plan[0]["cost_usd"] = "0"
        elif label == "job_coverage":
            plan.append(dict(plan[0]))
        elif label == "unassigned":
            plan[0].update(offering_id=None, cost_usd="0")
        else:
            plan[0]["offering_id"] = "missing"
        require(label in validate_plan(changed, plan)[0], f"Undetected violation: {label}")
        checks.append(label)
    for resource in data["offerings"]:
        resource["capacity"] = 0
    require(not list(enumerate_plans(data)), "Zero capacity must be infeasible")
    return {
        "plan": best,
        "cost_usd": str(cost),
        "rejected_errors": checks,
        "zero_capacity": "infeasible",
    }


def main():
    return execute("model", run)


if __name__ == "__main__":
    raise SystemExit(main())
