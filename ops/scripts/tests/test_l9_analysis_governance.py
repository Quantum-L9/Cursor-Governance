#!/usr/bin/env python3
"""Regression contract for L9 Analysis SDK policy selection."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_ROOT = ROOT / ".github" / "governance"
QUALITY_THRESHOLDS = GOVERNANCE_ROOT / "quality-thresholds.yaml"
WORKFLOWS = ROOT / ".github" / "workflows"
L9_ANALYSIS = WORKFLOWS / "l9-analysis.yml"
CORE = "Quantum-L9/l9-ci-core/"

# The one sanctioned consumer edge into Core: the reusable Sonar step
# (l9-ci-core #301, Core AGENTS.md section 36: "a composite action a consumer
# workflow calls", "Not a required check and not an organization gate",
# "Consumers reach it by full-SHA pin"), called only from the dispatch-only
# deep entrypoint that Core's nightly planner admits for this repository
# (l9-ci-core docs/nightly-deep-consumer-contract.md, cursor-governance-deep/v1).
# It is not organization analysis: org-ci.yml never calls it, so it is neither
# a workflow copy nor a Core revision selection for the central check
# (release-plane consumer rules; l9-ci-sdk ADR 0016).
SANCTIONED_CORE_CALLER = "sonarcloud.yml"
SANCTIONED_CORE_EDGE = re.compile(
    r"^\s*(?:-\s+)?uses:\s*Quantum-L9/l9-ci-core/\.github/actions/run-sonar@[0-9a-f]{40}"
    r"(?:\s+#.*)?$"
)


def _dispatch_only(text: str) -> bool:
    """The workflow's only trigger is workflow_dispatch (no PR-time caller)."""
    doc = yaml.safe_load(text) or {}
    triggers = doc.get(True, doc.get("on"))
    if isinstance(triggers, str):
        triggers = [triggers]
    return triggers is not None and set(triggers) == {"workflow_dispatch"}


def core_analysis_callers(workflows: Path) -> list[str]:
    """Workflows that reach into Core outside the one sanctioned edge."""
    offenders = []
    for path in sorted(workflows.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        if CORE not in text:
            continue
        edges = [line for line in text.splitlines() if CORE in line]
        if (
            path.name == SANCTIONED_CORE_CALLER
            and _dispatch_only(text)
            and len(edges) == 1
            and SANCTIONED_CORE_EDGE.match(edges[0])
        ):
            continue
        offenders.append(path.name)
    return offenders


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
        self.assertEqual(core_analysis_callers(WORKFLOWS), [], "repo-local Core analysis callers")

    def test_the_sanctioned_edge_is_exactly_one_file_and_one_action(self) -> None:
        """Only sonarcloud.yml, one run-sonar step at a full SHA, only on dispatch."""
        edge = "      - uses: Quantum-L9/l9-ci-core/.github/actions/run-sonar@" + "a" * 40 + "\n"
        dispatch = "on:\n  workflow_dispatch: {}\njobs:\n  s:\n    steps:\n"
        cases = {
            "sanctioned": ("sonarcloud.yml", dispatch + edge, []),
            "another file": ("ci.yml", dispatch + edge, ["ci.yml"]),
            "another core action": (
                "sonarcloud.yml",
                dispatch + edge.replace("run-sonar", "invoke-sdk"),
                ["sonarcloud.yml"],
            ),
            "the central workflow": (
                "sonarcloud.yml",
                "on:\n  workflow_dispatch: {}\njobs:\n  a:\n    uses: "
                + CORE
                + ".github/workflows/org-ci.yml@"
                + "a" * 40
                + "\n",
                ["sonarcloud.yml"],
            ),
            "a second pinned step": (
                "sonarcloud.yml",
                dispatch + edge + edge.replace("a" * 40, "b" * 40),
                ["sonarcloud.yml"],
            ),
            "a moving ref": (
                "sonarcloud.yml",
                dispatch + edge.replace("@" + "a" * 40, "@main"),
                ["sonarcloud.yml"],
            ),
            "a pull request trigger": (
                "sonarcloud.yml",
                dispatch.replace("{}\njobs", "{}\n  pull_request: {}\njobs") + edge,
                ["sonarcloud.yml"],
            ),
        }
        for label, (name, body, expected) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / name).write_text(body, encoding="utf-8")
                self.assertEqual(core_analysis_callers(Path(tmp)), expected)


if __name__ == "__main__":
    unittest.main()
