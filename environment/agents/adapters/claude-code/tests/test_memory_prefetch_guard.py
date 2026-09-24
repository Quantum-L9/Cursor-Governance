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
        self.assertNotIn('agent_id="claude-code"', text)
        self.assertNotIn('or ["cursor-governance"]', text)

    def test_prefetch_agent_id_follows_canonical_surface(self) -> None:
        sys.path.insert(0, str(PREFETCH.parent))
        import memory_prefetch as prefetch

        self.assertEqual(prefetch.prefetch_agent_id({"CURSOR_AGENT": "1"}), "cursor")
        self.assertEqual(
            prefetch.prefetch_agent_id(
                {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"}
            ),
            "cursor",
        )
        # One identity per surface, never one "claude-code" (ops/memory/agent_identity.py).
        self.assertEqual(prefetch.prefetch_agent_id({"CLAUDECODE": "1"}), "claude-code-desktop")
        self.assertEqual(
            prefetch.prefetch_agent_id({"L9_GOVERNANCE_SURFACE": "claude-code"}),
            "claude-code-desktop",
        )
        self.assertEqual(
            prefetch.prefetch_agent_id(
                {
                    "CLAUDECODE": "1",
                    "CLAUDE_CODE_REMOTE": "true",
                    "CLAUDE_CODE_ENTRYPOINT": "remote_mobile",
                }
            ),
            "claude-code-mobile",
        )
        self.assertEqual(
            prefetch.prefetch_agent_id({"CLAUDECODE": "1", "CLAUDE_CODE_REMOTE": "true"}),
            "claude-code-web",
        )

    def test_a_degraded_read_is_shown_to_the_user(self) -> None:
        """A memory read that failed or degraded is a user-visible systemMessage."""
        sys.path.insert(0, str(PREFETCH.parent))
        import memory_prefetch as prefetch

        quiet = prefetch.hook_session_start_payload("ctx")
        self.assertNotIn("systemMessage", quiet, "a healthy read adds nothing")
        loud = prefetch.hook_session_start_payload(
            "ctx", prefetch._loud_read_failure("DEGRADED at session start: x")
        )
        self.assertEqual(loud["systemMessage"], "L9 MEMORY READ — DEGRADED at session start: x")

    def test_additional_context_is_a_string_not_an_array(self) -> None:
        """SESSION_START_SPEC §3: ``additionalContext`` is a string.

        An array is not concatenated by the host — it is not injected at all,
        so the prefetch can hydrate successfully and still deliver nothing.
        The wire type is therefore asserted directly, since that is the
        property the host contract turns on.
        """
        sys.path.insert(0, str(PREFETCH.parent))
        import memory_prefetch as prefetch

        context = (
            "L9 memory: ENFORCED\n"
            "transport=memory-control-plane/v1\n"
            "namespace=cursor-governance\n"
            "law=CANONICAL_LAW §8"
        )
        payload = prefetch.hook_session_start_payload(context)
        emitted = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIsInstance(emitted, str)
        self.assertNotIsInstance(emitted, list)
        self.assertEqual(emitted, context)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")

        # Assert the shape on the wire form too — that is what the host parses.
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        reparsed = json.loads(rendered)
        self.assertIsInstance(reparsed["hookSpecificOutput"]["additionalContext"], str)
        self.assertEqual(reparsed["hookSpecificOutput"]["additionalContext"], context)

        # Readability of the *content* is still guaranteed: ensure_ascii=False
        # keeps the section sign literal rather than §-escaped.
        self.assertIn("CANONICAL_LAW §8", rendered)
        self.assertNotIn("\\u00a7", rendered)

    def test_false_packet_boolean_is_not_degraded(self) -> None:
        sys.path.insert(0, str(ROOT / "ops" / "scripts"))
        from classify_hydrate_state import classify

        markdown = '```json\n{"degraded": false, "hydrate_stats": {"close_gap": false}}\n```'
        self.assertEqual(classify(markdown), (False, ""))


if __name__ == "__main__":
    unittest.main()
