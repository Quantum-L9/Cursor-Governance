from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_SUBSYSTEM = Path(__file__).resolve().parents[3]
if str(_SUBSYSTEM) not in sys.path:
    sys.path.insert(0, str(_SUBSYSTEM))


def _load_provider():
    path = Path(__file__).resolve().parents[1] / "provider.py"
    spec = importlib.util.spec_from_file_location("cursor_bg_provider_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CursorBackgroundProviderTests(unittest.TestCase):
    def test_file_drop_probe_is_blocked(self) -> None:
        module = _load_provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as raw:
            provider = module.CursorBackgroundProvider(raw, repo_root)
            probe = provider.probe(None)
        self.assertEqual(probe.status, "BLOCKED")
        self.assertIn("file-drop", probe.blocked_reason)

    def test_missing_host_status_is_blocked_not_pass(self) -> None:
        module = _load_provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as raw:
            provider = module.CursorBackgroundProvider(raw, repo_root)
            execution_id = "exec-missing-status"
            result_dir = Path(raw) / "cursor-tasks" / "background"
            result_dir.mkdir(parents=True, exist_ok=True)
            (result_dir / f"{execution_id}.result.json").write_text(
                json.dumps({"changed_files": []}) + "\n",
                encoding="utf-8",
            )
            request = SimpleNamespace(execution_id=execution_id)
            invocation = provider.poll(request, {})
        self.assertEqual(invocation.status, "BLOCKED")
        self.assertEqual(invocation.result.status, "BLOCKED")

    def test_cancel_without_handle_is_unsupported(self) -> None:
        module = _load_provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as raw:
            provider = module.CursorBackgroundProvider(raw, repo_root)
            request = SimpleNamespace(execution_id="exec-no-handle")
            invocation = provider.cancel(request, {})
        self.assertEqual(invocation.status, "UNSUPPORTED")
        self.assertEqual(invocation.evidence[0]["type"], "cancellation_unsupported")

    def test_cancel_request_acceptance_is_not_terminal_cancelled(self) -> None:
        # T-004 (cursor-background): a cancel request marker alone must never
        # yield terminal CANCELLED. Only the host writing cancelled.json is
        # termination acknowledgement.
        module = _load_provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as raw:
            provider = module.CursorBackgroundProvider(raw, repo_root)
            execution_id = "exec-cancel-request"
            drop = Path(raw) / "cursor-tasks" / "background"
            drop.mkdir(parents=True, exist_ok=True)
            (drop / f"{execution_id}.handle.json").write_text(
                json.dumps({"pid": 4242}) + "\n", encoding="utf-8"
            )
            request = SimpleNamespace(execution_id=execution_id)
            invocation = provider.cancel(request, {})
            self.assertEqual(invocation.status, "RUNNING")
            self.assertEqual(invocation.evidence[0]["type"], "cancellation_requested")
            self.assertTrue((drop / f"{execution_id}.cancel.request.json").is_file())
            # The requester never synthesizes the host acknowledgement.
            self.assertFalse((drop / f"{execution_id}.cancelled.json").is_file())
            self.assertEqual(provider.transport.status(execution_id), "RUNNING")
            # Host terminates its owned process, then acknowledges.
            (drop / f"{execution_id}.cancelled.json").write_text(
                json.dumps({"terminated": True}) + "\n", encoding="utf-8"
            )
            self.assertEqual(provider.transport.status(execution_id), "CANCELLED")


if __name__ == "__main__":
    unittest.main()
