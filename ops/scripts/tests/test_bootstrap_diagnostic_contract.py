#!/usr/bin/env python3
"""Cold-start diagnostic contract: stdout purity, probe states, surface identity.

Covers findings F-08, F-09 and F-10.

Every case runs the REAL ops/scripts/bootstrap_agent_environment.sh against a
synthetic governance root, so the gate under probe can be replaced with a stub
that produces each of the three outcomes on demand. Nothing here needs network,
AWS, Infisical or a capability broker.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BOOTSTRAP = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"
SESSION_START = REPO / "ops" / "hooks" / "session_start_bootstrap.sh"
ENSURE_UV = REPO / "ops" / "scripts" / "ensure_uv_environment.sh"
RENDERER = REPO / "ops" / "scripts" / "render_bootstrap_context.py"

#: A gate that behaves like the real one: the path rule denies a raw push and
#: never denies `make pr`. A stub that denied both would be correctly reported
#: as BROKEN, not ENFORCED - the probe distinguishes those.
GATE_DENY = """#!/usr/bin/env python3
import json, sys
event = json.load(sys.stdin)
command = (event.get("tool_input") or {}).get("command", "")
if "make pr" in command:
    raise SystemExit(0)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Publish path: `git push` is not sanctioned.",
}}))
"""

#: Both probes denied by the path rule - the sanctioned route is closed.
GATE_DENY_EVERYTHING = """#!/usr/bin/env python3
import json, sys
json.load(sys.stdin)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Publish path: everything is denied.",
}}))
"""

#: A gate that permits everything - the genuine NOT_ENFORCED case.
GATE_ALLOW = """#!/usr/bin/env python3
import json, sys
json.load(sys.stdin)
"""

#: A gate that crashes. Historically indistinguishable from GATE_ALLOW.
GATE_CRASH = """#!/usr/bin/env python3
import sys
print("Traceback (most recent call last):", file=sys.stderr)
raise SystemExit(1)
"""

#: A gate that exits 0 but returns something that carries no decision.
GATE_MALFORMED = """#!/usr/bin/env python3
import sys
json_ish = '{"hookSpecificOutput": {"hookEventName": "PreToolUse"}}'
print(json_ish)
"""


class BootstrapFixture(unittest.TestCase):
    """Builds a synthetic governance root whose gate we control."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.gov = root / "gov"
        self.workspace = root / "ws"
        (self.gov / "ops" / "autonomy").mkdir(parents=True)
        (self.gov / "ops" / "scripts").mkdir(parents=True)
        (self.gov / "kernels").mkdir(parents=True)
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic\n", encoding="utf-8")
        for kernel in ("Recursive Alignment.md", "Validate & Repair.md"):
            (self.gov / "kernels" / kernel).write_text("synthetic\n", encoding="utf-8")
        # Reuse the real locked interpreter so the preflight import check passes.
        real_venv = REPO / ".venv"
        if real_venv.is_dir():
            (self.gov / ".venv").symlink_to(real_venv)
        # The real fingerprint helper, so its stream discipline is under test too.
        (self.gov / "ops" / "scripts" / "ensure_uv_environment.sh").write_text(
            ENSURE_UV.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.workspace.mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=False, capture_output=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def install_gate(self, source: str) -> None:
        gate = self.gov / "ops" / "autonomy" / "local_execution_gate.py"
        gate.write_text(source, encoding="utf-8")
        gate.chmod(0o755)

    def run_bootstrap(
        self, *extra: str, surface: str = "claude-code"
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("L9_GOVERNANCE_SURFACE", None)
        return subprocess.run(
            [
                "bash",
                str(BOOTSTRAP),
                "--surface",
                surface,
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
                *extra,
            ],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
            check=False,
        )


class StdoutMachineContractTests(BootstrapFixture):
    """F-08 - stdout is the machine channel and carries nothing else."""

    def test_bootstrap_writes_nothing_to_stdout(self) -> None:
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap()
        self.assertEqual(
            proc.stdout,
            "",
            f"bootstrap polluted the machine channel with: {proc.stdout!r}",
        )

    def test_stdout_stays_empty_without_quiet(self) -> None:
        """The contract must not depend on the caller remembering --quiet."""
        self.install_gate(GATE_DENY)
        verbose = self.run_bootstrap()
        quiet = self.run_bootstrap("--quiet")
        self.assertEqual(verbose.stdout, "")
        self.assertEqual(quiet.stdout, "")

    def test_diagnostics_are_still_produced_on_stderr(self) -> None:
        """Redirected, not suppressed."""
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap()
        self.assertIn("publish_path_gate=", proc.stderr)
        self.assertIn("interpreter:", proc.stderr)

    def test_uv_fingerprint_diagnostic_is_stderr_only(self) -> None:
        """F-08 / section 25 - the specific helper that leaked, isolated."""
        proc = subprocess.run(
            ["bash", str(ENSURE_UV), str(REPO), "apply"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        self.assertEqual(proc.stdout, "", f"ensure_uv wrote to stdout: {proc.stdout!r}")
        self.assertIn("UV:", proc.stderr)

    def test_session_start_stdout_parses_as_one_json_document(self) -> None:
        """The renderer's input contract, asserted with no cleanup whatsoever.

        resolve_governance_paths() is pinned to $HOME/.cursor-governance by
        design (rule 06 admits no alternate root), so the chain is isolated by
        moving HOME instead: the temp HOME's clone points at this checkout, and
        every artifact the hook writes lands in the temp tree.
        """
        home = Path(self._tmp.name) / "home"
        home.mkdir()
        (home / ".cursor-governance").symlink_to(REPO)
        env = {
            **os.environ,
            "HOME": str(home),
            "CURSOR_PROJECT_DIR": str(self.workspace),
            "GOVERNANCE_BACKUP_SKIP": "1",
        }
        proc = subprocess.run(
            ["bash", str(SESSION_START)],
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
            check=False,
        )
        # No find-first-brace, no line filtering, no take-last-line.
        payload = json.loads(proc.stdout)
        self.assertIsInstance(payload, dict)
        self.assertIn("additional_context", payload)

        render = subprocess.run(
            [str(REPO / ".venv" / "bin" / "python"), str(RENDERER)],
            input=proc.stdout,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(render.returncode, 0, f"renderer rejected stdout: {render.stdout}")
        # Diagnostics survived; they simply moved off the machine channel.
        self.assertNotEqual(proc.stderr.strip(), "")


class PublishPathProbeStateTests(BootstrapFixture):
    """F-09 - three states, and PROBE_ERROR is never NOT_ENFORCED."""

    def _state(self, proc: subprocess.CompletedProcess[str]) -> str:
        for line in proc.stderr.splitlines():
            if line.startswith("publish_path_gate="):
                return line.split("=", 1)[1].strip()
        self.fail(f"no publish_path_gate state emitted; stderr was:\n{proc.stderr}")

    def test_explicit_deny_reports_enforced(self) -> None:
        self.install_gate(GATE_DENY)
        self.assertEqual(self._state(self.run_bootstrap()), "ENFORCED")

    def test_explicit_allow_reports_not_enforced(self) -> None:
        self.install_gate(GATE_ALLOW)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "NOT_ENFORCED")
        self.assertIn("NOT ENFORCED", proc.stderr)

    def test_gate_crash_reports_probe_error_not_not_enforced(self) -> None:
        """The exact inversion that made every session cry wolf."""
        self.install_gate(GATE_CRASH)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "PROBE_ERROR")
        self.assertNotIn("NOT ENFORCED", proc.stderr)
        self.assertIn("could not reach a verdict", proc.stderr)

    def test_malformed_response_reports_probe_error(self) -> None:
        self.install_gate(GATE_MALFORMED)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "PROBE_ERROR")
        self.assertNotIn("NOT ENFORCED", proc.stderr)

    def test_path_rule_denying_make_pr_reports_not_enforced(self) -> None:
        """`make pr` denied by the path rule means the only route out is closed."""
        self.install_gate(GATE_DENY_EVERYTHING)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "NOT_ENFORCED")
        self.assertIn("BROKEN", proc.stderr)

    def test_missing_gate_reports_probe_error(self) -> None:
        gate = self.gov / "ops" / "autonomy" / "local_execution_gate.py"
        if gate.exists():
            gate.unlink()
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "PROBE_ERROR")

    def test_probe_event_carries_cwd(self) -> None:
        """Section 10 - the probe must test policy, not malformed-input handling."""
        recorder = self.gov / "event.json"
        self.install_gate(
            "#!/usr/bin/env python3\n"
            "import json, sys, pathlib\n"
            "event = json.load(sys.stdin)\n"
            f"pathlib.Path({str(recorder)!r}).write_text(json.dumps(event))\n"
            'print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",'
            ' "permissionDecision": "deny",'
            ' "permissionDecisionReason": "Publish path: denied."}}))\n'
        )
        self.run_bootstrap()
        event = json.loads(recorder.read_text(encoding="utf-8"))
        self.assertEqual(event.get("cwd"), str(self.workspace))


class SurfacePropagationTests(BootstrapFixture):
    """F-10 - attribution follows L9_GOVERNANCE_SURFACE, never a constant."""

    def test_claude_code_surface_is_reported_as_claude_code(self) -> None:
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap(surface="claude-code")
        self.assertIn("surface=claude-code", proc.stderr)
        self.assertNotIn("surface=cursor", proc.stderr)

    def test_cursor_surface_still_reports_cursor(self) -> None:
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap(surface="cursor")
        self.assertIn("surface=cursor", proc.stderr)

    def test_session_start_forwards_the_runtime_surface(self) -> None:
        """The hook must pass the variable through, not a hard-coded id."""
        text = SESSION_START.read_text(encoding="utf-8")
        self.assertIn('--surface "${L9_GOVERNANCE_SURFACE:-cursor}"', text)
        self.assertNotIn("--surface cursor \\", text)

    def test_default_is_cursor_when_variable_absent(self) -> None:
        script = "\n".join(
            [
                "set -u",
                'L9_GOVERNANCE_SURFACE=""',
                'printf "%s\\n" "${L9_GOVERNANCE_SURFACE:-cursor}"',
            ]
        )
        proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
        self.assertEqual(proc.stdout.strip(), "cursor")


if __name__ == "__main__":
    unittest.main()
