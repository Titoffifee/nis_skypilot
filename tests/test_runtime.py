import os
import socket
import unittest
from pathlib import Path

from skypilot_bench.runtime import offline_environment


class RuntimeTests(unittest.TestCase):
    def test_network_and_paths_are_restored_after_error(self):
        original = (
            socket.getaddrinfo,
            socket.create_connection,
            socket.socket.connect,
            socket.socket.connect_ex,
            os.path.expanduser,
        )
        with self.assertRaisesRegex(ValueError, "test exit"):
            with offline_environment():
                temporary = Path.home()
                self.assertTrue(temporary.is_dir())
                with self.assertRaisesRegex(RuntimeError, "Network access"):
                    socket.getaddrinfo("example.com", 443)
                raise ValueError("test exit")
        self.assertEqual(
            original,
            (
                socket.getaddrinfo,
                socket.create_connection,
                socket.socket.connect,
                socket.socket.connect_ex,
                os.path.expanduser,
            ),
        )
        self.assertFalse(temporary.exists())

    def test_nested_context_restores_outer_state(self):
        with offline_environment():
            outer = Path.home()
            with offline_environment():
                self.assertNotEqual(Path.home(), outer)
            self.assertEqual(Path.home(), outer)
