#!/usr/bin/env python3
"""Unit tests for shared Cursor rule frontmatter parsing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.rule_frontmatter import (  # noqa: E402
    always_apply_is_true,
    emit_native_frontmatter,
    normalize_globs,
    parse_rule,
)


class NormalizeGlobsTests(unittest.TestCase):
    def test_comma_separated_string_splits(self) -> None:
        self.assertEqual(normalize_globs("a, b"), ["a", "b"])
        self.assertEqual(
            normalize_globs("tests/**, **/*_test.py, **/*.test.ts"),
            ["tests/**", "**/*_test.py", "**/*.test.ts"],
        )

    def test_empty_and_none(self) -> None:
        self.assertEqual(normalize_globs(""), [])
        self.assertEqual(normalize_globs("   "), [])
        self.assertIsNone(normalize_globs(None))

    def test_yaml_list_preserved_per_item(self) -> None:
        self.assertEqual(
            normalize_globs(["src/**/*.py", "playwright.config.ts"]),
            ["src/**/*.py", "playwright.config.ts"],
        )

    def test_list_item_with_commas_splits(self) -> None:
        self.assertEqual(normalize_globs(["a, b", "c"]), ["a", "b", "c"])


class EmitNativeFrontmatterTests(unittest.TestCase):
    def test_always_apply_omits_globs(self) -> None:
        text = emit_native_frontmatter(
            {
                "description": "keep always",
                "globs": ["**/*"],
                "alwaysApply": True,
                "activation": "always",
            }
        )
        self.assertIn("alwaysApply: true", text)
        self.assertNotIn("globs:", text)
        self.assertNotIn("activation:", text)

    def test_glob_scoped_emits_comma_string(self) -> None:
        text = emit_native_frontmatter(
            {
                "description": "when tests change",
                "globs": ["tests/**", "**/*_test.py"],
                "alwaysApply": False,
            }
        )
        self.assertIn("globs: tests/**, **/*_test.py", text)
        self.assertIn("alwaysApply: false", text)

    def test_round_trip_comma_globs_via_parse_rule(self) -> None:
        dumped = emit_native_frontmatter(
            {
                "description": "paths",
                "globs": "src/**/*.py, tests/**",
                "alwaysApply": False,
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "10-sample.mdc"
            path.write_text(dumped + "\n# Sample\n", encoding="utf-8")
            parsed = parse_rule(path)
            self.assertEqual(
                normalize_globs(parsed.metadata.get("globs")),
                ["src/**/*.py", "tests/**"],
            )
            self.assertFalse(always_apply_is_true(parsed.metadata))


if __name__ == "__main__":
    unittest.main()
