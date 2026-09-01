"""Counterexample registry conformance (W8/S0).

W8/S0 requires that every v2 counterexample carry an ID and reproduce as a
test. The registry asserted exactly that in its ``verification`` field while
five of the nine test files it named did not exist, and its summary counts
disagreed with its own entries. A prose claim cannot notice when it stops
being true, so this suite makes the claim executable: the registry is checked
against the hardening suite on disk, and against itself.
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

import yaml

sys.dont_write_bytecode = True  # keep PE tree free of compiled debris

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "conformance/counterexamples/v2-gaps-registry.yaml"
HARDENING = ROOT / "tests/hardening"

ID_PATTERN = re.compile(r"^CE-[A-Z]+-\d{3}$")
REQUIRED_FIELDS = (
    "id",
    "invariant",
    "description",
    "current_outcome",
    "required_outcome",
    "test_file",
    "test_function",
    "severity",
)
SEVERITIES = ("critical", "high", "medium", "low")
ALL_REPRODUCE = "all_counterexamples_reproduce_as_xfail_tests"


def _registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def _xfail_reasons(path: Path) -> dict[str, list[str]]:
    """Map each top-level test function to the reasons of its xfail markers.

    Reading the decorators rather than importing the module keeps this suite
    independent of whether the counterexample's mock code happens to import.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        reasons: list[str] = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not _is_xfail(decorator.func):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "reason" and isinstance(keyword.value, ast.Constant):
                    value = keyword.value.value
                    if isinstance(value, str):
                        reasons.append(value)
        found[node.name] = reasons
    return found


def _is_xfail(func: ast.expr) -> bool:
    """True for ``pytest.mark.xfail`` and any equivalent attribute path."""
    return isinstance(func, ast.Attribute) and func.attr == "xfail"


class RegistryShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _registry()
        self.entries = self.registry["counterexamples"]

    def test_registry_declares_its_schema(self) -> None:
        self.assertEqual(
            self.registry.get("schema"),
            "l9.program-execution.counterexamples.v1",
        )
        self.assertTrue(self.registry.get("schema_version"))
        self.assertTrue(self.registry.get("baseline_commit"))

    def test_every_entry_is_complete_and_identified(self) -> None:
        for entry in self.entries:
            entry_id = entry.get("id", "<missing id>")
            with self.subTest(counterexample=entry_id):
                for field in REQUIRED_FIELDS:
                    self.assertIn(field, entry, f"{entry_id} is missing {field}")
                self.assertRegex(entry["id"], ID_PATTERN)
                self.assertIn(entry["severity"], SEVERITIES)

    def test_identifiers_are_unique(self) -> None:
        ids = [entry["id"] for entry in self.entries]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        self.assertEqual(duplicates, [], f"duplicate counterexample ids: {duplicates}")


class RegistrySummaryTests(unittest.TestCase):
    """The summary is a claim about the entries; hold it to them."""

    def setUp(self) -> None:
        self.registry = _registry()
        self.entries = self.registry["counterexamples"]
        self.summary = self.registry["summary"]

    def test_total_matches_entry_count(self) -> None:
        self.assertEqual(self.summary["total_counterexamples"], len(self.entries))

    def test_severity_counts_match_entries(self) -> None:
        actual = Counter(entry["severity"] for entry in self.entries)
        for severity in SEVERITIES:
            with self.subTest(severity=severity):
                self.assertEqual(
                    self.summary.get(severity, 0),
                    actual.get(severity, 0),
                    f"summary claims {self.summary.get(severity, 0)} {severity}, "
                    f"entries hold {actual.get(severity, 0)}",
                )

    def test_test_file_count_matches_distinct_files(self) -> None:
        distinct = {entry["test_file"] for entry in self.entries}
        self.assertEqual(self.summary["test_files"], len(distinct))


class RegistryReproductionTests(unittest.TestCase):
    """Every counterexample must reproduce as a test that actually exists."""

    def setUp(self) -> None:
        self.registry = _registry()
        self.entries = self.registry["counterexamples"]

    def test_referenced_test_files_exist(self) -> None:
        for entry in self.entries:
            with self.subTest(counterexample=entry["id"]):
                self.assertTrue(
                    (HARDENING / entry["test_file"]).is_file(),
                    f"{entry['id']} names {entry['test_file']}, which does not exist",
                )

    def test_referenced_test_functions_exist(self) -> None:
        for entry in self.entries:
            path = HARDENING / entry["test_file"]
            if not path.is_file():
                continue  # reported by test_referenced_test_files_exist
            with self.subTest(counterexample=entry["id"]):
                self.assertIn(
                    entry["test_function"],
                    _xfail_reasons(path),
                    f"{entry['id']} names {entry['test_function']}, "
                    f"which {entry['test_file']} does not define",
                )

    def test_verification_claim_is_earned(self) -> None:
        """``verification`` may only claim xfail reproduction if it is true.

        The marker must also name the counterexample it stands for, so a test
        cannot silently drift onto a different gap than the one it closes.
        """
        if self.registry.get("verification") != ALL_REPRODUCE:
            self.skipTest("registry does not claim xfail reproduction")
        for entry in self.entries:
            path = HARDENING / entry["test_file"]
            with self.subTest(counterexample=entry["id"]):
                self.assertTrue(path.is_file(), f"{entry['test_file']} is missing")
                reasons = _xfail_reasons(path).get(entry["test_function"], [])
                self.assertTrue(
                    reasons,
                    f"{entry['test_function']} carries no xfail marker",
                )
                self.assertTrue(
                    any(entry["id"] in reason for reason in reasons),
                    f"{entry['test_function']} xfail reason does not name {entry['id']}",
                )


if __name__ == "__main__":
    unittest.main()
