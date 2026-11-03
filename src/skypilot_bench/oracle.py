"""Full enumeration for small inputs, independent of the ILP adapter."""

from collections import Counter
from itertools import product

from .model import decimal, validate_input


def enumerate_plans(data, *, allow_partial=False):
    validate_input(data)
    choices = []
    for job in data["jobs"]:
        choices.append(
            [
                resource
                for resource in data["offerings"]
                if resource["cpus"] >= job["required_cpus"]
                and [resource["provider"], resource["region"]] in job["allowed_locations"]
                and decimal(job["duration_h"]) <= decimal(job["deadline_h"])
            ]
        )
        if allow_partial:
            choices[-1].append(None)
    for assignment in product(*choices):
        used = Counter(resource["id"] for resource in assignment if resource is not None)
        if any(used[r["id"]] > r["capacity"] for r in data["offerings"]):
            continue
        yield [
            {
                "job_id": job["id"],
                "offering_id": resource["id"],
                "cost_usd": str(decimal(resource["price_usd_h"]) * decimal(job["duration_h"])),
            }
            for job, resource in zip(data["jobs"], assignment)
            if resource is not None
        ]
