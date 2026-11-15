#!/usr/bin/env python3
"""#717: SonarCloud analyzes pull requests through a CI scan, fail-closed.

Modelled on Quantum-L9/Enrichment.Inference.Engine .github/workflows/sonarcloud.yml.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "sonarcloud.yml"
PROPERTIES = ROOT / "sonar-project.properties"
SHA = re.compile(r"@[0-9a-f]{40}$")


def _properties() -> dict[str, str]:
    pairs = {}
    for line in PROPERTIES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            pairs[key.strip()] = value.strip()
    return pairs


class SonarCloudWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(WORKFLOW.is_file(), f"{WORKFLOW} is required (#717)")
        self.doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        (self.job,) = self.doc["jobs"].values()
        self.steps = self.job["steps"]

    def test_runs_on_pull_requests_and_main(self) -> None:
        on = self.doc[True] if True in self.doc else self.doc["on"]
        self.assertIn("pull_request", on)
        self.assertEqual(on["push"]["branches"], ["main"])
        self.assertEqual(self.doc["permissions"], {"contents": "read"})

    def test_fork_pull_requests_skip_the_secret_bearing_job(self) -> None:
        guard = self.job["if"]
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", guard)

    def test_token_is_required_before_anything_else_runs(self) -> None:
        first = self.steps[0]
        self.assertEqual(first["name"], "Require SonarCloud analysis token")
        self.assertEqual(first["env"]["SONAR_TOKEN"], "${{ secrets.SONAR_TOKEN }}")
        self.assertIn("exit 1", first["run"])

    def test_every_external_action_is_sha_pinned(self) -> None:
        uses = [s["uses"] for s in self.steps if "uses" in s]
        self.assertTrue(any(u.startswith("SonarSource/sonarqube-scan-action@") for u in uses))
        for ref in uses:
            self.assertRegex(ref, SHA)

    def test_checkout_is_full_history_without_persisted_credentials(self) -> None:
        (checkout,) = [s for s in self.steps if s.get("uses", "").startswith("actions/checkout@")]
        self.assertEqual(checkout["with"]["fetch-depth"], 0)
        self.assertIs(checkout["with"]["persist-credentials"], False)

    def test_project_coordinates_come_from_sonar_project_properties(self) -> None:
        props = _properties()
        self.assertEqual(props["sonar.projectKey"], "Quantum-L9_Cursor-Governance")
        self.assertEqual(props["sonar.organization"], "quantum-l9")
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("-Dsonar.projectKey", text)
        self.assertNotIn("-Dsonar.organization", text)


if __name__ == "__main__":
    unittest.main()


class SonarSourcesExistTests(unittest.TestCase):
    """The scanner fails the whole analysis on a missing source folder (PR #998: 'hooks')."""

    def test_every_sonar_source_directory_exists(self) -> None:
        for name in ("sonar-project.properties", ".sonarcloud.properties"):
            text = (ROOT / name).read_text(encoding="utf-8")
            match = re.search(r"^sonar\.sources=(.+)$", text, re.MULTILINE)
            self.assertIsNotNone(match, name)
            assert match is not None
            for entry in match.group(1).split(","):
                with self.subTest(file=name, source=entry):
                    self.assertTrue((ROOT / entry.strip()).is_dir(), f"{name}: {entry} missing")
