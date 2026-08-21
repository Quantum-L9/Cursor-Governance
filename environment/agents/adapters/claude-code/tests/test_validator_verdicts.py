#!/usr/bin/env python3
"""Structural validity is not runtime readiness (INV-8, B-23).

Covers acceptance test T-14.

The audited runtime had eleven components NOT_LOADED, no bootstrap receipt and
no governance refresh — and this validator printed "RESULT: PASS — Claude Code
environment adapter is structurally sound". Every file it checks WAS correct.
That is the point: a file-level validator must not emit a word that reads as
readiness.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
VALIDATOR = REPO / "environment" / "agents" / "adapters" / "claude-code" / "validate_claude_env.py"

EXIT_OK = 0
EXIT_STRUCTURAL_FAIL = 1
EXIT_RUNTIME_NOT_READY = 5


class ValidatorVerdictTests(unittest.TestCase):
    def _run(self, *args: str, home: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        if home is not None:
            env["HOME"] = str(home)
            env.pop("L9_CLAUDE_BOOTSTRAP_RECEIPT", None)
            env.pop("L9_GOV_REFRESH_RECEIPT", None)
        return subprocess.run(
            ["python3", str(VALIDATOR), *args],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def _verdict(self, stdout: str) -> str:
        """This validator's OWN final verdict line.

        Not a substring search: the sub-validators it invokes print their own
        `RESULT:` lines into the same stream, so matching anywhere would assert
        against someone else's verdict.
        """
        lines = [ln for ln in stdout.splitlines() if ln.startswith("RESULT: ")]
        self.assertTrue(lines, "validator emitted no verdict")
        return lines[-1]

    def test_never_emits_a_bare_pass(self) -> None:
        """INV-8 is about the WORD, not about the repo currently being clean.

        Asserting STRUCTURAL_PASS would couple this test to whether every other
        contract in the repository happens to validate today — which is how it
        broke: a pre-existing memory-enforcement schema mismatch (unrelated to
        this adapter) turned the verdict to STRUCTURAL_FAIL and took three
        vocabulary assertions down with it.
        """
        verdict = self._verdict(self._run().stdout)
        self.assertRegex(verdict, r"^RESULT: STRUCTURAL_(PASS|FAIL)")
        self.assertNotEqual(verdict, "RESULT: PASS")
        self.assertNotRegex(verdict, r"^RESULT: PASS\b")

    def test_runtime_flag_reports_not_loaded_on_a_bare_home(self) -> None:
        """No receipts at all — the exact audited state."""
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run("--runtime", home=Path(tmp))
        self.assertIn("RUNTIME: NOT_LOADED", result.stdout)
        self.assertIn("never_ran", result.stdout)
        self.assertIn(result.returncode, (EXIT_RUNTIME_NOT_READY, EXIT_STRUCTURAL_FAIL))

    def test_structural_and_runtime_verdicts_are_separately_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run("--runtime", home=Path(tmp))
        structural = result.stdout.index(self._verdict(result.stdout))
        runtime = result.stdout.index("RUNTIME:")
        self.assertLess(structural, runtime, "runtime verdict must follow, not replace, structural")

    def test_make_claude_env_asserts_runtime(self) -> None:
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        self.assertIn("validate_claude_env.py --runtime", makefile)


if __name__ == "__main__":
    unittest.main()
