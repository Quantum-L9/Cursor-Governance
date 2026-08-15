from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_SUBSYSTEM = Path(__file__).resolve().parents[3]
if str(_SUBSYSTEM) not in sys.path:
    sys.path.insert(0, str(_SUBSYSTEM))


def _load_provider():
    path = Path(__file__).resolve().parents[1] / "provider.py"
    spec = importlib.util.spec_from_file_location("chatgpt_provider_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChatGPTProviderTests(unittest.TestCase):
    def test_missing_host_status_is_blocked_not_pass(self) -> None:
        module = _load_provider()
        with tempfile.TemporaryDirectory() as raw:
            provider = module.ChatGPTManualHandoffProvider(raw, raw)
            execution_id = "exec-missing"
            handoff = Path(raw) / "chatgpt-handoffs"
            handoff.mkdir(parents=True, exist_ok=True)
            (handoff / f"{execution_id}.result.json").write_text(
                json.dumps({"artifact": True}) + "\n",
                encoding="utf-8",
            )
            request = SimpleNamespace(execution_id=execution_id)
            collector = SimpleNamespace(
                collect_returned_artifact=lambda path, envelope: {"artifact": True}
            )
            with patch.object(module, "load_module", return_value=collector):
                invocation = provider.poll(
                    request,
                    {"envelope": {"task_id": "TASK-001"}},
                )
        self.assertEqual(invocation.status, "BLOCKED")
        self.assertEqual(invocation.result.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
