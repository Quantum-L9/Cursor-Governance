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

Exception, 2026-11-20 (DEGRADED start): a child container has no governance
source at Setup at all (its only source is Quantum-L9/.github and Setup holds no
GitHub credential), so neither projection can run before the session starts.
Only then does the stub write three narrow rules to USER scope, never to a
workspace settings file, and the first web/setup.sh run replaces them with the
template's. See DEGRADED_USER_RULES.

These tests pin that the template carries exactly these rules, that they are
narrow, and that the Setup stub writes nothing else.
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


#: The only rules the Setup stub may write, and only on a DEGRADED start (no
#: governance source on disk). 2026-11-20: a swarm child starts with
#: Quantum-L9/.github as its only source and Setup holds no GitHub credential, so
#: the template projection above cannot reach it before the session starts, and
#: in-session both the push attach ("[Unauthorized Access]") and web/setup.sh
#: ("[Undermining Oversight]") are refused without a rule. These three break that
#: cycle; web/setup.sh then re-projects user permissions wholly from the template.
DEGRADED_USER_RULES = [
    "mcp__claude-code-remote__add_repo",
    "mcp__claude-code-remote__register_repo_root",
    'Bash(bash "$HOME/.l9/bin/l9-materialize-governance":*)',
]


class SetupStubDoesNotInject(unittest.TestCase):
    def test_stub_never_writes_workspace_settings(self) -> None:
        body = STUB.read_text(encoding="utf-8")
        self.assertNotIn("CHILD_ALLOW_RULES", body)
        self.assertNotIn(".claude/settings.local.json", body)
        self.assertNotIn("$PWD/.claude", body)

    def test_stub_writes_only_the_degraded_user_rules_to_user_scope(self) -> None:
        body = STUB.read_text(encoding="utf-8")
        self.assertIn('settings="$HOME/.claude/settings.json"', body)
        for rule in DEGRADED_USER_RULES:
            self.assertIn(repr(rule) if rule.startswith("Bash(") else f'"{rule}"', body)
        start = body.index("rules = [")
        block = body[start : body.index("]", start)]
        self.assertEqual(block.count("\n    "), len(DEGRADED_USER_RULES))

    def test_degraded_bootstrap_runs_only_without_a_governance_source(self) -> None:
        body = STUB.read_text(encoding="utf-8")
        calls = [
            line.strip()
            for line in body.splitlines()
            if line.strip() == "l9_install_child_bootstrap"
        ]
        self.assertEqual(len(calls), 1)
        self.assertIn("L9_GOV_DEGRADED=1", body)

    def test_materialize_rule_is_dropped_by_the_template_projection(self) -> None:
        self.assertNotIn(DEGRADED_USER_RULES[2], template_allow())


if __name__ == "__main__":
    unittest.main()
