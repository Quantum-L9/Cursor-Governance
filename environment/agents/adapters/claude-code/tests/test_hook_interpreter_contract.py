#!/usr/bin/env python3
"""F-13 - governance hooks run on the locked interpreter, and failure is visible.

Two halves of one finding:

  * every governance-owned Python hook command resolves the locked governance
    interpreter instead of whatever PATH offers as `python3`; and
  * when the write-back hook cannot run, that is recorded as a runtime failure
    rather than printed as an ordinary skip.

The second half is why the first mattered in practice: on a container whose
system python3 lacks pydantic, memory_writeback exited 0 for every session while
never reaching close_session, so no PICKUP episode was ever written and nothing
said so.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]
ADAPTER = REPO / "environment" / "agents" / "adapters" / "claude-code"
TEMPLATE = ADAPTER / "settings.template.json"
GENERATED = REPO / ".claude" / "settings.json"
HOOKS = ADAPTER / "hooks"
MEMORY = ADAPTER / "memory"


def _python_hook_commands(settings: dict[str, Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for event, matchers in (settings.get("hooks") or {}).items():
        for matcher in matchers:
            for hook in matcher.get("hooks", []):
                command = str(hook.get("command", ""))
                if ".py" in command:
                    found.append((event, command))
    return found


class HookInterpreterBindingTests(unittest.TestCase):
    """No governance hook may depend on ambient PATH selection of python3.

    These assert against the RECONCILED settings, not the template. The template
    is the source, but what actually runs is the generated file, and a contract
    proven only on the source is not proven.
    """

    def setUp(self) -> None:
        if not GENERATED.is_file():
            self.skipTest("no reconciled .claude/settings.json in this checkout")
        self.settings = json.loads(GENERATED.read_text(encoding="utf-8"))
        self.commands = _python_hook_commands(self.settings)
        self.assertGreater(len(self.commands), 0, "settings declare no python hooks")

    def test_no_deployed_hook_execs_ambient_python(self) -> None:
        offenders = [
            (event, command)
            for event, command in self.commands
            if re.search(r"\bexec\s+python3?\b", command)
        ]
        self.assertEqual(offenders, [], f"hooks still using PATH python3: {offenders}")

    def test_hook_commands_share_one_shape(self) -> None:
        """Generated from one template constant, so drift is a defect."""
        shapes = {
            re.sub(r"[A-Za-z0-9_]+\.py", "HOOK", command) for _event, command in self.commands
        }
        self.assertEqual(len(shapes), 1, f"per-hook drift: {len(shapes)} distinct shapes")

    def test_commands_are_self_contained(self) -> None:
        """settings.json is copied into consumer repos, so a command must not
        depend on a helper file the governance clone may not carry yet: that
        failure mode is silent, which is the defect F-13 removes."""
        for event, command in self.commands:
            with self.subTest(event=event):
                self.assertNotIn("run_governance_hook", command)
                self.assertIn(".venv/bin/python", command)

    # --- the decisive acceptance test ------------------------------------

    def _synthetic_home(self, tmp: Path, *, with_venv: bool) -> tuple[Path, Path]:
        """A governance clone carrying only what the hook command addresses."""
        gov = tmp / ".cursor-governance"
        hooks = gov / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
        hooks.mkdir(parents=True)
        probe = hooks / "_interpreter_probe.py"
        probe.write_text("import sys\nprint(sys.executable)\n", encoding="utf-8")
        marker = tmp / "locked" / "bin"
        if with_venv:
            (gov / ".venv" / "bin").mkdir(parents=True)
            marker.mkdir(parents=True)
            locked = marker / "python3"
            locked.symlink_to(sys.executable)
            (gov / ".venv" / "bin" / "python3").symlink_to(locked)
        return gov, marker / "python3"

    def _argv(self, command: str) -> list[str]:
        """Deployed commands are `bash -c '<script>'`; split them to argv and run
        that directly. No interposed shell, so the test executes exactly what
        Claude Code executes."""
        return shlex.split(command)

    def _probe_command(self, command: str) -> str:
        command = re.sub(r"hooks/[A-Za-z0-9_]+\.py", "hooks/_interpreter_probe.py", command)
        return re.sub(
            r"[A-Za-z0-9_]+\.py did NOT run", "_interpreter_probe.py did NOT run", command
        )

    def test_every_deployed_hook_executes_on_the_locked_interpreter(self) -> None:
        ambient = subprocess.run(
            ["python3", "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            _gov, locked = self._synthetic_home(home, with_venv=True)
            for event, command in self.commands:
                with self.subTest(event=event, hook=command[-40:]):
                    proc = subprocess.run(
                        self._argv(self._probe_command(command)),
                        capture_output=True,
                        text=True,
                        timeout=120,
                        env={**os.environ, "HOME": str(home)},
                        check=False,
                    )
                    chosen = proc.stdout.strip()
                    self.assertTrue(chosen, f"hook produced no interpreter: {proc.stderr}")
                    self.assertEqual(
                        Path(chosen).resolve(),
                        Path(locked).resolve(),
                        "hook did not run on the governance-locked interpreter",
                    )
                    if ambient:
                        self.assertNotEqual(
                            Path(chosen).resolve(),
                            Path(ambient).resolve(),
                            "hook ran on ambient system python3",
                        )

    def test_missing_locked_interpreter_never_falls_back_to_ambient(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self._synthetic_home(home, with_venv=False)
            event, command = self.commands[0]
            proc = subprocess.run(
                self._argv(self._probe_command(command)),
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "HOME": str(home)},
                check=False,
            )
        # No interpreter ran at all - nothing on stdout.
        self.assertEqual(proc.stdout.strip(), "", f"{event}: something executed the hook anyway")
        # The failure is observable, not silent.
        self.assertIn("locked governance interpreter missing", proc.stderr)
        self.assertIn("did NOT run", proc.stderr)
        # Existing hook exit policy is preserved: never block the session.
        self.assertEqual(proc.returncode, 0)

    def test_absent_governance_clone_stays_quiet(self) -> None:
        """A machine with no governance at all keeps the original contract."""
        with tempfile.TemporaryDirectory() as tmp:
            _event, command = self.commands[0]
            proc = subprocess.run(
                self._argv(command),
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "HOME": tmp},
                check=False,
            )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "")
        self.assertEqual(proc.stderr.strip(), "")

    def test_locked_interpreter_satisfies_writeback_dependencies(self) -> None:
        """Section 5.5 - prove the imports the F-13 path actually needs."""
        gov = Path(os.path.expanduser("~/.cursor-governance"))
        interpreter = gov / ".venv" / "bin" / "python3"
        if not interpreter.is_file():
            self.skipTest("no locked governance interpreter in this environment")
        proc = subprocess.run(
            [
                str(interpreter),
                "-c",
                "import sys; sys.path.insert(0, sys.argv[1]); "
                "from ops.graphiti.hydration.close_session import close_session",
                str(gov),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"locked interpreter import failed: {proc.stderr}")


def _load_writeback() -> Any:
    sys.path.insert(0, str(MEMORY))
    spec = importlib.util.spec_from_file_location("memory_writeback", HOOKS / "memory_writeback.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load memory_writeback")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WritebackObservabilityTests(unittest.TestCase):
    """A dead write-back must not look like a healthy skip."""

    def setUp(self) -> None:
        self.wb = _load_writeback()
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name)
        self.session = "test-session-f13"
        self.receipts: dict[str, dict[str, Any]] = {}

        def fake_write_receipt(_contract: Any, session_id: str, payload: dict[str, Any]) -> Path:
            self.receipts[session_id] = payload
            return self.state / f"{session_id}.json"

        self.patches = [
            mock.patch.object(self.wb.st, "load_contract", return_value={"memory": {}}),
            mock.patch.object(self.wb.st, "write_receipt", side_effect=fake_write_receipt),
            mock.patch.object(self.wb.st, "workspace_root", return_value=self.state),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self) -> None:
        for patch in self.patches:
            patch.stop()
        self._tmp.cleanup()

    def _run(self) -> None:
        with mock.patch("sys.stdin", new=_Stdin({"session_id": self.session})):
            with mock.patch("sys.stderr", new=_Capture()) as err:
                rc = self.wb.main()
        self.rc = rc
        self.stderr = err.text()

    def _writeback_receipt(self) -> dict[str, Any]:
        key = f"{self.session}{self.wb.WRITEBACK_RECEIPT_SUFFIX}"
        self.assertIn(key, self.receipts, f"no write-back receipt; got {list(self.receipts)}")
        return self.receipts[key]

    def test_normal_policy_skip_is_recorded_as_a_skip(self) -> None:
        with mock.patch.object(self.wb.st, "fresh_receipt", return_value=False):
            self._run()
        self.assertEqual(self.rc, 0)
        self.assertEqual(self._writeback_receipt()["status"], "skipped_no_prefetch")

    def test_missing_module_is_recorded_as_runtime_failure(self) -> None:
        """The exact F-13 shape: pydantic absent, so write-back never ran."""
        with mock.patch.object(self.wb.st, "fresh_receipt", return_value=True):
            with mock.patch.object(self.wb.gb, "find_governance_root", return_value=self.state):
                with mock.patch.dict(sys.modules, {}, clear=False):
                    with mock.patch(
                        "builtins.__import__",
                        side_effect=_import_raiser("pydantic"),
                    ):
                        self._run()
        receipt = self._writeback_receipt()
        self.assertEqual(receipt["status"], "runtime_error")
        self.assertEqual(receipt["error"], "ModuleNotFoundError")
        self.assertEqual(receipt["missing_module"], "pydantic")
        self.assertIn("RUNTIME FAILURE", self.stderr)
        self.assertIn("did NOT run", self.stderr)

    def test_runtime_failure_is_distinguishable_from_skip(self) -> None:
        """The single invariant: two different states, not one word."""
        with mock.patch.object(self.wb.st, "fresh_receipt", return_value=False):
            self._run()
        skip_status = self._writeback_receipt()["status"]

        self.receipts.clear()
        with mock.patch.object(self.wb.st, "fresh_receipt", return_value=True):
            with mock.patch.object(self.wb.gb, "find_governance_root", return_value=self.state):
                with mock.patch("builtins.__import__", side_effect=_import_raiser("pydantic")):
                    self._run()
        failure_status = self._writeback_receipt()["status"]

        self.assertNotEqual(skip_status, failure_status)
        self.assertEqual(failure_status, "runtime_error")

    def test_stop_hook_never_blocks_session_termination(self) -> None:
        """Section 6.3 - observability, not a new blocking policy."""
        with mock.patch.object(self.wb.st, "fresh_receipt", return_value=True):
            with mock.patch.object(self.wb.gb, "find_governance_root", return_value=self.state):
                with mock.patch("builtins.__import__", side_effect=_import_raiser("anything")):
                    self._run()
        self.assertEqual(self.rc, 0)


def _import_raiser(missing: str) -> Any:
    real_import = __import__

    def _fake(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("ops.graphiti.hydration"):
            raise ModuleNotFoundError(f"No module named '{missing}'", name=missing)
        return real_import(name, *args, **kwargs)

    return _fake


class _Stdin:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._text = json.dumps(payload)

    def read(self) -> str:
        return self._text


class _Capture:
    def __init__(self) -> None:
        self._parts: list[str] = []

    def write(self, chunk: str) -> int:
        self._parts.append(chunk)
        return len(chunk)

    def flush(self) -> None:
        return None

    def text(self) -> str:
        return "".join(self._parts)


if __name__ == "__main__":
    unittest.main()
