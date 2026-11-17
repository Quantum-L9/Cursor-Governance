#!/usr/bin/env python3
"""Swarm-child pre-approvals reach every cloud container through the Setup stub.

Since 2026-11-16 Quantum-L9/.github and Quantum-L9/Cursor-Governance are
private. A /lcto swarm child starts with Quantum-L9/.github as its only session
source and must attach its other repositories with add_repo. In auto mode that
call, issued from the CTO's launch brief, is denied unless a permission rule
allows it (observed 2026-11-17 in session_017xwbxuvn1zQGzdYT5aPg5e: denied as
"[Unauthorized Access]" until the operator allowed it by hand).

settings.template.json carries the rules for every surface. A child's governance
clone is a stale environment snapshot it cannot refresh, so the Setup stub, the
only bootstrap code current in every container, merges the same rules into each
workspace's .claude/settings.json. These tests pin:

* the template and the stub carry the same five rules;
* the rules are narrow (nothing that grants arbitrary execution);
* the stub's merge is a union: it adds missing rules, keeps everything else,
  is idempotent, and creates the file when absent.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
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

HEREDOC = re.compile(
    r"<<'L9_CHILD_ALLOW_PY'[^\n]*\n(?:[^\n]*\n)*?(?P<body>import json.*?)\nL9_CHILD_ALLOW_PY\n",
    re.DOTALL,
)


def stub_merge_program() -> str:
    match = HEREDOC.search(STUB.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError("setup.bootstrap.sh has no L9_CHILD_ALLOW_PY merge block")
    return match.group("body") + "\n"


def stub_rules() -> list[str]:
    namespace: dict[str, object] = {}
    program = stub_merge_program()
    head = program.split("path = sys.argv[1]", 1)[0]
    exec(compile(head, str(STUB), "exec"), namespace)  # noqa: S102 - literal list only
    rules = namespace["CHILD_ALLOW_RULES"]
    assert isinstance(rules, list)
    return [str(rule) for rule in rules]


def run_merge(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-", str(path)],
        input=stub_merge_program(),
        capture_output=True,
        text=True,
        check=False,
    )


class TemplateCarriesRules(unittest.TestCase):
    def test_every_rule_is_in_the_template_allow_list(self) -> None:
        allow = json.loads(TEMPLATE.read_text(encoding="utf-8"))["permissions"]["allow"]
        for rule in EXPECTED_RULES:
            self.assertIn(rule, allow)

    def test_stub_list_equals_the_expected_list(self) -> None:
        self.assertEqual(stub_rules(), EXPECTED_RULES)


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
        joined = "\n".join(EXPECTED_RULES)
        self.assertNotIn('coding_agent_mode.py" off', joined)
        self.assertNotIn("setup.sh", joined)

    def test_stub_stays_backtick_free(self) -> None:
        self.assertNotIn("\x60", STUB.read_text(encoding="utf-8"))


class StubMergeIsAUnion(unittest.TestCase):
    def test_creates_the_file_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".claude" / "settings.json"
            result = run_merge(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["permissions"]["allow"], EXPECTED_RULES)

    def test_keeps_existing_keys_and_rules_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".claude" / "settings.json"
            path.parent.mkdir()
            existing = {
                "hooks": {"Stop": []},
                "permissions": {"allow": ["Bash(git status:*)", EXPECTED_RULES[0]], "deny": ["X"]},
            }
            path.write_text(json.dumps(existing), encoding="utf-8")
            result = run_merge(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["hooks"], {"Stop": []})
            self.assertEqual(data["permissions"]["deny"], ["X"])
            allow = data["permissions"]["allow"]
            self.assertEqual(allow[:2], ["Bash(git status:*)", EXPECTED_RULES[0]])
            self.assertEqual(allow[2:], EXPECTED_RULES[1:])

    def test_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".claude" / "settings.json"
            run_merge(path)
            first = path.read_text(encoding="utf-8")
            result = run_merge(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("+0", result.stdout)
            self.assertEqual(path.read_text(encoding="utf-8"), first)

    def test_refuses_a_non_object_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("[]", encoding="utf-8")
            result = run_merge(path)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "[]")


if __name__ == "__main__":
    unittest.main()
