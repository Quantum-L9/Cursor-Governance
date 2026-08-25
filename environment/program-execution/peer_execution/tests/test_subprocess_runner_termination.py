"""T-004 (Claude direct) regression: timeout termination kills the whole
process group — parent and spawned descendants — and evidence records it.

`run_argv` already starts a new session and escalates process-group
SIGTERM -> SIGKILL on timeout; this suite is the missing process-death proof,
not a behavior change.
"""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

from peer_execution.subprocess_runner import run_argv

_HEARTBEAT_SCRIPT = r"""
import subprocess, sys, time
heartbeat = sys.argv[1]
child = subprocess.Popen(
    [sys.executable, "-c",
     "import sys, time\n"
     "while True:\n"
     "    with open(sys.argv[1], 'a') as handle:\n"
     "        handle.write('beat\n')\n"
     "    time.sleep(0.05)",
     heartbeat],
)
print(f"child={child.pid}", flush=True)
time.sleep(60)
"""


class SubprocessGroupTerminationTests(unittest.TestCase):
    def test_timeout_kills_parent_and_descendants(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workdir = Path(raw)
            heartbeat = workdir / "heartbeat.log"
            started = time.monotonic()
            result = run_argv(
                [sys.executable, "-c", _HEARTBEAT_SCRIPT, str(heartbeat)],
                cwd=workdir,
                timeout_seconds=2,
            )
            elapsed = time.monotonic() - started
            self.assertTrue(result.timed_out)
            self.assertTrue(result.to_evidence()["timed_out"])
            # The 60s parent sleep never ran to completion.
            self.assertLess(elapsed, 30)
            # The descendant heartbeat writer is dead: no writes after return.
            size_after_return = heartbeat.stat().st_size if heartbeat.is_file() else 0
            time.sleep(0.5)
            size_later = heartbeat.stat().st_size if heartbeat.is_file() else 0
            self.assertEqual(size_after_return, size_later)

    def test_fast_process_is_not_marked_timed_out(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = run_argv(
                [sys.executable, "-c", "print('ok')"],
                cwd=raw,
                timeout_seconds=30,
            )
        self.assertFalse(result.timed_out)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
