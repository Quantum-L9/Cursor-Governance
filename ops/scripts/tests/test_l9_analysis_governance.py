#!/usr/bin/env python3
"""Regression contract for L9 Analysis SDK policy selection."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_ROOT = ROOT / ".github" / "governance"
QUALITY_THRESHOLDS = GOVERNANCE_ROOT / "quality-thresholds.yaml"
WORKFLOWS = ROOT / ".github" / "workflows"
L9_ANALYSIS = WORKFLOWS / "l9-analysis.yml"


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

    def test_no_repo_local_core_analysis_caller(self) -> None:
        """#732 option B: analysis runs only as the org-required central check.

        Core's release plane forbids consumer workflow copies
        (``consumer.workflow_copy_allowed=false``) and consumer pin selection
        (``core_revision_selection_allowed=false``). The org ruleset's
        "Analyze (central Core)" check runs on every PR, so a repo-local
        caller is a second, drifting pin of the same analysis.
        """
        self.assertFalse(L9_ANALYSIS.exists(), f"{L9_ANALYSIS} is retired (#732)")
        offenders = sorted(
            path.name
            for path in WORKFLOWS.glob("*.y*ml")
            if "Quantum-L9/l9-ci-core/" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(offenders, [], "repo-local Core analysis callers")


if __name__ == "__main__":
    unittest.main()
