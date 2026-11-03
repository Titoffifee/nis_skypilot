import unittest
from copy import deepcopy

from skypilot_bench.checks.fixtures import small_cases
from skypilot_bench.model import validate_input, validate_plan
from skypilot_bench.oracle import enumerate_plans


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.data = small_cases()[0].data

    def test_duplicate_ids_are_rejected(self):
        for group in ("jobs", "offerings"):
            with self.subTest(group=group):
                data = deepcopy(self.data)
                data[group].append(deepcopy(data[group][0]))
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    list(enumerate_plans(data))

    def test_invalid_numbers_are_rejected(self):
        for value in ("NaN", "Infinity", "-1", True, None):
            with self.subTest(value=value):
                data = deepcopy(self.data)
                data["offerings"][0]["price_usd_h"] = value
                with self.assertRaises(ValueError):
                    validate_input(data)

    def test_invalid_capacity_is_rejected(self):
        for value in (-1, True, 0.5, "1"):
            with self.subTest(value=value):
                data = deepcopy(self.data)
                data["offerings"][0]["capacity"] = value
                with self.assertRaises(ValueError):
                    validate_input(data)

    def test_missing_field_is_rejected(self):
        del self.data["jobs"][0]["duration_h"]
        with self.assertRaises(ValueError):
            validate_input(self.data)

    def test_malformed_plan_is_rejected(self):
        self.assertIn("plan_format", validate_plan(self.data, [None])[0])
        self.assertIn("plan_format", validate_plan(self.data, None)[0])

    def test_nan_plan_cost_is_rejected(self):
        plan = next(enumerate_plans(self.data))
        plan[0]["cost_usd"] = "NaN"
        self.assertIn("cost", validate_plan(self.data, plan)[0])

    def test_unknown_job_is_rejected(self):
        plan = next(enumerate_plans(self.data))
        plan[0]["job_id"] = "missing"
        errors, _, _ = validate_plan(self.data, plan)
        self.assertIn("unknown_job", errors)
        self.assertIn("job_coverage", errors)

    def test_empty_input_has_one_empty_plan(self):
        data = {"jobs": [], "offerings": []}
        self.assertEqual(list(enumerate_plans(data)), [[]])
        self.assertEqual(validate_plan(data, []), ([], 0, 0))

    def test_partial_validation_allows_missing_jobs_but_not_duplicates(self):
        plan = next(enumerate_plans(self.data))[:1]
        self.assertEqual(validate_plan(self.data, plan, require_complete=False)[0], [])
        self.assertIn("job_coverage", validate_plan(self.data, plan)[0])
        self.assertIn("job_coverage", validate_plan(self.data, plan * 2, require_complete=False)[0])

    def test_partial_enumeration_includes_empty_and_full_plans(self):
        plans = list(enumerate_plans(self.data, allow_partial=True))
        self.assertIn([], plans)
        self.assertEqual(max(map(len, plans)), 2)
        for plan in plans:
            self.assertEqual(validate_plan(self.data, plan, require_complete=False)[0], [])
