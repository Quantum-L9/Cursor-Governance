"""The campaign front door refuses what it cannot read, and reads what it routes.

Three defects, one seam: bytes that are not UTF-8 text escaped as a raw
`UnicodeDecodeError`; a byte-order mark in front of a declared architecture
header rerouted the document to the brief compiler; and an empty file
classified as a brief on its extension alone.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/campaign_input.py"

ARCHITECTURE_DOC = (
    "---\n"
    "schema: l9.program-execution.architecture-intent.v1\n"
    "target: Quantum-L9/LLM-Router\n"
    "---\n"
    "# Router\n\n"
    "DeepSeek MUST be the primary governed reasoning provider.\n"
)

PLAN_DOC = (
    "---\n"
    "name: Tip\n"
    "overview: Resolve the tip\n"
    "todos:\n"
    "  - id: T1\n"
    "    content: Add resolver\n"
    "---\n\n"
    "# PLAN: Tip\n"
)


def _load():
    spec = importlib.util.spec_from_file_location("campaign_input_front_door", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FrontDoorRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ci = _load()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _rejects(self, path: Path):
        with self.assertRaises(self.ci.CampaignInputRejected) as ctx:
            self.ci.classify(path)
        exc = ctx.exception
        self.assertIs(exc.detected, self.ci.CampaignInputKind.UNKNOWN)
        self.assertTrue(exc.to_dict()["nothing_executed"])
        self.assertTrue(exc.fix)
        return exc

    def test_invalid_utf8_markdown_is_a_typed_rejection_not_a_decode_error(self) -> None:
        path = self.root / "bad.md"
        path.write_bytes(b"# title\n\xff\xfe MUST do x\n")
        exc = self._rejects(path)
        self.assertEqual(exc.reason, "not UTF-8 text; binary or archive input is not supported")
        self.assertIn("UTF-8", exc.fix)

    def test_zip_bytes_named_yaml_are_refused_as_binary(self) -> None:
        path = self.root / "campaign.yaml"
        # A minimal zip: local-file-header magic followed by non-UTF-8 bytes.
        path.write_bytes(b"PK\x03\x04\x14\x00\x00\x00\x08\x00\xff\xfe\xfd\x00")
        exc = self._rejects(path)
        self.assertIn("binary or archive", exc.reason)

    def test_unreadable_file_is_a_typed_rejection_not_an_oserror(self) -> None:
        # A mode-000 file is still readable by root, so the denial is
        # injected at the read rather than staged on the filesystem.
        path = self.root / "locked.yaml"
        path.write_text("schema: x\n", encoding="utf-8")
        with patch.object(Path, "read_bytes", side_effect=PermissionError("denied")):
            exc = self._rejects(path)
        self.assertIn("cannot read campaign input", exc.reason)
        self.assertIn("PermissionError", exc.reason)

    def test_load_document_refuses_unreadable_bytes_typed_when_called_alone(self) -> None:
        """The helper is a second entry point; it must not regress to raw errors."""
        path = self.root / "bad.yaml"
        path.write_bytes(b"\xff\xfe")
        with self.assertRaises(self.ci.CampaignInputRejected):
            self.ci._load_document(path)

    def test_empty_markdown_is_refused_not_routed_as_a_brief(self) -> None:
        path = self.root / "empty.md"
        path.write_bytes(b"")
        exc = self._rejects(path)
        self.assertEqual(exc.reason, "empty document")

    def test_empty_yaml_is_refused_with_the_same_reason(self) -> None:
        path = self.root / "empty.yaml"
        path.write_bytes(b"")
        exc = self._rejects(path)
        self.assertEqual(exc.reason, "empty document")

    def test_whitespace_only_document_is_empty(self) -> None:
        path = self.root / "blank.md"
        path.write_bytes(b"\xef\xbb\xbf\r\n\r\n   \n")
        exc = self._rejects(path)
        self.assertEqual(exc.reason, "empty document")


class NormalizedRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ci = _load()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_bom_before_declared_architecture_frontmatter_still_routes_architecture(self):
        path = self.root / "arch.md"
        path.write_bytes(b"\xef\xbb\xbf" + ARCHITECTURE_DOC.encode("utf-8"))
        found = self.ci.classify(path)
        self.assertIs(found.kind, self.ci.CampaignInputKind.ARCHITECTURE_INTENT_V1)
        self.assertEqual(found.schema, self.ci.ARCHITECTURE_INTENT_SCHEMA)

    def test_bom_and_crlf_together_still_route_architecture(self) -> None:
        path = self.root / "arch-crlf.md"
        path.write_bytes(b"\xef\xbb\xbf" + ARCHITECTURE_DOC.replace("\n", "\r\n").encode("utf-8"))
        found = self.ci.classify(path)
        self.assertIs(found.kind, self.ci.CampaignInputKind.ARCHITECTURE_INTENT_V1)

    def test_crlf_plan_frontmatter_routes_as_a_plan(self) -> None:
        path = self.root / "demo.plan.md"
        path.write_bytes(PLAN_DOC.replace("\n", "\r\n").encode("utf-8"))
        found = self.ci.classify(path)
        self.assertIs(found.kind, self.ci.CampaignInputKind.PLAN)
        self.assertEqual(found.document["name"], "Tip")

    def test_a_plain_lf_document_classifies_exactly_as_before(self) -> None:
        path = self.root / "arch.md"
        path.write_text(ARCHITECTURE_DOC, encoding="utf-8")
        self.assertIs(self.ci.classify(path).kind, self.ci.CampaignInputKind.ARCHITECTURE_INTENT_V1)
        memo = self.root / "brief.md"
        memo.write_text("# campaign memo\n\nsome prose\n", encoding="utf-8")
        self.assertIs(self.ci.classify(memo).kind, self.ci.CampaignInputKind.BRIEF)

    def test_normalize_text_matches_the_compiler_source_identity(self) -> None:
        from compiler.architecture_intent import normalize_source

        raw = "﻿# T\r\nMUST x\r\n"
        self.assertEqual(self.ci._normalize_text(raw), normalize_source(raw))


if __name__ == "__main__":
    unittest.main()
