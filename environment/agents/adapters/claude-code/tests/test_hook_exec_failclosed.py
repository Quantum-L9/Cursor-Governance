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

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
LAUNCHER = (
    REPO / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
)
HOOKS_REL = Path("environment/agents/adapters/claude-code/hooks")

GATES = ("merge_gate_wrap.py", "local_execution_gate_wrap.py", "memory_gate.py")
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


if __name__ == "__main__":
    unittest.main()
