"""R12: legacy runtimes are classified and fenced, never silently blessed."""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import (
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    prepare_attempt,
    register_contract,
    run_cli,
    write_yaml,
)

sys.path.insert(0, str(SCRIPTS))
from pec.reasons import ALL_REASON_CODES  # noqa: E402


class LegacyReconciliationTests(unittest.TestCase):
    def test_current_runtime_is_reconciled_cleanly(self) -> None:
        with TemporaryDirectory() as raw:
            _, _, workspace = bootstrap_repo(Path(raw))
            report = run_cli("reconcile-legacy", "--workspace", str(workspace))
            self.assertEqual(report["status"], "RECONCILED")
            self.assertEqual(report["program_lock"]["disposition"], "ATTESTED")
            self.assertEqual(report["executing_without_attempt"], [])
            self.assertFalse(report["halt_required"])

    def test_semantically_stale_legacy_lock_halts(self) -> None:
        with TemporaryDirectory() as raw:
            blueprint, _, workspace = bootstrap_repo(Path(raw))
            path = blueprint / "CONVERGENCE_GATES.yaml"
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            doc["gates"][0]["blocking"] = False
            write_yaml(path, doc)
            # A legacy relock could have refreshed the digests over this edit;
            # simulate a digest-current lock by rewriting the recorded digests.
            lock_path = workspace / "runtime" / "program-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            import hashlib

            lock["source_digests"]["CONVERGENCE_GATES.yaml"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            from pec.common import digest_object

            lock.pop("lock_digest", None)
            lock["lock_digest"] = digest_object(lock)
            lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True), encoding="utf-8")
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute(
                "UPDATE meta SET value=? WHERE key='program_digest'",
                (json.dumps(lock["lock_digest"]),),
            )
            conn.commit()
            conn.close()
            report = run_cli("reconcile-legacy", "--workspace", str(workspace), expect=1)
            self.assertEqual(report["status"], "RUNTIME_RECONCILIATION_REQUIRED")
            self.assertEqual(report["program_lock"]["decision"], "WIDER_PROGRAM_DRIFT")
            self.assertEqual(report["program_lock"]["disposition"], "HALT_ROUTE_THROUGH_ADMISSION")

    def test_legacy_executing_task_without_attempt_is_marked_not_resumed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "w")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "w")
            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute("DELETE FROM execution_attempts")
            conn.commit()
            conn.close()
            report = run_cli("reconcile-legacy", "--workspace", str(workspace), expect=1)
            self.assertEqual(report["executing_without_attempt"], ["TASK-001"])
            status = run_cli("status", "--workspace", str(workspace))
            task = next(t for t in status["tasks"] if t["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "EXECUTING", "never auto-resumed or reset")
            self.assertIsNone(task["execution_attempt"], "no baseline was synthesized")
            # Recovery is the only way forward.
            recovered = run_cli(
                "recover-execution",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--reason",
                "legacy",
            )
            self.assertEqual(recovered["items"][0]["status"], "RECOVERED")
            cleanup_worktree(repo, workspace)

    def test_completed_runtime_with_live_authority_is_inconsistent(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "w")
            # A legacy closeout that wrote `completed` over a live lease.
            status_path = workspace / "runtime" / "campaign-status.json"
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            payload.update({"runtime_status": "completed", "verdict": "NOT_CONVERGED"})
            status_path.write_text(json.dumps(payload), encoding="utf-8")
            report = run_cli("reconcile-legacy", "--workspace", str(workspace), expect=1)
            self.assertEqual(report["terminal"]["disposition"], "TERMINAL_STATE_INCONSISTENT")
            self.assertIn("active_lease", report["terminal"]["problems"])
            self.assertIn("closure_receipt_missing", report["terminal"]["problems"])
            # History preserved: the status file still says completed.
            self.assertEqual(
                json.loads(status_path.read_text(encoding="utf-8"))["runtime_status"],
                "completed",
            )

    def test_receipts_are_classified_verified_or_unverified(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            run_cli("verify", "TASK-001", "--workspace", str(workspace))
            forged = workspace / "receipts" / "gates" / "GATE-001" / "GATE-EVAL-forged.json"
            forged.parent.mkdir(parents=True, exist_ok=True)
            forged.write_text(json.dumps({"gate_id": "GATE-001", "result": "PASS"}), "utf-8")
            report = run_cli("reconcile-legacy", "--workspace", str(workspace))
            self.assertIn("receipts/verification/TASK-001.json", report["receipts"]["verified"])
            self.assertIn(
                "receipts/gates/GATE-001/GATE-EVAL-forged.json", report["receipts"]["unverified"]
            )
            cleanup_worktree(repo, workspace)


class ReasonCodeTests(unittest.TestCase):
    def test_every_emitted_error_code_is_in_the_taxonomy(self) -> None:
        import re

        pec_dir = SCRIPTS / "pec"
        emitted: set[str] = set()
        for path in pec_dir.glob("*.py"):
            emitted.update(re.findall(r'error_code="([A-Z_]+)"', path.read_text(encoding="utf-8")))
        missing = sorted(emitted - ALL_REASON_CODES)
        self.assertEqual(missing, [], f"reason codes not in pec.reasons: {missing}")


if __name__ == "__main__":
    unittest.main()
