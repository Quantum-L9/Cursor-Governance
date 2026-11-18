"""A task whose objective already holds on its base is `already_satisfied`, not a scope FAIL.

A writing task that changes nothing has normally not done its work, and that
attempt still FAILs `scope`. The exception is proof, not a claim: the attempt
changed nothing, declared nothing, and the Controller's own run of the task's
validation commands passes on the unchanged worktree, so the change the task
asked for is already on the base.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from helpers import bootstrap_repo, cleanup_worktree, register_contract, run_cli, write_json

OUTPUT = "docs/result.txt"


def _commit_output(repo: Path) -> None:
    """Land the task's change on the target before the campaign runs."""
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / OUTPUT).write_text("ok\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", OUTPUT], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "already landed"], check=True, capture_output=True
    )


def _attempt_without_change(
    temp: Path, workspace: Path, *, claim_pass: bool = True
) -> dict[str, Any]:
    """Run claim -> start -> record-attempt with a worker that writes nothing."""
    run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
    run_cli("prepare", "TASK-001", "--workspace", str(workspace))
    rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
    run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
    contract = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
    receipt = {
        "schema": "program-execution-controller.attempt-receipt.v2",
        "task_id": "TASK-001",
        "contract_digest": contract["contract_digest"],
        "program_digest": contract["program_digest"],
        "base_sha": contract["base_sha"],
        "candidate_sha": None,
        "changed_files": [],
        "validation_results": [
            {
                "command": command,
                "status": "PASS" if claim_pass else "FAIL",
                "exit_code": 0 if claim_pass else 1,
                "evidence": "worker output",
            }
            for command in contract["validation_commands"]
        ],
        "produced_evidence": [],
        "residual_unknowns": [],
        "claimed_status": "completed",
    }
    path = write_json(temp / "TASK-001.attempt.json", receipt)
    run_cli("record-attempt", "TASK-001", "--workspace", str(workspace), "--receipt", str(path))
    return run_cli("verify", "TASK-001", "--workspace", str(workspace))


def _release(repo: Path, workspace: Path) -> None:
    run_cli(
        "release-lease",
        "TASK-001",
        "--workspace",
        str(workspace),
        "--reason",
        "test cleanup",
        "--actor",
        "test",
    )
    cleanup_worktree(repo, workspace)


class AlreadySatisfiedTests(unittest.TestCase):
    def test_a_change_already_on_the_base_verifies_as_already_satisfied(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _commit_output(repo)
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            register_contract(temp, workspace, output=OUTPUT)
            verification = _attempt_without_change(temp, workspace)
            self.assertEqual(verification["verdict"], "PASSED_LOCAL", verification["gates"])
            self.assertEqual(verification["outcome"], "already_satisfied")
            self.assertEqual(verification["gates"]["scope"], "PASS")
            self.assertEqual(verification["gates"]["no_change_required"], "PASS")
            self.assertEqual(verification["gates"]["validation"], "PASS")
            self.assertEqual(verification["observed_changed_files"], [])
            _release(repo, workspace)

    def test_a_worker_that_does_nothing_on_needed_work_still_fails_scope(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace, output=OUTPUT)
            verification = _attempt_without_change(temp, workspace)
            self.assertEqual(verification["verdict"], "FAILED")
            self.assertEqual(verification["outcome"], "changed")
            self.assertEqual(verification["gates"]["scope"], "FAIL")
            self.assertEqual(verification["gates"]["no_change_required"], "FAIL")
            self.assertEqual(verification["gates"]["validation"], "FAIL")
            _release(repo, workspace)

    def test_an_earlier_attempts_leftover_is_not_already_satisfied(self) -> None:
        """Validation passes only because attempt 1 left the file uncommitted."""
        from helpers import prepare_attempt

        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace, output=OUTPUT)
            # Attempt 1 writes the output but declares nothing: FAILED, file left.
            contract, _ = prepare_attempt(temp, workspace, output=OUTPUT, declared_changed=[])
            first = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(first["verdict"], "FAILED")
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
            receipt = {
                "schema": "program-execution-controller.attempt-receipt.v2",
                "task_id": "TASK-001",
                "contract_digest": contract["contract_digest"],
                "program_digest": contract["program_digest"],
                "base_sha": contract["base_sha"],
                "candidate_sha": None,
                "changed_files": [],
                "validation_results": [
                    {"command": c, "status": "PASS", "exit_code": 0, "evidence": "x"}
                    for c in contract["validation_commands"]
                ],
                "produced_evidence": [],
                "residual_unknowns": [],
                "claimed_status": "completed",
            }
            path = write_json(temp / "retry.attempt.json", receipt)
            run_cli(
                "record-attempt", "TASK-001", "--workspace", str(workspace), "--receipt", str(path)
            )
            second = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(second["verdict"], "FAILED", second["gates"])
            self.assertNotEqual(second["outcome"], "already_satisfied")
            _release(repo, workspace)

    def test_a_changing_attempt_is_recorded_as_changed(self) -> None:
        from helpers import prepare_attempt

        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace, output=OUTPUT)
            prepare_attempt(temp, workspace, output=OUTPUT)
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL", verification["gates"])
            self.assertEqual(verification["outcome"], "changed")
            self.assertNotIn("no_change_required", verification["gates"])
            _release(repo, workspace)


if __name__ == "__main__":
    unittest.main()
