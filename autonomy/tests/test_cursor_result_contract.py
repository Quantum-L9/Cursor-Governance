from __future__ import annotations

import unittest
from typing import Any

from autonomy.adapters.cursor.adapter import (
    CURSOR_SUBAGENT_RESULT_SCHEMA,
    build_cursor_task,
)


def _deployment(role: str) -> dict[str, Any]:
    return {
        "agent_contract": {
            "role": role,
            "agent_id": "cursor-agent-1",
            "action_id": "act-1",
            "mutation": role not in {"recon", "reviewer", "verifier"},
            "campaign_id": "camp-1",
            "graph_id": "graph-1",
            "lease_id": "lease-1",
            "capability_id": "cap-1",
            "base_sha": "a" * 40,
            "objective": "Perform one bounded action.",
            "authority": {
                "allowed_capabilities": ["repository.read"],
                "globally_forbidden_capabilities": ["merge"],
            },
            "completion": {
                "artifact_kind": "TestReport",
                "required_fields": ["summary"],
            },
            "scope": {"claims": [{"mode": "write", "key": "path:x", "exclusive": True}]},
            "stop_conditions": ["lease_revoked"],
        },
        "lease": {"lease_id": "lease-1"},
    }


class CursorResultContractTests(unittest.TestCase):
    def test_mapped_role_gets_result_contract(self) -> None:
        task = build_cursor_task(_deployment("executor"))
        contract = task["result_contract"]
        self.assertEqual(contract["schema"], CURSOR_SUBAGENT_RESULT_SCHEMA)
        self.assertEqual(contract["result_kind"], "TestReport")
        self.assertEqual(contract["required_output"], "one_structured_document")
        self.assertFalse(contract["narrative_only_completion_allowed"])

    def test_recon_maps_to_recon_report(self) -> None:
        task = build_cursor_task(_deployment("recon"))
        self.assertEqual(task["result_contract"]["result_kind"], "ReconReport")

    def test_unmapped_role_has_no_result_contract(self) -> None:
        task = build_cursor_task(_deployment("coordinator"))
        self.assertNotIn("result_contract", task)
        self.assertEqual(task["subagent_type"], "generalPurpose")
        self.assertFalse(task["subagent_type"].startswith("l9-"))

    def test_managed_roles_emit_l9_task_types(self) -> None:
        expected = {
            "recon": "l9-recon",
            "remediator": "l9-pr-remediation",
            "executor": "l9-test",
            "test": "l9-test",
            "evidence_writer": "l9-documentation",
            "documentation": "l9-documentation",
            "reviewer": "l9-verifier-reviewer",
            "verifier": "l9-verifier-reviewer",
            "verifier_reviewer": "l9-verifier-reviewer",
        }
        for role, name in expected.items():
            task = build_cursor_task(_deployment(role))
            self.assertEqual(task["subagent_type"], name, role)


if __name__ == "__main__":
    unittest.main()
