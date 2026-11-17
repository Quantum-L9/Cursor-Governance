#!/usr/bin/env python3
"""Swarm-child pre-approvals live in the governed Claude settings template.

Since 2026-11-16 Quantum-L9/.github and Quantum-L9/Cursor-Governance are
private. A /lcto swarm child starts with Quantum-L9/.github as its only session
source and must attach its other repositories with add_repo. In auto mode that
call, issued from the CTO's launch brief, is denied unless a permission rule
allows it (observed 2026-11-17 in session_017xwbxuvn1zQGzdYT5aPg5e: denied as
"[Unauthorized Access]" until the operator allowed it by hand).

The rules live in settings.template.json, the one source every workspace's
.claude/settings.json is projected from, at setup and again at every
SessionStart. They are deliberately NOT injected by the environment Setup stub:
SessionStart re-projects untracked workspace settings wholly from the template
(reconcile_claude_settings.merge_workspace_settings), so an injected rule is
removed again, and injecting would also edit repository-owned settings.

These tests pin that the template carries exactly these rules, that they are
narrow, and that the Setup stub does not inject them.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
TEMPLATE = ADAPTER / "settings.template.json"
STUB = ADAPTER / "web" / "setup.bootstrap.sh"

EXPECTED_RULES = [
    "mcp__claude-code-remote__add_repo",
    "mcp__claude-code-remote__register_repo_root",
    'Bash("$HOME/.cursor-governance/.venv/bin/python" '
    + '"$HOME/.cursor-governance/ops/autonomy/session_role.py" register-child:*)',
    'Bash("$HOME/.cursor-governance/.venv/bin/python" '
    + '"$HOME/.cursor-governance/ops/autonomy/coding_agent_mode.py" on:*)',
    "Bash(GOVERNANCE_SYNC_PUSH=0 GOVERNANCE_SYNC_HARD_RESET=0 bash "
    + '"$HOME/.cursor-governance/skills/l9-repo-sync/scripts/ff.sh" --ssot:*)',
]


def template_allow() -> list[str]:
    return list(json.loads(TEMPLATE.read_text(encoding="utf-8"))["permissions"]["allow"])


class TemplateCarriesRules(unittest.TestCase):
    def test_every_rule_is_in_the_template_allow_list_once(self) -> None:
        allow = template_allow()
        for rule in EXPECTED_RULES:
            self.assertEqual(allow.count(rule), 1, rule)


class RulesAreNarrow(unittest.TestCase):
    def test_no_rule_grants_arbitrary_execution(self) -> None:
        for rule in EXPECTED_RULES:
            self.assertNotIn(rule, {"Bash(*)", "Bash", "Bash(python*)", "Bash(bash*)"})
            if rule.startswith("Bash("):
                body = rule[len("Bash(") : -1]
                self.assertTrue(body.endswith(":*"), rule)
                prefix = body[: -len(":*")]
                self.assertIn("$HOME/.cursor-governance/", prefix, rule)
                self.assertRegex(prefix, r"(register-child|\bon|--ssot)$", rule)

    def test_no_off_switch_or_setup_script_is_pre_approved(self) -> None:
        joined = "\n".join(template_allow())
        self.assertNotIn('coding_agent_mode.py" off', joined)
        self.assertNotIn("setup.sh", joined)


class SetupStubDoesNotInject(unittest.TestCase):
    def test_stub_never_writes_permission_rules(self) -> None:
        body = STUB.read_text(encoding="utf-8")
        self.assertNotIn("mcp__claude-code-remote__add_repo", body)
        self.assertNotIn("CHILD_ALLOW_RULES", body)


if __name__ == "__main__":
    unittest.main()
