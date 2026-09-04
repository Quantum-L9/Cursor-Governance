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

    # ---------------------------------------------------------------- SA-F11

    def _background(self, directory: str):
        module = self._module("background_transport")
        transport = module.BackgroundTransport(directory)
        transport.dispatch(
            "dispatch-1",
            {
                "dispatch_id": "dispatch-1",
                "canonical_execution_request": {"rendered_contract_digest": "sha256:" + "a" * 64},
            },
        )
        return transport

    @staticmethod
    def _write(transport, name: str, body: dict) -> None:
        (transport.root / name).write_text(json.dumps(body) + "\n", encoding="utf-8")

    def test_cancellation_outranks_a_later_result_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transport = self._background(directory)
            self._write(transport, "dispatch-1.cancelled.json", {"terminated": True})
            self._write(
                transport,
                "dispatch-1.result.json",
                {
                    "status": "PASS",
                    "dispatch_id": "dispatch-1",
                    "rendered_contract_digest": "sha256:" + "a" * 64,
                },
            )
            self.assertEqual(transport.status("dispatch-1"), "CANCELLED")
            collected = transport.collect("dispatch-1")
            self.assertEqual(collected["status"], "BLOCKED")
            self.assertEqual(collected["evidence"]["type"], "cursor_task_cancelled")

    def test_result_must_echo_dispatch_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transport = self._background(directory)
            self._write(transport, "dispatch-1.result.json", {"status": "PASS"})
            self.assertEqual(transport.status("dispatch-1"), "BLOCKED")
            collected = transport.collect("dispatch-1")
            self.assertEqual(collected["status"], "BLOCKED")
            self.assertIn("dispatch_id", collected["reason"])
            self.assertEqual(collected["evidence"]["type"], "cursor_task_result_unbound")
            self.assertEqual(collected["unbound_result"], {"status": "PASS"})

    def test_result_must_echo_rendered_contract_digest_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transport = self._background(directory)
            self._write(
                transport,
                "dispatch-1.result.json",
                {
                    "status": "PASS",
                    "dispatch_id": "dispatch-1",
                    "rendered_contract_digest": "sha256:" + "b" * 64,
                },
            )
            self.assertEqual(transport.status("dispatch-1"), "BLOCKED")
            self.assertIn("rendered_contract_digest", transport.collect("dispatch-1")["reason"])

    def test_bound_result_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transport = self._background(directory)
            body = {
                "status": "PASS",
                "dispatch_id": "dispatch-1",
                "rendered_contract_digest": "sha256:" + "a" * 64,
            }
            self._write(transport, "dispatch-1.result.json", body)
            self.assertEqual(transport.status("dispatch-1"), "PASS")
            self.assertEqual(transport.collect("dispatch-1"), body)
            self.assertIsNone(transport.binding_error("dispatch-1"))

    def test_result_without_a_dispatch_request_is_not_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            module = self._module("background_transport")
            transport = module.BackgroundTransport(directory)
            self._write(
                transport, "dispatch-9.result.json", {"status": "PASS", "dispatch_id": "dispatch-9"}
            )
            self.assertEqual(transport.status("dispatch-9"), "BLOCKED")
            self.assertIn("no dispatch request", transport.collect("dispatch-9")["reason"])


if __name__ == "__main__":
    unittest.main()
