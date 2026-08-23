from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from environment.agents.integration.test_generated_data_execution import (
    BASE_SHA,
    result_document,
)
from environment.agents.lifecycle import compose_start, compose_stop
from environment.agents.readiness import compose as readiness

INGRESS = Path(__file__).resolve().parents[1] / "generated-data" / "ingress"
sys.path.insert(0, str(INGRESS))
import ingest  # noqa: E402


class ClosedLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("HOME")
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name
        os.environ["HOME"] = self.tmp.name
        os.environ.pop("L9_SGD_GRAPHITI_INGEST_COMMAND", None)

    def tearDown(self) -> None:
        os.environ.pop("L9_RUNTIME_ROOT", None)
        os.environ.pop("L9_SGD_GRAPHITI_INGEST_COMMAND", None)
        if self.old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.old_home
        self.tmp.cleanup()

    def _start(self) -> None:
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
                    "objective": "Inspect the generated-data path.",
                    "allowed_paths": ["environment/agents/**"],
                    "forbidden_paths": [],
                    "parent_agent_id": "cursor",
                    "workspace": self.tmp.name,
                    "repository": "Quantum-L9/Cursor-Governance",
                    "surface": "cursor-ide",
                    "base_sha": BASE_SHA,
                },
                "lease": {"lease_id": "lease-001", "status": "ACTIVE"},
                "deployment_receipt": {"status": "DEPLOYMENT_READY"},
            }
        )
        self.assertEqual(start["permission"], "allow")

    def test_happy_path_reaches_processor(self) -> None:
        self._start()
        stopped = compose_stop.compose_subagent_stop(
            {"assignment_id": "assignment-001", "output": result_document()}
        )
        self.assertEqual(stopped["status"], "RETURNED")
        pipeline = stopped["generated_data"]
        acceptance = pipeline["acceptance_receipt"]
        ingress_receipt = pipeline["ingress_receipt"]
        self.assertEqual(acceptance["status"], "ACCEPTED")
        self.assertEqual(ingress_receipt["outcome"], "CAPTURED")
        self.assertNotEqual(ingress_receipt["processing_status"], "PENDING")
        self.assertTrue(
            readiness.completion_evidence_ok(
                return_receipt=stopped["return_receipt"],
                acceptance_receipt=acceptance,
                ingress_receipt=ingress_receipt,
            )["allowed"]
        )

    def test_readiness_rejects_pending_and_failed_handoffs(self) -> None:
        common = {
            "return_receipt": {"status": "RETURNED"},
            "acceptance_receipt": {"status": "ACCEPTED"},
        }
        pending = readiness.completion_evidence_ok(
            **common,
            ingress_receipt={
                "outcome": "CAPTURED",
                "processor_job_id": "job-1",
                "processing_status": "PENDING",
            },
        )
        failed = readiness.completion_evidence_ok(
            **common,
            ingress_receipt={
                "outcome": "FAILED",
                "processor_job_id": "job-1",
                "processing_status": "FAILED",
            },
        )
        submitted = readiness.completion_evidence_ok(
            **common,
            ingress_receipt={
                "outcome": "CAPTURED",
                "processor_job_id": "job-1",
                "processing_status": "DESTINATION_SUBMITTED",
            },
        )
        self.assertFalse(pending["allowed"])
        self.assertFalse(failed["allowed"])
        self.assertTrue(submitted["allowed"])

    def test_failure_matrix_and_secret_quarantine(self) -> None:
        self.assertFalse(
            readiness.completion_evidence_ok(
                return_receipt={"status": "RETURNED"},
                acceptance_receipt=None,
                ingress_receipt={"outcome": "CAPTURED"},
            )["allowed"]
        )
        quarantined = ingest.ingest_packet(
            generated_data_packet={"token": "password=hunter2"},
            source_receipt_digest="acceptance-secret",
            source_kind="test",
            actor="test",
            repository_root=Path(__file__).resolve().parents[3],
        )
        self.assertEqual(quarantined["outcome"], "QUARANTINED")
        self.assertEqual(quarantined["processing_status"], "NOT_STARTED")
        self.assertTrue(Path(quarantined["packet_evidence_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
