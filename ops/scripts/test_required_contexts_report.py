"""A required status check must always report, so its workflow cannot be path-filtered.

The main-protection ruleset on `main` requires five contexts. GitHub never reports a
context whose workflow was filtered out of the event, and a required-but-absent context
leaves the pull request BLOCKED with no failing check to fix and no way to reach a
mergeable state. PR #136 (a WIP-only diff) sat in exactly that state.

The counter-intuitive consequence, and the reason this test exists: adding a
`paths-ignore` to save CI minutes on a workflow that owns a required context does not
make those PRs cheaper, it makes them unmergeable. Skip the *work* inside the job (see
the `scope` job in l9-lint-test.yml) instead of skipping the *event*.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

# Context name -> workflow file that produces it. Mirrors the required_status_checks
# rule of the `main-protection` ruleset. The ruleset lives in GitHub, not in git, so
# this mapping is the repo-side half of the contract and must be updated together with
# it: `gh api repos/{owner}/{repo}/rulesets`.
REQUIRED_CONTEXTS = {
    "Lint and Type Check": "l9-lint-test.yml",
    "Test Suite": "l9-lint-test.yml",
    "Root-file append-only gate": "root-file-protection.yml",
    "governance-self-check": "governance-self-check.yml",
    "repo-hygiene": "repo-hygiene.yml",
}


def _workflow(name: str) -> dict:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    # `on` is parsed as the boolean True by YAML 1.1, which is what PyYAML implements.
    return yaml.safe_load(text)


def _pull_request_trigger(workflow: dict) -> object:
    triggers = workflow.get(True, workflow.get("on"))
    assert isinstance(triggers, dict), "workflow triggers must be a mapping"
    assert "pull_request" in triggers, "workflow must run on pull_request"
    return triggers["pull_request"]


@pytest.mark.parametrize(("context", "workflow_file"), sorted(REQUIRED_CONTEXTS.items()))
def test_required_context_workflow_is_not_path_filtered(context: str, workflow_file: str) -> None:
    trigger = _pull_request_trigger(_workflow(workflow_file))
    if trigger is None:
        return
    for key in ("paths", "paths-ignore"):
        assert key not in trigger, (
            f"{workflow_file} filters pull_request on {key!r}, but it owns the required "
            f"context {context!r}. A filtered-out workflow never reports the context, so "
            f"every PR the filter excludes is permanently BLOCKED. Skip the work inside "
            f"the job instead."
        )


@pytest.mark.parametrize(("context", "workflow_file"), sorted(REQUIRED_CONTEXTS.items()))
def test_required_context_is_actually_produced(context: str, workflow_file: str) -> None:
    jobs = _workflow(workflow_file).get("jobs", {})
    produced = {spec.get("name", job_id) for job_id, spec in jobs.items()}
    assert context in produced, (
        f"no job in {workflow_file} is named {context!r}, so the required context can "
        f"never report. Job names are the context names GitHub matches."
    )
