"""Every required status check must also report on a merge queue's merge_group event.

GitHub runs a merge queue's checks on the ``merge_group`` event only. A workflow that
owns a required context of the main-protection ruleset but has no ``merge_group``
trigger never reports that context for a queued PR, so the PR waits in the queue
forever. A job skipped at job level reports "skipped", which blocks the queue the
same way. And a step that reads pull_request context under merge_group reads empty
values: for the root-file append-only gate that would judge an empty range and pass
vacuously.

The context-to-workflow mapping is the one in ops/scripts/test_required_contexts_report.py
(the repo-side half of the ruleset); this file adds the merge-queue half.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"


def _required_contexts() -> dict[str, str]:
    path = ROOT / "ops" / "scripts" / "test_required_contexts_report.py"
    spec = importlib.util.spec_from_file_location("_required_contexts_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.REQUIRED_CONTEXTS)


REQUIRED = _required_contexts()
WORKFLOW_FILES = sorted(set(REQUIRED.values()))
PR_ONLY_CONTEXT = ("github.event.pull_request", "github.base_ref", "github.head_ref")


def _workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    triggers = workflow.get(True, workflow.get("on"))  # YAML 1.1 parses `on` as True
    assert isinstance(triggers, dict)
    return triggers


def _required_jobs(workflow_file: str) -> list[tuple[str, dict]]:
    contexts = {ctx for ctx, wf in REQUIRED.items() if wf == workflow_file}
    jobs = _workflow(workflow_file)["jobs"]
    return [(jid, spec) for jid, spec in jobs.items() if spec.get("name", jid) in contexts]


def test_mapping_still_names_the_five_required_contexts() -> None:
    assert len(REQUIRED) == 5
    assert WORKFLOW_FILES == [
        "governance-self-check.yml",
        "l9-lint-test.yml",
        "repo-hygiene.yml",
        "root-file-protection.yml",
    ]


@pytest.mark.parametrize("workflow_file", WORKFLOW_FILES)
def test_required_context_workflow_runs_on_merge_group(workflow_file: str) -> None:
    triggers = _triggers(_workflow(workflow_file))
    assert "merge_group" in triggers, (
        f"{workflow_file} owns a required context but has no merge_group trigger, so a "
        "queued PR never gets that context and waits in the merge queue forever"
    )
    trigger = triggers["merge_group"] or {}
    assert trigger.get("types") == ["checks_requested"]
    for key in ("branches", "branches-ignore"):
        assert key not in trigger, f"{workflow_file} filters merge_group on {key!r}"


@pytest.mark.parametrize("workflow_file", WORKFLOW_FILES)
def test_required_jobs_and_their_needs_are_never_skipped_at_job_level(
    workflow_file: str,
) -> None:
    jobs = _workflow(workflow_file)["jobs"]
    required = _required_jobs(workflow_file)
    assert required
    chain: list[str] = []
    for job_id, spec in required:
        chain.append(job_id)
        needs = spec.get("needs") or []
        chain.extend([needs] if isinstance(needs, str) else needs)
    for job_id in chain:
        assert "if" not in jobs[job_id], (
            f"{workflow_file} job {job_id!r} has a job-level if:. A job skipped at job "
            "level reports 'skipped', which blocks the merge queue; skip steps instead"
        )


@pytest.mark.parametrize("workflow_file", WORKFLOW_FILES)
def test_no_required_step_reads_pull_request_context_on_merge_group(workflow_file: str) -> None:
    """A step reading PR-only context must be skipped on merge_group or branch on it."""
    for job_id, spec in _required_jobs(workflow_file):
        for step in spec.get("steps", []):
            text = yaml.safe_dump(step)
            if not any(token in text for token in PR_ONLY_CONTEXT):
                continue
            condition = str(step.get("if", ""))
            handled = "merge_group" in condition or "merge_group" in str(step.get("run", ""))
            assert handled, (
                f"{workflow_file} job {job_id!r} step {step.get('name')!r} reads "
                "pull_request context but neither skips merge_group nor handles it; under "
                "merge_group that context is empty"
            )


# --- Root-file append-only gate: the critical one --------------------------------

ROOT_FILE = "root-file-protection.yml"


def _root_file_steps() -> dict[str, dict]:
    ((_, job),) = _required_jobs(ROOT_FILE)
    return {step["name"]: step for step in job["steps"]}


def test_root_file_gate_judges_only_the_resolved_range() -> None:
    steps = _root_file_steps()
    names = list(steps)
    assert names.index("Resolve gate range") < names.index("Checkout gated head with base history")
    for name in ("Checkout gated head with base history", "Append-only gate"):
        step = steps[name]
        assert "if" not in step, f"{name!r} must never be skipped"
        text = yaml.safe_dump(step)
        for token in PR_ONLY_CONTEXT:
            assert token not in text, f"{name!r} reads {token}; it must use steps.range"
    gate = steps["Append-only gate"]
    assert gate["env"] == {
        "BASE": "${{ steps.range.outputs.base }}",
        "HEAD_SHA": "${{ steps.range.outputs.head }}",
    }
    resolve = steps["Resolve gate range"]
    assert "if" not in resolve
    assert resolve["env"]["MG_BASE_SHA"] == "${{ github.event.merge_group.base_sha }}"
    assert resolve["env"]["MG_HEAD_SHA"] == "${{ github.event.merge_group.head_sha }}"
    assert resolve["env"]["EVENT_SHA"] == "${{ github.sha }}"


def _resolve(tmp_path: Path, **env: str) -> tuple[int, dict[str, str], str]:
    script = _root_file_steps()["Resolve gate range"]["run"]
    out = tmp_path / "github_output"
    out.write_text("")
    base_env = {
        "PATH": os.environ["PATH"],
        "GITHUB_OUTPUT": str(out),
        "EVENT_NAME": "",
        "EVENT_SHA": "",
        "PR_BASE_REF": "",
        "PR_HEAD_SHA": "",
        "MG_BASE_SHA": "",
        "MG_HEAD_SHA": "",
    }
    result = subprocess.run(
        ["bash", "-c", script],
        env={**base_env, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)
    return result.returncode, outputs, result.stdout + result.stderr


BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40


def test_merge_group_range_is_the_queued_commit_against_its_base(tmp_path: Path) -> None:
    rc, outputs, log = _resolve(
        tmp_path,
        EVENT_NAME="merge_group",
        EVENT_SHA=HEAD_SHA,
        MG_BASE_SHA=BASE_SHA,
        MG_HEAD_SHA=HEAD_SHA,
        # Stale PR-shaped values must not leak into a merge_group range.
        PR_BASE_REF="main",
        PR_HEAD_SHA="c" * 40,
    )
    assert rc == 0, log
    assert outputs == {"base_fetch": BASE_SHA, "base": BASE_SHA, "head": HEAD_SHA}


@pytest.mark.parametrize(
    "overrides",
    [
        {"MG_BASE_SHA": ""},  # missing base fails closed
        {"MG_HEAD_SHA": ""},  # missing head fails closed
        {"MG_HEAD_SHA": "d" * 40},  # head is not the event's commit
        {"EVENT_NAME": "push"},  # an event the gate does not know
    ],
)
def test_merge_group_range_fails_closed(tmp_path: Path, overrides: dict[str, str]) -> None:
    env = {
        "EVENT_NAME": "merge_group",
        "EVENT_SHA": HEAD_SHA,
        "MG_BASE_SHA": BASE_SHA,
        "MG_HEAD_SHA": HEAD_SHA,
        **overrides,
    }
    rc, outputs, log = _resolve(tmp_path, **env)
    assert rc != 0, log
    assert "base" not in outputs and "head" not in outputs
    assert "::error::" in log


def test_pull_request_range_is_unchanged(tmp_path: Path) -> None:
    rc, outputs, log = _resolve(
        tmp_path, EVENT_NAME="pull_request", PR_BASE_REF="main", PR_HEAD_SHA=HEAD_SHA
    )
    assert rc == 0, log
    assert outputs == {
        "base_fetch": "+refs/heads/main:refs/remotes/origin/main",
        "base": "origin/main",
        "head": HEAD_SHA,
    }


def test_merge_group_checkout_requires_base_ancestry() -> None:
    run = _root_file_steps()["Checkout gated head with base history"]["run"]
    assert 'if [ "${EVENT_NAME}" = "merge_group" ]; then' in run
    assert 'git merge-base --is-ancestor "${BASE}" "${HEAD_SHA}"' in run
