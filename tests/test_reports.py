import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from skypilot_bench.checks.cli import execute


class ReportTests(unittest.TestCase):
    def test_failed_check_writes_failed_report_to_new_directory(self):
        def fail(args):
            raise ValueError("broken input")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new/result.json"
            with redirect_stdout(io.StringIO()):
                code = execute("example", fail, argv=["--output", str(output)])
            report = json.loads(output.read_text())
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertIn("broken input", report["reason"])
        self.assertIn("os", report["environment"])
