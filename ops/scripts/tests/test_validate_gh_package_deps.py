"""Narrow tests for validate_gh_package_deps so scoped pr-check infers this file."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_gh_package_deps as deps  # noqa: E402


class ValidateGhPackageDepsTests(unittest.TestCase):
    def test_scoped_deps_collects_quantum_l9_only(self) -> None:
        package = {
            "dependencies": {"@quantum-l9/foo": "1.0.0", "left-pad": "1.0.0"},
            "devDependencies": {"@quantum-l9/bar": "2.0.0"},
        }
        self.assertEqual(
            deps.scoped_deps(package),
            {"@quantum-l9/foo": "1.0.0", "@quantum-l9/bar": "2.0.0"},
        )

    def test_shape_problems_flags_non_tarball_resolved(self) -> None:
        problems = deps.shape_problems(
            "@quantum-l9/foo",
            {
                "version": "1.0.0",
                "resolved": "https://example.com/foo.tgz",
                "integrity": "sha512-x",
            },
        )
        self.assertTrue(problems)


if __name__ == "__main__":
    unittest.main()
