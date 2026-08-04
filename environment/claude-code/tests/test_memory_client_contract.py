#!/usr/bin/env python3
"""Contract pin: the stdlib hook client must read the l9-shared-memory schema.

Network-free. This is the regression guard for the memory divergence: the hook
path (memory_client.py) and the model path (l9-shared-memory MCP server) share
ONE contract (memory.* tools). memory.hydrate returns hydrated context under
`sections` (HydrationResult) — never `records`/`hits`. Reading the wrong key
made SessionStart report "0 record(s) hydrated" and inject nothing regardless of
stored memory. These fixtures mirror the real server responses so a future edit
that reintroduces the drift fails here instead of silently in production.

See docs/decisions/ADR-0003 (two entry points, one contract) and ADR-0004.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))
import memory_client as mc  # noqa: E402

# A recorded memory.hydrate result (HydrationResult), shape-faithful to the
# l9-graphite-memory ContextSection contract.
HYDRATE_POPULATED: dict = {
    "receipt_id": "72c9e872-9eb2-4c08-8e9c-1b4bec3cbbcb",
    "status": "complete",
    "task": "resume session",
    "sections": [
        {
            "memory_class": "lesson",
            "content": "Prefer the CLI over raw MCP add_memory for T2 writes.",
            "record_ids": ["11111111-1111-1111-1111-111111111111"],
            "tokens_estimated": 14,
            "highest_score": 0.92,
        },
        {
            "memory_class": "observation",
            "content": "cursor-governance group resolves from the git remote.",
            "record_ids": ["22222222-2222-2222-2222-222222222222"],
            "tokens_estimated": 12,
            "highest_score": 0.71,
        },
    ],
    "token_budget": 1200,
    "tokens_used": 26,
    "search_receipt_id": "36daed93-d9f0-44cf-99e2-d92ca5b0b264",
    "result_digest": "deadbeef",
    "warnings": [],
}

HYDRATE_EMPTY: dict = {
    "receipt_id": "00000000-0000-0000-0000-000000000000",
    "status": "complete",
    "task": "resume session",
    "sections": [],
    "token_budget": 1200,
    "tokens_used": 0,
    "search_receipt_id": "00000000-0000-0000-0000-000000000001",
    "result_digest": "empty",
    "warnings": [],
}

SEARCH_RESULT: dict = {
    "status": "complete",
    "query": "governance",
    "namespaces_authorized": ["cursor-governance"],
    "hits": [{"record_id": "33333333-3333-3333-3333-333333333333", "score": 0.8}],
}


class HydrateContract(unittest.TestCase):
    def test_sections_read_from_sections_key(self) -> None:
        sections = mc.hydrated_sections(HYDRATE_POPULATED)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["memory_class"], "lesson")

    def test_records_and_hits_keys_are_absent_from_hydrate(self) -> None:
        # The exact drift guard: the pre-fix parse read `records`/`hits`, which a
        # hydrate result never carries, so it always counted zero.
        self.assertNotIn("records", HYDRATE_POPULATED)
        self.assertNotIn("hits", HYDRATE_POPULATED)
        legacy = HYDRATE_POPULATED.get("records") or HYDRATE_POPULATED.get("hits") or []
        self.assertEqual(legacy, [], "hydrate has no records/hits; must read sections")

    def test_render_injects_content_and_class(self) -> None:
        text = mc.render_sections(HYDRATE_POPULATED)
        self.assertIn("Prefer the CLI over raw MCP add_memory", text)
        self.assertIn("[lesson]", text)
        self.assertIn("[observation]", text)

    def test_render_is_budget_bounded(self) -> None:
        # The final string (suffix included) must never exceed max_chars.
        text = mc.render_sections(HYDRATE_POPULATED, max_chars=100)
        self.assertLessEqual(len(text), 100)
        self.assertIn("truncated", text)

    def test_render_budget_smaller_than_suffix(self) -> None:
        # Even a budget smaller than the truncation suffix stays within bound.
        text = mc.render_sections(HYDRATE_POPULATED, max_chars=10)
        self.assertLessEqual(len(text), 10)

    def test_empty_hydrate_is_zero_not_error(self) -> None:
        self.assertEqual(mc.hydrated_sections(HYDRATE_EMPTY), [])
        self.assertEqual(mc.render_sections(HYDRATE_EMPTY), "")

    def test_malformed_bundle_is_safe(self) -> None:
        for bad in (None, [], "x", {"sections": None}, {"sections": "x"}):
            self.assertEqual(mc.hydrated_sections(bad), [])
            self.assertEqual(mc.render_sections(bad), "")


class SearchContract(unittest.TestCase):
    def test_hits_read_from_hits_key(self) -> None:
        self.assertEqual(len(mc.search_hits(SEARCH_RESULT)), 1)

    def test_search_and_hydrate_do_not_share_the_content_key(self) -> None:
        # search -> hits ; hydrate -> sections. Keeping them distinct is the point.
        self.assertEqual(mc.hydrated_sections(SEARCH_RESULT), [])
        self.assertEqual(mc.search_hits(HYDRATE_POPULATED), [])


if __name__ == "__main__":
    unittest.main()
