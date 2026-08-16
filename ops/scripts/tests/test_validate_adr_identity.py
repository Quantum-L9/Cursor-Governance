#!/usr/bin/env python3
"""Negative and positive fixtures for ADR identity integrity."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "validate_adr_identity.py"
REPO = Path(__file__).resolve().parents[3]


def _load_mod():
    spec = importlib.util.spec_from_file_location("validate_adr_identity", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _adr(number: str, slug: str, heading: str | None = None) -> str:
    hid = heading or f"ADR-{number}"
    return f"# {hid}: Example decision\n\n## Status\n\nAccepted\n"


def _replan(*refs: str) -> str:
    lines = ["governing_adrs:"]
    lines.extend(f"  - {ref}" for ref in refs)
    return "\n".join(lines) + "\n"


class AdrIdentityValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_mod()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def _seed_unique(self) -> None:
        decisions = self.tmp / "docs" / "decisions"
        _write(decisions / "ADR-0001-one.md", _adr("0001", "one"))
        _write(decisions / "ADR-0002-two.md", _adr("0002", "two"))
        contract = self.tmp / "environment/program-execution/core/shared/REPLAN_CONTRACT.yaml"
        _write(
            contract,
            _replan("docs/decisions/ADR-0001-one.md", "docs/decisions/ADR-0002-two.md"),
        )

    def test_current_repository_passes(self) -> None:
        self.assertEqual(self.mod.main(["--root", str(REPO)]), 0)

    def test_duplicate_numeric_id_fails(self) -> None:
        self._seed_unique()
        _write(
            self.tmp / "docs/decisions/ADR-0001-collision.md",
            _adr("0001", "collision"),
        )
        errors = self.mod.validate(self.tmp)
        self.assertTrue(any("duplicate ADR-0001" in item for item in errors), errors)

    def test_filename_heading_mismatch_fails(self) -> None:
        self._seed_unique()
        _write(
            self.tmp / "docs/decisions/ADR-0002-two.md",
            _adr("0002", "two", heading="ADR-0009"),
        )
        errors = self.mod.validate(self.tmp)
        self.assertTrue(any("does not match H1" in item for item in errors), errors)

    def test_unresolved_machine_reference_fails(self) -> None:
        self._seed_unique()
        _write(
            self.tmp / "environment/program-execution/core/shared/REPLAN_CONTRACT.yaml",
            _replan("docs/decisions/ADR-0099-missing.md"),
        )
        errors = self.mod.validate(self.tmp)
        self.assertTrue(any("unresolved machine ADR reference" in item for item in errors), errors)

    def test_bare_numeric_machine_reference_fails(self) -> None:
        self._seed_unique()
        _write(
            self.tmp / "environment/program-execution/core/shared/REPLAN_CONTRACT.yaml",
            _replan("ADR-0001"),
        )
        errors = self.mod.validate(self.tmp)
        self.assertTrue(any("bare numeric ADR reference" in item for item in errors), errors)

    def test_allocation_gap_fails(self) -> None:
        decisions = self.tmp / "docs" / "decisions"
        _write(decisions / "ADR-0001-one.md", _adr("0001", "one"))
        _write(decisions / "ADR-0003-three.md", _adr("0003", "three"))
        _write(
            self.tmp / "environment/program-execution/core/shared/REPLAN_CONTRACT.yaml",
            _replan("docs/decisions/ADR-0001-one.md"),
        )
        errors = self.mod.validate(self.tmp)
        self.assertTrue(any("missing ADR-0002" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
