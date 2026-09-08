#!/usr/bin/env python3
"""memory_prefetch must no-op outside a canonical Claude surface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parents[1]
ROOT = CLAUDE_DIR.parents[3]
PREFETCH = CLAUDE_DIR / "hooks" / "memory_prefetch.py"

_MARKERS = (
    "CURSOR_AGENT",
    "CLAUDECODE",
    "CLAUDE_CODE_REMOTE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION_ID",
    "L9_GOVERNANCE_SURFACE",
)


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
    def test_unknown_no_session_id_skips_with_no_context(self) -> None:
        proc = _run({})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", "must emit no additionalContext")
        self.assertIn("skipped", proc.stderr)
        self.assertIn("canonical surface detector", proc.stderr)

    def test_cursor_wins_over_projected_claude_surface(self) -> None:
        proc = _run(
            {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"},
            stdin=json.dumps({"session_id": "cursor"}),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", "Cursor must receive no Claude hydrate context")
        self.assertIn("skipped", proc.stderr)

    def test_claude_marker_does_not_take_the_skip_branch(self) -> None:
        # Empty contract dir means main() may still exit 0 early, but the
        # canonical surface skip line must not be the reason.
        proc = _run({"CLAUDECODE": "1"}, stdin=json.dumps({"session_id": "t"}))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("canonical surface detector says this is not Claude", proc.stderr)

    def test_explicit_session_id_remains_a_repair_override(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PREFETCH), "--session-id", "repair-session"],
            input="{}",
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            env={k: v for k, v in os.environ.items() if k not in _MARKERS},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("canonical surface detector says this is not Claude", proc.stderr)

    def test_prefetch_wires_shared_hydrate_classifier_after_compile(self) -> None:
        text = PREFETCH.read_text(encoding="utf-8")
        compile_pos = text.index("compiled = compile_and_format(")
        classify_pos = text.index("classify_hydrate_state(body)")
        self.assertGreater(classify_pos, compile_pos)
        self.assertNotIn("_claude_runtime_marker_present", text)

    def test_false_packet_boolean_is_not_degraded(self) -> None:
        sys.path.insert(0, str(ROOT / "ops" / "scripts"))
        from classify_hydrate_state import classify

        markdown = '```json\n{"degraded": false, "hydrate_stats": {"close_gap": false}}\n```'
        self.assertEqual(classify(markdown), (False, ""))


if __name__ == "__main__":
    unittest.main()
