import os
import random
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from skypilot_bench.adapter import load_capacity_optimizer
from skypilot_bench.author import installed_optimizer
from skypilot_bench.checks.fixtures import small_cases
from skypilot_bench.checks.paths import SOURCE
from skypilot_bench.model import validate_plan
from skypilot_bench.oracle import enumerate_plans
from skypilot_bench.runtime import offline_environment
from skypilot_bench.sky_bridge import build_problem


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        context = offline_environment()
        context.__enter__()
        cls.addClassCleanup(context.__exit__, None, None, None)
        cls.source = Path(os.environ.get("SKYPILOT_BENCH_SOURCE", SOURCE)).resolve()
        cls.optimizer, _ = load_capacity_optimizer(cls.source)

    def setUp(self):
        self.problem = build_problem(small_cases()[0].data)

    def solve(self, **kwargs):
        return self.optimizer._optimize_by_ilp(
            *self.problem.arguments, resource_capacities=self.problem.capacities, **kwargs
        )

    def test_unproven_incumbent_is_not_optimal(self):
        import pulp

        real_solve = pulp.LpProblem.solve

        def incumbent(problem, *args, **kwargs):
            result = real_solve(problem, *args, **kwargs)
            problem.sol_status = pulp.LpSolutionIntegerFeasible
            return result

        with patch.object(pulp.LpProblem, "solve", incumbent):
            best, _, status = self.solve()
        self.assertEqual(status, "feasible")
        self.assertIsNotNone(best)

    def test_unknown_clears_previous_plan(self):
        import pulp

        self.assertEqual(self.solve()[2], "optimal")

        def unknown(problem, *args, **kwargs):
            problem.status = pulp.LpStatusNotSolved
            problem.sol_status = pulp.LpSolutionNoSolutionFound

        with patch.object(pulp.LpProblem, "solve", unknown):
            self.assertEqual(self.solve(), (None, None, "unknown"))
        self.assertTrue(all(node.best_resources is None for node in self.problem.nodes))

    def test_missing_capacity_is_an_input_error(self):
        self.problem.capacities.pop(next(iter(self.problem.capacities)))
        with self.assertRaisesRegex(ValueError, "Missing capacity"):
            self.solve()

    def test_nonfinite_time_limit_is_rejected(self):
        for limit in (float("nan"), float("inf"), -1, 0, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.solve(time_limit=limit)

    def test_plan_rejects_missing_and_extra_assignments(self):
        best, _, _ = self.solve()
        incomplete = dict(best)
        incomplete.pop(self.problem.nodes[0])
        for assignments in (None, incomplete, {**best, object(): next(iter(best.values()))}):
            with (
                self.subTest(assignments=assignments),
                self.assertRaises(ValueError),
            ):
                self.problem.plan(assignments)

    def test_problem_keeps_its_input_snapshot(self):
        data = small_cases()[0].data
        self.problem = build_problem(data)
        data["jobs"][0]["id"] = "changed"
        data["jobs"][0]["duration_h"] = "100"
        data["offerings"][1]["price_usd_h"] = "100"
        best, objective, status = self.solve()
        plan = self.problem.plan(best)
        self.assertEqual(status, "optimal")
        self.assertAlmostEqual(objective, 1.7)
        self.assertEqual(plan[0]["job_id"], "flexible")
        self.assertEqual(plan[0]["cost_usd"], "1.00")

    def test_dependency_from_another_checkout_is_rejected(self):
        from sky import optimizer

        with patch.object(optimizer, "__file__", "/tmp/other-checkout/sky/optimizer.py"):
            with self.assertRaisesRegex(ValueError, "does not match"):
                installed_optimizer(self.source)

    def test_second_timeout_preserves_first_plan(self):
        import pulp

        real_solve = pulp.LpProblem.solve
        calls = []

        def timeout_second(model, *args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                return real_solve(model, *args, **kwargs)
            model.status = pulp.LpStatusNotSolved
            model.sol_status = pulp.LpSolutionNoSolutionFound
            for variable in model.variables():
                variable.varValue = None

        with patch.object(pulp.LpProblem, "solve", timeout_second):
            best, cost, status = self.solve()
        self.assertEqual(len(calls), 2)
        self.assertEqual(status, "feasible")
        self.assertAlmostEqual(cost, 1.7)
        self.assertEqual(validate_plan(self.problem.data, self.problem.plan(best))[0], [])

    def test_stages_share_one_time_budget(self):
        import pulp

        real_solve = pulp.LpProblem.solve
        limits = []

        def record_limit(model, *args, **kwargs):
            limits.append(kwargs["solver"].timeLimit)
            result = real_solve(model, *args, **kwargs)
            time.sleep(0.02)
            return result

        with patch.object(pulp.LpProblem, "solve", record_limit):
            self.assertEqual(self.solve(time_limit=10)[2], "optimal")
        self.assertEqual(len(limits), 2)
        self.assertLess(limits[0], 10)
        self.assertLess(limits[1], limits[0] - 0.01)

    def test_random_partial_plans_match_enumeration(self):
        for seed in range(30):
            rng = random.Random(seed)
            data = {
                "offerings": [
                    {
                        "id": f"r{i}",
                        "provider": "A",
                        "region": "east",
                        "instance_type": f"type{i}",
                        "cpus": rng.choice([2, 4, 8]),
                        "capacity": rng.randrange(3),
                        "price_usd_h": str(rng.randrange(5)),
                    }
                    for i in range(rng.randrange(5))
                ],
                "jobs": [
                    {
                        "id": f"j{i}",
                        "required_cpus": rng.choice([2, 4, 8]),
                        "duration_h": str(rng.randrange(1, 4)),
                        "deadline_h": "3",
                        "allowed_locations": [["A", "east"]] if rng.random() > 0.2 else [],
                    }
                    for i in range(rng.randrange(6))
                ],
            }
            with self.subTest(seed=seed):
                self.problem = build_problem(data)
                best, cost, status = self.solve()
                plan = self.problem.plan(best, allow_partial=True)
                errors, placed, total = validate_plan(data, plan, require_complete=False)
                expected = min(
                    (-len(p), sum(Decimal(row["cost_usd"]) for row in p))
                    for p in enumerate_plans(data, allow_partial=True)
                )
                self.assertEqual(status, "optimal")
                self.assertEqual(errors, [])
                self.assertEqual((-placed, total), expected)
                self.assertAlmostEqual(cost, float(total))
