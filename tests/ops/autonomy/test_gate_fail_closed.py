#!/usr/bin/env python3
"""F-11 - the execution gate denies when it cannot evaluate.

A PreToolUse hook that exits non-zero without emitting a decision is treated as
non-blocking, so an uncaught exception inside a gate whose purpose is to fail
closed became an accidental permit. These tests pin the inverse: every internal
evaluation fault produces a valid denial response, on both entrypoints.

Security decision (ALLOW / DENY) and diagnostic detail are separate channels:
the decision goes to stdout as the hook protocol payload, the reason the
evaluation failed goes to stderr.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
GATE_PATH = REPO / "ops" / "autonomy" / "local_execution_gate.py"


def _load_gate() -> Any:
    spec = importlib.util.spec_from_file_location("local_execution_gate", GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["local_execution_gate"] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _run(event: dict[str, Any], mode: str = "claude") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE_PATH), mode],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _decision(stdout: str) -> str | None:
    if not stdout.strip():
        return None
    payload = json.loads(stdout)
    hook = payload.get("hookSpecificOutput")
    if hook is not None:
        return str(hook.get("permissionDecision"))
    return str(payload.get("permission"))


class PreservedPolicyBehaviourTests(unittest.TestCase):
    """Section 22 - this slice repairs failure semantics, not policy."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=False, capture_output=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_prohibited_publish_is_still_denied(self) -> None:
        proc = _run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git push origin main"},
                "cwd": str(self.repo),
            }
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(_decision(proc.stdout), "deny")
        self.assertIn("Publish path", proc.stdout)

    def test_ordinary_command_is_still_allowed(self) -> None:
        proc = _run(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
                "cwd": str(self.repo),
            }
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIsNone(_decision(proc.stdout), "a benign command must stay allowed")


class FailClosedTests(unittest.TestCase):
    """Every internal fault denies, with a valid hook response."""

    def test_workspace_resolution_failure_denies(self) -> None:
        """The live regression: no cwd, and process cwd is not a git work tree."""
        with tempfile.TemporaryDirectory() as non_repo:
            proc = subprocess.run(
                [sys.executable, str(GATE_PATH), "claude"],
                input=json.dumps(
                    {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}
                ),
                capture_output=True,
                text=True,
                cwd=non_repo,
                timeout=60,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, "must not exit non-zero without a decision")
        self.assertEqual(_decision(proc.stdout), "deny")
        self.assertIn("INTERNAL_EVALUATION_ERROR", proc.stdout)
        # Diagnostic detail is available, and is NOT the decision channel.
        self.assertIn("failing closed", proc.stderr)
        self.assertNotIn("Traceback", proc.stdout)

    def test_policy_evaluation_exception_denies(self) -> None:
        with mock.patch.object(gate, "evaluate", side_effect=RuntimeError("policy boom")):
            with mock.patch("sys.stdin", new=_StringStdin({"tool_name": "Bash", "tool_input": {}})):
                with mock.patch("sys.stdout", new=_Capture()) as out:
                    with mock.patch("sys.stderr", new=_Capture()) as err:
                        rc = gate.main_claude()
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out.text()), "deny")
        self.assertIn("INTERNAL_EVALUATION_ERROR", out.text())
        self.assertIn("policy boom", err.text())

    def test_workspace_helper_exception_denies(self) -> None:
        with mock.patch.object(
            gate, "workspace_from_event", side_effect=RuntimeError("workspace boom")
        ):
            with mock.patch("sys.stdin", new=_StringStdin({"tool_name": "Bash", "tool_input": {}})):
                with mock.patch("sys.stdout", new=_Capture()) as out:
                    with mock.patch("sys.stderr", new=_Capture()):
                        rc = gate.main_claude()
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out.text()), "deny")

    def test_cursor_shell_entrypoint_also_fails_closed(self) -> None:
        with mock.patch.object(gate, "effective_root", side_effect=RuntimeError("root boom")):
            with mock.patch("sys.stdin", new=_StringStdin({"command": "git push origin main"})):
                with mock.patch("sys.stdout", new=_Capture()) as out:
                    with mock.patch("sys.stderr", new=_Capture()):
                        rc = gate.main_cursor_shell()
        self.assertEqual(rc, 0)
        self.assertEqual(_decision(out.text()), "deny")
        self.assertIn("INTERNAL_EVALUATION_ERROR", out.text())

    def test_failure_never_yields_allow(self) -> None:
        """The single invariant this finding exists for."""
        for target in ("evaluate", "workspace_from_event"):
            with self.subTest(target=target):
                with mock.patch.object(gate, target, side_effect=ValueError("boom")):
                    with mock.patch(
                        "sys.stdin", new=_StringStdin({"tool_name": "Bash", "tool_input": {}})
                    ):
                        with mock.patch("sys.stdout", new=_Capture()) as out:
                            with mock.patch("sys.stderr", new=_Capture()):
                                gate.main_claude()
                self.assertNotEqual(_decision(out.text()), "allow")
                self.assertEqual(_decision(out.text()), "deny")


class _StringStdin:
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
