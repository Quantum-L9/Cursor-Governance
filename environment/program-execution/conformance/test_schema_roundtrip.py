from __future__ import annotations

import unittest
from pathlib import Path

from adapters.common.core_receipts import attempt_receipt, verification_receipt
from adapters.common.digests import digest_object
from adapters.common.models import CapabilityReceipt, LifecycleReceipt
from adapters.common.schema_registry import SchemaRegistry

from conformance.helpers import CANDIDATE_SHA, PROGRAM_DIGEST, valid_contract


class SchemaRoundtripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.schemas = SchemaRegistry(self.root)

    def test_capability_and_lifecycle_receipts_validate(self) -> None:
        capability = CapabilityReceipt.create(
            adapter_id="fixture-adapter",
            adapter_version="1.0.0",
            status="PASS",
            capabilities=["inspect"],
            program_lock_digest=PROGRAM_DIGEST,
        )
        lifecycle = LifecycleReceipt.create(
            adapter_id="fixture-adapter",
            adapter_version="1.0.0",
            phase="probe",
            program_lock_digest=PROGRAM_DIGEST,
            status="PASS",
        )
        self.assertEqual(self.schemas.validate_capability(capability.to_dict()), [])
        self.assertEqual(self.schemas.validate_lifecycle(lifecycle.to_dict()), [])

    def test_core_attempt_and_verification_receipts_validate(self) -> None:
        contract = valid_contract()
        attempt = attempt_receipt(
            contract,
            candidate_sha=CANDIDATE_SHA,
            changed_files=["src/example.py"],
            validation_results=[
                {
                    "command": "python3 -V",
                    "status": "PASS",
                    "exit_code": 0,
                    "evidence": "sha256:" + "4" * 64,
                }
            ],
            produced_evidence=[{"type": "fixture"}],
        )
        verification = verification_receipt(
            contract,
            candidate_sha=CANDIDATE_SHA,
            declared_changed_files=["src/example.py"],
            observed_changed_files=["src/example.py"],
            validations=[{"status": "PASS"}],
            gates={"validation": "PASS"},
        )
        self.assertEqual(self.schemas.validate_terminal_receipt(attempt), [])
        self.assertEqual(self.schemas.validate_terminal_receipt(verification), [])

    def test_remote_and_deployment_receipts_validate(self) -> None:
        contract = valid_contract()
        remote = {
            "schema": "program-execution-adapter.remote-action-receipt.v1",
            "action": "read_checks",
            "repository": "Quantum-L9/example",
            "task_id": "TASK-001",
            "program_lock_digest": PROGRAM_DIGEST,
            "contract_digest": contract["contract_digest"],
            "approval_id": "READ_ONLY",
            "result": {},
            "evidence": [],
        }
        remote["receipt_digest"] = digest_object(remote)
        deployment = {
            "schema": "program-execution-adapter.deployment-receipt.v1",
            "operation": "read_environment",
            "repository": "Quantum-L9/example",
            "environment": "production",
            "ref": CANDIDATE_SHA,
            "artifact_digest": "sha256:" + "5" * 64,
            "approval_id": "READ_ONLY",
            "rollback_plan_digest": "sha256:" + "6" * 64,
            "result": {},
        }
        deployment["receipt_digest"] = digest_object(deployment)
        self.assertEqual(self.schemas.validate_terminal_receipt(remote), [])
        self.assertEqual(self.schemas.validate_terminal_receipt(deployment), [])


if __name__ == "__main__":
    unittest.main()
