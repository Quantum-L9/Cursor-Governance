from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import (
    bootstrap_repo,
    register_contract,
    run_cli,
    source_contract,
    write_json,
)


class SourceContractPlaceholderTest(unittest.TestCase):
    def test_register_rejects_replace_with_rollback(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            payload = source_contract()
            payload["rollback"] = "REPLACE_WITH_EXACT_ROLLBACK_OR_RECOVERY"
            path = write_json(temp / "bad.source.json", payload)
            result = run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(path),
                "--actor",
                "operator",
                expect=2,
            )
            self.assertIn("REPLACE_WITH", result["error"])

    def test_register_accepts_concrete_rollback(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)

    def test_draft_then_register_without_hand_edit(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            draft = temp / "TASK-001.source.json"
            run_cli(
                "draft-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--output",
                str(draft),
            )
            payload = json.loads(draft.read_text(encoding="utf-8"))
            self.assertNotIn("REPLACE_WITH", payload["rollback"])
            self.assertTrue(payload["writable_paths"])
            result = run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(draft),
                "--actor",
                "operator",
            )
            self.assertEqual(result["status"], "REGISTERED")

    def test_draft_fails_when_rollback_missing(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            lock_path = workspace / "runtime" / "program-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            for task in lock.get("tasks") or []:
                source = task.get("source") or {}
                source.pop("rollback", None)
                task["source"] = source
            lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
            draft = temp / "bad.draft.json"
            result = run_cli(
                "draft-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--output",
                str(draft),
                expect=2,
            )
            self.assertIn("DEFINITION_INVALID", result["error"])
            self.assertFalse(draft.is_file())


if __name__ == "__main__":
    unittest.main()
