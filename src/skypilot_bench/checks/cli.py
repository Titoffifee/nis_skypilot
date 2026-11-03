import argparse
import importlib.metadata
import json
import platform
from contextlib import nullcontext
from pathlib import Path

from skypilot_bench.checks.paths import SOURCE
from skypilot_bench.runtime import offline_environment


def environment():
    packages = {}
    for name in ("skypilot", "pulp", "networkx"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return {
        "os": platform.system(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "packages": packages,
    }


def write_report(report, output):
    rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered)
    print(rendered, end="")


def execute(name, check, *, source=False, offline=False, profile=False, argv=None):
    parser = argparse.ArgumentParser(description=check.__doc__)
    parser.add_argument("--output", type=Path)
    if source:
        parser.add_argument("--source", type=Path, default=SOURCE)
    if profile:
        parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args(argv)
    report = {"check": name, "environment": environment()}
    try:
        with offline_environment() if offline else nullcontext():
            report.update(check(args))
        report["status"] = "passed"
    except Exception as exc:
        report.update(status="failed", reason=f"{type(exc).__name__}: {exc}")
    write_report(report, args.output)
    return 0 if report["status"] == "passed" else 1
