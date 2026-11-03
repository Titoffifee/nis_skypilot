"""Input validation and an independent plan validator."""

from collections import Counter
from decimal import Decimal, InvalidOperation


def decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(f"Expected a number, got {value!r}")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid number: {value!r}") from exc
    if not result.is_finite():
        raise ValueError("Numbers must be finite")
    return result


def validate_input(data):
    if not isinstance(data, dict):
        raise ValueError("Input must be an object")
    for group in ("jobs", "offerings"):
        records = data.get(group)
        if not isinstance(records, list):
            raise ValueError(f"{group} must be a list")
        seen = set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"Every {group} entry must be an object")
            key = record.get("id")
            if not isinstance(key, str) or not key or key in seen:
                raise ValueError(f"Missing or duplicate {group} id: {key!r}")
            seen.add(key)
    for resource in data["offerings"]:
        for field in ("provider", "region", "instance_type"):
            if not isinstance(resource.get(field), str) or not resource[field]:
                raise ValueError(f"Invalid resource {field}")
        for field, minimum in (("cpus", 1), ("capacity", 0)):
            value = resource.get(field)
            if type(value) is not int or value < minimum:
                raise ValueError(f"Invalid resource {field}")
        if decimal(resource.get("price_usd_h")) < 0:
            raise ValueError("Price cannot be negative")
    for job in data["jobs"]:
        if type(job.get("required_cpus")) is not int or job["required_cpus"] <= 0:
            raise ValueError("required_cpus must be a positive integer")
        if decimal(job.get("duration_h")) <= 0 or decimal(job.get("deadline_h")) < 0:
            raise ValueError("Invalid duration or deadline")
        locations = job.get("allowed_locations")
        if not isinstance(locations, list) or any(
            not isinstance(pair, list)
            or len(pair) != 2
            or any(not isinstance(part, str) or not part for part in pair)
            for pair in locations
        ):
            raise ValueError("allowed_locations must contain [provider, region] pairs")


def validate_plan(data, plan, *, require_complete=True):
    validate_input(data)
    if not isinstance(plan, list):
        return ["plan_format"], 0, Decimal(0)
    jobs = {job["id"]: job for job in data["jobs"]}
    resources = {resource["id"]: resource for resource in data["offerings"]}
    errors, used, seen = [], Counter(), Counter()
    total, placed = Decimal(0), 0
    for entry in plan:
        if not isinstance(entry, dict) or not isinstance(entry.get("job_id"), str):
            errors.append("plan_format")
            continue
        jid = entry["job_id"]
        seen[jid] += 1
        if jid not in jobs:
            errors.append("unknown_job")
            continue
        rid = entry.get("offering_id")
        if rid is None:
            errors.append("unassigned")
            continue
        if not isinstance(rid, str) or rid not in resources:
            errors.append("unknown_offering")
            continue
        job, resource = jobs[jid], resources[rid]
        used[rid] += 1
        placed += 1
        if resource["cpus"] < job["required_cpus"]:
            errors.append("cpu")
        if [resource["provider"], resource["region"]] not in job["allowed_locations"]:
            errors.append("region")
        if decimal(job["duration_h"]) > decimal(job["deadline_h"]):
            errors.append("deadline")
        cost = decimal(resource["price_usd_h"]) * decimal(job["duration_h"])
        total += cost
        try:
            if abs(decimal(entry.get("cost_usd")) - cost) > Decimal("0.000001"):
                errors.append("cost")
        except ValueError:
            errors.append("cost")
    if (require_complete and set(seen) != set(jobs)) or any(count != 1 for count in seen.values()):
        errors.append("job_coverage")
    if any(count > resources[rid]["capacity"] for rid, count in used.items()):
        errors.append("capacity")
    return sorted(set(errors)), placed, total
