import unittest

from skypilot_bench.checks.fixtures import large_cases, small_cases
from skypilot_bench.greedy import place
from skypilot_bench.metrics import evaluate_plan
from skypilot_bench.model import validate_plan
from skypilot_bench.oracle import enumerate_plans


class GreedyTests(unittest.TestCase):
    def test_unplaceable_task_does_not_stop_later_assignments(self):
        data = large_cases()[1].data
        result = place(data)
        self.assertEqual(result["status"], "feasible")
        metrics = evaluate_plan(data, result["plan"])
        self.assertEqual(metrics["placed"], 5)
        self.assertFalse(metrics["complete"])
        self.assertEqual(metrics["placement_rate"], 5 / 6)
        self.assertEqual(validate_plan(data, result["plan"], require_complete=False)[0], [])
        self.assertIn("job_coverage", validate_plan(data, result["plan"])[0])
        self.assertIsNotNone(next(enumerate_plans(data), None))

    def test_equal_prices_do_not_depend_on_catalog_order(self):
        data = small_cases()[1].data
        for resource in data["offerings"]:
            resource["price_usd_h"] = "1"
        first = place(data)
        data["offerings"].reverse()
        self.assertEqual(place(data), first)
        self.assertEqual(first["status"], "feasible")
        self.assertEqual(validate_plan(data, first["plan"])[0], [])
