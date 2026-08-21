#!/usr/bin/env python3
"""The installer leaves a receipt on every exit path (INV-2, B-04).

Covers acceptance tests T-09, T-10, T-41.

Each case runs the REAL install.sh against a synthetic governance root broken in
one specific way. The audited runtime had NO receipt at all — the installer's
bookkeeping lived below the failure point and inside an `if [ -n "$GOV_PY" ]`
that a missing interpreter never satisfied — so every one of these paths used to
produce silence.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from claude_bootstrap_receipt import NEVER_RAN, read  # noqa: E402

INSTALL = REPO / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"


class InstallReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.gov = self.root / "gov"
        self.gov.mkdir()
        self.workspace = self.root / "ws"
        self.workspace.mkdir()
        self.receipt = self.root / "bootstrap-state.json"
        self.addCleanup(self._tmp.cleanup)

    def _run(self) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update(
            {
                "HOME": str(self.home),
                "L9_CLAUDE_BOOTSTRAP_RECEIPT": str(self.receipt),
            }
        )
        env.pop("L9_GOVERNANCE_DIR", None)
        return subprocess.run(
            [
                "bash",
                str(INSTALL),
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def _receipt(self) -> dict:
        self.assertTrue(self.receipt.is_file(), "every exit path must leave a receipt")
        return json.loads(self.receipt.read_text(encoding="utf-8"))

    # -- T-09: a failure leaves a receipt naming the stage -------------------

    def test_absent_governance_writes_a_failed_receipt(self) -> None:
        """The earliest guard clause — it used to exit 1 before any bookkeeping."""
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        parsed = self._receipt()
        self.assertEqual(parsed["state"], "failed")
        self.assertEqual(parsed["stage"], "startup")
        self.assertTrue(parsed["remediation"], "a failure receipt must name its repair")
        self.assertRegex(parsed["generated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_missing_interpreter_still_writes_a_receipt(self) -> None:
        """The exact audited shape: governance present, no .venv, no receipt.

        This is the branch that used to `downgrade ... "no receipt written"` and
        then write nothing — recording the problem in a file it declined to
        create.
        """
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        result = self._run()
        self.assertNotEqual(result.returncode, 0, "BLOCKED must exit non-zero")
        parsed = self._receipt()
        self.assertEqual(parsed["state"], "BLOCKED")
        self.assertEqual(parsed["shared_bootstrap"], "BLOCKED")
        self.assertEqual(parsed["workspace"], str(self.workspace))

    def test_receipt_is_parseable_json_without_the_locked_interpreter(self) -> None:
        """It is written in bash precisely because .venv may be the thing missing."""
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        self._run()
        parsed = self._receipt()
        self.assertEqual(parsed["schema"], "l9.claude-bootstrap.v1")
        self.assertIsInstance(parsed["ttl_seconds"], int)

    def test_non_repository_workspace_is_blocked_not_ready(self) -> None:
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        self._run()  # workspace is not a git repo
        parsed = self._receipt()
        for key in ("settings", "skills", "rules"):
            self.assertEqual(parsed[key], "BLOCKED", f"{key} must not read READY")

    # -- T-10: absence is never_ran, never ready ----------------------------

    def test_absent_receipt_reads_never_ran(self) -> None:
        result = read(self.receipt)
        self.assertEqual(result["state"], NEVER_RAN)
        self.assertIn("never completed", result["reason"])

    def test_reader_classifies_the_failed_receipt(self) -> None:
        self._run()
        result = read(self.receipt)
        self.assertEqual(result["state"], "failed")
        self.assertIn("startup", result["reason"])


if __name__ == "__main__":
    unittest.main()
