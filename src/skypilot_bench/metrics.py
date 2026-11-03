"""Measure a validated placement, including a partial one."""

from .model import validate_plan


def evaluate_plan(data, plan):
    errors, placed, cost = validate_plan(data, plan, require_complete=False)
    if errors:
        raise ValueError(f"Invalid plan: {', '.join(errors)}")
    total = len(data["jobs"])
    return {
        "placed": placed,
        "total_jobs": total,
        "placement_rate": placed / total if total else None,
        "complete": placed == total,
        "cost_usd": str(cost),
    }
