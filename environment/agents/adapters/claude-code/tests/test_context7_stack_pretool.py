from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "context7_stack_pretool.py"


def _load():
    spec = importlib.util.spec_from_file_location("context7_stack_pretool_test", HOOK)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load hook")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context7StackPretoolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load()

    def test_denies_seed_edit_without_proof(self) -> None:
        payload = {
            "tool_name": "Edit",
            "session_id": "sess-none",
            "tool_input": {"file_path": "CAMPAIGN_SOURCE.yaml", "new_string": "x"},
        }
        blob = self.mod._payload_paths(payload)
        self.assertTrue(self.mod.STACK_NAME_RE.search(blob))
        self.assertFalse(self.mod._session_called_context7("sess-none"))

    def test_deny_reason_names_skill_fallback(self) -> None:
        src = HOOK.read_text(encoding="utf-8")
        self.assertIn("l9-context7-docs", src)
        self.assertIn("when those tools exist", src)

    def test_allows_when_receipt_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primed = Path(raw) / "primed" / "demo" / "stack-proof.json"
            primed.parent.mkdir(parents=True)
            primed.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
            import os

            os.environ["L9_ROOT"] = raw
            self.addCleanup(lambda: os.environ.pop("L9_ROOT", None))
            self.assertTrue(self.mod._pass_receipt_exists())


if __name__ == "__main__":
    unittest.main()
