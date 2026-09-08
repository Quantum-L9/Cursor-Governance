"""R6: exactly one code path turns an active runtime terminal (PEC-P1-002/003)."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from helpers import (
    bootstrap_repo,
    cleanup_worktree,
    prepare_attempt,
    register_contract,
    run_cli,
)


def _snapshot(workspace: Path) -> dict[str, Any]:
    conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        tables = ("tasks", "leases", "gates", "execution_attempts", "decisions", "unknowns")
        rows = {t: [dict(r) for r in conn.execute(f"SELECT * FROM {t}")] for t in tables}  # nosec
    finally:
        conn.close()
    status_path = workspace / "runtime" / "campaign-status.json"
    rows["campaign_status"] = json.loads(status_path.read_text(encoding="utf-8"))
    return rows


def _converge(temp: Path, workspace: Path) -> str:
    register_contract(temp, workspace)
    prepare_attempt(temp, workspace)
    verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
    evidence_id = verification["evidence_id"]
    run_cli(
        "evaluate-gate",
        "GATE-001",
        "PASS",
        "--workspace",
        str(workspace),
        "--evidence-id",
        evidence_id,
        "--method",
        "independent verification",
        "--actor",
        "controller",
    )
    run_cli(
        "complete",
        "TASK-001",
        "--workspace",
        str(workspace),
        "--actor",
        "operator",
        "--evidence-id",
        evidence_id,
    )
    return evidence_id


class HandoffIsSideEffectFreeTests(unittest.TestCase):
    def test_export_handoff_mutates_no_lifecycle_state(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp, two_tasks=True)
            register_contract(temp, workspace)
            # A live task with a live attempt, and a failed gate: the terminal
            # recommendation is NOT_CONVERGED, which export used to write over
            # the runtime as `completed`.
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute("UPDATE gates SET result='FAIL' WHERE id='GATE-001'")
            conn.commit()
            conn.close()
            before = _snapshot(workspace)
            receipt = run_cli(
                "export-handoff",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--output",
                str(temp / "handoff.json"),
            )
            self.assertEqual(receipt["recommended_program_verdict"], "NOT_CONVERGED")
            self.assertIn("active_execution_attempts", receipt["completion_blockers"])
            after = _snapshot(workspace)
            self.assertEqual(before, after, "export-handoff changed canonical runtime state")
            # A retry of the export is equally inert.
            run_cli(
                "export-handoff",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--output",
                str(temp / "handoff-2.json"),
            )
            self.assertEqual(_snapshot(workspace), before)
            cleanup_worktree(repo, workspace)


class ClosureReceiptTests(unittest.TestCase):
    def test_close_emits_a_bound_closure_receipt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _converge(temp, workspace)
            closed = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "CONVERGED",
            )
            self.assertEqual(closed["runtime_status"], "completed")
            receipt_path = Path(closed["closure_receipt"])
            self.assertTrue(receipt_path.is_file())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "program-execution-controller.closure-receipt.v1")
            self.assertEqual(receipt["producer"], "Program Execution Controller")
            self.assertEqual(receipt["verdict"], "CONVERGED")
            self.assertEqual(receipt["campaign_id"], "test-program")
            self.assertEqual(
                receipt["program_digest"],
                run_cli("status", "--workspace", str(workspace))["program_digest"],
            )
            self.assertIn("active_execution_attempts", receipt["blockers_checked"])
            self.assertEqual(closed["closure"]["receipt_digest"], receipt["receipt_digest"])
            status = json.loads((workspace / "runtime" / "campaign-status.json").read_text())
            self.assertEqual(status["closure_receipt"], str(receipt_path))
            cleanup_worktree(repo, workspace)

    def test_close_retry_replays_the_same_closure(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _converge(temp, workspace)
            first = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "CONVERGED",
            )
            second = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "CONVERGED",
            )
            self.assertTrue(second["replayed"])
            self.assertEqual(second["closure"]["closure_id"], first["closure"]["closure_id"])
            refused = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "NOT_CONVERGED",
                expect=2,
            )
            self.assertEqual(refused["error_code"], "TERMINAL_ALREADY_CLOSED")
            cleanup_worktree(repo, workspace)

    def test_failed_gate_with_a_live_attempt_cannot_close_as_not_converged(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute("UPDATE gates SET result='FAIL' WHERE id='GATE-001'")
            conn.commit()
            conn.close()
            refused = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "NOT_CONVERGED",
                expect=2,
            )
            self.assertEqual(refused["error_code"], "TERMINAL_BLOCKED_ACTIVE_ATTEMPT")
            self.assertIn("active_execution_attempts", refused["error"])
            # Once execution is safely stopped and finalized, NOT_CONVERGED is terminal.
            run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "abandoned",
                "--actor",
                "operator",
            )
            closed = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "NOT_CONVERGED",
            )
            self.assertEqual(closed["verdict"], "NOT_CONVERGED")
            cleanup_worktree(repo, workspace)

    def test_close_refuses_over_a_tampered_program_lock(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _converge(temp, workspace)
            lock_path = workspace / "runtime" / "program-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["gates"] = []
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            refused = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "CONVERGED",
                expect=2,
            )
            self.assertIn("program_lock", refused["error"])
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
