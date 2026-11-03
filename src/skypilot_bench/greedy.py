"""Place jobs in input order on the cheapest available machine."""

from collections import Counter

from .model import decimal, validate_input


def place(data):
    validate_input(data)
    used, plan = Counter(), []
    for job in data["jobs"]:
        available = [
            r
            for r in data["offerings"]
            if r["cpus"] >= job["required_cpus"]
            and [r["provider"], r["region"]] in job["allowed_locations"]
            and decimal(job["duration_h"]) <= decimal(job["deadline_h"])
            and used[r["id"]] < r["capacity"]
        ]
        if not available:
            continue
        resource = min(available, key=lambda r: (decimal(r["price_usd_h"]), r["id"]))
        used[resource["id"]] += 1
        plan.append(
            {
                "job_id": job["id"],
                "offering_id": resource["id"],
                "cost_usd": str(decimal(resource["price_usd_h"]) * decimal(job["duration_h"])),
            }
        )
    return {
        "status": "feasible",
        "cost_usd": str(sum(decimal(row["cost_usd"]) for row in plan)),
        "plan": plan,
    }
