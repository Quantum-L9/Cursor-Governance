from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import (
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    prepare_attempt,
    register_contract,
    run_cli,
)

sys.path.insert(0, str(SCRIPTS))
from pec.state import StateDB


class CampaignStatusTest(unittest.TestCase):
    def test_accepted_bootstrap_activates_runtime_status(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            boot_status = json.loads((workspace / "runtime" / "campaign-status.json").read_text())
            self.assertEqual(boot_status["runtime_status"], "active")
            self.assertEqual(boot_status["source_status"], "operator_intake")
            self.assertEqual(
                boot_status["schema"], "program-execution-controller.campaign-status.v1"
            )
            status = run_cli("status", "--workspace", str(workspace))
            self.assertEqual(status["campaign_status"]["runtime_status"], "active")
            ledger = (workspace / "ledger" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("CAMPAIGN_ACTIVATED", ledger)

    def test_claim_reactivates_if_receipt_missing(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            receipt = workspace / "runtime" / "campaign-status.json"
            receipt.unlink()
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker-a")
            restored = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(restored["runtime_status"], "active")
            self.assertEqual(restored["actor"], "worker-a")

    def test_export_handoff_completes_runtime_status(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
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
            receipt = run_cli(
                "export-handoff",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--output",
                str(temp / "handoff.json"),
            )
            self.assertEqual(receipt["recommended_program_verdict"], "CONVERGED")
            status = json.loads((workspace / "runtime" / "campaign-status.json").read_text())
            self.assertEqual(status["runtime_status"], "completed")
            self.assertEqual(status["verdict"], "CONVERGED")
            self.assertEqual(
                run_cli("status", "--workspace", str(workspace))["campaign_status"][
                    "runtime_status"
                ],
                "completed",
            )
            cleanup_worktree(repo, workspace)

    def test_export_handoff_keeps_runtime_active_over_live_children(self) -> None:
        """HANDOFF_PROTOCOL: a recommendation is not terminal acceptance."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp, two_tasks=True)
            register_contract(temp, workspace)
            # TASK-001 is mid-flight (LEASED); a NOT_CONVERGED recommendation is
            # terminal, and export-handoff used to write runtime_status=completed
            # over it, after which every claim/start was refused.
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            # A failed blocking gate is what makes the recommendation NOT_CONVERGED
            # (terminal); a merely leased task alone is INCONCLUSIVE.
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                db.set_gate("GATE-001", "FAIL", [], "receipt-path")
            finally:
                db.close()
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
            self.assertIn("completion_blockers", receipt)
            self.assertIn("TASK-001", receipt["completion_blockers"].get("tasks", []))
            status = run_cli("status", "--workspace", str(workspace))["campaign_status"]
            self.assertNotEqual(status.get("runtime_status"), "completed")
            cleanup_worktree(repo, workspace)

    def test_pec_close_refuses_live_children(self) -> None:
        # RC-01: a terminal verdict must never close over live canonical
        # child state. A fresh bootstrap has a non-terminal TASK-001, so
        # every terminal verdict is refused with the blockers named.
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            for verdict in ("CONVERGED", "NOT_CONVERGED"):
                refused = run_cli(
                    "close",
                    "--workspace",
                    str(workspace),
                    "--actor",
                    "AUTH-001",
                    "--verdict",
                    verdict,
                    expect=2,
                )
                self.assertIn("campaign close refused", refused["error"])
                self.assertIn("TASK-001", refused["error"])
            status = json.loads((workspace / "runtime" / "campaign-status.json").read_text())
            self.assertNotEqual(status["runtime_status"], "completed")
            cleanup_worktree(repo, workspace)

    def test_pec_close_not_converged_permits_failed_children(self) -> None:
        # RC-01: NOT_CONVERGED permits terminal failed/cancelled children but
        # a successful verdict still refuses them.
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli(
                "fail",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--reason",
                "provider failed",
                "--actor",
                "worker",
            )
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
            self.assertIn("campaign close refused", refused["error"])
            closed = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "NOT_CONVERGED",
                "--evidence",
                "reason=child failed terminally",
            )
            self.assertEqual(closed["runtime_status"], "completed")
            self.assertEqual(closed["verdict"], "NOT_CONVERGED")
            cleanup_worktree(repo, workspace)

    def test_pec_close_marks_completed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
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
            closed = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "AUTH-001",
                "--verdict",
                "CONVERGED",
                "--evidence",
                "pull_request=https://example.test/pr/1",
            )
            self.assertEqual(closed["runtime_status"], "completed")
            self.assertEqual(closed["verdict"], "CONVERGED")
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
