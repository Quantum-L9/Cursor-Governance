"""PEC-P1-004: state, event chain and receipts converge after any crash.

Kill the Controller at every tested durability boundary and restart it: the
runtime must converge to exactly one defensible state without inventing
evidence or duplicating state advancement.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from helpers import (
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    prepare_attempt,
    register_contract,
    run_cli,
)

sys.path.insert(0, str(SCRIPTS))
from pec import controller as pec_controller  # noqa: E402
from pec import ledger as pec_ledger  # noqa: E402
from pec.common import ControllerError  # noqa: E402
from pec.runtime import open_runtime  # noqa: E402
from pec.state import StateDB  # noqa: E402


def _file_events(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / "ledger" / "events.jsonl"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _db_events(workspace: Path) -> list[dict[str, Any]]:
    db = StateDB(workspace / "runtime" / "state.sqlite")
    try:
        return db.events()
    finally:
        db.close()


def _task_state(workspace: Path, task_id: str = "TASK-001") -> str:
    db = StateDB(workspace / "runtime" / "state.sqlite")
    try:
        return str(db.task(task_id)["runtime_state"])  # type: ignore[index]
    finally:
        db.close()


class EventProjectionTests(unittest.TestCase):
    def test_file_is_a_projection_of_the_committed_chain(self) -> None:
        with TemporaryDirectory() as raw:
            _, _, workspace = bootstrap_repo(Path(raw))
            self.assertEqual(_file_events(workspace), _db_events(workspace))
            self.assertTrue(_db_events(workspace))

    def test_crash_after_commit_before_projection_converges_on_reopen(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            before = len(_file_events(workspace))
            # The file append dies exactly when the claim's own event -- the one
            # committed with the lease -- is projected. Reconcile at open has
            # nothing pending, so nothing earlier trips it.
            original = pec_ledger.EventLedger._write_line

            def dying(self: Any, event: dict[str, Any]) -> None:
                if event["type"] == "TASK_LEASED":
                    raise OSError("disk gone")
                original(self, event)

            with (
                unittest.mock.patch.object(pec_ledger.EventLedger, "_write_line", dying),
                self.assertRaises(OSError),
            ):
                pec_controller.claim_task(workspace, "TASK-001", "worker")
            self.assertEqual(_task_state(workspace), "LEASED", "the claim itself committed")
            # The committed chain is one event (TASK_LEASED) ahead of the file.
            self.assertGreater(len(_db_events(workspace)), before)
            self.assertEqual(len(_file_events(workspace)), len(_db_events(workspace)) - 1)
            self.assertEqual(_db_events(workspace)[-1]["type"], "TASK_LEASED")
            # Restart: reconciliation projects the pending event; nothing is duplicated.
            db, ledger = open_runtime(workspace)
            try:
                self.assertEqual(ledger.verify(), (True, "PASS"))
                self.assertEqual(ledger.file_events(), db.events())
                self.assertEqual(db.pending_events(), [])
            finally:
                db.close()
            validated = run_cli("validate", "--workspace", str(workspace))
            self.assertEqual(validated["status"], "PASS")

    def test_a_failure_inside_the_transaction_persists_nothing(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            events_before = _db_events(workspace)
            receipt_path = workspace / "receipts" / "verification" / "TASK-001.json"
            with (
                unittest.mock.patch.object(
                    StateDB, "upsert_evidence", side_effect=RuntimeError("mid-transaction crash")
                ),
                self.assertRaises(RuntimeError),
            ):
                pec_controller.verify_attempt(workspace, "TASK-001")
            # VERIFYING is the durable in-flight marker taken before the verdict
            # transaction; the verdict itself, its receipt and its event never
            # landed, so nothing advanced.
            self.assertEqual(_task_state(workspace), "VERIFYING")
            self.assertFalse(receipt_path.exists(), "receipt materialized without a commit")
            self.assertEqual(_db_events(workspace), events_before)
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                self.assertEqual(db.receipts("verification"), [])
                self.assertEqual(db.pending_receipts(), [])
            finally:
                db.close()
            # The interrupted verification is residue: `start` lands it FAILED
            # and dispatches a fresh attempt, which then verifies normally.
            started = run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "w")
            self.assertEqual(started["attempt_number"], 2)
            contract = json.loads(
                (workspace / "contracts" / "rendered" / "TASK-001.json").read_text("utf-8")
            )
            receipt = {
                "schema": "program-execution-controller.attempt-receipt.v2",
                "task_id": "TASK-001",
                "contract_digest": contract["contract_digest"],
                "program_digest": contract["program_digest"],
                "base_sha": contract["base_sha"],
                "candidate_sha": None,
                "changed_files": ["docs/result.txt"],
                "validation_results": [
                    {"command": c, "status": "PASS", "exit_code": 0, "evidence": "w"}
                    for c in contract["validation_commands"]
                ],
                "produced_evidence": [],
                "residual_unknowns": [],
                "claimed_status": "completed",
            }
            receipt_file = temp / "attempt-2.json"
            receipt_file.write_text(json.dumps(receipt), encoding="utf-8")
            run_cli(
                "record-attempt",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--receipt",
                str(receipt_file),
            )
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL")
            cleanup_worktree(repo, workspace)

    def test_concurrent_controllers_never_mint_the_same_sequence(self) -> None:
        with TemporaryDirectory() as raw:
            _, _, workspace = bootstrap_repo(Path(raw))
            errors: list[BaseException] = []

            def writer(name: str) -> None:
                try:
                    db, ledger = open_runtime(workspace)
                    try:
                        for index in range(20):
                            with db.controller_transaction():
                                db.set_meta(f"{name}-{index}", index)
                                ledger.append("RACE_PROBE", name, {"index": index})
                    finally:
                        db.close()
                except Exception as exc:  # noqa: BLE001 - collected for the assertion
                    errors.append(exc)

            threads = [threading.Thread(target=writer, args=(f"w{i}",)) for i in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])
            events = _db_events(workspace)
            sequences = [e["sequence"] for e in events]
            self.assertEqual(sequences, list(range(1, len(events) + 1)))
            self.assertEqual(sum(1 for e in events if e["type"] == "RACE_PROBE"), 80)
            db, ledger = open_runtime(workspace)
            try:
                self.assertEqual(ledger.verify(), (True, "PASS"))
                self.assertEqual(ledger.file_events(), events)
            finally:
                db.close()


class ReceiptProjectionTests(unittest.TestCase):
    def test_missing_receipt_file_is_rematerialized_from_the_canonical_record(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            receipt_path = workspace / "receipts" / "verification" / "TASK-001.json"
            original = json.loads(receipt_path.read_text(encoding="utf-8"))
            original.pop("signal", None)
            receipt_path.unlink()
            # Any reopen converges the projection.
            run_cli("status", "--workspace", str(workspace))
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8")), original)
            # And completion still finds the canonical verification.
            run_cli(
                "evaluate-gate",
                "GATE-001",
                "--workspace",
                str(workspace),
                "--evidence-id",
                verification["evidence_id"],
                "--actor",
                "controller",
            )
            completed = run_cli(
                "complete",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--evidence-id",
                verification["evidence_id"],
            )
            self.assertEqual(completed["status"], "COMPLETED")
            cleanup_worktree(repo, workspace)

    def test_crash_between_receipt_write_and_projection_mark_converges(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            with (
                unittest.mock.patch.object(
                    StateDB, "mark_receipt_projected", side_effect=OSError("crash")
                ),
                self.assertRaises(OSError),
            ):
                pec_controller.verify_attempt(workspace, "TASK-001")
            self.assertEqual(_task_state(workspace), "PASSED_LOCAL", "the verdict committed")
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                self.assertEqual(len(db.pending_receipts()), 1)
            finally:
                db.close()
            db, _ = open_runtime(workspace)
            try:
                self.assertEqual(db.pending_receipts(), [])
                record = db.receipts("verification")[0]
                self.assertTrue(Path(record["artifact_path"]).is_file())
            finally:
                db.close()
            cleanup_worktree(repo, workspace)

    def test_a_receipt_file_without_a_canonical_record_is_not_believed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            forged = workspace / "receipts" / "verification" / "TASK-001.json"
            forged.parent.mkdir(parents=True, exist_ok=True)
            forged.write_text(
                json.dumps({"task_id": "TASK-001", "verdict": "PASSED_LOCAL", "evidence_id": "X"}),
                encoding="utf-8",
            )
            db, _ = open_runtime(workspace)
            try:
                task = db.task("TASK-001")
                assert task is not None
                self.assertIsNone(pec_controller._verified_this_attempt(workspace, task, None, db))
                self.assertTrue(forged.is_file(), "foreign artifacts are left alone, never adopted")
                self.assertEqual(db.receipts("verification"), [])
            finally:
                db.close()

    def test_tampered_receipt_projection_is_repaired_from_the_record(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            run_cli("verify", "TASK-001", "--workspace", str(workspace))
            receipt_path = workspace / "receipts" / "verification" / "TASK-001.json"
            canonical = json.loads(receipt_path.read_text(encoding="utf-8"))
            canonical.pop("signal", None)
            receipt_path.write_text(json.dumps({**canonical, "verdict": "TAMPERED"}), "utf-8")
            run_cli("status", "--workspace", str(workspace))
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8")), canonical)
            cleanup_worktree(repo, workspace)


class LegacyRuntimeTests(unittest.TestCase):
    def _strip_to_legacy(self, workspace: Path) -> None:
        conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM receipts")
        conn.commit()
        conn.close()

    def test_pre_r8_runtime_imports_a_verifying_file_chain_once(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            run_cli("verify", "TASK-001", "--workspace", str(workspace))
            file_chain = _file_events(workspace)
            self._strip_to_legacy(workspace)
            db, ledger = open_runtime(workspace)
            try:
                self.assertEqual(db.events(), file_chain)
                self.assertEqual(ledger.verify(), (True, "PASS"))
                self.assertEqual(
                    len(db.receipts("verification")), 1, "self-consistent receipt adopted"
                )
            finally:
                db.close()
            # Idempotent.
            db, _ = open_runtime(workspace)
            try:
                self.assertEqual(len(db.events()), len(file_chain))
            finally:
                db.close()
            cleanup_worktree(repo, workspace)

    def test_pre_r8_runtime_with_a_broken_chain_fails_closed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            self._strip_to_legacy(workspace)
            ledger = workspace / "ledger" / "events.jsonl"
            lines = ledger.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(lines[0])
            tampered["actor"] = "intruder"
            lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
            ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(ControllerError) as caught:
                open_runtime(workspace)
            self.assertEqual(caught.exception.error_code, "RUNTIME_RECONCILIATION_REQUIRED")
            self.assertEqual(_db_events(workspace), [], "an unverifiable chain was adopted")

    def test_inconsistent_legacy_receipt_is_left_unadopted(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self._strip_to_legacy(workspace)
            receipt_path = workspace / "receipts" / "verification" / "TASK-001.json"
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["verdict"] = "PASSED_LOCAL"
            payload["gates"] = {"forged": "PASS"}
            receipt_path.write_text(json.dumps(payload), encoding="utf-8")
            db, _ = open_runtime(workspace)
            try:
                self.assertEqual(db.receipts("verification"), [])
                task = db.task("TASK-001")
                assert task is not None
                self.assertIsNone(
                    pec_controller._verified_this_attempt(
                        workspace, task, db.latest_attempt("TASK-001"), db
                    )
                )
            finally:
                db.close()
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
