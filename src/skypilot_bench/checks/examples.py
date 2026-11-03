"""Compare enumeration and Greedy on the larger examples."""

from decimal import Decimal

from skypilot_bench.greedy import place
from skypilot_bench.metrics import evaluate_plan
from skypilot_bench.oracle import enumerate_plans

from . import require
from .cli import execute
from .fixtures import large_cases


def run(args):
    rows = []
    for case in large_cases():
        best = min(
            enumerate_plans(case.data, allow_partial=True),
            key=lambda plan: (-len(plan), sum(Decimal(row["cost_usd"]) for row in plan)),
        )
        oracle = evaluate_plan(case.data, best)
        greedy = place(case.data)
        greedy.update(evaluate_plan(case.data, greedy["plan"]))
        require(oracle["placed"] >= greedy["placed"], "Greedy exceeds exhaustive optimum")
        if oracle["placed"] == greedy["placed"]:
            require(Decimal(oracle["cost_usd"]) <= Decimal(greedy["cost_usd"]), "Wrong optimum")
        rows.append({"case": case.name, "oracle": {**oracle, "plan": best}, "greedy": greedy})
    require(Decimal(rows[0]["greedy"]["cost_usd"]) == Decimal("10.50"), "Wrong greedy cost")
    require(
        rows[1]["oracle"]["placed"] == 6 and rows[1]["greedy"]["placed"] == 5,
        "Unexpected placement after reordering",
    )
    require(rows[2]["oracle"]["placed"] == 6, "Expected six of seven tasks")
    return {"cases": rows}


def main():
    return execute("examples", run)


if __name__ == "__main__":
    raise SystemExit(main())
