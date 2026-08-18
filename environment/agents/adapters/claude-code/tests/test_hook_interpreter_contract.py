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
LAUNCHER = HOOKS / "run_governance_hook.sh"
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
    """No governance hook may depend on ambient PATH selection of python3."""

    def setUp(self) -> None:
        self.template = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_launcher_exists_and_is_executable(self) -> None:
        self.assertTrue(LAUNCHER.is_file(), "missing hooks/run_governance_hook.sh")
        self.assertTrue(os.access(LAUNCHER, os.X_OK), "launcher is not executable")

    def test_no_template_hook_execs_bare_python3(self) -> None:
        offenders = [
            (event, command)
            for event, command in _python_hook_commands(self.template)
            if re.search(r"\bexec\s+python3?\b", command)
        ]
        self.assertEqual(offenders, [], f"hooks still using PATH python3: {offenders}")

    def test_every_python_hook_routes_through_the_launcher(self) -> None:
        commands = _python_hook_commands(self.template)
        self.assertGreater(len(commands), 0, "template declares no python hooks")
        for event, command in commands:
            with self.subTest(event=event, command=command[:60]):
                self.assertIn("run_governance_hook.sh", command)

    def test_generated_settings_match_the_template_contract(self) -> None:
        """.claude/settings.json is generated; it must carry the same binding."""
        if not GENERATED.is_file():
            self.skipTest("no generated .claude/settings.json in this checkout")
        generated = json.loads(GENERATED.read_text(encoding="utf-8"))
        for event, command in _python_hook_commands(generated):
            with self.subTest(event=event):
                self.assertIn("run_governance_hook.sh", command)
                self.assertNotRegex(command, r"\bexec\s+python3?\b")

    def test_launcher_selects_the_locked_interpreter(self) -> None:
        """Direct evidence from the real command path, not merely that it exists."""
        probe = HOOKS / "_interpreter_probe.py"
        probe.write_text(
            "import sys\nprint(sys.executable)\n",
            encoding="utf-8",
        )
        try:
            proc = subprocess.run(
                ["bash", str(LAUNCHER), probe.name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        finally:
            probe.unlink(missing_ok=True)
        chosen = proc.stdout.strip()
        self.assertTrue(chosen, f"launcher produced no interpreter; stderr={proc.stderr}")
        self.assertIn(".venv", chosen, f"launcher did not select a locked venv: {chosen}")
        self.assertNotEqual(chosen, sys.executable.replace("/usr/local", "/usr/local"))

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

    def test_launcher_reports_rather_than_silently_using_system_python(self) -> None:
        """A missing locked venv must say so, not fall through to python3."""
        with tempfile.TemporaryDirectory() as home:
            proc = subprocess.run(
                ["bash", str(LAUNCHER), "memory_writeback.py"],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "HOME": home},
                input="{}",
                check=False,
            )
        self.assertEqual(proc.returncode, 0, "hook contract is fail-open on exit code")
        self.assertIn("locked governance interpreter not found", proc.stderr)
        self.assertIn("did NOT run", proc.stderr)


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
