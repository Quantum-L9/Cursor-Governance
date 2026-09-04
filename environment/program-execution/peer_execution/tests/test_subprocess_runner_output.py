"""Output capture is bounded, and says so; it never dies on the bytes it captures.

The runner kept a silent tail slice of stdout/stderr, digested that slice as
if it were the whole stream, and decoded strictly, so a process emitting
one non-UTF-8 byte killed the attempt with no receipt at all.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from peer_execution.subprocess_runner import _MAX_OUTPUT, CommandResult, run_argv


class OutputBoundingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _run(self, payload: bytes, *, stream: str = "stdout") -> CommandResult:
        blob = self.root / "blob.bin"
        blob.write_bytes(payload)
        target = "sys.stdout.buffer" if stream == "stdout" else "sys.stderr.buffer"
        script = f"import sys; {target}.write(open(sys.argv[1], 'rb').read())"
        return run_argv(
            [sys.executable, "-c", script, str(blob)], cwd=self.root, timeout_seconds=60
        )

    def test_output_beyond_the_budget_is_flagged_and_digested_in_full(self) -> None:
        payload = b"A" * (_MAX_OUTPUT + 10) + b"\n"
        result = self._run(payload)
        self.assertTrue(result.stdout_truncated)
        self.assertEqual(result.stdout_bytes, len(payload))
        self.assertEqual(len(result.stdout.encode("utf-8")), _MAX_OUTPUT)
        self.assertEqual(result.stdout_digest, "sha256:" + hashlib.sha256(payload).hexdigest())
        evidence = result.to_evidence()
        self.assertTrue(evidence["stdout_truncated"])
        self.assertFalse(evidence["stderr_truncated"])
        self.assertEqual(evidence["stdout_bytes"], len(payload))

    def test_stderr_is_bounded_the_same_way(self) -> None:
        payload = b"E" * (_MAX_OUTPUT + 1)
        result = self._run(payload, stream="stderr")
        self.assertTrue(result.stderr_truncated)
        self.assertFalse(result.stdout_truncated)
        self.assertEqual(result.stderr_bytes, len(payload))
        self.assertEqual(result.stderr_digest, "sha256:" + hashlib.sha256(payload).hexdigest())

    def test_output_within_the_budget_is_not_flagged(self) -> None:
        result = self._run(b"hello\n")
        self.assertFalse(result.stdout_truncated)
        self.assertEqual(result.stdout_bytes, 6)
        self.assertEqual(result.stdout, "hello\n")
        self.assertEqual(result.stdout_digest, "sha256:" + hashlib.sha256(b"hello\n").hexdigest())

    def test_invalid_utf8_output_survives_with_a_receipt(self) -> None:
        payload = b"ok\xff\xfe\n"
        result = self._run(payload)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "ok��\n")
        self.assertFalse(result.stdout_truncated)
        self.assertEqual(result.stdout_digest, "sha256:" + hashlib.sha256(payload).hexdigest())

    def test_stdin_still_reaches_the_process_as_utf8(self) -> None:
        result = run_argv(
            [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read())"],
            cwd=self.root,
            timeout_seconds=60,
            stdin="héllo",
        )
        self.assertEqual(result.stdout, "héllo")

    def test_command_result_defaults_keep_existing_constructors_valid(self) -> None:
        fake = CommandResult(
            argv=("x",),
            executable="/bin/x",
            exit_code=0,
            stdout="",
            stderr="",
            stdout_digest="sha256:" + "0" * 64,
            stderr_digest="sha256:" + "0" * 64,
            duration_seconds=0.0,
            timed_out=False,
            environment_fingerprint="sha256:test",
        )
        self.assertFalse(fake.stdout_truncated)
        self.assertIn("stdout_truncated", fake.to_evidence())


if __name__ == "__main__":
    unittest.main()
