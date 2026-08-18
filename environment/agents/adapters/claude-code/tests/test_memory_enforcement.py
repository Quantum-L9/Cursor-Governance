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

    def test_allows_git_push_without_lock(self) -> None:
        """``git``/``gh`` commands are exempt from the memory gate.

        Per ``ops/autonomy/git_execution_exemption`` (and the sibling proofs in
        ``tests/ops/autonomy/test_git_execution_exemption.py``), a raw
        ``git push`` no longer needs a phase-lock to *execute*. Policy still
        prefers the ``make pr`` publish path, and the MCP GitHub tools plus
        ``make push`` remain governed by the gate — but the shell executables
        themselves are unconditionally exempt, even without a lock and even
        without a receipt. This test locks that invariant in from the memory
        gate's own perspective.
        """
        # Deliberately no receipt and no lock: the exemption must not depend on
        # either. (Contrast with ``test_denies_authority_edit_without_lock``
        # above, which still denies an Edit tool call in the same state.)
        out, _ = run_gate(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git push origin main"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(
            is_deny(out),
            "git/gh commands are exempt from the memory gate; deny would"
            " reintroduce the split-brain this PR removed",
        )

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
                "--session-id",
                self.session,
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
        self._prev_cursor_dir = os.environ.get("CURSOR_PROJECT_DIR")
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
        if self._prev_cursor_dir is None:
            os.environ.pop("CURSOR_PROJECT_DIR", None)
        else:
            os.environ["CURSOR_PROJECT_DIR"] = self._prev_cursor_dir

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

    def test_cursor_project_dir_used_when_claude_unset(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.environ["CURSOR_PROJECT_DIR"] = str(self.root / "cursor-explicit")
        os.chdir(self.subdir)
        self.assertEqual(st.workspace_root(), (self.root / "cursor-explicit").resolve())
        os.environ.pop("CURSOR_PROJECT_DIR", None)

    def test_outermost_l9_memory_when_subrepo_also_has_state(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.environ.pop("CURSOR_PROJECT_DIR", None)
        nested_state = self.subdir / ".l9" / "memory"
        nested_state.mkdir(parents=True)
        os.chdir(self.subdir)
        # Both workspace and subrepo have .l9/memory — one state root (workspace).
        self.assertEqual(st.workspace_root(), self.root)

    def test_falls_back_to_cwd_when_no_l9_memory_ancestor(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        bare = Path(tempfile.mkdtemp()).resolve()
        os.chdir(bare)
        self.assertEqual(st.workspace_root(), bare)


class LockGateIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp()).resolve()
        self.session = "real-uuid"
        self.env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.workspace)}
        self._prev = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.workspace)
        self.contract = st.load_contract()

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = self._prev
        os.environ.pop("CURSOR_PROJECT_DIR", None)

    def _stamp_lock(self, session_id: str) -> None:
        st.write_receipt(self.contract, session_id, {"namespaces": ["cursor-governance"]})
        st.write_lock(self.contract, "cursor-governance", session_id, "sig")
        path = st.lock_path(self.contract, "cursor-governance")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["transport"] = "cursor-graphiti-phase-lock"
        data["granted"] = True
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    def test_gate_denies_lock_with_wrong_session_id(self) -> None:
        st.write_receipt(self.contract, self.session, {"namespaces": ["cursor-governance"]})
        self._stamp_lock("unknown-session")
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertTrue(is_deny(out))
        self.assertIn("LOCK_IDENTITY_MISMATCH", out)
        self.assertIn("unknown-session", out)
        self.assertIn(self.session, out)

    def test_gate_denies_divergent_project_dirs(self) -> None:
        other = Path(tempfile.mkdtemp()).resolve()
        self._stamp_lock(self.session)
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            {**self.env, "CURSOR_PROJECT_DIR": str(other)},
        )
        self.assertTrue(is_deny(out))
        self.assertIn("LOCK_IDENTITY_MISMATCH", out)
        self.assertIn(str(self.workspace), out)
        self.assertIn(str(other), out)

    def test_matching_lock_allows_authority_edit(self) -> None:
        self._stamp_lock(self.session)
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(is_deny(out), out)

    def test_bridge_overwrites_stale_conversation_id(self) -> None:
        sys.path.insert(0, str(MEM))
        import graphiti_bridge as gb

        env = gb.bind_session_env({"CURSOR_CONVERSATION_ID": "default"}, "abc")
        self.assertEqual(env["CURSOR_CONVERSATION_ID"], "abc")

    def test_phase_lock_satisfied_ignores_default_json(self) -> None:
        sys.path.insert(0, str(MEM))
        import graphiti_bridge as gb

        home = Path(tempfile.mkdtemp())
        state = home / ".cursor" / "graphiti-state"
        state.mkdir(parents=True)
        (state / "default.json").write_text(
            json.dumps({"memory_satisfied_for": ["gmp:phase_lock"]}),
            encoding="utf-8",
        )
        prev_home = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            self.assertFalse(gb.phase_lock_satisfied("abc"))
        finally:
            if prev_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = prev_home

    def test_lock_status_reports_session_and_path(self) -> None:
        self._stamp_lock(self.session)
        proc = subprocess.run(
            [sys.executable, str(LOCK), "status"],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(self.session, proc.stdout)
        self.assertIn("lock_path", proc.stdout)


if __name__ == "__main__":
    unittest.main()
