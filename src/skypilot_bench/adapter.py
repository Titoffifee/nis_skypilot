"""Apply the capacity patch without modifying the SkyPilot checkout."""

import hashlib
import importlib.util
import subprocess
import tempfile
from importlib.resources import files
from pathlib import Path

from .author import installed_optimizer


def load_capacity_optimizer(source):
    _, metadata = installed_optimizer(source)
    raw = (Path(source) / "sky/optimizer.py").read_bytes()
    patch_bytes = files("skypilot_bench").joinpath("patches/capacity.patch").read_bytes()
    with tempfile.TemporaryDirectory(prefix="p17-capacity-") as directory:
        target = Path(directory) / "sky/optimizer.py"
        target.parent.mkdir()
        target.write_bytes(raw)
        result = subprocess.run(
            ["git", "apply", "-"],
            cwd=directory,
            capture_output=True,
            input=patch_bytes,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError(f"Cannot apply capacity patch: {result.stderr.decode().strip()}")
        patched = target.read_bytes()
        spec = importlib.util.spec_from_file_location("sky_capacity_optimizer", target)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    metadata.update(
        patch_sha256=hashlib.sha256(patch_bytes).hexdigest(),
        patched_optimizer_sha256=hashlib.sha256(patched).hexdigest(),
    )
    return module.Optimizer, metadata
