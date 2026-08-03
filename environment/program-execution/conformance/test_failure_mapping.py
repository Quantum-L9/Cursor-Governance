from __future__ import annotations

import unittest
from pathlib import Path

import yaml


class FailureMappingTests(unittest.TestCase):
    def test_required_canonical_errors_are_mapped(self) -> None:
        path = Path(__file__).resolve().parents[1] / "registry/EXECUTION_ERROR_MAPPING.yaml"
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        text = str(value)
        for code in (
            "PROGRAM_LOCK_STALE",
            "AUTHORIZATION_INFLATION",
            "REPOSITORY_STATE_DRIFT",
            "SCOPE_VIOLATION",
            "VALIDATION_FAILURE",
            "EVIDENCE_INVALID_OR_STALE",
            "LEASE_EXPIRED",
        ):
            self.assertIn(code, text)


if __name__ == "__main__":
    unittest.main()
