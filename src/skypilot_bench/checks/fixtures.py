"""Shared inputs for the original ILP, patched ILP and enumeration."""

import json
from copy import deepcopy
from dataclasses import dataclass

from skypilot_bench.checks.paths import DATA


@dataclass
class Case:
    name: str
    data: dict


def small_cases():
    original = json.loads((DATA / "smoke.json").read_text())
    enough = deepcopy(original)
    enough["offerings"][0]["capacity"] = 2
    split = deepcopy(original)
    split["jobs"][0]["allowed_locations"] = [["B", "west"]]
    return [
        Case("capacity_gap", original),
        Case("enough_capacity", enough),
        Case("region_split", split),
    ]


def large_cases():
    original = json.loads((DATA / "capacity-six-jobs.json").read_text())
    reordered = deepcopy(original)
    reordered["jobs"] = [reordered["jobs"][i] for i in (0, 5, 1, 2, 3, 4)]
    bottleneck = deepcopy(original)
    for resource in bottleneck["offerings"]:
        if resource["cpus"] == 4:
            resource["capacity"] = 3
    bottleneck["jobs"].append(
        {
            "id": "flexible_large",
            "required_cpus": 8,
            "duration_h": "1",
            "deadline_h": "1",
            "allowed_locations": [["A", "east"], ["B", "west"]],
        }
    )
    repaired = deepcopy(bottleneck)
    repaired["offerings"][1]["capacity"] = 2
    return [
        Case("six_jobs_cost", original),
        Case("six_jobs_greedy_blocked", reordered),
        Case("seven_jobs_cpu_bottleneck", bottleneck),
        Case("seven_jobs_extra_large_machine", repaired),
    ]


def original_cases():
    large = large_cases()
    return small_cases() + [large[i] for i in (0, 2, 3)]


def capacity_cases():
    cases = small_cases() + large_cases()
    original = cases[0].data
    for name in (
        "zero_capacity",
        "no_candidate",
        "impossible_deadline",
        "zero_cost",
        "colliding_names",
    ):
        data = deepcopy(original)
        if name == "zero_capacity":
            for resource in data["offerings"]:
                resource["capacity"] = 0
        elif name == "no_candidate":
            data["jobs"][0]["required_cpus"] = 32
        elif name == "impossible_deadline":
            data["jobs"][0]["deadline_h"] = "0.5"
        elif name == "zero_cost":
            for resource in data["offerings"]:
                resource["price_usd_h"] = "0"
        else:
            data["jobs"][0]["id"], data["jobs"][1]["id"] = "job-a", "job_a"
        cases.append(Case(name, data))
    expensive = deepcopy(original)
    expensive["offerings"][0]["capacity"] = 0
    expensive["offerings"][1]["price_usd_h"] = "1000000"
    for job in expensive["jobs"]:
        job["allowed_locations"] = [["B", "west"]]
    expensive["jobs"][0]["duration_h"] = expensive["jobs"][0]["deadline_h"] = "2"
    cases.append(Case("count_before_cost", expensive))
    cases.append(Case("empty_input", {"jobs": [], "offerings": []}))
    return cases
