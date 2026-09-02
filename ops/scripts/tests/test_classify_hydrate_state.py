#!/usr/bin/env python3
"""Hydrate classification: packet booleans decide, substrings never do."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import classify_hydrate_state as chs  # noqa: E402

SCRIPT = REPO / "ops" / "scripts" / "classify_hydrate_state.py"


def _packet(degraded: bool, close_gap: bool = False, reason: str = "") -> str:
    body = {
        "packet_id": "4c38fc2777aa8dc4",
        "group_id": "cursor-governance",
        "agent_id": "cursor",
        "degraded": degraded,
        "hydrate_stats": {
            "facts_returned": 6,
            "degraded": degraded,
            "degrade_reason": reason,
            "close_gap": close_gap,
        },
    }
    return (
        "graphiti hydrate: group_id=cursor-governance packet=4c38fc2777aa8dc4\n"
        "stats: facts_returned=6 | pickup_parsed=yes\n"
        "```json\n" + json.dumps(body, indent=1) + "\n```\n"
    )


class PacketBooleanTests(unittest.TestCase):
    def test_healthy_packet_with_degraded_false_text_is_not_degraded(self) -> None:
        """The regression this exists for: '"degraded": false' in the fence."""
        md = _packet(degraded=False)
        self.assertIn('"degraded": false', md)
        degraded, reason = chs.classify(md)
        self.assertFalse(degraded)
        self.assertEqual(reason, "")

    def test_packet_degraded_true_is_degraded_with_reason(self) -> None:
        degraded, reason = chs.classify(
            _packet(degraded=True, reason="search timeout")
        )
        self.assertTrue(degraded)
        self.assertEqual(reason, "search timeout")

    def test_close_gap_true_is_degraded_even_when_degraded_false(self) -> None:
        degraded, reason = chs.classify(_packet(degraded=False, close_gap=True))
        self.assertTrue(degraded)
        self.assertIn("close_gap", reason)

    def test_packet_wins_over_prose_mentioning_degraded(self) -> None:
        md = "notes: a previous session was degraded\n" + _packet(degraded=False)
        degraded, _ = chs.classify(md)
        self.assertFalse(degraded)


class NoPacketFallbackTests(unittest.TestCase):
    def test_hydrate_cli_missing_is_degraded(self) -> None:
        degraded, reason = chs.classify("hydrate CLI missing — cannot compile packet")
        self.assertTrue(degraded)
        self.assertEqual(reason, "hydrate CLI missing")

    def test_leading_degraded_marker_is_degraded(self) -> None:
        degraded, reason = chs.classify("DEGRADED\nREPAIR: /end-session")
        self.assertTrue(degraded)
        self.assertIn("DEGRADED", reason)

    def test_bare_degraded_substring_without_packet_is_not_degraded(self) -> None:
        degraded, _ = chs.classify("the word degraded appears in prose only")
        self.assertFalse(degraded)

    def test_disabled_message_is_not_degraded(self) -> None:
        degraded, _ = chs.classify("Graphiti disabled — no resume memory")
        self.assertFalse(degraded)


class CliContractTests(unittest.TestCase):
    def _run(self, md: str) -> tuple[str, str]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=md,
            capture_output=True,
            text=True,
            check=True,
        )
        lines = proc.stdout.splitlines()
        return lines[0], lines[1] if len(lines) > 1 else ""

    def test_cli_healthy_packet(self) -> None:
        flag, reason = self._run(_packet(degraded=False))
        self.assertEqual(flag, "false")
        self.assertEqual(reason, "")

    def test_cli_degraded_packet(self) -> None:
        flag, reason = self._run(_packet(degraded=True, reason="empty task state"))
        self.assertEqual(flag, "true")
        self.assertEqual(reason, "empty task state")

    def test_cli_reason_is_single_line(self) -> None:
        md = "```json\n" + json.dumps(
            {"degraded": True, "hydrate_stats": {"degrade_reason": "a\nb\nc"}}
        ) + "\n```"
        flag, reason = self._run(md)
        self.assertEqual(flag, "true")
        self.assertNotIn("\n", reason)


if __name__ == "__main__":
    unittest.main()
