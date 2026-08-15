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
    spec = importlib.util.spec_from_file_location("cursor_fg_provider_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CursorForegroundProviderTests(unittest.TestCase):
    def test_descriptor_exists(self) -> None:
        self.assertTrue((Path(__file__).resolve().parents[1] / "ADAPTER.yaml").is_file())

    def test_file_drop_probe_is_blocked(self) -> None:
        module = _load_provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as raw:
            provider = module.CursorForegroundProvider(raw, repo_root)
            probe = provider.probe(None)
        self.assertEqual(probe.status, "BLOCKED")
        self.assertIn("file-drop", probe.blocked_reason)

    def test_missing_host_status_is_blocked_not_pass(self) -> None:
        module = _load_provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as raw:
            provider = module.CursorForegroundProvider(raw, repo_root)
            execution_id = "exec-missing-status"
            result_dir = Path(raw) / "cursor-tasks" / "foreground"
            result_dir.mkdir(parents=True, exist_ok=True)
            (result_dir / f"{execution_id}.result.json").write_text(
                json.dumps({"changed_files": []}) + "\n",
                encoding="utf-8",
            )
            request = SimpleNamespace(execution_id=execution_id)
            invocation = provider.poll(request, {})
        self.assertEqual(invocation.status, "BLOCKED")
        self.assertIsNotNone(invocation.result)
        self.assertEqual(invocation.result.status, "BLOCKED")

    def test_explicit_pass_status_is_preserved(self) -> None:
        module = _load_provider()
        repo_root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as raw:
            provider = module.CursorForegroundProvider(raw, repo_root)
            execution_id = "exec-pass"
            result_dir = Path(raw) / "cursor-tasks" / "foreground"
            result_dir.mkdir(parents=True, exist_ok=True)
            (result_dir / f"{execution_id}.result.json").write_text(
                json.dumps({"status": "PASS", "changed_files": []}) + "\n",
                encoding="utf-8",
            )
            request = SimpleNamespace(execution_id=execution_id)
            invocation = provider.poll(request, {})
        self.assertEqual(invocation.status, "PASS")
        self.assertEqual(invocation.result.status, "PASS")


if __name__ == "__main__":
    unittest.main()
