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


def test_hydration_cursor_rotates_and_fails_open(tmp_path) -> None:
    """The cap must rotate, and a broken cursor must never cost hydration.

    A cap plus a stable sort served the same six repositories every session and
    starved the same six forever. The cursor advances the window; a missing or
    corrupt one costs the session its rotation, never its facts — this runs
    inside a fail-open observer hook.
    """
    import importlib.util
    from pathlib import Path as _Path

    here = _Path(__file__).resolve().parents[1] / "hooks" / "memory_prefetch.py"
    spec = importlib.util.spec_from_file_location("mp_cursor", here)
    mp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mp)

    mp._CURSOR_FILE = tmp_path / "hydration-cursor.json"
    ws = tmp_path / "container"

    assert mp._read_hydration_offset(ws) == 0, "absent cursor starts at zero"

    mp._advance_hydration_cursor(ws, 6)
    assert mp._read_hydration_offset(ws) == 6
    mp._advance_hydration_cursor(ws, 6)
    assert mp._read_hydration_offset(ws) == 12

    # Per container, never global: a sibling workspace keeps its own window.
    assert mp._read_hydration_offset(tmp_path / "other") == 0

    # A no-op hydrate must not move the window past unserved repositories.
    mp._advance_hydration_cursor(ws, 0)
    assert mp._read_hydration_offset(ws) == 12

    # Corrupt, unreadable and hostile cursors all degrade to zero, never raise.
    mp._CURSOR_FILE.write_text("{ not json", encoding="utf-8")
    assert mp._read_hydration_offset(ws) == 0
    mp._CURSOR_FILE.write_text('{"' + str(ws) + '": -5}', encoding="utf-8")
    assert mp._read_hydration_offset(ws) == 0
    mp._CURSOR_FILE.write_text('["not", "a", "mapping"]', encoding="utf-8")
    assert mp._read_hydration_offset(ws) == 0
