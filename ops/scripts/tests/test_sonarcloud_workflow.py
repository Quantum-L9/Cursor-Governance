#!/usr/bin/env python3
"""SonarCloud is a dispatch-only deep entrypoint. It does not scan pull requests.

Heavy pytest and coverage run only for mode=apply after the SHA check, once.
Sonar consumes that coverage. Waiting on Core apply: this file does not claim
a nightly Sonar run occurred.
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
DISPATCH_INPUTS = (
    "expected_sha",
    "utc_slot",
    "deep_contract",
    "dispatch_key",
    "mode",
)


def _triggers(doc: dict) -> dict:
    return doc[True] if True in doc else doc["on"]


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
        self.assertTrue(WORKFLOW.is_file(), f"{WORKFLOW} is required")
        self.text = WORKFLOW.read_text(encoding="utf-8")
        self.doc = yaml.safe_load(self.text)
        self.on = _triggers(self.doc)
        (self.job,) = self.doc["jobs"].values()
        self.steps = self.job["steps"]

    def test_dispatch_contract_has_no_pr_push_or_schedule(self) -> None:
        self.assertEqual(set(self.on), {"workflow_dispatch"})
        self.assertNotIn("pull_request", self.on)
        self.assertNotIn("push", self.on)
        self.assertNotIn("schedule", self.on)
        inputs = self.on["workflow_dispatch"]["inputs"]
        self.assertEqual(tuple(inputs), DISPATCH_INPUTS)
        for name in DISPATCH_INPUTS:
            self.assertIs(inputs[name]["required"], True)

    def test_records_that_sonar_waits_on_core_apply(self) -> None:
        self.assertIn("Waiting on Core apply", self.text)
        self.assertIn("No nightly Sonar run is claimed", self.text)
        self.assertNotIn("cron:", self.text)

    def test_repository_guard_replaces_the_fork_pull_request_guard(self) -> None:
        guard = self.job["if"]
        self.assertIn("github.repository == 'Quantum-L9/Cursor-Governance'", guard)
        self.assertIn("workflow_dispatch", guard)
        self.assertNotIn("pull_request", guard)
        self.assertEqual(self.doc["permissions"]["contents"], "read")
        self.assertNotIn("write", self.doc["permissions"].values())

    def test_sha_guard_and_plan_mode_precede_heavy_steps(self) -> None:
        admit = self.steps[0]
        self.assertEqual(admit["name"], "Admit dispatch before any heavy step")
        self.assertIn("STALE_SHA", admit["run"])
        self.assertIn("mode=plan", admit["run"])
        self.assertIn("wait on Core apply", admit["run"])
        suite_at = next(
            index
            for index, step in enumerate(self.steps)
            if "run_python_test_suites.py" in step.get("run", "")
        )
        self.assertGreater(suite_at, 0)
        self.assertIn("apply", self.steps[suite_at]["if"])

    def test_token_is_required_before_the_suite_on_apply(self) -> None:
        token = next(
            step for step in self.steps if step["name"] == "Require SonarCloud analysis token"
        )
        suite = next(
            step for step in self.steps if "run_python_test_suites.py" in step.get("run", "")
        )
        self.assertEqual(token["env"]["SONAR_TOKEN"], "${{ secrets.SONAR_TOKEN }}")
        self.assertIn("exit 1", token["run"])
        self.assertIn("apply", token["if"])
        self.assertLess(self.steps.index(token), self.steps.index(suite))

    def test_every_external_action_is_sha_pinned(self) -> None:
        uses = [step["uses"] for step in self.steps if "uses" in step]
        self.assertTrue(any(item.startswith("SonarSource/sonarqube-scan-action@") for item in uses))
        for ref in uses:
            self.assertRegex(ref, SHA)

    def test_checkout_pins_expected_sha_without_persisted_credentials(self) -> None:
        checkouts = [
            step for step in self.steps if step.get("uses", "").startswith("actions/checkout@")
        ]
        (checkout,) = checkouts
        self.assertEqual(checkout["with"]["ref"], "${{ inputs.expected_sha }}")
        self.assertEqual(checkout["with"]["fetch-depth"], 0)
        self.assertIs(checkout["with"]["persist-credentials"], False)
        self.assertIn("apply", checkout["if"])
        verify = next(step for step in self.steps if step["name"] == "Verify checked out SHA")
        self.assertIn("STALE_SHA", verify["run"])

    def test_one_suite_invocation_and_duplicate_dispatch_is_refused(self) -> None:
        invocations = [
            step
            for step in self.steps
            if "run_python_test_suites.py --profile ci" in step.get("run", "")
        ]
        self.assertEqual(len(invocations), 1)
        self.assertIn("apply", invocations[0]["if"])
        self.assertIn("DUPLICATE_DISPATCH", self.text)
        self.assertIn("cancel-in-progress: false", self.text)
        reject = next(
            step for step in self.steps if step["name"] == "Reject duplicate dispatch key"
        )
        checkout = next(
            step
            for step in self.steps
            if step.get("uses", "").startswith("actions/checkout@")
        )
        self.assertLess(self.steps.index(reject), self.steps.index(checkout))
        self.assertEqual(reject["env"]["GH_REPO"], "${{ github.repository }}")
        self.assertIn('--repo "$GH_REPO"', reject["run"])

    def test_scan_consumes_coverage_and_does_not_invoke_pytest(self) -> None:
        scan = next(
            step
            for step in self.steps
            if step.get("uses", "").startswith("SonarSource/sonarqube-scan-action@")
        )
        suite = next(
            step for step in self.steps if "run_python_test_suites.py" in step.get("run", "")
        )
        self.assertLess(self.steps.index(suite), self.steps.index(scan))
        self.assertIn("steps.coverage.outcome == 'success'", scan["if"])
        self.assertIn("-Dsonar.python.coverage.reportPaths=coverage.xml", scan["with"]["args"])
        self.assertNotIn("pytest", scan.get("run", ""))
        self.assertNotIn("run_python_test_suites.py", scan.get("with", {}).get("args", ""))
        self.assertIn("test -s coverage.xml", suite["run"])

    def test_failed_suite_does_not_scan_and_preserves_the_report(self) -> None:
        preserve = next(step for step in self.steps if step["name"] == "Preserve failed coverage")
        self.assertIn("steps.coverage.outcome == 'failure'", preserve["if"])
        self.assertIn("coverage.xml", preserve["with"]["path"])

    def test_project_coordinates_come_from_sonar_project_properties(self) -> None:
        props = _properties()
        self.assertEqual(props["sonar.projectKey"], "Quantum-L9_Cursor-Governance")
        self.assertEqual(props["sonar.organization"], "quantum-l9")
        self.assertNotIn("-Dsonar.projectKey", self.text)
        self.assertNotIn("-Dsonar.organization", self.text)


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


class SonarCoverageTests(unittest.TestCase):
    """Apply mode produces coverage before the scan. Plan mode does not."""

    def test_coverage_report_is_produced_before_the_scan_and_passed_to_it(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        produce = text.index("run_python_test_suites.py --profile ci")
        scan = text.index("SonarSource/sonarqube-scan-action@")
        self.assertLess(produce, scan)
        self.assertEqual(text.count("run_python_test_suites.py --profile ci"), 1)
        self.assertIn("-Dsonar.python.coverage.reportPaths=coverage.xml", text[scan:])
        self.assertIn("steps.admit.outputs.apply == 'true'", text)


if __name__ == "__main__":
    unittest.main()
