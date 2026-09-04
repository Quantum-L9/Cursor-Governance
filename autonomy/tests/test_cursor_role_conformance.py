"""Cursor role vocabulary conformance (SA-F01 / SA-F07).

One mapping owner — ``result_bridge.AUTONOMY_ROLE_TO_CURSOR_ROLE`` — resolves
the autonomy role root Autonomy persists (``executor``) to the Cursor role a
result document carries (``test``). The adapter's result-kind map, the roles
YAML, the schema role enum, and the background policy are all projections of
that one table; this suite fails the moment any of them drifts.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

import yaml

from autonomy.adapters.cursor import adapter

ROOT = Path(__file__).resolve().parents[2]
ROLES_PATH = ROOT / "environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml"
SCHEMA_PATH = (
    ROOT / "environment/agents/cursor-subagents/schemas/cursor-subagent-result.schema.json"
)


def _deployment(role: str) -> dict[str, Any]:
    return {
        "agent_contract": {
            "role": role,
            "agent_id": "cursor-agent-1",
            "action_id": "act-1",
            "mutation": role in {"executor", "remediator"},
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
            "completion": {"artifact_kind": "TestReport", "required_fields": ["summary"]},
            "scope": {"claims": []},
            "stop_conditions": ["lease_revoked"],
        },
        "lease": {"lease_id": "lease-1"},
    }


class RoleVocabularyConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = adapter._result_bridge()
        cls.roles = yaml.safe_load(ROLES_PATH.read_text(encoding="utf-8"))["roles"]
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.schema_roles = set(schema["$defs"]["role"]["enum"])
        cls.schema_kinds = set(schema["$defs"]["resultKind"]["enum"])

    def test_adapter_result_kind_projects_the_bridge_vocabulary(self) -> None:
        mapping = self.bridge.AUTONOMY_ROLE_TO_CURSOR_ROLE
        self.assertEqual(set(adapter.CURSOR_ROLE_TO_RESULT_KIND), set(mapping))
        for role, kind in adapter.CURSOR_ROLE_TO_RESULT_KIND.items():
            self.assertEqual(kind, self.bridge.ROLE_TO_RESULT_KIND[mapping[role]], role)

    def test_roles_yaml_schema_and_bridge_agree(self) -> None:
        self.assertEqual(set(self.roles), set(self.bridge.ROLE_TO_RESULT_KIND))
        self.assertEqual(set(self.roles), self.schema_roles)
        self.assertEqual(set(self.bridge.ROLE_TO_RESULT_KIND.values()), self.schema_kinds)
        for cursor_role, definition in self.roles.items():
            autonomy_role = definition["autonomy_role"]
            self.assertEqual(
                self.bridge.AUTONOMY_ROLE_TO_CURSOR_ROLE[autonomy_role], cursor_role, cursor_role
            )
            self.assertEqual(
                definition["result_kind"], self.bridge.ROLE_TO_RESULT_KIND[cursor_role], cursor_role
            )
            self.assertEqual(
                definition["generated_data_role"],
                self.bridge.ROLE_TO_GENERATED_DATA_ROLE[cursor_role],
                cursor_role,
            )
            # Every defined role binds to a managed l9-* agent definition.
            self.assertTrue(
                adapter._cursor_subagent_type(autonomy_role).startswith("l9-"), cursor_role
            )

    def test_canonical_cursor_role_resolves_every_spelling(self) -> None:
        canonical = self.bridge.canonical_cursor_role
        for autonomy_role, cursor_role in self.bridge.AUTONOMY_ROLE_TO_CURSOR_ROLE.items():
            self.assertEqual(canonical(autonomy_role), cursor_role)
            self.assertEqual(canonical(cursor_role), cursor_role)
            self.assertEqual(canonical("l9-" + autonomy_role.replace("_", "-")), cursor_role)
            self.assertEqual(canonical(autonomy_role.upper()), cursor_role)
        self.assertEqual(canonical("l9_verifier"), "verifier_reviewer")
        self.assertEqual(canonical("l9-pr-remediation"), "pr_remediation")
        # Unknown spellings stay unmapped so callers reject them explicitly.
        self.assertEqual(canonical("mystery-role"), "mystery_role")
        self.assertNotIn(canonical("mystery-role"), self.bridge.ROLE_TO_RESULT_KIND)

    def test_run_in_background_follows_roles_yaml(self) -> None:
        for cursor_role, definition in self.roles.items():
            autonomy_role = definition["autonomy_role"]
            expected = bool(definition["default_background"])
            self.assertEqual(adapter.runs_in_background(autonomy_role), expected, cursor_role)
            self.assertEqual(adapter.runs_in_background(cursor_role), expected, cursor_role)
            task = adapter.build_cursor_task(_deployment(autonomy_role))
            self.assertEqual(task["run_in_background"], expected, autonomy_role)

    def test_roles_without_cursor_definition_keep_adapter_policy(self) -> None:
        self.assertTrue(adapter.runs_in_background("poller"))
        self.assertTrue(adapter.runs_in_background("sentinel"))
        self.assertFalse(adapter.runs_in_background("coordinator"))
        self.assertFalse(adapter.build_cursor_task(_deployment("coordinator"))["run_in_background"])


if __name__ == "__main__":
    unittest.main()
