"""Measure fresh processes running the original ILP checks."""

import json
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from skypilot_bench.checks.paths import ROOT

from . import require
from .cli import execute


def run(args):
    require(args.repeats > 0, "repeats must be positive")
    system = platform.system()
    if system not in ("Darwin", "Linux"):
        raise ValueError("Profiling is supported on Linux and macOS")
    rows = []
    for repeat in range(args.repeats):
        with tempfile.TemporaryDirectory(prefix="p17-profile-") as directory:
            metrics = Path(directory) / "time.json"
            check = [
                sys.executable,
                "-m",
                "skypilot_bench.checks.native",
                "--source",
                str(args.source.resolve()),
            ]
            if system == "Darwin":
                command = ["/usr/bin/time", "-l", *check]
            else:
                command = ["/usr/bin/time", "-f", '{"max_rss_kib": %M}', "-o", str(metrics), *check]
            started = time.perf_counter()
            process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
            seconds = time.perf_counter() - started
            require(process.returncode == 0, f"Profile failed: {process.stderr}\n{process.stdout}")
            result = json.loads(process.stdout)
            require(result["status"] == "passed", "Native checks failed")
            if system == "Darwin":
                rss = re.search(r"(\d+)\s+maximum resident set size", process.stderr)
                require(rss is not None, "Missing RSS measurement")
                rss_kib = int(rss.group(1)) / 1024
            else:
                rss_kib = json.loads(metrics.read_text())["max_rss_kib"]
            rows.append(
                {
                    "repeat": repeat,
                    "wall_seconds": seconds,
                    "max_rss_kib": rss_kib,
                    "check_status": result["status"],
                    "case_count": len(result["cases"]),
                }
            )
    return {
        "runs": rows,
        "summary": {
            "median_wall_seconds": statistics.median(row["wall_seconds"] for row in rows),
            "min_wall_seconds": min(row["wall_seconds"] for row in rows),
            "max_wall_seconds": max(row["wall_seconds"] for row in rows),
            "max_rss_kib": max(row["max_rss_kib"] for row in rows),
        },
        "scope": "Import and six original ILP cases in each process",
        "memory_scope": "Peak RSS reported by time, normalized to KiB; not aggregate process-tree memory",
    }


def main():
    return execute("profile", run, source=True, profile=True)


if __name__ == "__main__":
    raise SystemExit(main())
