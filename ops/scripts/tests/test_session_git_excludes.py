"""Option B session excludes: no tracked .gitignore, no blanket .claude/."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HELPER = REPO / "ops" / "scripts" / "lib" / "session_git_excludes.sh"
BOOTSTRAP = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"
SETUP = REPO / "ops" / "scripts" / "setup_workspace_symlinks.sh"
INSTALL = REPO / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"
SCRIPT = HERE / "test_session_git_excludes.sh"

BLANKET = (".claude/", "/.claude/", ".claude", "/.claude")


class SessionGitExcludesContractTests(unittest.TestCase):
    def test_helper_exists_and_refuses_blanket(self) -> None:
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("session_is_forbidden_blanket_claude", text)
        self.assertIn("apply_session_git_excludes", text)
        self.assertIn("apply_machine_session_excludes", text)
        self.assertIn("session_machine_exclude_globs", text)
        self.assertIn("session_prune_session_only_from_machine_file", text)
        self.assertNotRegex(text, r'(?m)^[ \t]*["\']?/?\.claude/?["\']?[ \t]*$')
        machine_fn = text.split("session_machine_exclude_globs()", 1)[1].split("}", 1)[0]
        self.assertNotIn(".mcp.json", machine_fn)
        self.assertIn(".claude/settings.local.json", machine_fn)
        machine_apply = text.split("apply_machine_session_excludes()", 1)[1]
        self.assertNotIn("session_claude_mirror_exclude_globs", machine_apply)

    def test_shared_bootstrap_applies_option_b(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("lib/session_git_excludes.sh", text)
        self.assertIn("apply_session_git_excludes", text)
        for token in BLANKET:
            self.assertNotIn(f'"{token}"', text)

    def test_setup_wires_machine_excludes(self) -> None:
        text = SETUP.read_text(encoding="utf-8")
        self.assertIn("lib/session_git_excludes.sh", text)
        self.assertIn("apply_machine_session_excludes", text)
        self.assertIn("WARN: cannot write global gitignore", text)

    def test_bootstrap_warns_when_session_excludes_fail(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("could not write session git excludes", text)

    def test_claude_install_reuses_helper(self) -> None:
        text = INSTALL.read_text(encoding="utf-8")
        self.assertIn("session_git_excludes.sh", text)
        self.assertIn("apply_session_claude_mirror_excludes", text)
        self.assertIn("apply_session_untracked_artifact_excludes", text)

    def test_bash_fixture(self) -> None:
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
