#!/usr/bin/env python3
"""Hook launcher: gates fail closed, observers log their skips (INV-1).

Covers audit finding B-03 and acceptance tests T-05, T-06, T-40.

Every case runs the REAL l9_hook_exec.sh against a synthetic governance root
that is deliberately broken in one specific way — no locked interpreter, no hook
file, no governance tree at all. A test that only exercises a healthy
environment cannot detect the class of defect this suite exists to catch: the
audit found all eight hooks exiting 0 on a missing .venv, three of which were
gates.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[5]
LAUNCHER = (
    REPO / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
)
HOOKS_REL = Path("environment/agents/adapters/claude-code/hooks")

GATES = (
    "merge_gate_wrap.py",
    "local_execution_gate_wrap.py",
    "memory_gate.py",
    "session_debt_wrap.py",
)
OBSERVERS = (
    "skill_usage_logger.py",
    "user_prompt_skill_router.py",
    "context7_stack_pretool.py",
    "memory_prefetch.py",
    "memory_writeback.py",
)


class HookExecFailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.gov = self.home / ".cursor-governance"
        (self.gov / HOOKS_REL).mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def _materialize_governance(self) -> None:
        """A governance tree that is complete except for whatever a test breaks."""
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        for name in GATES + OBSERVERS:
            (self.gov / HOOKS_REL / name).write_text(
                "#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8"
            )

    def _install_interpreter(self) -> None:
        venv_bin = self.gov / ".venv" / "bin"
        venv_bin.mkdir(parents=True, exist_ok=True)
        python3 = venv_bin / "python3"
        python3.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        python3.chmod(0o755)

    def _run(self, hook_class: str, name: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env.pop("L9_GOVERNANCE_DIR", None)
        # These tests assert Claude gate fail-closed behavior. Clear Cursor
        # markers inherited from the parent session so the surface guard does
        # not skip before the launcher can fail closed.
        for key in (
            "CURSOR_AGENT",
            "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_CODE_REMOTE",
            "L9_GOVERNANCE_SURFACE",
            "L9_SURFACE_GUARD",
        ):
            env.pop(key, None)
        env["CLAUDECODE"] = "1"
        env["L9_HOOK_SKIP_LOG"] = str(self.home / ".l9" / "claude" / "hook-skips.log")
        return subprocess.run(
            ["bash", str(LAUNCHER), "--class", hook_class, name],
            input="{}",
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    @property
    def _skip_log(self) -> Path:
        return self.home / ".l9" / "claude" / "hook-skips.log"

    # -- T-05: gates fail closed --------------------------------------------

    def test_gate_blocks_when_locked_interpreter_absent(self) -> None:
        self._materialize_governance()  # no .venv
        for name in GATES:
            with self.subTest(gate=name):
                result = self._run("gate", name)
                self.assertEqual(result.returncode, 2, f"{name} must BLOCK, not pass")
                self.assertIn("BLOCKING", result.stderr)

    def test_gate_blocks_when_hook_file_absent(self) -> None:
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        result = self._run("gate", "merge_gate_wrap.py")
        self.assertEqual(result.returncode, 2)

    def test_gate_blocks_when_governance_absent(self) -> None:
        result = self._run("gate", "memory_gate.py")  # nothing materialized
        self.assertEqual(result.returncode, 2)

    def test_gate_never_writes_a_skip_log_entry(self) -> None:
        """A blocked gate is not a skip. Logging it as one would understate it."""
        self._materialize_governance()
        self._run("gate", "memory_gate.py")
        self.assertFalse(self._skip_log.exists())

    def test_malformed_registration_is_treated_as_a_gate(self) -> None:
        self._materialize_governance()
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        for key in (
            "CURSOR_AGENT",
            "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_CODE_REMOTE",
            "L9_GOVERNANCE_SURFACE",
        ):
            env.pop(key, None)
        env["CLAUDECODE"] = "1"
        for argv in (["--class", "gate"], ["--class", "wat", "memory_gate.py"], []):
            with self.subTest(argv=argv):
                result = subprocess.run(
                    ["bash", str(LAUNCHER), *argv],
                    capture_output=True,
                    text=True,
                    env=env,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)

    # -- T-06: observers exit 0 but leave a timestamped trace ----------------

    def test_observer_passes_but_records_a_timestamped_skip(self) -> None:
        self._materialize_governance()  # no .venv
        for name in OBSERVERS:
            with self.subTest(observer=name):
                result = self._run("observer", name)
                self.assertEqual(result.returncode, 0, f"{name} must not block a session")

        self.assertTrue(self._skip_log.is_file(), "skip must be auditable, not invisible")
        lines = self._skip_log.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), len(OBSERVERS))
        for line in lines:
            stamp, klass, hook, _reason = line.split(" ", 3)
            self.assertEqual(klass, "observer")
            self.assertIn(hook, OBSERVERS)
            # UTC ISO-8601, e.g. 2026-08-21T02:09:05Z (INV-2).
            self.assertRegex(stamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    # -- healthy path regression --------------------------------------------

    def test_healthy_environment_execs_the_hook(self) -> None:
        self._materialize_governance()
        self._install_interpreter()
        for hook_class, name in (("gate", "memory_gate.py"), ("observer", "memory_prefetch.py")):
            with self.subTest(hook=name):
                self.assertEqual(self._run(hook_class, name).returncode, 0)
        self.assertFalse(self._skip_log.exists(), "a hook that ran is not a skip")

    def test_shell_hook_does_not_require_the_locked_interpreter(self) -> None:
        """A bash hook has no uv.lock dependency; demanding .venv would fail it
        closed for a reason that does not apply to it."""
        self._materialize_governance()
        script = self.gov / HOOKS_REL / "session_start_claude_governance.sh"
        script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        self.assertEqual(self._run("observer", "session_start_claude_governance.sh").returncode, 0)


class SettingsRegistrationTests(unittest.TestCase):
    """T-40 static scan: no gate registration may exit 0 when it cannot evaluate."""

    SETTINGS = (
        REPO / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json",
        REPO / ".claude" / "settings.json",
    )

    def test_every_gate_registration_blocks_on_missing_launcher(self) -> None:
        import json

        for path in self.SETTINGS:
            with self.subTest(settings=path.name):
                hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
                commands = [
                    entry["command"]
                    for group in hooks.values()
                    for matcher in group
                    for entry in matcher["hooks"]
                ]
                gate_commands = [c for c in commands if "--class gate" in c]
                self.assertEqual(len(gate_commands), len(GATES))
                for command in gate_commands:
                    self.assertIn("exit 2", command)
                    self.assertNotIn("|| exit 0", command)
                for name in GATES:
                    self.assertTrue(
                        any(f"--class gate {name}" in c for c in gate_commands),
                        f"{name} must be registered as a gate",
                    )


# ---------------------------------------------------------------------------
# T-41: Program-bound root authorization composed into the PreToolUse wrapper.
#
# These cases run the real wrapper against a real root autonomy runtime and a
# real canonical Program state database. Nothing on the authorization path is
# mocked: a fake authorizer would allow whatever the wrapper asked it, which is
# precisely the failure mode this suite exists to detect. Only the downstream
# ops gate is stubbed, because what is under test is what the wrapper hands it.
# ---------------------------------------------------------------------------

WRAPPER = REPO / "environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py"
PE_ROOT = REPO / "environment/program-execution"
INTEGRATION = PE_ROOT / "integrations/autonomy-control-plane"
PEC_SCRIPTS = PE_ROOT / "core/program-execution-controller-template/scripts"

STUB_GATE = """import os
import pathlib
import sys

pathlib.Path(os.environ["L9_TEST_GATE_LOG"]).write_bytes(sys.stdin.buffer.read())
raise SystemExit(0)
"""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    return completed.stdout.strip()


class ProgramBoundAuthorizationTests(unittest.TestCase):
    """The wrapper authorizes a live effect before the ops gate ever runs."""

    @classmethod
    def setUpClass(cls) -> None:
        for path in (str(REPO), str(PE_ROOT), str(PEC_SCRIPTS)):
            if path not in sys.path:
                sys.path.insert(0, path)
        cls.wrapper = _load(WRAPPER, "l9_test_local_execution_gate_wrap")
        cls.grant = _load(INTEGRATION / "grant.py", "l9_test_autonomy_grant")

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.workspace = self.root / "workspace"
        self.worktree = self.workspace / "worktrees" / "TASK-1"
        self.worktree.mkdir(parents=True)
        _git("init", "--initial-branch=pec/task-1", cwd=self.worktree)
        (self.worktree / "README.md").write_text("seed\n", encoding="utf-8")
        _git("add", "README.md", cwd=self.worktree)
        _git("commit", "-m", "seed", cwd=self.worktree)
        self.base_sha = _git("rev-parse", "HEAD", cwd=self.worktree)
        self.contract = {
            "program_id": "Program A",
            "task_id": "TASK-1",
            "objective": "Edit the declared path",
            "base_sha": self.base_sha,
            "requested_actions": ["inspect", "local_write"],
            "writable_paths": ["docs/result.txt"],
            "contract_digest": "digest-1",
            "repository_id": "repo-a",
            "branch": "pec/task-1",
            "lease_id": "lease-program-1",
            "worktree": str(self.worktree),
        }
        self._bind_parent()
        self.authority = self.grant.grant_task_mutation(
            REPO,
            self.workspace,
            self.contract,
            attempt_number=1,
            agent_ref="claude-code",
            surface="claude-cli",
        )["autonomy_authority"]
        self.gate_log = self.root / "gate-stdin.bin"
        self.gate = self.root / "stub_gate.py"
        self.gate.write_text(STUB_GATE, encoding="utf-8")

    def _bind_parent(self, *, expires_in_seconds: int = 900, state: str = "EXECUTING") -> None:
        from pec.state import StateDB

        database = StateDB(self.workspace / "runtime" / "state.sqlite")
        try:
            database.upsert_task(
                {
                    "id": "TASK-1",
                    "title": "TASK-1",
                    "wave_id": "WAVE-1",
                    "workstream_id": "WS-1",
                    "target_id": "TARGET-A",
                    "repository_id": "repo-a",
                    "execution_kind": "code_change",
                    "objective": "Edit the declared path",
                    "risk_tier": "low",
                    "definition_status": "defined",
                }
            )
            now = datetime.now(tz=UTC)
            database.create_lease(
                {
                    "lease_id": "lease-program-1",
                    "task_id": "TASK-1",
                    "repository_id": "repo-a",
                    "holder": "make-campaign",
                    "base_sha": self.base_sha,
                    "branch": "pec/task-1",
                    "worktree": str(self.worktree),
                    "contract_digest": "digest-1",
                    "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "expires_at": (now + timedelta(seconds=expires_in_seconds)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
            )
            database.update_task("TASK-1", lease_id="lease-program-1")
            for transition in ("ELIGIBLE", "LEASED", "PREPARED", "CONTRACTED", state):
                if database.task("TASK-1")["runtime_state"] != transition:
                    database.transition_task("TASK-1", transition)
        finally:
            database.close()

    def _environment(self) -> dict[str, str]:
        parent = self.authority.get("program_parent") or {}
        return {
            "L9_AUTONOMY_REQUIRED": "1",
            "L9_ADAPTER_SESSION_ID": str(self.authority["adapter_session_id"]),
            "L9_LEASE_ID": str(self.authority["lease_id"]),
            "L9_AGENT_ID": str(self.authority["agent_id"]),
            "L9_AUTONOMY_DATABASE": str(self.authority["runtime_database"]),
            "L9_AUTONOMY_ROOT": str(self.authority["repository_root"]),
            "L9_PROGRAM_WORKSPACE": str(self.authority["workspace"]),
            "L9_PROGRAM_TASK_ID": str(self.authority["task_id"]),
            "L9_PROGRAM_LEASE_ID": str(parent.get("lease_id") or ""),
            "L9_PROGRAM_WORKTREE": str(parent.get("worktree") or self.worktree),
        }

    def _run(
        self,
        event: dict,
        *,
        environment: dict[str, str] | None = None,
        gate: Path | None = None,
    ) -> tuple[int, bytes]:
        raw = json.dumps(event).encode("utf-8")
        env = dict(os.environ)
        env.update(self._environment() if environment is None else environment)
        env["L9_TEST_GATE_LOG"] = str(self.gate_log)
        stub = self.gate if gate is None else gate
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(self.wrapper.sys, "stdin", mock.Mock(buffer=io.BytesIO(raw))),
            mock.patch.object(self.wrapper, "GATE", stub),
        ):
            code = self.wrapper.main()
        replayed = self.gate_log.read_bytes() if self.gate_log.exists() else b""
        return code, replayed

    def _write_event(self, path: str) -> dict:
        return {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}

    # -- the authorized path ------------------------------------------------

    def test_authorized_write_reaches_the_downstream_gate_byte_identical(self) -> None:
        event = self._write_event(str(self.worktree / "docs/result.txt"))
        code, replayed = self._run(event)
        self.assertEqual(code, 0)
        self.assertEqual(replayed, json.dumps(event).encode("utf-8"))

    def test_authorization_precedes_the_downstream_gate(self) -> None:
        """A denial must never reach the ops gate at all."""
        code, replayed = self._run(self._write_event("/etc/passwd"))
        self.assertEqual(code, 2)
        self.assertEqual(replayed, b"")

    def test_outside_a_worker_window_the_gate_still_decides_alone(self) -> None:
        code, replayed = self._run(
            self._write_event(str(self.worktree / "docs/result.txt")),
            environment={"L9_AUTONOMY_REQUIRED": ""},
        )
        self.assertEqual(code, 0)
        self.assertTrue(replayed)

    # -- fail closed --------------------------------------------------------

    def test_missing_authority_blocks(self) -> None:
        for dropped in (
            "L9_ADAPTER_SESSION_ID",
            "L9_LEASE_ID",
            "L9_AGENT_ID",
            "L9_AUTONOMY_DATABASE",
            "L9_PROGRAM_WORKSPACE",
        ):
            with self.subTest(missing=dropped):
                environment = self._environment()
                environment[dropped] = ""
                code, replayed = self._run(
                    self._write_event(str(self.worktree / "docs/result.txt")),
                    environment=environment,
                )
                self.assertEqual(code, 2)
                self.assertEqual(replayed, b"")

    def test_forged_identity_blocks(self) -> None:
        for field, value in (
            ("L9_ADAPTER_SESSION_ID", "adapter-session-forged"),
            ("L9_LEASE_ID", "lease-forged"),
            ("L9_AGENT_ID", "agent-forged"),
        ):
            with self.subTest(forged=field):
                environment = self._environment()
                environment[field] = value
                code, _ = self._run(
                    self._write_event(str(self.worktree / "docs/result.txt")),
                    environment=environment,
                )
                self.assertEqual(code, 2)

    def test_missing_downstream_gate_blocks_inside_a_worker_window(self) -> None:
        code, _ = self._run(
            self._write_event(str(self.worktree / "docs/result.txt")),
            gate=self.root / "absent_gate.py",
        )
        self.assertEqual(code, 2)

    def test_expired_program_parent_blocks(self) -> None:
        connection = sqlite3.connect(self.workspace / "runtime" / "state.sqlite")
        try:
            connection.execute(
                "UPDATE leases SET expires_at=? WHERE lease_id=?",
                ("2000-01-01T00:00:00Z", "lease-program-1"),
            )
            connection.commit()
        finally:
            connection.close()
        code, replayed = self._run(self._write_event(str(self.worktree / "docs/result.txt")))
        self.assertEqual(code, 2)
        self.assertEqual(replayed, b"")

    def test_revoked_program_parent_blocks(self) -> None:
        connection = sqlite3.connect(self.workspace / "runtime" / "state.sqlite")
        try:
            connection.execute("UPDATE leases SET active=0 WHERE lease_id=?", ("lease-program-1",))
            connection.commit()
        finally:
            connection.close()
        code, _ = self._run(self._write_event(str(self.worktree / "docs/result.txt")))
        self.assertEqual(code, 2)

    def test_stale_actual_worktree_head_blocks(self) -> None:
        """The heartbeat is against the worktree's real HEAD, not a claim."""
        (self.worktree / "drift.txt").write_text("drift\n", encoding="utf-8")
        _git("add", "drift.txt", cwd=self.worktree)
        _git("commit", "-m", "drift", cwd=self.worktree)
        code, replayed = self._run(self._write_event(str(self.worktree / "docs/result.txt")))
        self.assertEqual(code, 2)
        self.assertEqual(replayed, b"")

    def test_path_escapes_block(self) -> None:
        cases = {
            "absolute_outside": str(self.root / "outside.txt"),
            "traversal": "../../outside.txt",
            "system_path": "/etc/passwd",
        }
        for label, path in cases.items():
            with self.subTest(escape=label):
                code, _ = self._run(self._write_event(path))
                self.assertEqual(code, 2)

    def test_symlink_escape_blocks(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.worktree / "docs").symlink_to(outside, target_is_directory=True)
        code, _ = self._run(self._write_event("docs/result.txt"))
        self.assertEqual(code, 2)

    def test_non_canonical_shell_command_blocks(self) -> None:
        for command in (
            "ls -1 'a' 'b' >/dev/null",
            'python3 -c "import os"',
            "git push origin HEAD",
            "rm -rf / && echo done",
        ):
            with self.subTest(command=command):
                code, _ = self._run({"tool_name": "Bash", "tool_input": {"command": command}})
                self.assertEqual(code, 2)

    def test_a_local_write_window_never_authorizes_a_commit(self) -> None:
        """DG-001 at the effect edge: no commit capability, no commit effect."""
        code, _ = self._run({"tool_name": "git_commit", "tool_input": {"path": "docs/result.txt"}})
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
