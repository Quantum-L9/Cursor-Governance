"""Deterministic GitHub Actions workflow contract assessment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_METHODS = frozenset({"checkout", "setup", "build", "test", "deploy"})


def _finding(
    rule_id: str,
    *,
    property_name: str,
    observed: str,
    expected: str,
    line: int | None = None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": "material",
        "property": property_name,
        "observed_state": observed,
        "expected_state": expected,
        "line": line,
        "remediation_class": "HANDOFF",
    }


def _workflow_lines(text: str, needle: str) -> int | None:
    for number, row in enumerate(text.splitlines(), start=1):
        if needle in row:
            return number
    return None


def _uses_values(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("uses"), str):
            found.append(value["uses"])
        for child in value.values():
            found.extend(_uses_values(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_uses_values(child))
    return found


def analyze(root: Path, target: Path) -> dict[str, Any]:
    if not target.is_file():
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": [f"workflow target is missing: {target}"],
        }
    try:
        text = target.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return {"status": "BLOCKED", "findings": [], "blockers": [f"workflow is unreadable: {exc}"]}
    if not isinstance(data, dict):
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": ["workflow root must be a mapping"],
        }

    findings: list[dict[str, Any]] = []
    jobs = data.get("jobs")
    if jobs is None:
        # A repository may carry a dispatch/template file under workflows.
        # This narrow analyzer owns job-reference consistency only.
        return {"status": "PASS", "findings": [], "blockers": []}
    if not isinstance(jobs, dict):
        return {
            "status": "BLOCKED",
            "findings": [],
            "blockers": ["workflow jobs mapping is absent or unreadable"],
        }
    known_jobs = set(jobs)
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        raw_needs = job.get("needs", [])
        needs = (
            [raw_needs]
            if isinstance(raw_needs, str)
            else raw_needs
            if isinstance(raw_needs, list)
            else []
        )
        for dependency in needs:
            if isinstance(dependency, str) and dependency not in known_jobs:
                findings.append(
                    _finding(
                        "workflow.job.needs_resolution",
                        property_name="job.needs",
                        observed=f"{job_id} -> {dependency}",
                        expected="every needs entry names a job in the same workflow",
                        line=_workflow_lines(text, "needs:"),
                    )
                )
    for uses in sorted(set(_uses_values(data))):
        if not uses.startswith("./"):
            continue
        local = uses.split("@", 1)[0]
        if not (root / local[2:]).exists():
            findings.append(
                _finding(
                    "workflow.uses.local_resolution",
                    property_name="uses.local_path",
                    observed=uses,
                    expected="a local uses reference resolves under the repository root",
                    line=_workflow_lines(text, uses),
                )
            )
    return {
        "status": "NEEDS_IMPROVEMENT" if findings else "PASS",
        "findings": findings,
        "blockers": [],
    }
