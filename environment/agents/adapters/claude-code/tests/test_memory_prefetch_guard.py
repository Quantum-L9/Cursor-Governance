#!/usr/bin/env python3
"""memory_prefetch must no-op outside a Claude runtime (observer-class guard).

Observed leak: a Cursor session's context carried two agent_id=claude-code
hydrate blocks because this hook ran with no runtime guard. The guard mirrors
the marker set session_start_claude_governance.sh already trusts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parents[1]
PREFETCH = CLAUDE_DIR / "hooks" / "memory_prefetch.py"

_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_REMOTE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID")


def _run(env_extra: dict[str, str], stdin: str = "{}") -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in _MARKERS}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(PREFETCH)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )


class PrefetchRuntimeGuardTests(unittest.TestCase):
    def test_no_marker_no_session_id_skips_with_no_context(self) -> None:
        proc = _run({})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", "must emit no additionalContext")
        self.assertIn("skipped", proc.stderr)
        self.assertIn("no Claude runtime marker", proc.stderr)

    def test_marker_present_does_not_take_the_skip_branch(self) -> None:
        # Empty contract dir means main() may still exit 0 early, but the skip
        # log line must not be the reason.
        proc = _run({"CLAUDECODE": "1"}, stdin=json.dumps({"session_id": "t"}))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("no Claude runtime marker", proc.stderr)


if __name__ == "__main__":
    unittest.main()
