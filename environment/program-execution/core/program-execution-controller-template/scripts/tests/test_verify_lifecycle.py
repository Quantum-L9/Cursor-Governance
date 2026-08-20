"""A verification attempt gets exactly one controller verdict.

The runner used to call `verify`, watch the verdict move the task to FAILED,
and then call `verify` again — which the state machine answered with the
unexplained `task must be SUBMITTED`. A duplicate call now replays the recorded
receipt, and a call from a genuinely wrong state says how the task got there.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, register_contract, run_cli


def _run_cli_error(*args: str) -> str:
    import os
    import sys

    controller_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.setdefault("L9_ALLOW_PEC_DIRECT", "1")
    completed = subprocess.run(
        [sys.executable, str(controller_root / "scripts/pec.py"), *args],
        cwd=controller_root,
        text=True,
        capture_output=True,
        check=False,
        timeout=45,
        env=env,
    )
    return (completed.stdout or "") + (completed.stderr or "")


class VerifyLifecycleTest(unittest.TestCase):
    def test_pass_verdict_completes_and_a_duplicate_call_replays_it(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            _contract, prepared = prepare_attempt(temp, workspace)
            worktree = Path(prepared["worktree"])
            _commit(worktree, "docs/result.txt")

            first = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(first["verdict"], "PASSED_LOCAL")
            self.assertNotIn("replayed", first)

            second = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertTrue(second["replayed"], "duplicate verify did not replay")
            self.assertEqual(second["verification_id"], first["verification_id"])
            self.assertEqual(second["runtime_state"], "PASSED_LOCAL")
            cleanup_worktree(repo, workspace)

    def test_fail_verdict_preserves_the_receipt_and_replays_instead_of_erroring(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            # Declaring a file the worker never wrote fails the scope gate.
            prepare_attempt(temp, workspace, declared_changed=["docs/never-written.txt"])

            first = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(first["verdict"], "FAILED")
            receipt = workspace / "receipts/verification/TASK-001.json"
            self.assertTrue(receipt.is_file(), "failed verification receipt was not preserved")

            second = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertTrue(second["replayed"])
            self.assertEqual(second["verdict"], "FAILED")
            self.assertEqual(second["runtime_state"], "FAILED")
            self.assertEqual(
                json.loads(receipt.read_text("utf-8"))["verification_id"],
                first["verification_id"],
                "replay overwrote the preserved receipt",
            )
            cleanup_worktree(repo, workspace)

    def test_retry_after_repair_is_a_new_attempt_with_its_own_verdict(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            contract, prepared = prepare_attempt(
                temp, workspace, declared_changed=["docs/never-written.txt"]
            )
            worktree = Path(prepared["worktree"])
            failed = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(failed["verdict"], "FAILED")

            # Repair re-enters execution and submits fresh work.
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
            _commit(worktree, "docs/result.txt")
            _record(workspace, temp, contract, worktree, changed=["docs/result.txt"])

            repaired = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertNotIn("replayed", repaired)
            self.assertEqual(repaired["verdict"], "PASSED_LOCAL")
            self.assertNotEqual(repaired["verification_id"], failed["verification_id"])
            cleanup_worktree(repo, workspace)

    def test_verify_from_an_unreachable_state_explains_how_it_got_there(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            # Never claimed, so no attempt exists to replay.
            message = _run_cli_error("verify", "TASK-001", "--workspace", str(workspace))
            self.assertIn("expected SUBMITTED", message)
            self.assertIn("Why:", message)
            self.assertIn("Attempts recorded: 0", message)
            self.assertIn("Retry safe", message)
            self.assertNotEqual(message.strip(), "task must be SUBMITTED")


def _commit(worktree: Path, rel: str) -> None:
    target = worktree / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("ok\n", encoding="utf-8")
    for args in (
        ["config", "user.email", "worker@example.com"],
        ["config", "user.name", "worker"],
        ["add", rel],
        ["commit", "-m", f"task work {rel}"],
    ):
        subprocess.run(["git", "-C", str(worktree), *args], check=True, capture_output=True)


def _record(
    workspace: Path, temp: Path, contract: dict, worktree: Path, *, changed: list[str]
) -> None:
    head = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    receipt = {
        "schema": "program-execution-controller.attempt-receipt.v2",
        "task_id": "TASK-001",
        "contract_digest": contract["contract_digest"],
        "program_digest": contract["program_digest"],
        "base_sha": contract["base_sha"],
        "candidate_sha": head,
        "changed_files": changed,
        "validation_results": [
            {"command": command, "status": "PASS", "exit_code": 0, "evidence": "worker output"}
            for command in contract["validation_commands"]
        ],
        "produced_evidence": [],
        "residual_unknowns": [],
        "claimed_status": "completed",
    }
    path = temp / "retry.attempt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_cli("record-attempt", "TASK-001", "--workspace", str(workspace), "--receipt", str(path))


if __name__ == "__main__":
    unittest.main()
