"""Temporary state and network isolation for offline checks."""

import os
import socket
import tempfile
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


def deny_network(*args, **kwargs):
    raise RuntimeError("Network access is disabled during offline checks")


@contextmanager
def offline_environment():
    original_expanduser = os.path.expanduser
    with tempfile.TemporaryDirectory(prefix="p17-sky-state-") as directory, ExitStack() as stack:

        def expanduser(path):
            value = os.fspath(path)
            decoded = os.fsdecode(value)
            if decoded == "~" or decoded.startswith("~/"):
                result = str(Path(directory) / decoded[2:]) if decoded != "~" else directory
                return os.fsencode(result) if isinstance(value, bytes) else result
            return original_expanduser(value)

        stack.enter_context(patch("os.path.expanduser", expanduser))
        stack.enter_context(patch.dict(os.environ, {"SKYPILOT_DISABLE_USAGE_COLLECTION": "1"}))
        for owner, name in (
            (socket, "create_connection"),
            (socket, "getaddrinfo"),
            (socket.socket, "connect"),
            (socket.socket, "connect_ex"),
        ):
            stack.enter_context(patch.object(owner, name, deny_network))
        yield
