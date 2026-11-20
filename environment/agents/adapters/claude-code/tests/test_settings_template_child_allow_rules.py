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

One bootstrap path (operator decision 2026-11-20): a swarm child starts from its
lane's primary repository exactly as the CTO session does, so the environment's
Setup script and SessionStart are its whole bootstrap. The Setup stub writes no
permission rule anywhere, and there is no DEGRADED child start or materializer.

These tests pin that the template carries exactly these rules, that they are
narrow, and that the Setup stub writes no settings at all.
"""

from __future__ import annotations

import json
import os
import subprocess
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
    def test_stub_never_writes_settings(self) -> None:
        body = STUB.read_text(encoding="utf-8")
        self.assertNotIn("CHILD_ALLOW_RULES", body)
        self.assertNotIn(".claude/settings", body)
        self.assertNotIn("$PWD/.claude", body)

    def test_there_is_no_child_only_bootstrap(self) -> None:
        body = STUB.read_text(encoding="utf-8")
        for gone in ("l9_install_child_bootstrap", "l9-materialize-governance", "L9_GOV_DEGRADED"):
            self.assertNotIn(gone, body)


if __name__ == "__main__":
    unittest.main()


def _git_repo(path: Path, origin: str) -> Path:

    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", origin], check=True)
    return path


def _run_stub(cwd: Path, home: Path) -> subprocess.CompletedProcess[str]:
    import subprocess

    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "CLAUDE_CODE_REMOTE": "true",
        "GIT_TERMINAL_PROMPT": "0",
        # Unreadable on purpose: the private network clone fails, as it does in
        # a hosted Setup script with no credential.
        "L9_GOVERNANCE_REMOTE": f"file://{cwd}/no-such-remote",
    }
    return subprocess.run(
        ["bash", str(STUB)], cwd=cwd, env=env, capture_output=True, text=True, check=False
    )


class OneBootstrapPath(unittest.TestCase):
    """A session with no governance source fails closed, whatever else it holds."""

    def setUp(self) -> None:

        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.work = self.root / "work"
        self.work.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ordinary_session_without_governance_fails_closed(self) -> None:
        result = _run_stub(self.work, self.home)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse((self.home / ".l9" / "bin").exists())
        self.assertFalse((self.home / ".claude" / "settings.json").exists())

    def test_dotgithub_only_layout_is_not_special_and_fails_closed(self) -> None:
        _git_repo(self.work / ".github", "https://github.com/Quantum-L9/.github")
        result = _run_stub(self.work, self.home)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("DEGRADED", result.stdout + result.stderr)
        self.assertFalse((self.home / ".l9" / "bin").exists())
        self.assertFalse((self.home / ".claude" / "settings.json").exists())

    def test_governance_named_checkout_with_a_foreign_origin_is_not_trusted(self) -> None:
        _git_repo(
            self.work / "Cursor-Governance", "https://github.com/someone-else/Cursor-Governance"
        )
        result = _run_stub(self.work, self.home)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse((self.home / ".cursor-governance").exists())
