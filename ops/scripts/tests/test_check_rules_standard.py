#!/usr/bin/env python3
"""Tests for the rules-standard ratchet gate."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from check_rules_standard import ALWAYS_BUDGET, check_rules  # noqa: E402


def _write(root: Path, name: str, text: str) -> None:
    (root / "rules").mkdir(exist_ok=True)
    (root / "rules" / name).write_text(text, encoding="utf-8")


class CheckRulesStandardTests(unittest.TestCase):
    def test_native_only_passes_under_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "00-global.mdc",
                "---\ndescription: kernel\nalwaysApply: true\n---\n\n# Global\n",
            )
            _write(
                root,
                "10-lang.mdc",
                (
                    "---\ndescription: ts\nglobs: '**/*.ts, **/*.tsx'\n"
                    "alwaysApply: false\n---\n\n# TS\n"
                ),
            )
            errs, _warns, total, files = check_rules(root)
            self.assertEqual(errs, [])
            self.assertEqual(files, 2)
            self.assertGreater(ALWAYS_BUDGET, total)

    def test_non_native_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "00-global.mdc",
                "---\nownerTeam: x\ndescription: kernel\nalwaysApply: true\n---\n\n# G\n",
            )
            errs, _warns, _total, _files = check_rules(root)
            self.assertTrue(any("non-native" in item for item in errs))
            # L9 metadata id is allowed
            _write(
                root,
                "01-ok.mdc",
                "---\nid: l9.rule.ok\ndescription: ok\nalwaysApply: false\n---\n\n# O\n",
            )
            errs2, _w2, _t2, _f2 = check_rules(root)
            self.assertFalse(any("01-ok.mdc: non-native" in item for item in errs2))

    def test_yaml_list_globs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "10-lang.mdc",
                "---\ndescription: ts\nglobs:\n  - '**/*.ts'\nalwaysApply: false\n---\n\n# T\n",
            )
            errs, _warns, _total, _files = check_rules(root)
            self.assertTrue(any("YAML list form" in item for item in errs))

    def test_prefix_collision_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "93-one.mdc",
                "---\ndescription: a\nalwaysApply: false\n---\n\n# A\n",
            )
            _write(
                root,
                "93-two.mdc",
                "---\ndescription: b\nalwaysApply: false\n---\n\n# B\n",
            )
            errs, warns, _total, files = check_rules(root)
            self.assertEqual(files, 2)
            self.assertTrue(any("prefix 93-" in item for item in errs))
            self.assertFalse(any("prefix 93-" in item for item in warns))

    def test_dead_md_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rules").mkdir()
            (root / "rules" / "93-dead.md").write_text("# dead\n", encoding="utf-8")
            _write(
                root,
                "00-ok.mdc",
                "---\ndescription: ok\nalwaysApply: false\n---\n\n# Ok\n",
            )
            errs, _warns, _total, _files = check_rules(root)
            self.assertTrue(any(".md" in item for item in errs))

    def test_unparseable_frontmatter_is_a_named_error(self) -> None:
        """Harvest C4: parse failure is reported, not skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "10-broken.mdc",
                "---\n{[\n---\n# broken\n",
            )
            errs, _warns, _total, files = check_rules(root)
            self.assertEqual(files, 1)
            self.assertTrue(any("frontmatter parse failed" in item for item in errs))


if __name__ == "__main__":
    unittest.main()
