"""Commit authority and kernel_profile must survive the Controller, not be invented there.

Two seams meet in `draft_source_contract`. It projected only `inspect` and
`local_write` into the Source Contract while the runner went on to create a
local commit, so every downstream surface derived commit authority from
something other than the locked task ceiling. And the Task Card carried no
`kernel_profile` at all, so an authored CHANGE or AUDIT reached the Rendered
Contract as BUILD by way of a default nobody chose.

These tests read the artifacts the Controller actually writes -- the Program
Lock, the draft Source Contract, the Rendered Contract -- rather than
re-deriving the projection in the test.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, run_cli

COMMIT_CEILING = {"authorization_ceiling": {"commit": True}}


def _draft_path(temp: Path, workspace: Path, task_id: str = "TASK-001") -> Path:
    output = temp / f"{task_id}.draft.json"
    run_cli(
        "draft-contract",
        task_id,
        "--workspace",
        str(workspace),
        "--output",
        str(output),
    )
    return output


def _draft(temp: Path, workspace: Path, task_id: str = "TASK-001") -> dict:
    return json.loads(_draft_path(temp, workspace, task_id).read_text(encoding="utf-8"))


class SourceContractAuthorityTests(unittest.TestCase):
    def test_commit_is_absent_when_the_locked_ceiling_withholds_it(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            draft = _draft(temp, workspace)
            self.assertIn("local_write", draft["requested_actions"])
            self.assertNotIn("commit", draft["requested_actions"])

    def test_commit_is_requested_when_the_locked_ceiling_permits_it(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp, task_overrides=COMMIT_CEILING)
            draft = _draft(temp, workspace)
            self.assertIn("commit", draft["requested_actions"])

    def test_the_source_contract_never_carries_a_remote_action(self) -> None:
        """A ceiling cannot project push/pull_request even if it claims them."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(
                temp,
                task_overrides={
                    "authorization_ceiling": {
                        "commit": True,
                        "push": True,
                        "pull_request": True,
                    }
                },
            )
            draft = _draft(temp, workspace)
            self.assertEqual(draft["remote_mutation"], "denied")
            for action in ("push", "pull_request", "merge", "publish_or_release"):
                self.assertNotIn(action, draft["requested_actions"])


class KernelProfileLineageTests(unittest.TestCase):
    def test_audit_profile_survives_lock_draft_and_rendered_contract(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(
                temp,
                task_overrides={
                    "kernel_profile": "AUDIT",
                    "authorization_ceiling": {"commit": True},
                },
            )
            lock = json.loads(
                (workspace / "runtime" / "program-lock.json").read_text(encoding="utf-8")
            )
            locked = next(item for item in lock["tasks"] if item["id"] == "TASK-001")
            self.assertEqual(locked["source"]["kernel_profile"], "AUDIT")

            # Register the draft itself, which is exactly what the runner does:
            # `register_task_contract` drafts and then registers that file. A
            # hand-authored substitute would prove the fixture, not the lineage.
            draft_path = _draft_path(temp, workspace)
            self.assertEqual(
                json.loads(draft_path.read_text(encoding="utf-8"))["kernel_profile"], "AUDIT"
            )
            run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(draft_path),
                "--actor",
                "operator",
            )
            try:
                contract, _ = prepare_attempt(temp, workspace)
            finally:
                cleanup_worktree(repo, workspace)
            self.assertEqual(contract["kernel_profile"], "AUDIT")
            self.assertIn("commit", contract["requested_actions"])

    def test_change_profile_is_not_flattened_to_build(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp, task_overrides={"kernel_profile": "CHANGE"})
            self.assertEqual(_draft(temp, workspace)["kernel_profile"], "CHANGE")


if __name__ == "__main__":
    unittest.main()
