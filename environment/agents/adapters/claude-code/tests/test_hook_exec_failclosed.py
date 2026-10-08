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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[5]
LAUNCHER = (
    REPO / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
)
HOOKS_REL = Path("environment/agents/adapters/claude-code/hooks")

# Fail-closed launcher coverage: every known gate script, including
# session_debt_wrap.py which remains invocable manually but is no longer
# registered on Stop.
GATES = (
    "merge_gate_wrap.py",
    "local_execution_gate_wrap.py",
    "memory_gate.py",
    "session_debt_wrap.py",
)
REGISTERED_GATES = (
    "merge_gate_wrap.py",
    "local_execution_gate_wrap.py",
    "memory_gate.py",
)
OBSERVERS = (
    "skill_usage_logger.py",
    "user_prompt_skill_router.py",
    "context7_stack_pretool.py",
    "memory_prefetch.py",
    "memory_writeback.py",
    "ci_parity_posttool.py",
    # Blocks by exit 2 when it evaluates, fails OPEN when it cannot (CI stays
    # authoritative): see the ci_parity_push_gate.py docstring.
    "ci_parity_push_gate.py",
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
            "CURSOR_CONVERSATION_ID",
            "CURSOR_EXTENSION_HOST_ROLE",
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

    def test_a_gate_registered_as_an_observer_is_refused(self) -> None:
        """The class is a property of the HOOK, not of the caller (INV-1b).

        This launcher exists so the fail-open/fail-closed decision is made once
        rather than re-typed inside eight `bash -c` one-liners where a slip
        silently disables a gate. It took --class on trust, so the slip it was
        built to prevent still worked: a gate registered --class observer exited
        0 without evaluating, indistinguishable from a gate that passed.
        """
        self._materialize_governance()  # no .venv, so a real gate would BLOCK
        for name in GATES:
            with self.subTest(gate=name):
                result = self._run("observer", name)
                self.assertEqual(
                    result.returncode, 2, f"{name} must not be downgradable to an observer"
                )
                self.assertIn("refusing to downgrade", result.stderr)
        # And a downgrade refusal is not a skip.
        self.assertFalse(self._skip_log.exists())

    def test_a_genuine_observer_is_not_forced_to_a_gate(self) -> None:
        """Only gates are named, so adding an observer needs no edit here."""
        self._materialize_governance()
        result = self._run("observer", "skill_usage_logger.py")
        self.assertEqual(result.returncode, 0)
        self.assertIn("did NOT run", result.stderr)

    def test_skip_log_falls_back_when_home_is_unwritable(self) -> None:
        """The audit trail must survive the broken environment it audits.

        record_skip returned silently when its directory could not be created,
        so the record vanished in exactly the case it exists for — a wrong or
        unwritable HOME is what makes hooks skip in the first place.
        """
        with tempfile.TemporaryDirectory() as tmp:
            fallback = Path(tmp) / "l9-hook-skips.log"
            env = dict(os.environ)
            env["HOME"] = "/proc/nonexistent"
            env["TMPDIR"] = tmp
            env.pop("L9_HOOK_SKIP_LOG", None)
            # Observer skip precedes record_skip unless this is a Claude surface.
            #
            # L9_GOVERNANCE_DIR used to belong in this list for a reason the
            # launcher no longer gives it: it honoured any value naming a
            # directory with a CANONICAL_LAW.md, so inheriting the runner's
            # value pointed GOV_DIR at a VALID clone, the hook ran normally and
            # no skip was recorded — stderr came back empty and this test failed
            # for a reason unrelated to an unwritable HOME, passing under a bare
            # `pytest` and failing under any runner that exported it. INV-1c
            # removed that redirect; the scrub stays because the hooks this
            # launcher execs still read the variable.
            for key in (
                "CURSOR_AGENT",
                "CURSOR_CONVERSATION_ID",
                "CURSOR_EXTENSION_HOST_ROLE",
                "L9_GOVERNANCE_SURFACE",
                "L9_GOVERNANCE_DIR",
                "CLAUDE_CODE_ENTRYPOINT",
                "CLAUDE_CODE_SESSION_ID",
                "CLAUDE_CODE_REMOTE",
            ):
                env.pop(key, None)
            env["CLAUDECODE"] = "1"
            result = subprocess.run(
                ["bash", str(LAUNCHER), "--class", "observer", "skill_usage_logger.py"],
                capture_output=True,
                text=True,
                env=env,
                input="",
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("skip log unwritable", result.stderr)
            self.assertTrue(fallback.exists(), "the skip must be recorded somewhere")
            self.assertIn("skill_usage_logger.py", fallback.read_text(encoding="utf-8"))

    def test_malformed_registration_is_treated_as_a_gate(self) -> None:
        self._materialize_governance()
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        for key in (
            "CURSOR_AGENT",
            "CURSOR_CONVERSATION_ID",
            "CURSOR_EXTENSION_HOST_ROLE",
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
                self.assertEqual(len(gate_commands), len(REGISTERED_GATES))
                for command in gate_commands:
                    self.assertIn("exit 2", command)
                    self.assertNotIn("|| exit 0", command)
                for name in REGISTERED_GATES:
                    self.assertTrue(
                        any(f"--class gate {name}" in c for c in gate_commands),
                        f"{name} must be registered as a gate",
                    )
                self.assertFalse(
                    any("session_debt_wrap.py" in c for c in gate_commands),
                    "session_debt_wrap.py must not be registered as a Stop/bootstrap gate",
                )


# ---------------------------------------------------------------------------
# Root-gate forwarding. The wrapper resolves the ops gate, forwards the
# byte-identical stdin, and propagates the result. It does not authorize.
# ---------------------------------------------------------------------------

WRAPPER = REPO / "environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py"

STUB_ALLOW = """import os
import pathlib
import sys

pathlib.Path(os.environ["L9_TEST_GATE_LOG"]).write_bytes(sys.stdin.buffer.read())
raise SystemExit(0)
"""

STUB_DENY = """import sys

sys.stderr.write("gate denied\\n")
raise SystemExit(2)
"""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RootGateForwardingTests(unittest.TestCase):
    """The surviving wrapper contract: one stdin, one root gate, fail closed."""

    RAW = b'{"tool_name":"Bash","tool_input":{"command":"echo hi"}}'

    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = _load(WRAPPER, "l9_test_local_execution_gate_wrap")

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.gate_log = root / "gate.log"
        self.allow = root / "allow_gate.py"
        self.deny = root / "deny_gate.py"
        self.allow.write_text(STUB_ALLOW, encoding="utf-8")
        self.deny.write_text(STUB_DENY, encoding="utf-8")

    def _run(self, gate: Path) -> tuple[int, bytes]:
        env = dict(os.environ)
        env["L9_TEST_GATE_LOG"] = str(self.gate_log)
        with (
            mock.patch.dict(os.environ, env, clear=False),
            mock.patch.object(self.wrapper.sys, "stdin", mock.Mock(buffer=io.BytesIO(self.RAW))),
            mock.patch.object(self.wrapper, "GATE", gate),
        ):
            code = self.wrapper.main()
        replayed = self.gate_log.read_bytes() if self.gate_log.exists() else b""
        return code, replayed

    def test_byte_identical_stdin_reaches_the_root_gate(self) -> None:
        code, replayed = self._run(self.allow)
        self.assertEqual(code, 0)
        self.assertEqual(replayed, self.RAW)

    def test_missing_root_gate_denies(self) -> None:
        code, replayed = self._run(Path(self._tmp.name) / "missing.py")
        self.assertEqual(code, 2)
        self.assertEqual(replayed, b"")

    def test_root_gate_denial_propagates(self) -> None:
        code, _replayed = self._run(self.deny)
        self.assertEqual(code, 2)

    def test_root_gate_success_propagates(self) -> None:
        code, _replayed = self._run(self.allow)
        self.assertEqual(code, 0)

    def test_wrapper_source_does_not_reach_program_execution(self) -> None:
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("program-execution", text)
        self.assertNotIn("ProgramBoundEffectAuthorizer", text)
        self.assertNotIn("L9_PROGRAM_", text)


class GovernanceDirIsNotRedirectableTests(unittest.TestCase):
    """INV-1c: the launcher dispatches out of $HOME/.cursor-governance, only.

    SESSION_START_SPEC hard constraint 2 pins governance for the SessionStart
    hook. The launcher resolves more than that: it picks BOTH the policy file it
    execs and the locked interpreter it runs it on. It used to accept any
    ``L9_GOVERNANCE_DIR`` naming a directory with a ``CANONICAL_LAW.md``,
    guarding only an unexpanded literal ``$HOME`` — so an environment variable
    could hand a gate its own policy and its own interpreter. These tests run
    the real launcher with such a variable exported and prove it is ignored.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "home"
        self.canonical = self.home / ".cursor-governance"
        self.foreign = Path(self._tmp.name) / "foreign-governance"
        for tree, exit_code in ((self.canonical, 0), (self.foreign, 3)):
            (tree / HOOKS_REL).mkdir(parents=True)
            (tree / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
            venv_bin = tree / ".venv" / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "python3").write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
            (venv_bin / "python3").chmod(0o755)
            for name in (*GATES, *OBSERVERS):
                (tree / HOOKS_REL / name).write_text("raise SystemExit(0)\n", encoding="utf-8")
            # A shell hook is exec'd directly, bypassing the interpreter, so it
            # needs its own tell-tale exit code to identify the tree that ran.
            (tree / HOOKS_REL / "session_start_claude_governance.sh").write_text(
                f"#!/usr/bin/env bash\nexit {exit_code}\n", encoding="utf-8"
            )

    def _run(self, hook_class: str, name: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env["CLAUDECODE"] = "1"
        env["L9_GOVERNANCE_DIR"] = str(self.foreign)
        env["L9_HOOK_SKIP_LOG"] = str(self.home / ".l9" / "claude" / "hook-skips.log")
        for key in (
            "CURSOR_AGENT",
            "CURSOR_CONVERSATION_ID",
            "CURSOR_EXTENSION_HOST_ROLE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_CODE_REMOTE",
            "L9_GOVERNANCE_SURFACE",
            "L9_SURFACE_GUARD",
        ):
            env.pop(key, None)
        return subprocess.run(
            ["bash", str(LAUNCHER), "--class", hook_class, name],
            input="{}",
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_a_divergent_governance_dir_cannot_supply_gate_policy(self) -> None:
        """Exit 3 is the foreign tree's interpreter; 0 is the canonical one."""
        for name in GATES:
            with self.subTest(gate=name):
                result = self._run("gate", name)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"{name} ran the tree named by L9_GOVERNANCE_DIR",
                )

    def test_a_divergent_governance_dir_cannot_supply_observer_context(self) -> None:
        """A SessionStart observer emits into the session; its source is pinned."""
        result = self._run("observer", "session_start_claude_governance.sh")
        self.assertEqual(result.returncode, 0, "the SessionStart hook ran from a foreign tree")

    def test_a_divergent_governance_dir_does_not_rescue_a_missing_canonical_tree(self) -> None:
        """The foreign tree is complete; the canonical one is gone. Gates block."""
        shutil.rmtree(self.canonical)
        result = self._run("gate", "memory_gate.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKING", result.stderr)


if __name__ == "__main__":
    unittest.main()
