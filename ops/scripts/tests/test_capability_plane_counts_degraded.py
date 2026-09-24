#!/usr/bin/env python3
"""Capability broker is retired — shared bootstrap must not score it as DEGRADED.

The broker never shipped. Session bootstrap owns session_start_secrets.py and
does not call ops/secrets/bootstrap_agent_env.sh. Stubs at that path must not
change the degraded-count or the ready banner.
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


class _PlaneBootstrapCase(unittest.TestCase):
    """Shared bootstrap fixture. Carries no tests of its own."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.gov = self.root / "gov"
        self.workspace = self.root / "ws"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for sub in ("ops/autonomy", "ops/scripts", "ops/secrets", "ops/graphiti", "kernels"):
            (self.gov / sub).mkdir(parents=True, exist_ok=True)
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic\n", encoding="utf-8")
        for kernel in ("Recursive Alignment.md", "Validate & Repair.md"):
            (self.gov / "kernels" / kernel).write_text("synthetic\n", encoding="utf-8")
        real_venv = REPO / ".venv"
        if real_venv.is_dir():
            (self.gov / ".venv").symlink_to(real_venv)
        (self.gov / "ops" / "scripts" / "ensure_uv_environment.sh").write_text(
            "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
        )
        gate = self.gov / "ops" / "autonomy" / "local_execution_gate.py"
        gate.write_text(GATE_DENY, encoding="utf-8")
        gate.chmod(0o755)
        gitleaks = self.bin / "gitleaks"
        gitleaks.write_text("#!/bin/sh\necho 'gitleaks version 8.24.3'\n", encoding="utf-8")
        gitleaks.chmod(0o755)
        self.receipt_argv = self.root / "receipt-argv.json"
        writer = self.gov / "ops" / "scripts" / "write_runtime_readiness_receipt.py"
        writer.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"open({str(self.receipt_argv)!r}, 'w').write(json.dumps(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        self.workspace.mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=False, capture_output=True)
        self.addCleanup(self._tmp.cleanup)

    def _write_owner(self, *, exit_code: int, receipt: dict[str, object] | None = None) -> None:
        """Stand in for session_start_secrets.py with a chosen exit + receipt."""
        owner = self.gov / "ops" / "secrets" / "session_start_secrets.py"
        owner.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "receipt = " + repr(json.dumps(receipt) if receipt is not None else None) + "\n"
            "if receipt is not None and '--receipt-out' in sys.argv:\n"
            "    dest = sys.argv[sys.argv.index('--receipt-out') + 1]\n"
            "    open(dest, 'w', encoding='utf-8').write(receipt)\n"
            f"raise SystemExit({exit_code})\n",
            encoding="utf-8",
        )

    def _run(self, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("L9_GOVERNANCE_SURFACE", None)
        env.pop("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE", None)
        env.pop("CLAUDE_CODE_REMOTE_ENVIRONMENT_ID", None)
        env.update(extra_env or {})
        env["PATH"] = f"{self.bin}:{env.get('PATH', '')}"
        return subprocess.run(
            [
                "bash",
                str(BOOTSTRAP),
                "--surface",
                "cursor",
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def _degraded_count(self) -> int:
        argv = json.loads(self.receipt_argv.read_text(encoding="utf-8"))
        return int(argv[argv.index("--degraded-count") + 1])


class RetiredCapabilityPlaneTests(_PlaneBootstrapCase):
    def test_retired_plane_does_not_degrade_or_call_the_stub(self) -> None:
        self._write_owner(exit_code=0)
        stub = self.gov / "ops" / "secrets" / "bootstrap_agent_env.sh"
        stub.write_text("#!/usr/bin/env bash\necho STUB_RAN >&2\nexit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("secrets plane: session_start_secrets.py", result.stderr)
        self.assertNotIn("STUB_RAN", result.stderr)
        self.assertIn("Agent environment ready", result.stderr)
        self.assertEqual(self._degraded_count(), 0)


class SecretsPlaneNoSurfaceExemptionTests(_PlaneBootstrapCase):
    """Infisical is the only plane and no surface is exempt from binding it.

    The retired AWS carve-out scored a hosted surface's missing plane as "not a
    fault". Every surface now binds through its machine identity, so a hosted
    surface that did not bind degrades exactly like any other.
    """

    HOSTED = {"CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default"}

    def test_a_hosted_surface_without_an_identity_degrades(self) -> None:
        self._write_owner(exit_code=1)
        result = self._run(self.HOSTED)
        self.assertIn("session_start_secrets failed", result.stderr)
        self.assertNotIn("unavailable by surface", result.stderr)
        self.assertEqual(self._degraded_count(), 1)

    def test_owner_failure_still_degrades(self) -> None:
        """The negative: a surface that should have bound, and did not."""
        self._write_owner(exit_code=1)
        result = self._run()
        self.assertIn("session_start_secrets failed", result.stderr)
        self.assertNotIn("unavailable by surface", result.stderr)
        self.assertEqual(self._degraded_count(), 1)

    def test_plane_ok_says_nothing_about_the_surface(self) -> None:
        """state=ok reports the identity and prints no exemption line."""
        self._write_owner(
            exit_code=0,
            receipt={"ok": True, "state": "ok", "surface_class": "operator", "binds": []},
        )
        result = self._run(self.HOSTED)
        self.assertNotIn("unavailable by surface", result.stderr)
        self.assertEqual(self._degraded_count(), 0)


if __name__ == "__main__":
    unittest.main()
