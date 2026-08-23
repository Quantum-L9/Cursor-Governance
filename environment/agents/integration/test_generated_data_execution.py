from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from environment.agents.lifecycle import compose_start, compose_stop

BASE_SHA = "a" * 40


def result_document(result_id: str = "result-001") -> dict[str, Any]:
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
            "lease_id": "lease-001",
            "base_sha": BASE_SHA,
        },
        "assignment": {
            "role": "recon",
            "objective": "Inspect the generated-data path.",
            "input_artifact_ids": [],
            "allowed_paths": ["environment/agents/**"],
            "forbidden_paths": [],
        },
        "deliverable": {
            "summary": "The generated-data path has one reusable repository fact.",
            "findings": [
                {
                    "finding_id": "finding-001",
                    "primary_class": "repository_fact",
                    "secondary_tags": ["generated-data"],
                    "epistemic_status": "observed",
                    "statement": "Raw subagent results are persisted before processing.",
                    "scope": {"paths": ["environment/agents/lifecycle"]},
                    "confidence": 0.99,
                    "evidence": [
                        {
                            "source_id": "source-001",
                            "source_type": "repository_path",
                            "repository": "Quantum-L9/Cursor-Governance",
                            "path": "environment/agents/lifecycle/compose_stop.py",
                            "base_sha": BASE_SHA,
                        }
                    ],
                    "proposed_routes": ["memory"],
                    "expected_reuse": {
                        "task_local": False,
                        "cross_task": True,
                        "cross_campaign": True,
                        "cross_repository": False,
                        "description": "The lifecycle invariant applies to every subagent.",
                    },
                    "invalidation_conditions": [
                        {
                            "condition_type": "relevant_path_changed",
                            "selector": "environment/agents/lifecycle",
                        }
                    ],
                }
            ],
            "files_read": ["environment/agents/lifecycle/compose_stop.py"],
            "files_changed": [],
            "evidence": [
                {
                    "source_id": "source-001",
                    "source_type": "repository_path",
                    "repository": "Quantum-L9/Cursor-Governance",
                    "path": "environment/agents/lifecycle/compose_stop.py",
                    "base_sha": BASE_SHA,
                }
            ],
            "commands_executed": [],
            "validations": [
                {
                    "validation_id": "validation-001",
                    "method": "inspection",
                    "result": "PASS",
                    "evidence_refs": ["source-001"],
                }
            ],
            "unresolved_items": [],
            "recommended_next_actions": [],
            "reuse_assessment": {
                "reusable_data_found": True,
                "task_local_value": 2,
                "cross_task_value": 4,
                "cross_repository_value": 0,
                "confidence": 0.99,
                "reason": "The invariant applies to future subagent runs.",
            },
            "visibility": "repository_local",
        },
        "provenance": {"produced_at": "2026-08-23T12:00:00Z"},
    }


class GeneratedDataExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        os.environ["L9_RUNTIME_ROOT"] = self.temp.name
        os.environ.pop("L9_SGD_GRAPHITI_INGEST_COMMAND", None)

    def tearDown(self) -> None:
        os.environ.pop("L9_RUNTIME_ROOT", None)
        os.environ.pop("L9_SGD_GRAPHITI_INGEST_COMMAND", None)
        self.temp.cleanup()

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
                    "parent_agent_id": "cursor",
                    "workspace": self.temp.name,
                    "repository": "Quantum-L9/Cursor-Governance",
                    "repository_class": "governed_repository",
                    "surface": "cursor-ide",
                    "base_sha": BASE_SHA,
                },
                "lease": {"lease_id": "lease-001", "status": "ACTIVE"},
                "deployment_receipt": {"status": "DEPLOYMENT_READY"},
            }
        )
        self.assertEqual(start["permission"], "allow")

    def test_live_stop_captures_raw_and_processes_packet(self) -> None:
        self._start()
        result = compose_stop.compose_subagent_stop(
            {
                "assignment_id": "assignment-001",
                "output": result_document(),
            }
        )
        self.assertEqual(result["status"], "RETURNED")
        self.assertTrue(Path(result["raw_result"]["path"]).is_file())
        pipeline = result["generated_data"]
        self.assertEqual(pipeline["status"], "ACCEPTED")
        self.assertEqual(pipeline["acceptance_receipt"]["status"], "ACCEPTED")
        ingress = pipeline["ingress_receipt"]
        self.assertEqual(ingress["outcome"], "CAPTURED")
        self.assertIn(
            ingress["processing_status"],
            {
                "LEARNING_CLOSED",
                "DESTINATION_SUBMITTED",
                "RETRY_WAIT",
                "DESTINATION_DEFERRED",
                "DESTINATION_ACCEPTED",
            },
        )
        self.assertTrue(Path(ingress["packet_evidence_path"]).is_file())

    def test_repeated_stop_is_idempotent(self) -> None:
        self._start()
        first = compose_stop.compose_subagent_stop(
            {"assignment_id": "assignment-001", "output": result_document()}
        )
        second = compose_stop.compose_subagent_stop(
            {"assignment_id": "assignment-001", "output": result_document()}
        )
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(
            first["generated_data"]["acceptance_receipt"]["receipt_digest"],
            second["generated_data"]["acceptance_receipt"]["receipt_digest"],
        )

    def test_raw_evidence_collision_is_refused(self) -> None:
        self._start()
        compose_stop.compose_subagent_stop(
            {"assignment_id": "assignment-001", "output": result_document()}
        )
        changed = result_document()
        changed["deliverable"]["summary"] = "different result"
        with self.assertRaises(RuntimeError):
            compose_stop.compose_subagent_stop(
                {"assignment_id": "assignment-001", "output": changed}
            )


if __name__ == "__main__":
    unittest.main()
