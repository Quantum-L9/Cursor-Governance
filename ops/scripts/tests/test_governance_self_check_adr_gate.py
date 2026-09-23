"""Guard the CI boundary that promotes active ADR defects to failures."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "governance-self-check.yml"


def test_repo_docs_ci_gate_fails_closed_for_missing_or_active_adr_evidence() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    bodies = [
        step["run"]
        for job in jobs.values()
        for step in job.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("run"), str)
    ]
    repo_docs = next(body for body in bodies if "Repository documentation obligations" in body)

    assert 'catalog = receipt.get("adr_catalog")' in repo_docs
    assert 'enforcement.get("active_finding_count")' in repo_docs
    assert "receipt lacks ADR enforcement evidence" in repo_docs
    assert "active ADR contract violation(s)" in repo_docs
    assert "raise SystemExit(1)" in repo_docs
    assert repo_docs.index("if active_adr_findings:") < repo_docs.index("if rc == 3:")
