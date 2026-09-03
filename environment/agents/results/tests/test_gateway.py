from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from environment.agents.lifecycle import compose_start
from environment.agents.results import gateway

BASE_SHA = "a" * 40


def result_document(
    *, result_id: str = "result-001", lease_id: str = "lease-001"
) -> dict[str, Any]:
    return {
        "schema": "l9.cursor-subagent.result.v1",
        "schema_version": "1.0.0",
        "result_id": result_id,
        "result_kind": "ReconReport",
        "status": "completed",
        "identity": {
            "campaign_id": "campaign-001",
            "graph_id": "graph-001",
            "action_id": "action-001",
            "agent_id": "agent-001",
            "lease_id": lease_id,
            "base_sha": BASE_SHA,
        },
        "assignment": {
            "role": "recon",
            "objective": "Inspect the generated-data seam.",
            "input_artifact_ids": [],
            "allowed_paths": ["environment/agents/**"],
            "forbidden_paths": [],
        },
        "deliverable": {
            "summary": "One durable result was produced.",
            "findings": [],
            "files_read": ["environment/agents/results/gateway.py"],
            "files_changed": [],
            "evidence": [],
            "commands_executed": [],
            "validations": [],
            "unresolved_items": [],
            "recommended_next_actions": [],
            "reuse_assessment": {
                "reusable_data_found": False,
                "confidence": 1.0,
                "reason": "No reusable finding in this gateway fixture.",
            },
            "visibility": "repository_local",
        },
        "provenance": {"produced_at": "2026-08-23T12:00:00Z"},
    }


class GatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name
        start = compose_start.compose_subagent_start(
            {
                "assignment": {
                    "assignment_id": "assignment-001",
                    "campaign_id": "campaign-001",
                    "graph_id": "graph-001",
                    "action_id": "action-001",
                    "agent_id": "agent-001",
                    "subagent_role": "recon",
                    "result_role": "recon",
                    "objective": "Inspect the generated-data seam.",
                    "allowed_paths": ["environment/agents/**"],
                    "forbidden_paths": [],
                    "workspace": self.tmp.name,
                    "base_sha": BASE_SHA,
                },
                "lease": {"lease_id": "lease-001", "status": "ACTIVE"},
                "deployment_receipt": {"status": "DEPLOYMENT_READY"},
            }
        )
        self.assertEqual(start["permission"], "allow")
        self.return_receipt = {
            "assignment_id": "assignment-001",
            "status": "RETURNED",
            "campaign_id": "campaign-001",
            "graph_id": "graph-001",
            "action_id": "action-001",
            "agent_id": "agent-001",
            "lease_id": "lease-001",
            "base_sha": BASE_SHA,
            "parent_agent_id": "cursor",
            "surface": "cursor-ide",
        }

    def tearDown(self) -> None:
        os.environ.pop("L9_RUNTIME_ROOT", None)
        self.tmp.cleanup()

    def test_reject_without_return(self) -> None:
        out = gateway.accept(
            return_receipt=None,
            surface_result=result_document(),
        )
        self.assertEqual(out["status"], "REJECTED")

    def test_accept_is_idempotent(self) -> None:
        first = gateway.accept(
            return_receipt=self.return_receipt,
            surface_result=result_document(),
        )
        second = gateway.accept(
            return_receipt=self.return_receipt,
            surface_result=result_document(),
        )
        self.assertEqual(first["status"], "ACCEPTED")
        self.assertEqual(first["receipt_digest"], second["receipt_digest"])

    def test_failed_ingress_is_not_reported_as_successful_handoff(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "gateway.py").read_text(encoding="utf-8")
        self.assertIn('handoff_status = "FAILED"', source)
        self.assertIn('"generated_data_status": ingress_outcome', source)

    def test_wrong_lease_is_rejected(self) -> None:
        out = gateway.accept(
            return_receipt=self.return_receipt,
            surface_result=result_document(result_id="result-wrong", lease_id="lease-wrong"),
        )
        self.assertEqual(out["status"], "REJECTED")
        self.assertIn("lease", out["reason"])

    def test_result_id_collision_is_refused(self) -> None:
        gateway.accept(
            return_receipt=self.return_receipt,
            surface_result=result_document(),
        )
        changed = result_document()
        changed["deliverable"]["summary"] = "Different content under the same result ID."
        with self.assertRaises(RuntimeError):
            gateway.accept(
                return_receipt=self.return_receipt,
                surface_result=changed,
            )

    def test_shallow_narrative_result_is_rejected(self) -> None:
        out = gateway.accept(
            return_receipt=self.return_receipt,
            surface_result={"status": "completed", "result_id": "not-a-contract"},
        )
        self.assertEqual(out["status"], "REJECTED")
        self.assertIn("validation failed", out["reason"])

    def test_host_terminal_failure_status_rejects_a_valid_document(self) -> None:
        for host_status in ("CANCELLED", "error", "timeout", "killed", "FAILED"):
            out = gateway.accept(
                return_receipt={**self.return_receipt, "host_status": host_status},
                surface_result=result_document(result_id=f"result-{host_status.lower()}"),
            )
            self.assertEqual(out["status"], "REJECTED", host_status)
            self.assertIn(host_status, out["reason"])
        ok = gateway.accept(
            return_receipt={**self.return_receipt, "host_status": "COMPLETED"},
            surface_result=result_document(result_id="result-completed"),
        )
        self.assertEqual(ok["status"], "ACCEPTED")

    def test_unavailable_root_database_rejects_rather_than_trusting_the_document(self) -> None:
        out = gateway.accept(
            return_receipt={
                **self.return_receipt,
                "runtime_database": str(Path(self.tmp.name) / "absent.sqlite3"),
            },
            surface_result=result_document(result_id="result-no-db"),
        )
        self.assertEqual(out["status"], "REJECTED")
        self.assertIn("undeterminable", out["reason"])

    def test_correlation_rejection_leaves_a_durable_receipt(self) -> None:
        document = result_document(result_id="result-wrong-role")
        document["result_kind"] = "TestReport"
        document["assignment"]["role"] = "test"
        out = gateway.accept_and_ingest(
            return_receipt=self.return_receipt,
            surface_result=document,
            repository="local/test",
        )
        self.assertEqual(out["status"], "REJECTED")
        receipt = out["acceptance_receipt"]
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["status"], "REJECTED")
        self.assertIn("role", receipt["reason"])
        from environment.agents.results import receipts as result_receipts

        path = result_receipts.acceptance_path(receipt["result_id"], receipt["assignment_id"])
        self.assertTrue(path.is_file(), path)

    def test_partial_document_is_accepted_incomplete(self) -> None:
        document = result_document(result_id="result-partial")
        document["status"] = "partial"
        out = gateway.accept_and_ingest(
            return_receipt=self.return_receipt,
            surface_result=document,
            repository="local/test",
        )
        self.assertEqual(out["status"], "ACCEPTED_INCOMPLETE", out)
        self.assertEqual(out["document_status"], "partial")
        self.assertEqual(out["result_acceptance_status"], "ACCEPTED")
        self.assertEqual(out["acceptance_receipt"]["document_status"], "partial")

    def test_same_result_id_under_another_assignment_is_not_a_collision(self) -> None:
        compose_start.compose_subagent_start(
            {
                "assignment": {
                    "assignment_id": "assignment-002",
                    "campaign_id": "campaign-001",
                    "graph_id": "graph-001",
                    "action_id": "action-002",
                    "agent_id": "agent-002",
                    "subagent_role": "recon",
                    "result_role": "recon",
                    "objective": "Inspect a second seam.",
                    "allowed_paths": ["environment/agents/**"],
                    "forbidden_paths": [],
                    "workspace": self.tmp.name,
                    "base_sha": BASE_SHA,
                },
                "lease": {"lease_id": "lease-002", "status": "ACTIVE"},
                "deployment_receipt": {"status": "DEPLOYMENT_READY"},
            }
        )
        first = gateway.accept(return_receipt=self.return_receipt, surface_result=result_document())
        second_document = result_document(lease_id="lease-002")
        second_document["identity"]["action_id"] = "action-002"
        second_document["identity"]["agent_id"] = "agent-002"
        second = gateway.accept(
            return_receipt={
                **self.return_receipt,
                "assignment_id": "assignment-002",
                "action_id": "action-002",
                "agent_id": "agent-002",
                "lease_id": "lease-002",
            },
            surface_result=second_document,
        )
        self.assertEqual(first["status"], "ACCEPTED")
        self.assertEqual(second["status"], "ACCEPTED", second)
        self.assertNotEqual(first["receipt_digest"], second["receipt_digest"])
        from environment.agents.results import receipts as result_receipts

        self.assertNotEqual(
            result_receipts.acceptance_path("result-001", "assignment-001"),
            result_receipts.acceptance_path("result-001", "assignment-002"),
        )
        with self.assertRaises(ValueError):
            result_receipts.acceptance_path("result-001", "../escape")


if __name__ == "__main__":
    unittest.main()
