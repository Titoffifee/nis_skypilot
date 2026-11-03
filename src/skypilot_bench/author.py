"""Read the pinned optimizer and check the installed SkyPilot checkout."""

import ast
import collections
import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

REVISION = "fff7b16adc0cad0626afbbcfa469d4704978d4e8"


def git(source, *args):
    return subprocess.check_output(
        ["git", "-C", str(source), *args], stderr=subprocess.PIPE, timeout=30
    )


def read_optimizer(source):
    source = Path(source).resolve()
    revision = git(source, "rev-parse", "HEAD").decode().strip()
    if revision != REVISION:
        raise ValueError(f"Expected SkyPilot {REVISION}, got {revision}")
    if git(source, "diff", "HEAD", "--", "sky").strip():
        raise ValueError("SkyPilot checkout contains modified source files")
    if git(source, "ls-files", "--others", "--exclude-standard", "--", "sky").strip():
        raise ValueError("SkyPilot checkout contains untracked source files")
    raw = (source / "sky/optimizer.py").read_bytes()
    if raw != git(source, "show", "HEAD:sky/optimizer.py"):
        raise ValueError("optimizer.py differs from the pinned commit")
    return raw, {"source_commit": revision, "optimizer_sha256": hashlib.sha256(raw).hexdigest()}


def extract_methods(source, names):
    raw, metadata = read_optimizer(source)
    path = Path(source) / "sky/optimizer.py"
    tree = ast.parse(raw)
    cls = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Optimizer"
    )
    methods = [
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    if {node.name for node in methods} != set(names):
        raise ValueError("Requested optimizer method is missing")
    module = ast.Module(
        body=[
            ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
            ast.ClassDef(name="Optimizer", bases=[], keywords=[], body=methods, decorator_list=[]),
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace = {
        "collections": collections,
        "np": SimpleNamespace(inf=float("inf")),
        "_DUMMY_SOURCE_NAME": "skypilot-dummy-source",
    }
    exec(compile(module, str(path), "exec"), namespace)
    metadata["author_methods"] = {node.name: node.lineno for node in methods}
    return namespace["Optimizer"], metadata


def installed_optimizer(source):
    _, metadata = read_optimizer(source)
    import pulp
    from sky import optimizer

    expected = Path(source).resolve() / "sky/optimizer.py"
    if Path(optimizer.__file__).resolve() != expected:
        raise ValueError("Installed SkyPilot does not match --source")
    if not hasattr(pulp, "PULP_CBC_CMD") or not pulp.PULP_CBC_CMD(msg=False).available():
        raise RuntimeError("CBC is unavailable; install requirements-skypilot.txt")
    return optimizer.Optimizer, metadata
