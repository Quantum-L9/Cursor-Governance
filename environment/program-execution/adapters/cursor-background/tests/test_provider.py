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


if __name__ == "__main__":
    unittest.main()
