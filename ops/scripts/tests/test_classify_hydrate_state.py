#!/usr/bin/env python3
"""Hydrate classification: packet booleans decide, substrings never do.

ADR-0032: ``degraded`` is canonical memory degradation only. Close-gap,
staleness and an unbound runtime are reported as *conditions* on a third
output line and never flip the degraded flag.
"""

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


def _packet(
    degraded: bool,
    close_gap: bool = False,
    reason: str = "",
    continuation_stale: bool | None = None,
    *,
    memory_degraded: bool | None = None,
    environment_fault: bool | None = None,
    memory_status: str | None = None,
    close_gap_reason: str = "",
    fault_class: str | None = None,
    environment_fault_reason: str = "",
) -> str:
    stats: dict = {
        "facts_returned": 6,
        "degraded": degraded,
        "degrade_reason": reason,
        "close_gap": close_gap,
        "continuation_stale": continuation_stale,
    }
    body: dict = {
        "packet_id": "4c38fc2777aa8dc4",
        "group_id": "cursor-governance",
        "agent_id": "cursor",
        "degraded": degraded,
        "hydrate_stats": stats,
    }
    if memory_degraded is not None:
        body["memory_degraded"] = memory_degraded
        stats["memory_degraded"] = memory_degraded
    if environment_fault is not None:
        body["environment_fault"] = environment_fault
        stats["environment_fault"] = environment_fault
    if memory_status is not None:
        stats["memory_status"] = memory_status
    if close_gap_reason:
        body["close_gap_reason"] = close_gap_reason
        stats["close_gap_reason"] = close_gap_reason
    if fault_class is not None:
        stats["fault_class"] = fault_class
    if environment_fault_reason:
        stats["environment_fault_reason"] = environment_fault_reason
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
        self.assertEqual(chs.classify_verdict(md).condition, "")

    def test_packet_degraded_true_is_degraded_with_reason(self) -> None:
        degraded, reason = chs.classify(_packet(degraded=True, reason="search timeout"))
        self.assertTrue(degraded)
        self.assertEqual(reason, "search timeout")

    def test_typed_memory_degraded_wins_over_legacy_degraded(self) -> None:
        md = _packet(degraded=True, memory_degraded=False, close_gap=True)
        degraded, _ = chs.classify(md)
        self.assertFalse(degraded)
        md = _packet(degraded=False, memory_degraded=True, reason="TIMEOUT: 20s")
        degraded, reason = chs.classify(md)
        self.assertTrue(degraded)
        self.assertEqual(reason, "TIMEOUT: 20s")

    def test_continuation_stale_none_is_not_stale(self) -> None:
        verdict = chs.classify_verdict(_packet(degraded=False, continuation_stale=None))
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, "")

    def test_packet_wins_over_prose_mentioning_degraded(self) -> None:
        md = "notes: a previous session was degraded\n" + _packet(degraded=False)
        degraded, _ = chs.classify(md)
        self.assertFalse(degraded)


class NonDegradedConditionTests(unittest.TestCase):
    """ADR-0032: lifecycle and environment are conditions, not memory degradation."""

    def test_close_gap_is_a_condition_not_degraded(self) -> None:
        md = _packet(
            degraded=False,
            memory_degraded=False,
            close_gap=True,
            close_gap_reason="session old-1 closed without a receipt",
        )
        verdict = chs.classify_verdict(md)
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.reason, "")
        self.assertEqual(verdict.condition, chs.CONDITION_CLOSE_GAP)
        self.assertEqual(verdict.condition_detail, "session old-1 closed without a receipt")
        self.assertEqual(
            verdict.condition_line, "CLOSE_GAP: session old-1 closed without a receipt"
        )
        self.assertEqual(chs.classify(md), (False, ""))

    def test_continuation_stale_is_a_condition_not_degraded(self) -> None:
        verdict = chs.classify_verdict(_packet(degraded=False, continuation_stale=True))
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, chs.CONDITION_STALE)
        self.assertIn("continuation_stale=true", verdict.condition_line)

    def test_environment_fault_is_a_condition_not_degraded(self) -> None:
        md = _packet(
            degraded=False,
            memory_degraded=False,
            environment_fault=True,
            memory_status="BINDING_FAILED",
            fault_class="environment",
            environment_fault_reason="BINDING_FAILED: version 2.3.1 != 2.4.0 (heal=skipped:ci)",
        )
        verdict = chs.classify_verdict(md)
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, chs.CONDITION_ENVIRONMENT_FAULT)
        self.assertIn("heal=skipped:ci", verdict.condition_detail)

    def test_environment_fault_outranks_close_gap(self) -> None:
        md = _packet(
            degraded=False,
            memory_degraded=False,
            environment_fault=True,
            close_gap=True,
            memory_status="BINDING_FAILED",
        )
        verdict = chs.classify_verdict(md)
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, chs.CONDITION_ENVIRONMENT_FAULT)

    def test_memory_degraded_outranks_every_condition(self) -> None:
        md = _packet(
            degraded=True,
            memory_degraded=True,
            reason="CANONICAL_UNAVAILABLE: store down",
            close_gap=True,
            continuation_stale=True,
        )
        verdict = chs.classify_verdict(md)
        self.assertTrue(verdict.degraded)
        self.assertEqual(verdict.reason, "CANONICAL_UNAVAILABLE: store down")
        self.assertEqual(verdict.condition, "")


class LegacyPacketTests(unittest.TestCase):
    """Packets compiled before the split ORed ``degraded`` with close_gap."""

    def test_legacy_close_gap_only_packet_is_a_close_gap_condition(self) -> None:
        md = _packet(degraded=True, close_gap=True, reason="prior session close-gap")
        verdict = chs.classify_verdict(md)
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, chs.CONDITION_CLOSE_GAP)

    def test_legacy_close_gap_with_answering_status_is_not_degraded(self) -> None:
        for status in ("OK", "NO_HITS"):
            md = _packet(
                degraded=True,
                close_gap=True,
                memory_status=status,
                reason="prior session close-gap",
            )
            verdict = chs.classify_verdict(md)
            self.assertFalse(verdict.degraded, status)
            self.assertEqual(verdict.condition, chs.CONDITION_CLOSE_GAP, status)

    def test_legacy_binding_failed_packet_is_an_environment_fault(self) -> None:
        md = _packet(degraded=True, memory_status="BINDING_FAILED", reason="BINDING_FAILED: x")
        verdict = chs.classify_verdict(md)
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, chs.CONDITION_ENVIRONMENT_FAULT)
        self.assertEqual(verdict.condition_detail, "BINDING_FAILED")

    def test_legacy_canonical_failure_stays_degraded(self) -> None:
        md = _packet(
            degraded=True,
            memory_status="CANONICAL_UNAVAILABLE",
            reason="store down",
            close_gap=True,
        )
        degraded, reason = chs.classify(md)
        self.assertTrue(degraded)
        self.assertEqual(reason, "store down")


class NoPacketFallbackTests(unittest.TestCase):
    def test_hydrate_cli_missing_is_degraded(self) -> None:
        degraded, reason = chs.classify("hydrate CLI missing — cannot compile packet")
        self.assertTrue(degraded)
        self.assertEqual(reason, "hydrate CLI missing")

    def test_leading_degraded_marker_is_degraded(self) -> None:
        degraded, reason = chs.classify("DEGRADED\n### memory hydrate")
        self.assertTrue(degraded)
        self.assertIn("DEGRADED", reason)

    def test_leading_close_gap_marker_is_a_condition(self) -> None:
        verdict = chs.classify_verdict("CLOSE_GAP\nREPAIR: /end-session")
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, chs.CONDITION_CLOSE_GAP)

    def test_leading_environment_fault_marker_is_a_condition(self) -> None:
        verdict = chs.classify_verdict(
            "ENVIRONMENT_FAULT\nREPAIR: make -C ~/.cursor-governance memory-readiness"
        )
        self.assertFalse(verdict.degraded)
        self.assertEqual(verdict.condition, chs.CONDITION_ENVIRONMENT_FAULT)
        self.assertIn("memory-readiness", verdict.condition_detail)

    def test_bare_degraded_substring_without_packet_is_not_degraded(self) -> None:
        degraded, _ = chs.classify("the word degraded appears in prose only")
        self.assertFalse(degraded)

    def test_disabled_message_is_not_degraded(self) -> None:
        degraded, _ = chs.classify("Graphiti disabled — no resume memory")
        self.assertFalse(degraded)


class CliContractTests(unittest.TestCase):
    def _run(self, md: str) -> tuple[str, str, str]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=md,
            capture_output=True,
            text=True,
            check=True,
        )
        lines = proc.stdout.splitlines()
        while len(lines) < 3:
            lines.append("")
        return lines[0], lines[1], lines[2]

    def test_cli_healthy_packet(self) -> None:
        flag, reason, condition = self._run(_packet(degraded=False))
        self.assertEqual(flag, "false")
        self.assertEqual(reason, "")
        self.assertEqual(condition, "")

    def test_cli_degraded_packet(self) -> None:
        flag, reason, condition = self._run(_packet(degraded=True, reason="empty task state"))
        self.assertEqual(flag, "true")
        self.assertEqual(reason, "empty task state")
        self.assertEqual(condition, "")

    def test_cli_close_gap_is_third_line_not_flag(self) -> None:
        flag, reason, condition = self._run(
            _packet(degraded=False, memory_degraded=False, close_gap=True, close_gap_reason="x")
        )
        self.assertEqual(flag, "false")
        self.assertEqual(reason, "")
        self.assertEqual(condition, "CLOSE_GAP: x")

    def test_cli_reason_is_single_line(self) -> None:
        md = (
            "```json\n"
            + json.dumps({"degraded": True, "hydrate_stats": {"degrade_reason": "a\nb\nc"}})
            + "\n```"
        )
        flag, reason, _ = self._run(md)
        self.assertEqual(flag, "true")
        self.assertNotIn("\n", reason)


if __name__ == "__main__":
    unittest.main()
