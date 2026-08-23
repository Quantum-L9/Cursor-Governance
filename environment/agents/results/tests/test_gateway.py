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


if __name__ == "__main__":
    unittest.main()
