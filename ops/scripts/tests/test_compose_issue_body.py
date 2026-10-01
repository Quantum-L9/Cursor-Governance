"""compose_issue_body.py renders the org issue forms the way GitHub does.

The contract tests render each vendored org form and run the vendored org
parsers (issue-triage.yml, governance-issue.yml) over the result, so an
agent-filed issue is proven to label exactly like a hand-filed one.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from compose_issue_body import (  # noqa: E402
    NO_RESPONSE,
    SCHEMA,
    FormError,
    compose_issue,
    form_file_name,
    main,
    resolve_form,
)

FORMS = Path(__file__).resolve().parent / "fixtures" / "org_issue_forms"
FORM_FILES = (
    "1-bug.yml",
    "2-feature.yml",
    "3-task.yml",
    "4-incident.yml",
    "ci-failure.yml",
    "seed-ci-failure.yml",
    "gov-violation.yml",
)
TRACE = 'Traceback (most recent call last):\n  File "x.py", line 1\nValueError: boom'


def _form(name: str) -> str:
    return (FORMS / name).read_text(encoding="utf-8")


def _complete(name: str, **overrides: Any) -> dict[str, Any]:
    """Answer every required field of a vendored form; overrides win."""
    form = yaml.safe_load(_form(name))
    answers: dict[str, Any] = {}
    for el in form["body"]:
        if el["type"] == "markdown" or not (el.get("validations") or {}).get("required"):
            continue
        if el["type"] == "dropdown":
            answers[el["id"]] = el["attributes"]["options"][0]
        elif el["type"] == "checkboxes":
            answers[el["id"]] = [0]
        else:
            answers[el["id"]] = TRACE if el["id"] == "evidence" else f"{el['id']} answer"
    answers.update(overrides)
    return answers


def _run_org_parser(
    workflow: str, body: str, labels: list[str] | None = None, action: str = "opened"
) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        # Not a skip: without node these tests cannot prove the composed body
        # labels correctly, and silence would read as a pass.
        raise AssertionError("node is required to run the vendored org issue parsers")
    with tempfile.TemporaryDirectory() as tmp:
        body_file = Path(tmp) / "body.md"
        body_file.write_text(body, encoding="utf-8")
        proc = subprocess.run(
            [
                node,
                str(FORMS / "run_issue_workflow.js"),
                str(FORMS / workflow),
                str(body_file),
                ",".join(labels or []),
                action,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    if proc.returncode != 0:
        raise AssertionError(f"{workflow} runner failed: {proc.stderr.strip()}")
    result: dict[str, Any] = json.loads(proc.stdout)
    return result


class VendoredFixtureTests(unittest.TestCase):
    def test_vendored_forms_and_parsers_match_their_manifest(self) -> None:
        manifest = json.loads((FORMS / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "l9.org_issue_form_fixtures.v1")
        files = {entry["file"] for entry in manifest["fixtures"]}
        self.assertEqual(files, {*FORM_FILES, "issue-triage.yml", "governance-issue.yml"})
        for entry in manifest["fixtures"]:
            with self.subTest(fixture=entry["file"]):
                self.assertRegex(entry["ref"], r"^[0-9a-f]{40}$")
                digest = hashlib.sha256((FORMS / entry["file"]).read_bytes()).hexdigest()
                self.assertEqual(digest, entry["sha256"])


class RenderTests(unittest.TestCase):
    def test_body_is_githubs_rendering_in_form_order(self) -> None:
        issue = compose_issue(
            _form("1-bug.yml"),
            _complete("1-bug.yml", severity="S2", environment="prod"),
            title="report totals drift",
        )
        self.assertEqual(issue.title, "bug: report totals drift")
        self.assertEqual(issue.labels, ["type:bug", "needs:triage"])
        self.assertEqual(issue.missing_required, [])
        headings = [line for line in issue.body.splitlines() if line.startswith("### ")]
        self.assertEqual(
            headings,
            [
                "### Problem",
                "### Evidence",
                "### Reproduction",
                "### Environment",
                "### Version / commit",
                "### Last known good version",
                "### Severity",
                "### Done when",
                "### Related",
                "### Anything else",
            ],
        )
        self.assertIn(f"### Evidence\n\n```shell\n{TRACE}\n```", issue.body)
        self.assertIn("### Environment\n\nProduction", issue.body)
        self.assertIn("### Severity\n\nS2 — major function broken, no workaround", issue.body)
        self.assertIn(f"### Reproduction\n\n{NO_RESPONSE}", issue.body)

    def test_title_prefix_is_not_doubled(self) -> None:
        issue = compose_issue(_form("1-bug.yml"), _complete("1-bug.yml"), title="bug: x")
        self.assertEqual(issue.title, "bug: x")
        with self.assertRaises(FormError):
            compose_issue(_form("1-bug.yml"), _complete("1-bug.yml"), title="bug: ")

    def test_dropdown_takes_a_unique_prefix_and_rejects_the_rest(self) -> None:
        form = _form("1-bug.yml")
        with self.assertRaisesRegex(FormError, "severity"):
            compose_issue(form, _complete("1-bug.yml", severity="S9"), title="x")
        with self.assertRaisesRegex(FormError, "pick exactly one"):
            compose_issue(form, _complete("1-bug.yml", severity=["S1", "S2"]), title="x")

    def test_unknown_field_is_an_error_not_a_dropped_answer(self) -> None:
        with self.assertRaisesRegex(FormError, "priority"):
            compose_issue(_form("1-bug.yml"), {"priority": "P0"}, title="x")

    def test_missing_required_is_reported_never_invented(self) -> None:
        answers = _complete("1-bug.yml")
        del answers["problem"], answers["done"]
        issue = compose_issue(_form("1-bug.yml"), answers, title="x")
        self.assertEqual(issue.missing_required, ["problem", "done"])
        self.assertIn(f"### Problem\n\n{NO_RESPONSE}", issue.body)

    def test_mechanical_version_fills_only_an_unanswered_field(self) -> None:
        sha = "a" * 40
        issue = compose_issue(
            _form("1-bug.yml"), _complete("1-bug.yml"), title="x", mechanical={"version": sha}
        )
        self.assertEqual(issue.mechanical_filled, ["version"])
        self.assertIn(f"### Version / commit\n\n{sha}", issue.body)
        mine = compose_issue(
            _form("1-bug.yml"),
            _complete("1-bug.yml", version="v1.2.3"),
            title="x",
            mechanical={"version": sha},
        )
        self.assertEqual(mine.mechanical_filled, [])
        self.assertIn("### Version / commit\n\nv1.2.3", mine.body)

    def test_checkboxes_render_and_required_boxes_are_enforced(self) -> None:
        answers = _complete(
            "4-incident.yml", gates=[0, "Timeline is being kept in the comments below."]
        )
        issue = compose_issue(_form("4-incident.yml"), answers, title="x")
        self.assertIn("- [X] On-call paged.", issue.body)
        self.assertIn("- [X] Timeline is being kept in the comments below.", issue.body)
        self.assertIn("- [ ] Postmortem issue will be opened within 48h of resolution.", issue.body)
        issue = compose_issue(
            _form("4-incident.yml"), _complete("4-incident.yml", gates=[2]), title="x"
        )
        self.assertIn("gates", issue.missing_required)

    def test_aliases_name_the_org_files(self) -> None:
        self.assertEqual(form_file_name("bug"), "1-bug.yml")
        self.assertEqual(form_file_name("governance"), "gov-violation.yml")
        self.assertEqual(form_file_name("ci-failure"), "ci-failure.yml")


class ResolveFormTests(unittest.TestCase):
    def test_a_workspace_folder_hides_the_org_defaults_like_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
            (ws / ".github" / "ISSUE_TEMPLATE" / "1-bug.yml").write_text(_form("1-bug.yml"))
            name, _text, source = resolve_form("bug", ws, fetch_org=False)
            self.assertEqual(name, "1-bug.yml")
            self.assertTrue(source.startswith("workspace:"))
            with self.assertRaisesRegex(FormError, "none of the org default forms"):
                resolve_form("governance", ws, fetch_org=False)

    def test_no_workspace_folder_falls_back_to_the_governance_fork(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as gov:
            fork = Path(gov) / ".github" / "ISSUE_TEMPLATE"
            fork.mkdir(parents=True)
            (fork / "3-task.yml").write_text(_form("3-task.yml"))
            _name, _text, source = resolve_form(
                "task", Path(tmp), gov_root=Path(gov), fetch_org=False
            )
            self.assertTrue(source.startswith("governance-fork:"))
            with self.assertRaisesRegex(FormError, "no issue form"):
                resolve_form("incident", Path(tmp), gov_root=Path(gov), fetch_org=False)


class OrgIssueParserContractTests(unittest.TestCase):
    def test_every_form_labels_through_both_org_parsers(self) -> None:
        severity_s1 = {
            name: next(
                o
                for el in yaml.safe_load(_form(name))["body"]
                if el.get("id") == "severity"
                for o in el["attributes"]["options"]
                if o.startswith("S1")
            )
            for name in FORM_FILES
            if "id: severity" in _form(name)
        }
        for name in FORM_FILES:
            with self.subTest(form=name):
                answers = _complete(name)
                if name in severity_s1:
                    answers["severity"] = severity_s1[name]
                body = compose_issue(_form(name), answers, title="x").body
                triage = _run_org_parser("issue-triage.yml", body)
                self.assertEqual(triage["failures"], [])
                self.assertEqual(triage["comments"], [], "a complete composed body earns no nudge")
                if name in severity_s1:
                    self.assertIn("sev:S1", triage["added"])
                    self.assertIn("priority:P0", triage["added"])
                # Consumer repos run governance-issue.yml: same labels, never a red run.
                consumer = _run_org_parser("governance-issue.yml", body)
                self.assertEqual(consumer["added"], triage["added"])
                self.assertEqual(consumer["failures"], [])

    def test_bug_and_feature_routing_fields_reach_the_parser(self) -> None:
        bug = compose_issue(
            _form("1-bug.yml"),
            _complete("1-bug.yml", severity="S3", environment="Production", regression="v0.8.7"),
            title="x",
        ).body
        self.assertEqual(
            _run_org_parser("issue-triage.yml", bug)["added"],
            ["env:prod", "priority:P2", "regression", "sev:S3"],
        )
        feat = compose_issue(
            _form("2-feature.yml"), _complete("2-feature.yml", scope="L", breaking="Yes"), title="x"
        ).body
        self.assertEqual(
            _run_org_parser("issue-triage.yml", feat)["added"], ["breaking", "scope:L"]
        )

    def test_parser_runner_still_labels_nothing_for_free_text(self) -> None:
        # Guards the harness: a runner that labelled everything would make the
        # contract test above vacuous.
        result = _run_org_parser("issue-triage.yml", "it is broken, please fix")
        self.assertEqual(result["added"], [])


class CliTests(unittest.TestCase):
    def _run(self, *extra: str) -> tuple[int, dict[str, Any], str]:
        with tempfile.TemporaryDirectory() as tmp:
            handoff = Path(tmp) / "handoff.json"
            evidence = Path(tmp) / "trace.txt"
            evidence.write_text(TRACE, encoding="utf-8")
            argv = [
                "--workspace",
                tmp,
                "--form",
                "bug",
                "--form-file",
                str(FORMS / "1-bug.yml"),
                "--no-org",
                "--title",
                "totals drift",
                "--handoff",
                str(handoff),
                "--set",
                f"evidence=@{evidence}",
                *extra,
            ]
            out = StringIO()
            with redirect_stdout(out):
                code = main(argv)
            return code, json.loads(handoff.read_text(encoding="utf-8")), out.getvalue()

    def test_incomplete_answers_exit_2_with_a_handoff(self) -> None:
        code, handoff, body = self._run("--set", "problem=totals drift after the reducer rewrite")
        self.assertEqual(code, 2)
        self.assertEqual(handoff["schema"], SCHEMA)
        self.assertEqual(handoff["missing_required"], ["environment", "severity", "done"])
        self.assertIn(f"### Evidence\n\n```shell\n{TRACE}\n```", body)

    def test_complete_answers_exit_0(self) -> None:
        code, handoff, body = self._run(
            "--set",
            "problem=totals drift",
            "--set",
            "environment=CI",
            "--set",
            "severity=S4",
            "--set",
            "done=totals match the ledger",
        )
        self.assertEqual(code, 0)
        self.assertEqual(handoff["missing_required"], [])
        self.assertEqual(handoff["title"], "bug: totals drift")
        self.assertIn("### Environment\n\nCI", body)


if __name__ == "__main__":
    unittest.main()
