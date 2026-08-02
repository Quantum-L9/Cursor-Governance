#!/usr/bin/env python3
"""Behavioral proof that the memory gate enforces (denies) rather than advises.

Network-free assertions run everywhere. A live section that exercises a real
phase-lock against the memory server runs only when L9_MEMORY_HTTP_URL and
L9_MEMORY_CLIENT_TOKEN are set and reachable, so CI without memory stays green.
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
        # Route state into the temp workspace for in-process helpers too.
        os.environ["CLAUDE_PROJECT_DIR"] = self.workspace
        self.contract = st.load_contract()

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
                "tool_input": {"file_path": "environment/claude-code/x.py"},
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

    def test_disable_env_allows(self) -> None:
        out, code = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
                "session_id": self.session,
            },
            {**self.env, "L9_MEMORY_ENFORCEMENT": "off"},
        )
        self.assertFalse(is_deny(out))
        self.assertEqual(code, 0)

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

    @unittest.skipUnless(
        os.environ.get("L9_MEMORY_HTTP_URL") and os.environ.get("L9_MEMORY_CLIENT_TOKEN"),
        "live memory endpoint not configured",
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
                "tool_input": {"file_path": "environment/claude-code/x.py"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(
            is_deny(out), "authority edit must be allowed once a verified lock is held"
        )


if __name__ == "__main__":
    unittest.main()
