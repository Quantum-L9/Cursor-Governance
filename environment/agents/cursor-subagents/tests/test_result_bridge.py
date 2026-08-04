from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "result_bridge.py"
SCHEMA_PATH = ROOT / "schemas/cursor-subagent-result.schema.json"


def load_bridge():
    spec = importlib.util.spec_from_file_location(
        "l9_cursor_subagent_result_bridge",
        BRIDGE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {BRIDGE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_document(
    *,
    role: str = "recon",
    result_kind: str = "ReconReport",
) -> dict[str, Any]:
    assignment: dict[str, Any] = {
        "role": role,
        "objective": "Inspect the bounded Cursor subagent integration.",
        "input_artifact_ids": [],
        "allowed_paths": ["environment/agents/cursor-subagents/**"],
        "forbidden_paths": ["environment/program-execution/core/**"],
    }
    if role == "verifier_reviewer":
        assignment["subject_agent_id"] = "cursor-executor-1"
    return {
        "schema": "l9.cursor-subagent.result.v1",
        "schema_version": "1.0.0",
        "result_id": "cursor-result-001",
        "result_kind": result_kind,
        "status": "completed",
        "identity": {
            "campaign_id": "cursor-subagent-campaign",
            "graph_id": "cursor-subagent-graph",
            "action_id": "inspect-contract",
            "agent_id": "cursor-recon-1",
            "lease_id": "lease-001",
            "base_sha": "a" * 40,
        },
        "assignment": assignment,
        "deliverable": {
            "summary": "The inspected contract uses campaign terminology.",
            "findings": [
                {
                    "finding_id": "finding-001",
                    "primary_class": "repository_fact",
                    "secondary_tags": ["cursor", "subagent"],
                    "epistemic_status": "observed",
                    "statement": (
                        "The Cursor subagent result contract uses campaign_id "
                        "and contains no legacy program identifier field."
                    ),
                    "scope": {"module": "environment/agents/cursor-subagents"},
                    "confidence": 1.0,
                    "evidence": [
                        {
                            "source_id": "schema-path",
                            "source_type": "repository_path",
                            "path": (
                                "environment/agents/cursor-subagents/"
                                "schemas/cursor-subagent-result.schema.json"
                            ),
                            "base_sha": "a" * 40,
                        }
                    ],
                    "proposed_routes": ["contracts"],
                    "expected_reuse": {
                        "task_local": True,
                        "cross_task": True,
                        "cross_campaign": True,
                        "cross_repository": False,
                        "description": (
                            "The result contract applies across Cursor subagent campaigns."
                        ),
                    },
                    "invalidation_conditions": [
                        {
                            "condition_type": "schema_version_changed",
                            "selector": ("l9.cursor-subagent.result.v1"),
                        }
                    ],
                }
            ],
            "files_read": [
                ("environment/agents/cursor-subagents/schemas/cursor-subagent-result.schema.json")
            ],
            "files_changed": [],
            "evidence": [
                {
                    "source_id": "schema-path",
                    "source_type": "repository_path",
                    "path": (
                        "environment/agents/cursor-subagents/"
                        "schemas/cursor-subagent-result.schema.json"
                    ),
                    "base_sha": "a" * 40,
                }
            ],
            "commands_executed": [],
            "validations": [
                {
                    "validation_id": "schema-inspection",
                    "method": "read_only_inspection",
                    "result": "PASS",
                    "evidence_refs": ["schema-path"],
                }
            ],
            "unresolved_items": [],
            "recommended_next_actions": [],
            "reuse_assessment": {
                "reusable_data_found": True,
                "task_local_value": 5,
                "cross_task_value": 4,
                "cross_repository_value": 0,
                "confidence": 1.0,
                "reason": (
                    "The campaign-bound result format is reusable by future "
                    "Cursor subagent actions."
                ),
            },
            "visibility": "repository_local",
        },
        "provenance": {"produced_at": "2026-08-03T22:43:00-04:00"},
    }


class ResultBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = load_bridge()

    def test_schema_is_valid_json(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertIn("campaign_id", json.dumps(schema))
        self.assertNotIn("program_id", json.dumps(schema))

    def test_valid_recon_document_passes(self) -> None:
        document = self.bridge.with_artifact_digest(valid_document())
        self.bridge.validate_result_document(document)
        self.assertRegex(
            document["provenance"]["artifact_digest"],
            r"^[0-9a-f]{64}$",
        )

    def test_digest_is_deterministic(self) -> None:
        document = valid_document()
        first = self.bridge.compute_artifact_digest(document)
        second = self.bridge.compute_artifact_digest(document)
        self.assertEqual(first, second)

    def test_program_id_is_rejected(self) -> None:
        document = valid_document()
        document["identity"]["program_id"] = "legacy-program"
        with self.assertRaises(self.bridge.ResultValidationError):
            self.bridge.validate_result_document(document)

    def test_role_and_result_kind_must_match(self) -> None:
        document = valid_document(
            role="recon",
            result_kind="TestReport",
        )
        with self.assertRaises(self.bridge.ResultValidationError):
            self.bridge.validate_result_document(document)

    def test_recon_must_not_claim_changed_files(self) -> None:
        document = valid_document()
        document["deliverable"]["files_changed"] = ["environment/agents/cursor-subagents/README.md"]
        with self.assertRaises(self.bridge.ResultValidationError):
            self.bridge.validate_result_document(document)

    def test_reviewer_must_not_review_itself(self) -> None:
        document = valid_document(
            role="verifier_reviewer",
            result_kind="VerificationReviewReport",
        )
        document["identity"]["agent_id"] = "cursor-reviewer-1"
        document["assignment"]["subject_agent_id"] = "cursor-reviewer-1"
        with self.assertRaises(self.bridge.ResultValidationError):
            self.bridge.validate_result_document(document)

    def test_generated_data_packet_uses_campaign_identity(self) -> None:
        packet = self.bridge.to_generated_data_packet(
            valid_document(),
            repository="Quantum-L9/Cursor-Governance",
        )
        self.assertEqual(
            packet["identity"]["campaign_id"],
            "cursor-subagent-campaign",
        )
        self.assertEqual(packet["identity"]["role"], "recon")
        self.assertEqual(
            packet["primary_result"]["artifact_kind"],
            "ReconReport",
        )
        self.assertEqual(len(packet["generated_data_units"]), 1)
        self.assertFalse(packet["generated_data_units"][0]["self_promoted"])
        self.assertNotIn("program_id", json.dumps(packet))

    def test_packet_contains_existing_pipeline_required_fields(self) -> None:
        packet = self.bridge.to_generated_data_packet(
            valid_document(),
            repository="Quantum-L9/Cursor-Governance",
        )
        required = {
            "schema_version",
            "packet_id",
            "identity",
            "primary_result",
            "generated_data_units",
            "reuse_assessment",
            "generated_at",
        }
        self.assertTrue(required.issubset(packet))

    def test_generated_data_role_mapping(self) -> None:
        cases = [
            ("recon", "ReconReport", "recon"),
            (
                "pr_remediation",
                "PRRemediationReport",
                "remediator",
            ),
            ("test", "TestReport", "executor"),
            (
                "documentation",
                "DocumentationReport",
                "evidence_writer",
            ),
            (
                "verifier_reviewer",
                "VerificationReviewReport",
                "reviewer",
            ),
        ]
        for role, result_kind, expected_pipeline_role in cases:
            with self.subTest(role=role):
                document = valid_document(
                    role=role,
                    result_kind=result_kind,
                )
                document["identity"]["agent_id"] = f"cursor-{role}-1"
                if role not in {"recon", "verifier_reviewer"}:
                    document["deliverable"]["files_changed"] = [f"bounded/{role}.md"]
                packet = self.bridge.to_generated_data_packet(
                    document,
                    repository="Quantum-L9/Cursor-Governance",
                )
                self.assertEqual(
                    packet["identity"]["role"],
                    expected_pipeline_role,
                )


if __name__ == "__main__":
    unittest.main()
