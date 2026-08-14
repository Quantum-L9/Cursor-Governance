#!/usr/bin/env python3
"""Regression guards for active-surface legacy doctrine residue scanning."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "validate_legacy_doctrine_residue.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("validate_legacy_doctrine_residue", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LegacyDoctrineResidueTests(unittest.TestCase):
    def test_allow_line_permits_forbidden_teaching(self) -> None:
        mod = _load_mod()
        self.assertTrue(mod.ALLOW_LINE.search("FORBIDDEN: retired L9_MEMORY_HTTP_URL side door"))
        self.assertTrue(mod.ALLOW_LINE.search("**Wrong:** `$HOME/Dropbox/Cursor Governance/...`"))

    def test_dropbox_live_matches_ssot_paths(self) -> None:
        mod = _load_mod()
        self.assertTrue(
            mod.DROPBOX_LIVE.search("at $HOME/Dropbox/Cursor Governance/GlobalCommands")
        )
        self.assertTrue(mod.DROPBOX_LIVE.search("legacy Dropbox is fallback only"))
        self.assertTrue(mod.DROPBOX_LIVE.search("against the Dropbox governance SSOT"))

    def test_http_live_matches_assignments_not_forbid_lists(self) -> None:
        mod = _load_mod()
        self.assertTrue(mod.HTTP_LIVE.search("L9_MEMORY_HTTP_URL=https://example.com"))
        self.assertTrue(mod.HTTP_LIVE.search('"l9-shared-memory": {'))
        self.assertTrue(
            mod.HTTP_LIVE.search("claude mcp add-json --scope user l9-shared-memory '{}'")
        )
        self.assertFalse(mod.HTTP_LIVE.search("Forbidden: L9_MEMORY_HTTP_URL"))

    def test_main_passes_on_clean_fixture_tree(self) -> None:
        mod = _load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rules").mkdir()
            (root / "rules" / "ok.mdc").write_text(
                "SSOT is $HOME/.cursor-governance. "
                "Dropbox governance fallback is retired and forbidden.\n",
                encoding="utf-8",
            )
            original = mod.ROOT
            try:
                mod.ROOT = root
                self.assertEqual(mod.main(), 0)
            finally:
                mod.ROOT = original

    def test_main_fails_on_live_dropbox_teaching(self) -> None:
        mod = _load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "commands").mkdir()
            (root / "commands" / "bad.md").write_text(
                'bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/x.sh"\n',
                encoding="utf-8",
            )
            original = mod.ROOT
            try:
                mod.ROOT = root
                self.assertEqual(mod.main(), 1)
            finally:
                mod.ROOT = original

    def test_retired_client_allow_permits_retirement_notice(self) -> None:
        mod = _load_mod()
        # A doctrine line that teaches the client is gone is allowed.
        self.assertTrue(
            mod.RETIRED_CLIENT_ALLOW.search(
                "- `cursor_memory_client.py` — replaced by `graphiti_memory_client.py`"
            )
        )
        self.assertTrue(mod.RETIRED_MEMORY_CLIENT.search("agents/cursor/cursor_memory_client.py"))

    def test_main_fails_on_live_retired_client_call_on_authority_surface(self) -> None:
        mod = _load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # A live invocation on the session protocol must fail closed.
            (root / "end-session.yaml").write_text(
                "phase_2:\n  command: |\n"
                '    python3 agents/cursor/cursor_memory_client.py write "X" --kind lesson\n',
                encoding="utf-8",
            )
            original = mod.ROOT
            try:
                mod.ROOT = root
                self.assertEqual(mod.main(), 1)
            finally:
                mod.ROOT = original

    def test_main_passes_when_retired_client_only_named_as_retired(self) -> None:
        mod = _load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CANONICAL_LAW.md").write_text(
                "- `cursor_memory_client.py` (agents/cursor/cursor_memory_client.py) "
                "is retired — use the Graphiti front door instead.\n",
                encoding="utf-8",
            )
            original = mod.ROOT
            try:
                mod.ROOT = root
                self.assertEqual(mod.main(), 0)
            finally:
                mod.ROOT = original


if __name__ == "__main__":
    unittest.main()
