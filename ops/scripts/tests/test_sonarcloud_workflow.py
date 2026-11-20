#!/usr/bin/env python3
"""SonarCloud is a dispatch-only deep entrypoint. It does not scan pull requests.

Heavy pytest and coverage run only for mode=apply after the SHA check, once.
Sonar consumes that coverage. A missing SONAR_TOKEN does not skip that suite.
Waiting on Core apply: this file does not claim a nightly Sonar run occurred.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
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

    def test_missing_sonar_token_does_not_gate_pytest(self) -> None:
        suite = next(
            step for step in self.steps if "run_python_test_suites.py" in step.get("run", "")
        )
        suite_at = self.steps.index(suite)
        self.assertEqual(suite["if"], "steps.admit.outputs.apply == 'true'")
        for step in self.steps[:suite_at]:
            self.assertNotIn("SONAR_TOKEN", str(step))
        token = next(
            step for step in self.steps if step["name"] == "Require SonarCloud analysis token"
        )
        scan = next(
            step
            for step in self.steps
            if step.get("uses", "").startswith("SonarSource/sonarqube-scan-action@")
        )
        self.assertGreater(self.steps.index(token), suite_at)
        self.assertGreater(self.steps.index(scan), self.steps.index(token))
        self.assertEqual(token["id"], "sonar_token")
        self.assertEqual(token["env"]["SONAR_TOKEN"], "${{ secrets.SONAR_TOKEN }}")
        self.assertIn("exit 1", token["run"])
        self.assertIn("steps.coverage.outcome == 'success'", token["if"])
        self.assertIn("steps.sonar_token.outcome == 'success'", scan["if"])
        self.assertNotIn("SONAR_TOKEN", suite["if"])

    def test_token_script_reports_a_missing_token_and_accepts_one(self) -> None:
        token = next(
            step for step in self.steps if step["name"] == "Require SonarCloud analysis token"
        )
        missing = _bash(token["run"], {"SONAR_TOKEN": "   "})
        self.assertEqual(missing.returncode, 1, missing.stderr)
        self.assertIn("SONAR_TOKEN is required", missing.stdout)
        present = _bash(token["run"], {"SONAR_TOKEN": "present-token"})
        self.assertEqual(present.returncode, 0, present.stderr)
        self.assertNotIn("present-token", present.stdout)
        self.assertNotIn("present-token", present.stderr)

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
            step for step in self.steps if step.get("uses", "").startswith("actions/checkout@")
        )
        self.assertLess(self.steps.index(reject), self.steps.index(checkout))
        self.assertLess(self.steps.index(reject), self.steps.index(invocations[0]))
        self.assertEqual(reject["env"]["GH_REPO"], "${{ github.repository }}")
        self.assertIn("repos/${GH_REPO}/actions/workflows/sonarcloud.yml/runs", reject["run"])
        self.assertIn("gh api --paginate", reject["run"])
        self.assertNotIn("gh run list", reject["run"])
        self.assertNotIn("--limit", reject["run"])
        self.assertNotIn("gh run list", self.text)

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


_LIST_SHA = "a" * 40
_OTHER_SHA = "b" * 40
_LIST_KEY = "slot-key-9"
_LIST_REPO = "Quantum-L9/Cursor-Governance"


def _bash(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    child = os.environ.copy()
    child.update(env)
    return subprocess.run(
        ["bash", "-c", script],
        env=child,
        text=True,
        capture_output=True,
        check=False,
    )


def _dispatch_run(
    run_id: int,
    *,
    title: str,
    sha: str,
    status: str = "completed",
    conclusion: str | None = "success",
) -> dict[str, object]:
    return {
        "id": run_id,
        "event": "workflow_dispatch",
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "display_title": title,
    }


def _pages(*groups: list[dict[str, object]], total: int) -> str:
    documents = []
    for group in groups:
        body = {"total_count": total, "workflow_runs": group}
        documents.append(json.dumps(body, separators=(",", ":")))
    return "\n".join(documents) + "\n"


def _same_key(sha: str = _LIST_SHA) -> str:
    return f"SonarCloud apply {_LIST_KEY} {sha}"


def _reject_script() -> str:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = next(iter(doc["jobs"].values()))["steps"]
    return next(step["run"] for step in steps if step["name"] == "Reject duplicate dispatch key")


def _run_reject(pages: str, *, current: str, gh_rc: int = 0) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        fixture = root / "pages.json"
        fixture.write_text(pages, encoding="utf-8")
        gh = bin_dir / "gh"
        gh.write_text(
            textwrap.dedent(
                """\
                #!/bin/bash
                set -euo pipefail
                expected="repos/${GH_REPO}/actions/workflows/sonarcloud.yml/runs"
                query="?event=workflow_dispatch&head_sha=${EXPECTED_SHA}&per_page=100"
                if [[ "$1" != api || "$2" != --paginate || "${3-}" != "${expected}${query}" ]]; then
                  echo "unexpected gh invocation: $*" >&2
                  exit 2
                fi
                if [[ "${GH_RC}" != 0 ]]; then
                  echo "gh failed" >&2
                  exit "${GH_RC}"
                fi
                cat "${GH_FIXTURE}"
                """
            ),
            encoding="utf-8",
        )
        gh.chmod(0o755)
        child = os.environ.copy()
        child["PATH"] = f"{bin_dir}{os.pathsep}{child.get('PATH', '')}"
        child["GH_REPO"] = _LIST_REPO
        child["GH_RC"] = str(gh_rc)
        child["GH_FIXTURE"] = str(fixture)
        child["EXPECTED_SHA"] = _LIST_SHA
        child["DISPATCH_KEY"] = _LIST_KEY
        child["CURRENT_RUN"] = current
        script = root / "reject.sh"
        script.write_text(_reject_script(), encoding="utf-8")
        return subprocess.run(
            ["bash", str(script)],
            cwd=root,
            env=child,
            text=True,
            capture_output=True,
            check=False,
        )


class DuplicateDispatchListTests(unittest.TestCase):
    """The apply dedup must read every page. A capped window is not a proof."""

    def setUp(self) -> None:
        if shutil.which("jq") is None:
            self.fail("jq is required to prove the dispatch list is complete")

    def test_success_on_a_later_page_is_a_duplicate(self) -> None:
        pages = _pages(
            [_dispatch_run(11, title=f"SonarCloud apply other-key {_LIST_SHA}", sha=_LIST_SHA)],
            [_dispatch_run(22, title=_same_key(), sha=_LIST_SHA)],
            total=2,
        )
        result = _run_reject(pages, current="99")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("already ran", result.stdout)

    def test_retry_after_failure_ignores_self_other_keys_and_other_shas(self) -> None:
        pages = _pages(
            [
                _dispatch_run(11, title=_same_key(), sha=_LIST_SHA),
                _dispatch_run(22, title=_same_key(), sha=_LIST_SHA, conclusion="failure"),
            ],
            [
                _dispatch_run(33, title=f"SonarCloud apply other-key {_LIST_SHA}", sha=_LIST_SHA),
                _dispatch_run(44, title=_same_key(_OTHER_SHA), sha=_OTHER_SHA),
            ],
            total=4,
        )
        result = _run_reject(pages, current="11")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_in_progress_run_is_a_duplicate(self) -> None:
        pages = _pages(
            [
                _dispatch_run(
                    11,
                    title=_same_key(),
                    sha=_LIST_SHA,
                    status="in_progress",
                    conclusion=None,
                )
            ],
            total=1,
        )
        result = _run_reject(pages, current="99")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("already ran", result.stdout)

    def test_empty_complete_list_allows_apply(self) -> None:
        result = _run_reject(_pages([], total=0), current="99")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_truncated_list_refuses_apply(self) -> None:
        pages = _pages([_dispatch_run(11, title=_same_key(), sha=_LIST_SHA)], total=3)
        result = _run_reject(pages, current="99")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("truncated", result.stdout)

    def test_failed_page_fetch_refuses_apply(self) -> None:
        result = _run_reject(_pages([], total=0), current="99", gh_rc=1)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("incomplete", result.stdout)

    def test_unknown_run_id_refuses_apply(self) -> None:
        result = _run_reject(_pages([], total=0), current="not-a-run")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("current run id is unknown", result.stdout)


if __name__ == "__main__":
    unittest.main()
