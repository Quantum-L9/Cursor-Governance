#!/usr/bin/env python3
"""Regression guards for the governance runtime-contract surface validator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "validate_governance_contract_surface.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("validate_governance_contract_surface", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_contract(root: Path, body: str) -> Path:
    cfg = root / "ops" / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    contract = cfg / "governance-runtime-contract.yaml"
    contract.write_text(body, encoding="utf-8")
    return contract


class ContractSurfaceTests(unittest.TestCase):
    def _run(self, mod, root: Path, contract: Path) -> int:
        orig_root, orig_contract = mod.ROOT, mod.CONTRACT
        try:
            mod.ROOT = root
            mod.CONTRACT = contract
            return mod.main()
        finally:
            mod.ROOT, mod.CONTRACT = orig_root, orig_contract

    def test_real_repo_contract_passes(self) -> None:
        # The shipped contract must agree with the shipped sources.
        mod = _load_mod()
        self.assertEqual(mod.main(), 0)

    def test_passes_when_all_projections_agree(self) -> None:
        mod = _load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "law.md").write_text("aliases run the same gate\n", encoding="utf-8")
            contract = _write_contract(
                root,
                "invariants:\n"
                "  - id: demo\n"
                "    projections:\n"
                "      - type: file_exists\n"
                "        path: law.md\n"
                "      - type: file_contains\n"
                "        path: law.md\n"
                "        pattern: 'same gate'\n"
                "        present: true\n"
                "      - type: file_contains\n"
                "        path: law.md\n"
                "        pattern: 'case-sensitive errors'\n"
                "        present: false\n",
            )
            self.assertEqual(self._run(mod, root, contract), 0)

    def test_fails_when_forbidden_string_reappears(self) -> None:
        mod = _load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "law.md").write_text("case-sensitive errors reintroduced\n", encoding="utf-8")
            contract = _write_contract(
                root,
                "invariants:\n"
                "  - id: demo\n"
                "    projections:\n"
                "      - type: file_contains\n"
                "        path: law.md\n"
                "        pattern: 'case-sensitive errors'\n"
                "        present: false\n",
            )
            self.assertEqual(self._run(mod, root, contract), 1)

    def test_fails_when_required_file_missing(self) -> None:
        mod = _load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = _write_contract(
                root,
                "invariants:\n"
                "  - id: demo\n"
                "    projections:\n"
                "      - type: file_exists\n"
                "        path: does_not_exist.py\n",
            )
            self.assertEqual(self._run(mod, root, contract), 1)


if __name__ == "__main__":
    unittest.main()
