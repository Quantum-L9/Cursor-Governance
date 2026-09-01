"""Counterexample registry conformance (W8/S0).

W8/S0 requires that every v2 counterexample carry an ID and reproduce as a
test. The registry asserted exactly that in its ``verification`` field while
five of the nine test files it named did not exist, and its summary counts
disagreed with its own entries. A prose claim cannot notice when it stops
being true, so this suite makes the claim executable: the registry is checked
against the hardening suite on disk, and against itself.
"""

from __future__ import annotations

import importlib.util
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
GATE = ROOT / "scripts/gate_s0_baseline.py"


def _load(name: str, path: Path):
    """Load a module by path.

    The repository root carries its own ``scripts`` package, which shadows the
    Program Execution one whenever the runner is invoked from there. Loading by
    path is the idiom the rest of this tree already uses for exactly that
    reason.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: The gate owns the definition of what counts as a reproduction. This suite
#: consumes it rather than restating it, so the two can never disagree.
gate = _load("pes_gate_s0_baseline", GATE)
_xfail_reasons = gate.xfail_reasons

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


class RegistryBaselineTests(unittest.TestCase):
    """The baseline block must keep its three kinds of pin distinct.

    A single ``baseline_commit`` could not say whether a SHA was forensic
    evidence, the commit the counterexamples were characterized against, or the
    commit that reached ``main`` -- so a forensic pin sat in a field that read
    as live. These tests hold that separation.
    """

    def setUp(self) -> None:
        self.registry = _registry()
        self.baseline = self.registry.get("baseline")

    def test_baseline_block_is_present_and_complete(self) -> None:
        self.assertIsInstance(self.baseline, dict)
        for field in gate.BASELINE_REQUIRED_KEYS:
            with self.subTest(field=field):
                self.assertIn(field, self.baseline)

    def test_forensic_pin_is_bound_to_the_legacy_field(self) -> None:
        """The forensic campaign still reads the top-level field; keep them equal."""
        self.assertEqual(
            self.baseline["forensic_commit"],
            self.registry["baseline_commit"],
            "baseline.forensic_commit and baseline_commit must not drift apart",
        )

    def test_forensic_commit_is_never_used_as_a_live_pin(self) -> None:
        forensic = self.baseline["forensic_commit"]
        for field in ("characterized_at", "orchestrator_plane_a", "pinned_to_main"):
            with self.subTest(field=field):
                self.assertNotEqual(
                    self.baseline.get(field),
                    forensic,
                    f"{field} holds the forensic commit; it is evidence, not a live pin",
                )

    def test_live_pins_are_well_formed_shas_or_absent(self) -> None:
        self.assertRegex(self.baseline["characterized_at"], gate.SHA_PATTERN)
        self.assertRegex(self.baseline["orchestrator_plane_a"], gate.SHA_PATTERN)
        pinned = self.baseline["pinned_to_main"]
        if pinned is not None:
            self.assertRegex(pinned, gate.SHA_PATTERN)

    def test_recorded_digest_matches_the_reproduction_surface(self) -> None:
        """Editing a counterexample without re-characterizing must be caught."""
        self.assertEqual(
            self.baseline["characterized_reproduction_digest"],
            gate.reproduction_digest(self.registry, HARDENING),
        )


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
