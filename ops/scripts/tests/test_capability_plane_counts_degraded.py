#!/usr/bin/env python3
"""A dead capability plane is a DEGRADED component, not a warning (INV-3).

Covers audit finding B-08 and acceptance test T-01.

The bootstrap used to run the capability check as `... || warn "capability plane
DEGRADED"` — a warning with no effect on the counter. Every other section in the
file increments. So a session whose entire capability plane was unreachable
still printed "Agent environment ready" and wrote `--degraded-count 0` into the
runtime readiness receipt.

Each case stubs ops/secrets/bootstrap_agent_env.sh to exit with a chosen code
and stubs the receipt writer to record its argv, so the assertion is on what the
receipt WOULD carry rather than on log prose.
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

#: The path rule denies a raw push and never denies `make pr` — the shape the
#: publish-path probe expects, so it does not add a degradation of its own.
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

EXIT_DEGRADED = 6


class CapabilityPlaneDegradedTests(unittest.TestCase):
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
        # The real uv sync cannot succeed against a synthetic root with no
        # pyproject/uv.lock, and its failure would satisfy `degraded > 0` on its
        # own — letting every assertion below pass even with the fix reverted.
        # Stub it so the capability plane is the ONLY possible degradation, and
        # the counts can be asserted exactly.
        (self.gov / "ops" / "scripts" / "ensure_uv_environment.sh").write_text(
            "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
        )
        gate = self.gov / "ops" / "autonomy" / "local_execution_gate.py"
        gate.write_text(GATE_DENY, encoding="utf-8")
        gate.chmod(0o755)

        # gitleaks is genuinely absent from this runtime and would add its own
        # degradation, masking the one under test.
        gitleaks = self.bin / "gitleaks"
        gitleaks.write_text("#!/bin/sh\necho 'gitleaks version 8.24.3'\n", encoding="utf-8")
        gitleaks.chmod(0o755)

        self.receipt_argv = self.root / "receipt-argv.json"
        writer = self.gov / "ops" / "scripts" / "write_runtime_readiness_receipt.py"
        writer.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys, os\n"
            f"open({str(self.receipt_argv)!r}, 'w').write(json.dumps(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        self.workspace.mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=False, capture_output=True)
        self.addCleanup(self._tmp.cleanup)

    def _install_capability_stub(self, exit_code: int, message: str = "") -> None:
        stub = self.gov / "ops" / "secrets" / "bootstrap_agent_env.sh"
        stub.write_text(
            f'#!/usr/bin/env bash\nprintf "%s\\n" {message!r} >&2\nexit {exit_code}\n',
            encoding="utf-8",
        )

    def _run(self) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("L9_GOVERNANCE_SURFACE", None)
        env["PATH"] = f"{self.bin}:{env.get('PATH', '')}"
        return subprocess.run(
            [
                "bash",
                str(BOOTSTRAP),
                "--surface",
                "claude-code",
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
        self.assertTrue(self.receipt_argv.is_file(), "the receipt writer was never invoked")
        argv = json.loads(self.receipt_argv.read_text(encoding="utf-8"))
        self.assertIn("--degraded-count", argv)
        return int(argv[argv.index("--degraded-count") + 1])

    # -- T-01 ---------------------------------------------------------------

    def test_degraded_capability_plane_counts_and_blocks_the_ready_banner(self) -> None:
        self._install_capability_stub(1, "capability bootstrap: DEGRADED")
        result = self._run()
        self.assertEqual(result.returncode, EXIT_DEGRADED)
        self.assertNotIn("Agent environment ready", result.stderr)
        self.assertEqual(
            self._degraded_count(), 1, "the receipt must carry exactly this degradation"
        )

    def test_blocked_by_platform_counts_and_is_named_as_such(self) -> None:
        """Exit 4 is the platform-blocked class and must not read as a config gap."""
        self._install_capability_stub(4)
        result = self._run()
        self.assertEqual(result.returncode, EXIT_DEGRADED)
        self.assertIn("BLOCKED_BY_PLATFORM", result.stderr)
        self.assertNotIn("no broker configured", result.stderr)
        self.assertEqual(self._degraded_count(), 1)

    def test_absent_capability_bootstrap_counts(self) -> None:
        """A missing capability plane is still a missing capability plane."""
        result = self._run()  # no stub installed at all
        self.assertEqual(result.returncode, EXIT_DEGRADED)
        self.assertEqual(self._degraded_count(), 1)

    def test_healthy_capability_plane_reaches_the_ready_banner(self) -> None:
        """Regression guard: the counter must not fire when nothing is wrong."""
        self._install_capability_stub(0)
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("Agent environment ready", result.stderr)
        self.assertEqual(self._degraded_count(), 0)


if __name__ == "__main__":
    unittest.main()
