import unittest

from skypilot_bench.checks.fixtures import small_cases
from skypilot_bench.metrics import evaluate_plan
from skypilot_bench.oracle import enumerate_plans


class MetricsTests(unittest.TestCase):
    def test_partial_cost_and_rate(self):
        data = small_cases()[0].data
        plan = next(enumerate_plans(data))[:1]
        metrics = evaluate_plan(data, plan)
        self.assertEqual(metrics["placed"], 1)
        self.assertEqual(metrics["placement_rate"], 0.5)
        self.assertFalse(metrics["complete"])
        self.assertEqual(metrics["cost_usd"], plan[0]["cost_usd"])
        with self.assertRaises(ValueError):
            evaluate_plan(data, plan * 2)

    def test_empty_input_has_no_task_rate(self):
        metrics = evaluate_plan({"jobs": [], "offerings": []}, [])
        self.assertTrue(metrics["complete"])
        self.assertIsNone(metrics["placement_rate"])
        self.assertEqual(metrics["cost_usd"], "0")
