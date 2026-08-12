#!/usr/bin/env python3
"""Behavioral proof that the memory gate enforces (denies) rather than advises.

Network-free assertions run everywhere. A live section that exercises a real
live Graphiti phase-lock section runs only when GRAPHITI_MCP_URL/TOKEN are
reachable; CI without Graphiti stays green.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent.parent
GATE = CLAUDE_DIR / "hooks" / "memory_gate.py"
PREFETCH = CLAUDE_DIR / "hooks" / "memory_prefetch.py"
LOCK = CLAUDE_DIR / "hooks" / "memory_lock.py"
MEM = CLAUDE_DIR / "memory"
sys.path.insert(0, str(MEM))
import memory_state as st  # noqa: E402


def run_gate(event: dict, env: dict) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    return proc.stdout, proc.returncode


def is_deny(stdout: str) -> bool:
    try:
        out = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return False
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class MemoryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = tempfile.mkdtemp()
        self.session = "test-session-abc"
        self.env = {**os.environ, "CLAUDE_PROJECT_DIR": self.workspace}
        # Route state into the temp workspace for in-process helpers too, and
        # restore the prior value in tearDown so tests do not leak across files.
        self._prev_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = self.workspace
        self.contract = st.load_contract()

    def tearDown(self) -> None:
        if self._prev_project_dir is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = self._prev_project_dir

    def _write_receipt(self) -> None:
        st.write_receipt(self.contract, self.session, {"namespaces": ["cursor-governance"]})

    def test_denies_governed_write_without_receipt(self) -> None:
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertTrue(is_deny(out), "authority edit with no prefetch must be denied")

    def test_allows_non_governed_tool(self) -> None:
        out, code = run_gate(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(is_deny(out))
        self.assertEqual(code, 0)

    def test_allows_edit_other_with_receipt(self) -> None:
        self._write_receipt()
        out, _ = run_gate(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "notes.txt"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(is_deny(out), "non-authority edit with a receipt needs only prefetch")

    def test_denies_authority_edit_without_lock(self) -> None:
        self._write_receipt()
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertTrue(is_deny(out), "authority edit requires a phase-lock, not just prefetch")

    def test_denies_git_push_without_lock(self) -> None:
        self._write_receipt()
        out, _ = run_gate(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git push origin main"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertTrue(is_deny(out))

    def test_enforcement_off_is_not_a_side_door(self) -> None:
        """L9_MEMORY_ENFORCEMENT=off must not bypass the gate — admin breakglass only."""
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
                "session_id": self.session,
            },
            {**self.env, "L9_MEMORY_ENFORCEMENT": "off"},
        )
        self.assertTrue(is_deny(out), "ENFORCEMENT=off must not be an agent escape hatch")

    def test_breakglass_allows_and_is_operator_only(self) -> None:
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
                "session_id": self.session,
            },
            {**self.env, "L9_MEMORY_ENFORCEMENT_BREAKGLASS": "incident-123"},
        )
        self.assertFalse(is_deny(out))
        self.assertFalse(self.contract["operator_override"]["agent_settable"])
        overrides = st.state_root(self.contract) / "overrides.jsonl"
        self.assertTrue(overrides.is_file(), "breakglass must persist an override event")
        self.assertIn("incident-123", overrides.read_text(encoding="utf-8"))

    @unittest.skipUnless(
        os.environ.get("GRAPHITI_MCP_URL") and os.environ.get("GRAPHITI_MCP_TOKEN"),
        "live Graphiti endpoint not configured",
    )
    def test_live_lock_allows_authority_edit(self) -> None:
        self._write_receipt()
        acquire = subprocess.run(
            [
                sys.executable,
                str(LOCK),
                "acquire",
                "--namespace",
                "cursor-governance",
                "--task",
                "enforcement self-test",
            ],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=40,
            check=False,
        )
        if acquire.returncode != 0:
            self.skipTest(f"lock acquire unavailable: {acquire.stderr.strip()}")
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(
            is_deny(out), "authority edit must be allowed once a verified lock is held"
        )


class WorkspaceRootTests(unittest.TestCase):
    """workspace_root() must anchor .l9/memory consistently for the gate (which
    gets CLAUDE_PROJECT_DIR) and the CLI (which often does not, run from a subdir)."""

    def setUp(self) -> None:
        self._prev_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        self._prev_cwd = os.getcwd()
        self.root = Path(tempfile.mkdtemp()).resolve()
        (self.root / ".l9" / "memory").mkdir(parents=True)
        self.subdir = self.root / "repo" / "nested"
        self.subdir.mkdir(parents=True)

    def tearDown(self) -> None:
        os.chdir(self._prev_cwd)
        if self._prev_project_dir is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = self._prev_project_dir

    def test_env_var_wins(self) -> None:
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root / "explicit")
        os.chdir(self.subdir)
        self.assertEqual(st.workspace_root(), (self.root / "explicit").resolve())

    def test_walks_up_to_nearest_l9_memory_when_env_unset(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.chdir(self.subdir)
        # No .l9/memory in the subdir chain until self.root — so a lock acquired
        # here resolves the same state root the gate uses at the session root.
        self.assertEqual(st.workspace_root(), self.root)

    def test_falls_back_to_cwd_when_no_l9_memory_ancestor(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        bare = Path(tempfile.mkdtemp()).resolve()
        os.chdir(bare)
        self.assertEqual(st.workspace_root(), bare)


if __name__ == "__main__":
    unittest.main()
