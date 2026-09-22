#!/usr/bin/env python3
"""Regression contract for L9 Analysis SDK policy selection."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_ROOT = ROOT / ".github" / "governance"
QUALITY_THRESHOLDS = GOVERNANCE_ROOT / "quality-thresholds.yaml"


class L9AnalysisGovernanceTests(unittest.TestCase):
    def test_sdk_policy_names_are_bare_and_resolvable(self) -> None:
        """Match Core's resolver contract for bundled SDK policy selection."""
        document = json.loads(QUALITY_THRESHOLDS.read_text(encoding="utf-8"))
        profiles = document["profiles"]
        self.assertIsInstance(profiles, dict)
        self.assertTrue(profiles)

        for profile_name, profile in profiles.items():
            with self.subTest(profile=profile_name):
                policy = profile["sdk_policy"]
                candidate = Path(policy)
                self.assertFalse(candidate.is_absolute())
                self.assertEqual(candidate.name, policy)
                self.assertNotIn(policy, {".", ".."})
                self.assertTrue(
                    (GOVERNANCE_ROOT / policy).is_file(),
                    f"sdk policy for {profile_name} must exist under .github/governance",
                )


if __name__ == "__main__":
    unittest.main()
