"""W8/S1: prohibitions are classified, not flattened into one field.

DO_NOT_BUILD carried two different kinds of rule in `path_or_pattern`: repo
globs the Controller can match, and architecture laws it cannot. The laws were
never enforced - a sentence does not appear inside a path - so `do_not_build`
reported PASS having matched nothing. These tests pin the split at the seam
that emits it.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
CLASSIFIER = PE_ROOT / "compiler/prohibition_kind.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kinds = _load("pes_prohibition_kind_under_test", CLASSIFIER)


class ClassificationTests(unittest.TestCase):
    def test_repo_paths_and_globs_stay_paths(self) -> None:
        """Conservative by design: nothing matchable is reclassified away."""
        for statement in (
            "src/**",
            "*.py",
            "environment/program-execution/",
            "docs/adr/ADR-002.md",
            "**/generated/*.json",
        ):
            with self.subTest(statement=statement):
                self.assertEqual(kinds.classify(statement), kinds.PATH)

    def test_architecture_laws_are_semantic(self) -> None:
        for statement in (
            "a second Program Execution runtime or Controller",
            "compiler-owned mutable runtime state",
            "never widen authority beyond the declared ceiling",
        ):
            with self.subTest(statement=statement):
                self.assertEqual(kinds.classify(statement), kinds.SEMANTIC)

    def test_unusable_statements_fail_closed_to_semantic(self) -> None:
        """Never invent a pattern: what cannot be a path is not matched as one."""
        for statement in ("", "   ", None, 17, ["src/**"]):
            with self.subTest(statement=statement):
                self.assertEqual(kinds.classify(statement), kinds.SEMANTIC)


class EntryShapeTests(unittest.TestCase):
    def test_a_path_entry_keeps_the_pattern_the_controller_matches(self) -> None:
        row = kinds.entry(
            identifier="DNB-001",
            statement="src/**",
            reason="fixture",
            detection="controller_verify",
            exception_authority="NONE",
        )
        self.assertEqual(row["kind"], kinds.PATH)
        self.assertEqual(row["path_or_pattern"], "src/**")
        self.assertEqual(row["statement"], "src/**")

    def test_a_semantic_entry_carries_no_pattern_to_glob(self) -> None:
        row = kinds.entry(
            identifier="DNB-002",
            statement="a second Program Execution runtime or Controller",
            reason="the existing Controller is the sole runtime authority",
            detection="review_and_conformance",
            exception_authority="NONE",
        )
        self.assertEqual(row["kind"], kinds.SEMANTIC)
        self.assertNotIn(
            "path_or_pattern",
            row,
            "a law must not reach the Controller as something to glob",
        )

    def test_no_prohibition_is_dropped(self) -> None:
        """Both channels keep the rule, its reason, and its identity."""
        for statement in ("src/**", "a second Controller"):
            with self.subTest(statement=statement):
                row = kinds.entry(
                    identifier="DNB-009",
                    statement=statement,
                    reason="why",
                    detection="d",
                    exception_authority="NONE",
                )
                self.assertEqual(row["id"], "DNB-009")
                self.assertEqual(row["statement"], statement)
                self.assertEqual(row["reason"], "why")


class SynthesizerEmissionTests(unittest.TestCase):
    """The shipped synthesizer used to hardcode two laws as path patterns."""

    def test_shipped_prohibitions_are_semantic(self) -> None:
        source = (PE_ROOT / "compiler/synthesizer.py").read_text(encoding="utf-8")
        self.assertIn("prohibition_entry(", source)
        self.assertNotIn(
            '"path_or_pattern": "a second Program Execution runtime or Controller"',
            source,
            "an architecture law must not ship as a path pattern",
        )
        self.assertNotIn(
            '"path_or_pattern": "compiler-owned mutable runtime state"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
