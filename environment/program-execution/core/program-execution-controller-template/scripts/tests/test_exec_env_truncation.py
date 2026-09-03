"""Validation output tails are declared as tails."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS

sys.path.insert(0, str(SCRIPTS))
from pec.exec_env import (  # noqa: E402
    _EVIDENCE_TAIL,
    _STREAM_TAIL,
    TRUNCATION_MARKER,
    run_validation_command,
    to_attempt_result,
)


class ValidationTruncationTests(unittest.TestCase):
    def test_a_stream_beyond_the_tail_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = run_validation_command(
                f"python3 -c \"print('x' * {_STREAM_TAIL + 100})\"", Path(raw)
            )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["stdout_truncated"])
        self.assertFalse(result["stderr_truncated"])
        self.assertEqual(len(result["stdout"]), _STREAM_TAIL)

    def test_a_short_stream_is_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = run_validation_command("echo ok", Path(raw))
        self.assertFalse(result["stdout_truncated"])
        self.assertFalse(result["stderr_truncated"])
        self.assertEqual(result["stdout"], "ok\n")

    def test_the_attempt_receipt_marks_cut_evidence_within_the_schema_shape(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = run_validation_command(
                f"python3 -c \"print('y' * {_STREAM_TAIL + 100}); raise SystemExit(3)\"",
                Path(raw),
            )
        entry = to_attempt_result(result)
        self.assertEqual(sorted(entry), ["command", "evidence", "exit_code", "status"])
        self.assertTrue(entry["evidence"].startswith(TRUNCATION_MARKER))
        self.assertIn(f"{_EVIDENCE_TAIL} of ", entry["evidence"])
        self.assertTrue(entry["evidence"].endswith("y"))

    def test_evidence_cut_only_by_the_evidence_tail_is_also_marked(self) -> None:
        body = "z" * (_EVIDENCE_TAIL + 5)
        entry = to_attempt_result(
            {"command": "x", "status": "FAIL", "exit_code": 1, "stdout": body, "stderr": ""}
        )
        self.assertTrue(entry["evidence"].startswith(TRUNCATION_MARKER))
        self.assertIn(f"{_EVIDENCE_TAIL} of {len(body)} characters", entry["evidence"])

    def test_complete_evidence_carries_no_marker(self) -> None:
        entry = to_attempt_result(
            {"command": "x", "status": "PASS", "exit_code": 0, "stdout": "fine\n", "stderr": ""}
        )
        self.assertEqual(entry["evidence"], "fine")


if __name__ == "__main__":
    unittest.main()
