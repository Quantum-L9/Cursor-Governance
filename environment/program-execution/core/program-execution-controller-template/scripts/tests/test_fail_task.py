"""Canonical Controller failure path (PHASE-5).

A task that dies after claim — at any stage from LEASED through VERIFYING —
lands in FAILED through one operation that records the reason, appends the
ledger event, releases the Controller writer lease, and preserves the task
worktree and attempt receipts as evidence.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli


def _ledger_events(workspace: Path) -> list[dict]:
    ledger = workspace / "ledger" / "events.jsonl"
    if not ledger.is_file():
        return []
    return [
        json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


class FailTaskTests(unittest.TestCase):
    def test_fail_from_leased_releases_lease_and_records_reason(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            result = run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "provider dispatch failed before execution",
                "--actor",
                "make-campaign",
            )
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(result["lease_released"])
            status = run_cli("status", "--workspace", str(workspace))
            task = next(t for t in status["tasks"] if t["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "FAILED")
            self.assertFalse(status.get("active_leases"))
            events = [e for e in _ledger_events(workspace) if e.get("type") == "TASK_FAILED"]
            self.assertTrue(events)

    def test_fail_from_executing_preserves_worktree(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            prepared = run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
            result = run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "provider window died",
                "--actor",
                "make-campaign",
            )
            self.assertEqual(result["previous_state"], "EXECUTING")
            self.assertTrue(result["lease_released"])
            self.assertTrue(
                Path(prepared["worktree"]).is_dir(), "worktree must survive as evidence"
            )

    def test_fail_is_tolerant_when_already_failed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "first failure",
                "--actor",
                "make-campaign",
            )
            result = run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "reconciliation replay",
                "--actor",
                "make-campaign",
            )
            self.assertEqual(result["status"], "FAILED")
            self.assertFalse(result["transitioned"])
            self.assertFalse(result["lease_released"])

    def test_fail_refuses_states_outside_the_contract(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            result = run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "nothing claimed yet",
                "--actor",
                "make-campaign",
                expect=2,
            )
            self.assertIn("canonical failure", result["error"])

    def test_failed_task_permits_governed_retry(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "transient provider failure",
                "--actor",
                "make-campaign",
            )
            # FAILED -> ELIGIBLE is a legal transition, so a governed retry can
            # re-claim after the failure released the writer lease.
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker-2")
            status = run_cli("status", "--workspace", str(workspace))
            task = next(t for t in status["tasks"] if t["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "LEASED")


if __name__ == "__main__":
    unittest.main()
