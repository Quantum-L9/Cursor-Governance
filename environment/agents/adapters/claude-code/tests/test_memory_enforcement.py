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
import re
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

    def _receipt_event(self) -> dict:
        return {"session_id": self.session}

    def _receipt_id(self) -> str:
        return st.resolve_receipt_id(event=self._receipt_event())

    def _write_receipt(self) -> None:
        st.write_receipt(
            self.contract,
            self._receipt_id(),
            {"namespaces": ["cursor-governance"], "session_id": self.session},
        )

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

    def test_allows_governed_write_when_receipt_is_degraded(self) -> None:
        """A degraded SessionStart receipt must not permanently deny writes."""
        st.write_receipt(
            self.contract,
            self._receipt_id(),
            {"namespaces": [], "degraded": True, "status": "degraded", "session_id": self.session},
        )
        self.assertFalse(st.fresh_receipt(self.contract, self._receipt_id()))
        self.assertTrue(st.usable_receipt(self.contract, self._receipt_id()))
        out, code = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(is_deny(out), "degraded hydration continues; it does not block")
        self.assertEqual(code, 0)

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

    def test_denial_hint_repairs_with_one_identity(self) -> None:
        """Black box (audit P573-F1): deny → run the hinted repair → allow.

        The denial must name the RAW chat id (and the writer agent id the gate
        composed its key from), never the composed receipt key: prefetch
        composes the key itself, so a hint carrying ``claude-code__<chat>`` was
        composed again into ``claude-code__claude-code__<chat>`` and following
        the denial stamped a file the gate never looked up.
        """
        event = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "skills/x/SKILL.md"},
            "session_id": self.session,
        }
        env = {**self.env, "L9_MEMORY_SESSION_STATE_DIR": str(Path(self.workspace) / "state")}
        out, _ = run_gate(event, env)
        self.assertTrue(is_deny(out), "no receipt yet: the governed write must be denied")
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        # Both identity parts are path-safe by construction (memory_state._safe_id_part).
        match = re.search(
            r"(?:L9_MEMORY_AGENT_ID=([A-Za-z0-9_.-]+)\s+)?(\S*memory_prefetch\.py)"
            r"\s+--session-id\s+([A-Za-z0-9_.-]+)",
            reason,
        )
        self.assertIsNotNone(match, f"denial must name a runnable repair: {reason}")
        writer_agent, script, hinted = match.groups()
        self.assertEqual(hinted, self.session, "hint carries the raw chat id, not the composed key")
        self.assertNotIn("__", hinted)
        self.assertTrue(script.endswith("memory_prefetch.py"))
        self.assertNotIn(
            "--workspace /", reason, "repair must not hardcode a Cursor-Governance path"
        )

        # Run the repair exactly as hinted (empty stdin: a shell, not a hook event).
        repair_env = dict(env)
        if writer_agent:
            repair_env["L9_MEMORY_AGENT_ID"] = writer_agent
        repair_cmd = [sys.executable, str(PREFETCH), "--session-id", hinted]
        proc = subprocess.run(
            repair_cmd,
            input="",
            capture_output=True,
            text=True,
            env=repair_env,
            timeout=120,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # ONE identity end to end: the repair stamped exactly the file the gate
        # resolves for this event — composed once, never doubled.
        receipts = sorted((Path(self.workspace) / ".l9" / "memory" / "receipts").glob("*.json"))
        self.assertEqual([p.name for p in receipts], [f"{self._receipt_id()}.json"])
        self.assertNotIn("__claude-code__", receipts[0].name)

        out, code = run_gate(event, env)
        self.assertFalse(is_deny(out), "the hinted repair must unblock the same governed write")
        self.assertEqual(code, 0)

    def test_one_session_receipt_allows_edit_in_another_clone(self) -> None:
        """Remediator from this session: one prefetch, not a second CG hydrate."""
        other = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init"], cwd=other, check=True, capture_output=True, text=True)
        target = other / "skills" / "x.md"
        target.parent.mkdir()
        target.write_text("x\n", encoding="utf-8")
        self._write_receipt()
        out, code = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(target)},
                "session_id": self.session,
            },
            self.env,
        )
        self.assertFalse(is_deny(out), "one session receipt is enough to edit another repo")
        self.assertEqual(code, 0)

    def test_precomposed_receipt_key_is_reduced_not_doubled(self) -> None:
        """An old-style hint that passes the composed key still repairs the right file."""
        # The writer is DERIVED from host markers, so the surface is stated here
        # (Claude Code Desktop) rather than inherited from the machine running it.
        no_markers = {
            "CURSOR_AGENT": "",
            "CLAUDECODE": "",
            "CLAUDE_CODE_ENTRYPOINT": "",
            "CLAUDE_CODE_SESSION_ID": "",
            "CLAUDE_CODE_REMOTE": "",
        }
        with mock.patch.dict(os.environ, {**no_markers, "CLAUDECODE": "1"}):
            raw = st.resolve_receipt_id(event={}, cli_arg="chat-42")
            composed = st.resolve_receipt_id(event={}, cli_arg="claude-code-desktop__chat-42")
        self.assertEqual(raw, "claude-code-desktop__chat-42")
        self.assertEqual(composed, raw)
        # An agent with no host markers is identified by its adapter's setting.
        with mock.patch.dict(os.environ, {**no_markers, "L9_MEMORY_AGENT_ID": "manus"}):
            # Another writer's prefix is chat text, not this writer's key.
            other = st.resolve_receipt_id(event={}, cli_arg="claude-code-desktop__chat-42")
        self.assertEqual(other, "manus__claude-code-desktop__chat-42")

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

    def test_allows_memory_lane_invocations_without_receipt(self) -> None:
        """Memory writes / hydrates / repairs are never gated on hydration.

        ADR-0033 B8 (INV-03b): an agent is a first-class memory writer, and a
        hydration precondition on repository writes must not interpose on the
        agent lane. Before this exemption the gate's own remediation — run
        ``memory_prefetch.py`` — was itself a ``Bash`` call it would deny.
        """
        for command in (
            'l9-memory write "gate writeback contract requires X" --kind insight',
            "l9-memory search 'writeback'",
            ".venv/bin/python -m ops.memory.cli --surface plan-prefetch hydrate --task t",
            "L9_MEMORY_AGENT_ID=claude-code "
            "environment/agents/adapters/claude-code/hooks/memory_prefetch.py "
            f"--session-id {self.session}",
        ):
            with self.subTest(command=command):
                out, _ = run_gate(
                    {
                        "tool_name": "Bash",
                        "tool_input": {"command": command},
                        "session_id": self.session,
                    },
                    self.env,
                )
                self.assertFalse(
                    is_deny(out),
                    "memory-lane invocations are exempt from the memory gate; a deny"
                    " is the agent-lane interposition ADR-0033 removes",
                )

    def test_memory_lane_exemption_is_scoped_to_the_executable(self) -> None:
        """A compound that also mutates history is still governed.

        Neither exemption fires: not every segment is git, not every segment
        is memory, so the ``git-mutation`` rule classifies it and, without a
        receipt, denies. A memory prefix must not launder anything else.
        """
        out, _ = run_gate(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "l9-memory health && git commit -m 'x'",
                },
                "session_id": self.session,
            },
            self.env,
        )
        self.assertTrue(is_deny(out), "a memory prefix must not launder a governed command")

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

    def _receipt_id(self) -> str:
        return st.resolve_receipt_id(event={"session_id": self.session})

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
        st.write_receipt(
            self.contract,
            self._receipt_id(),
            {"namespaces": ["cursor-governance"], "session_id": self.session},
        )
        self.assertFalse(is_deny(self._authority_edit()))

    def test_another_sessions_lock_does_not_revoke_authority(self) -> None:
        """E10: another agent's memory state cannot block this agent's write."""
        st.write_receipt(
            self.contract,
            self._receipt_id(),
            {"namespaces": ["cursor-governance"], "session_id": self.session},
        )
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
        st.write_receipt(
            self.contract,
            self._receipt_id(),
            {"namespaces": ["cursor-governance"], "session_id": self.session},
        )
        env = {**self.env, "CURSOR_PROJECT_DIR": str(Path(tempfile.mkdtemp()).resolve())}
        self.assertFalse(is_deny(self._authority_edit(env)))

    def test_gate_rejects_a_reintroduced_phase_lock_precondition(self) -> None:
        """E7 fail-closed: a non-conformant contract raises, it does not enforce."""
        with self.assertRaises(ValueError) as ctx:
            st.validate_requires({"id": "x", "requires": ["session_prefetch", "phase_lock"]})
        self.assertIn("non-conformant precondition", str(ctx.exception))

    def test_receipt_id_is_not_session_id_and_isolates_agents(self) -> None:
        same_chat = {"session_id": "sess-shared", "conversation_id": "chat-1"}
        a = st.resolve_receipt_id(event={**same_chat, "agent_id": "agent-a"})
        b = st.resolve_receipt_id(event={**same_chat, "agent_id": "agent-b"})
        self.assertNotEqual(a, "sess-shared")
        self.assertNotEqual(b, "sess-shared")
        self.assertNotEqual(a, b)
        st.write_receipt(
            self.contract, a, {"namespaces": ["cursor-governance"], "session_id": "sess-shared"}
        )
        self.assertTrue(st.usable_receipt(self.contract, a))
        self.assertFalse(st.usable_receipt(self.contract, b))

    def test_session_scoped_receipt_does_not_pass_the_write_gate(self) -> None:
        """A leftover SessionStart file named after session_id is not a pass."""
        st.write_receipt(
            self.contract,
            self.session,
            {"namespaces": ["cursor-governance"], "session_id": self.session},
        )
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
                "session_id": self.session,
                "conversation_id": "later-chat",
                "agent_id": "agent-a",
            },
            self.env,
        )
        self.assertTrue(is_deny(out), "session-keyed receipt must not authorize another chat")

    def test_gate_denies_when_receipt_id_cannot_be_resolved(self) -> None:
        st.write_receipt(
            self.contract,
            self.session,
            {"namespaces": ["cursor-governance"], "session_id": self.session},
        )
        out, _ = run_gate(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "skills/x/SKILL.md"},
            },
            self.env,
        )
        self.assertTrue(is_deny(out), "missing chat id must not fall back to session_id")

    def test_bridge_overwrites_stale_conversation_id(self) -> None:
        sys.path.insert(0, str(MEM))
        import memory_bridge as mb

        env = mb.bind_session_env({"CURSOR_CONVERSATION_ID": "default"}, "abc")
        self.assertEqual(env["CURSOR_CONVERSATION_ID"], "abc")
