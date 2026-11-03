"""Check the author DP on a small synthetic input."""

import json
from dataclasses import dataclass
from decimal import Decimal

from skypilot_bench.author import extract_methods
from skypilot_bench.checks.paths import DATA
from skypilot_bench.model import validate_plan as validate

from . import require
from .cli import execute


@dataclass(eq=False)
class Node:
    name: str
    resources: tuple = ()
    best_resources: object = None


def run(args):
    optimizer, metadata = extract_methods(args.source, {"_optimize_by_dp"})
    # Explicitly scoped to a fixture with no transfers.
    optimizer._egress_cost_or_time = staticmethod(lambda *unused: 0)
    original = json.loads((DATA / "smoke.json").read_text())
    results = []
    for label, allowed, expected_id, expected_cost in [
        ("cheapest", [["A", "east"], ["B", "west"]], "A/east/small", "0.70"),
        ("region_filter", [["B", "west"]], "B/west/small", "1.00"),
    ]:
        job = dict(original["jobs"][0], allowed_locations=allowed)
        data = {"offerings": original["offerings"], "jobs": [job]}
        start = Node("skypilot-dummy-source", ("source",))
        task = Node(job["id"])
        end = Node("skypilot-dummy-sink", ("sink",))
        candidates = {
            r["id"]: float(Decimal(r["price_usd_h"]) * Decimal(job["duration_h"]))
            for r in data["offerings"]
            if [r["provider"], r["region"]] in job["allowed_locations"]
            and r["cpus"] >= job["required_cpus"]
            and Decimal(job["duration_h"]) <= Decimal(job["deadline_h"])
        }
        plan, objective = optimizer._optimize_by_dp(
            [start, task, end], {start: {"source": 0}, task: candidates, end: {"sink": 0}}, True
        )
        chosen = plan[task]
        resource = next(r for r in data["offerings"] if r["id"] == chosen)
        cost = Decimal(resource["price_usd_h"]) * Decimal(job["duration_h"])
        output = [{"job_id": job["id"], "offering_id": chosen, "cost_usd": str(cost)}]
        errors, placed, recalculated = validate(data, output)
        require(chosen == expected_id and cost == Decimal(expected_cost), f"{label}: wrong choice")
        require(not errors and placed == 1 and recalculated == cost, f"{label}: invalid plan")
        require(abs(objective - float(cost)) < 1e-9, f"{label}: objective mismatch")
        results.append(
            {
                "case": label,
                "status": "passed",
                "plan": output,
                "author_objective": objective,
                "validator_errors": errors,
            }
        )
    return {
        **metadata,
        "cases": results,
        "scope": "Extracted author DP; synthetic candidates and zero transfer cost",
    }


def main():
    return execute("dp", run, source=True)


if __name__ == "__main__":
    raise SystemExit(main())
