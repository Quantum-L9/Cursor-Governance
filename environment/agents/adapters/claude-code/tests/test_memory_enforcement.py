#!/usr/bin/env python3
"""Behavioral proof that the memory gate enforces (denies) rather than advises.

The gate enforces exactly one precondition: fresh session hydration. It does not
consult, require, or accept a Graphiti phase-lock — repository-write authority
comes from worktree/branch isolation and the publication gate
(rules/96-multi-agent-main-bound-execution.mdc, E7/E10). These assertions are
network-free and run everywhere.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CLAUDE_DIR = Path(__file__).resolve().parent.parent
GATE = CLAUDE_DIR / "hooks" / "memory_gate.py"
PREFETCH = CLAUDE_DIR / "hooks" / "memory_prefetch.py"
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

    def test_allows_authority_edit_with_hydration_only(self) -> None:
        """E7: an authority-path edit needs hydration, and nothing more.

        This previously required a conflict-checked phase-lock, which made a
        memory marker into repository-write permission. Isolation is now the
        worktree's job and collision safety the publication gate's, so a hydrated
        session may edit authority paths directly.
        """
        self._write_receipt()
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(is_deny(out), "hydrated session must be able to edit authority paths")

    def test_denies_authority_edit_without_hydration(self) -> None:
        """The gate still enforces: no receipt, no governed write."""
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertTrue(is_deny(out))
        self.assertIn("not hydrated", out)

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

    def test_home_l9_memory_is_not_a_workspace_anchor(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.environ.pop("CURSOR_PROJECT_DIR", None)
        fake_home = Path(tempfile.mkdtemp()).resolve()
        (fake_home / ".l9" / "memory").mkdir(parents=True)
        repo = fake_home / "Website-Bot"
        repo.mkdir()
        os.chdir(repo)
        with mock.patch.object(st.Path, "home", return_value=fake_home):
            self.assertEqual(st.workspace_root(), repo)
            self.assertNotEqual(st.workspace_root(), fake_home)

    def test_outermost_skips_home_keeps_workspace(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.environ.pop("CURSOR_PROJECT_DIR", None)
        fake_home = Path(tempfile.mkdtemp()).resolve()
        (fake_home / ".l9" / "memory").mkdir(parents=True)
        workspace = fake_home / "ws"
        (workspace / ".l9" / "memory").mkdir(parents=True)
        nested = workspace / "vendor" / "lib"
        (nested / ".l9" / "memory").mkdir(parents=True)
        os.chdir(nested)
        with mock.patch.object(st.Path, "home", return_value=fake_home):
            self.assertEqual(st.workspace_root(), workspace)

    def test_does_not_walk_into_parent_git_clone(self) -> None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.environ.pop("CURSOR_PROJECT_DIR", None)
        outer = Path(tempfile.mkdtemp()).resolve()
        (outer / ".l9" / "memory").mkdir(parents=True)
        inner = outer / "Cursor-Governance"
        (inner / ".l9" / "memory").mkdir(parents=True)
        for repo in (outer, inner):
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        os.chdir(inner)
        self.assertEqual(st.workspace_root(), inner)


class MemoryDoesNotGateRepositoryWritesTests(unittest.TestCase):
    """E7/E10: memory state cannot grant or revoke repository-write authority.

    Replaces the former LockGateIdentityTests, whose whole subject -- which
    session a lock belonged to, whether a lock matched the gate's project dir --
    existed only because a lock could grant permission. Nothing does now.
    """

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

    def _authority_edit(self, env: dict | None = None) -> str:
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "environment/agents/adapters/claude-code/x.py"},
                "session_id": self.session,
            },
            env or self.env,
        )
        return out

    def test_stray_lock_artifact_grants_nothing(self) -> None:
        """A lock file on disk is inert: hydration alone decides."""
        locks = st.state_root(self.contract) / "locks"
        locks.mkdir(parents=True, exist_ok=True)
        (locks / "cursor-governance.json").write_text(
            json.dumps(
                {
                    "namespace": "cursor-governance",
                    "session_id": self.session,
                    "transport": "cursor-graphiti-phase-lock",
                    "granted": True,
                    "acquired_at": 9e9,
                }
            ),
            encoding="utf-8",
        )
        # No receipt: the forged "granted" lock must not unlock the write.
        self.assertTrue(is_deny(self._authority_edit()), "a lock artifact must not grant authority")

        # With hydration, the write is allowed -- and still not because of the lock.
        st.write_receipt(self.contract, self.session, {"namespaces": ["cursor-governance"]})
        self.assertFalse(is_deny(self._authority_edit()))

    def test_another_sessions_lock_does_not_revoke_authority(self) -> None:
        """E10: another agent's memory state cannot block this agent's write."""
        st.write_receipt(self.contract, self.session, {"namespaces": ["cursor-governance"]})
        locks = st.state_root(self.contract) / "locks"
        locks.mkdir(parents=True, exist_ok=True)
        (locks / "cursor-governance.json").write_text(
            json.dumps({"namespace": "cursor-governance", "session_id": "some-other-agent"}),
            encoding="utf-8",
        )
        self.assertFalse(
            is_deny(self._authority_edit()),
            "one agent's lock artifact must not revoke another agent's write authority",
        )

    def test_divergent_project_dirs_do_not_block_writes(self) -> None:
        """The lock-identity mismatch check went with the lock it protected."""
        st.write_receipt(self.contract, self.session, {"namespaces": ["cursor-governance"]})
        env = {**self.env, "CURSOR_PROJECT_DIR": str(Path(tempfile.mkdtemp()).resolve())}
        self.assertFalse(is_deny(self._authority_edit(env)))

    def test_gate_rejects_a_reintroduced_phase_lock_precondition(self) -> None:
        """E7 fail-closed: a non-conformant contract raises, it does not enforce."""
        with self.assertRaises(ValueError) as ctx:
            st.validate_requires({"id": "x", "requires": ["session_prefetch", "phase_lock"]})
        self.assertIn("non-conformant precondition", str(ctx.exception))

    def test_bridge_overwrites_stale_conversation_id(self) -> None:
        sys.path.insert(0, str(MEM))
        import graphiti_bridge as gb

        env = gb.bind_session_env({"CURSOR_CONVERSATION_ID": "default"}, "abc")
        self.assertEqual(env["CURSOR_CONVERSATION_ID"], "abc")
