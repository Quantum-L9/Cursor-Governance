"""T4 surface for overlap-gate proofs (SSOT remains ops/scripts/tests)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SSOT = (
    Path(__file__).resolve().parents[3]
    / "ops"
    / "scripts"
    / "tests"
    / "test_pr_overlap_check.py"
)


def load_tests(
    loader: unittest.TestLoader,
    _tests: unittest.TestSuite,
    _pattern: str | None,
) -> unittest.TestSuite:
    spec = importlib.util.spec_from_file_location("pr_overlap_check_ssot", _SSOT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load overlap tests from {_SSOT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)


if __name__ == "__main__":
    unittest.main()
