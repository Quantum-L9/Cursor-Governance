from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_replan import digest_object, validate_revision  # noqa: E402


def _revision(**overrides: object) -> dict:
    payload = {
        "schema": "program-execution.replan.revision.v1",
        "revision_id": "REV-001",
        "program_id": "bounded-replanning-v1",
        "program_lock_digest": "a" * 64,
        "previous_plan_revision": "plan-rev-0",
        "proposed_plan_revision": "plan-rev-0+REV-001",
        "trigger_evidence_ids": ["EVID-006"],
        "affected_future_task_ids": ["TASK-003"],
        "delta": {
            "classes": ["retry_failed_compliant_path"],
            "operations": [
                {"op": "retry", "target_task_id": "TASK-003", "note": "retry after flake"}
            ],
        },
        "authority_containment": {
            "result": "PASS",
            "forbidden_classes_present": [],
            "widens_lock": False,
        },
        "expected_validation_effect": "preserve_lock_retry_future_task",
        "proposer_actor": "worker",
        "verifier_actor": "controller-verifier",
        "status": "proposed",
        "created_at": "2026-08-14T21:00:00+00:00",
        "activated_at": None,
        "rejected_reason": None,
    }
    payload.update(overrides)
    body = {k: v for k, v in payload.items() if k != "revision_digest"}
    payload["revision_digest"] = digest_object(body)
    return payload


class ReplanContractTests(unittest.TestCase):
    def test_positive_revision_passes(self) -> None:
        self.assertEqual(validate_revision(_revision()), [])

    def test_objective_widening_fails(self) -> None:
        revision = _revision(
            delta={
                "classes": ["objective"],
                "operations": [{"op": "adapt_strategy", "target_task_id": "TASK-003"}],
            },
            authority_containment={
                "result": "FAIL",
                "forbidden_classes_present": ["objective"],
                "widens_lock": True,
            },
        )
        errors = validate_revision(revision)
        self.assertTrue(any("forbidden" in e or "widens" in e for e in errors))

    def test_permission_widening_fails(self) -> None:
        revision = _revision(
            delta={
                "classes": ["authorization_ceiling"],
                "operations": [{"op": "adapt_strategy", "target_task_id": "TASK-003"}],
            },
            authority_containment={
                "result": "PASS",
                "forbidden_classes_present": [],
                "widens_lock": False,
            },
        )
        errors = validate_revision(revision)
        self.assertTrue(any("forbidden" in e for e in errors))

    def test_self_verification_fails(self) -> None:
        errors = validate_revision(_revision(proposer_actor="same", verifier_actor="same"))
        self.assertTrue(any("proposer_actor" in e for e in errors))

    def test_digest_tamper_fails(self) -> None:
        revision = _revision()
        revision["revision_digest"] = hashlib.sha256(b"tamper").hexdigest()
        errors = validate_revision(revision)
        self.assertTrue(any("revision_digest" in e for e in errors))

    def test_cli_positive_fixture(self) -> None:
        revision = _revision()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rev.json"
            path.write_text(json.dumps(revision), encoding="utf-8")
            from subprocess import run

            proc = run(
                [sys.executable, str(ROOT / "scripts/validate_replan.py"), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
