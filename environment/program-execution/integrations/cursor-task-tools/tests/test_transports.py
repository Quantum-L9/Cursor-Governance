from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.common.imports import load_module


class CursorTaskTransportTests(unittest.TestCase):
    def _module(self, name: str):
        root = Path(__file__).resolve().parents[1]
        return load_module(root / f"{name}.py", f"pes_test_{name}")

    def test_foreground_request_is_durable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            module = self._module("foreground_transport")
            transport = module.ForegroundTransport(directory)
            path = transport.dispatch("dispatch-1", {"task": "TASK-1"})
            self.assertEqual(json.loads(path.read_text())["task"], "TASK-1")

    def test_background_cancel_requires_live_handle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            module = self._module("background_transport")
            transport = module.BackgroundTransport(directory)
            self.assertFalse(transport.cancel("dispatch-1"))


if __name__ == "__main__":
    unittest.main()
