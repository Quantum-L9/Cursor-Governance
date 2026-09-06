"""PEC-P1-005: the Controller derives gate verdicts; callers only supply evidence."""

from __future__ import annotations

import json
import sqlite3
import sys
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
from pec.gates import (  # noqa: E402
    GATE_EVALUATOR_VERSION,
    GATE_EVIDENCE_CONTRADICTS,
    GATE_EVIDENCE_MISSING,
    GATE_EVIDENCE_STALE,
    GATE_UNKNOWN_TYPE,
    GATE_VERIFICATION_REQUIRED,
    derive_gate_result,
)
from pec.state import StateDB  # noqa: E402


def _evaluate(workspace: Path, *evidence: str, expected: str | None = None, expect: int = 0) -> Any:
    argv: list[str] = ["evaluate-gate", "GATE-001"]
    if expected:
        argv.append(expected)
    argv.extend(["--workspace", str(workspace), "--actor", "controller"])
    for item in evidence:
        argv.extend(["--evidence-id", item])
    return run_cli(*argv, expect=expect)


def _gate(workspace: Path) -> dict[str, Any]:
    conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        row = dict(conn.execute("SELECT * FROM gates WHERE id='GATE-001'").fetchone())
    finally:
        conn.close()
    row["evidence_ids"] = json.loads(row["evidence_ids"])
    return row


def _verified(temp: Path, workspace: Path) -> str:
    register_contract(temp, workspace)
    prepare_attempt(temp, workspace)
    return str(run_cli("verify", "TASK-001", "--workspace", str(workspace))["evidence_id"])


class DerivedGateTests(unittest.TestCase):
    def test_satisfying_evidence_derives_pass_without_a_caller_result(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            receipt = _evaluate(workspace, evidence)
            self.assertEqual(receipt["result"], "PASS")
            self.assertTrue(receipt["derived"])
            self.assertEqual(receipt["evaluator_version"], GATE_EVALUATOR_VERSION)
            self.assertIsNone(receipt["expected_result"])
            self.assertEqual(_gate(workspace)["result"], "PASS")
            cleanup_worktree(repo, workspace)

    def test_caller_pass_over_missing_evidence_is_recorded_unknown_and_refused(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            refused = _evaluate(workspace, "EVID-NOPE", expected="PASS", expect=2)
            self.assertEqual(refused["error_code"], "GATE_EXPECTATION_MISMATCH")
            self.assertIn("derived UNKNOWN", refused["error"])
            gate = _gate(workspace)
            self.assertEqual(gate["result"], "UNKNOWN")
            receipt = json.loads(Path(gate["evaluation_receipt"]).read_text(encoding="utf-8"))
            self.assertIn(GATE_EVIDENCE_MISSING, receipt["reason_codes"])
            self.assertEqual(receipt["expected_result"], "PASS")

    def test_planning_evidence_cannot_close_an_execution_gate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            receipt = _evaluate(workspace, "EVID-PLAN")
            self.assertEqual(receipt["result"], "UNKNOWN")
            self.assertIn(GATE_VERIFICATION_REQUIRED, receipt["reason_codes"])

    def test_negative_verification_evidence_derives_fail(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace, declared_changed=["docs/other.txt"])
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "FAILED")
            receipt = _evaluate(workspace, verification["evidence_id"])
            self.assertEqual(receipt["result"], "FAIL")
            self.assertIn(GATE_EVIDENCE_CONTRADICTS, receipt["reason_codes"])
            # And a caller cannot talk it into PASS.
            refused = _evaluate(workspace, verification["evidence_id"], expected="PASS", expect=2)
            self.assertEqual(refused["error_code"], "GATE_EXPECTATION_MISMATCH")
            self.assertEqual(_gate(workspace)["result"], "FAIL")
            cleanup_worktree(repo, workspace)

    def test_a_caller_cannot_record_fail_or_blocked_by_assertion(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            for asserted in ("FAIL", "BLOCKED", "UNKNOWN"):
                refused = _evaluate(workspace, evidence, expected=asserted, expect=2)
                self.assertEqual(refused["error_code"], "GATE_EXPECTATION_MISMATCH")
                self.assertEqual(_gate(workspace)["result"], "PASS")
            cleanup_worktree(repo, workspace)

    def test_stale_verification_evidence_is_unknown(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            receipt_path = workspace / "receipts" / "verification" / "TASK-001.json"
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["receipt_digest"] = "0" * 64
            receipt_path.write_text(json.dumps(payload), encoding="utf-8")
            receipt = _evaluate(workspace, evidence)
            self.assertEqual(receipt["result"], "UNKNOWN")
            self.assertIn(GATE_EVIDENCE_STALE, receipt["reason_codes"])
            cleanup_worktree(repo, workspace)

    def test_evidence_for_the_wrong_program_lock_is_unknown(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            receipt_path = workspace / "receipts" / "verification" / "TASK-001.json"
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["program_digest"] = "1" * 64
            # keep the digest consistent with the evidence record's copy
            body = dict(payload)
            body.pop("receipt_digest", None)
            from pec.common import digest_object

            payload["receipt_digest"] = digest_object(body)
            receipt_path.write_text(json.dumps(payload), encoding="utf-8")
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                item = db.evidence(evidence)
                assert item is not None
                db.upsert_evidence({**item, "digest": payload["receipt_digest"]})
            finally:
                db.close()
            receipt = _evaluate(workspace, evidence)
            self.assertEqual(receipt["result"], "UNKNOWN")
            self.assertIn(GATE_EVIDENCE_STALE, receipt["reason_codes"])
            cleanup_worktree(repo, workspace)

    def test_unknown_gate_class_is_unknown_never_pass(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                gate = db.gate("GATE-001")
                assert gate is not None
                verdict = derive_gate_result(
                    db,
                    {**gate, "definition": {**gate["definition"], "class": "oracle"}},
                    [evidence],
                )
            finally:
                db.close()
            self.assertEqual(verdict.result, "UNKNOWN")
            self.assertIn(GATE_UNKNOWN_TYPE, verdict.reason_codes)
            cleanup_worktree(repo, workspace)

    def test_a_changed_gate_definition_invalidates_a_prior_pass(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            _evaluate(workspace, evidence)
            self.assertEqual(_gate(workspace)["result"], "PASS")
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                gate = db.gate("GATE-001")
                assert gate is not None
                db.upsert_gate({**gate["definition"], "pass_condition": "stricter now"})
                self.assertEqual(db.gate("GATE-001")["result"], "UNKNOWN")  # type: ignore[index]
                db.upsert_gate({**gate["definition"], "pass_condition": "stricter now"})
                self.assertEqual(db.gate("GATE-001")["result"], "UNKNOWN")  # type: ignore[index]
            finally:
                db.close()
            cleanup_worktree(repo, workspace)

    def test_repeated_evaluation_is_deterministic(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            first = _evaluate(workspace, evidence)
            second = _evaluate(workspace, evidence)
            for key in ("result", "reason_codes", "unresolved", "gate_definition_digest"):
                self.assertEqual(first[key], second[key])
            cleanup_worktree(repo, workspace)

    def test_waiver_derives_not_applicable_and_cannot_be_asserted_as_pass(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            evidence = _verified(temp, workspace)
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                gate = db.gate("GATE-001")
                assert gate is not None
                db.upsert_gate({**gate["definition"], "waiver_allowed": True})
                db.upsert_waiver(
                    {
                        "id": "WAIVER-001",
                        "scope": ["GATE-001"],
                        "status": "active",
                        "expires_at": "2099-01-01T00:00:00+00:00",
                        "evidence_ids": [evidence],
                    }
                )
            finally:
                db.close()
            refused = run_cli(
                "evaluate-gate",
                "GATE-001",
                "PASS",
                "--workspace",
                str(workspace),
                "--evidence-id",
                evidence,
                "--actor",
                "controller",
                "--waiver-id",
                "WAIVER-001",
                expect=2,
            )
            self.assertEqual(refused["error_code"], "GATE_EXPECTATION_MISMATCH")
            waived = run_cli(
                "evaluate-gate",
                "GATE-001",
                "--workspace",
                str(workspace),
                "--evidence-id",
                evidence,
                "--actor",
                "controller",
                "--waiver-id",
                "WAIVER-001",
            )
            self.assertEqual(waived["result"], "NOT_APPLICABLE_WITH_REASON")
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
