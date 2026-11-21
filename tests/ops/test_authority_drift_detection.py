"""Authority drift is detected in Cursor-Governance, never published by a bot.

Operator decision 2026-11-21: no bot pull requests. Scheduled and dispatched runs of
the projection workflows regenerate or verify inside the runner and fail when the
committed projection is stale; an agent regenerates and publishes through make pr.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
IDENTITY = WORKFLOWS / "l9-canonical-identity-projection.yml"
BUNDLES = WORKFLOWS / "l9-projection-bundle-verify.yml"
DRIFT_TRIGGERS = {"schedule", "workflow_dispatch", "repository_dispatch"}
DISPATCH = {"types": ["l9-semantic-authority-updated"]}
PUBLISHING = ("git push", "git commit", "gh pr", "create-pull-request", "pulls -f")


def _load(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    text = path.read_text()
    workflow = yaml.safe_load(text)
    triggers = workflow[True] if True in workflow else workflow["on"]
    return workflow, triggers, text


def test_identity_projection_detects_drift_without_publishing() -> None:
    workflow, triggers, text = _load(IDENTITY)
    assert DRIFT_TRIGGERS <= set(triggers)
    assert triggers["repository_dispatch"] == DISPATCH
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert job.get("permissions", {"contents": "read"}) == {"contents": "read"}
    for forbidden in PUBLISHING:
        assert forbidden not in text, forbidden
    steps = workflow["jobs"]["refresh"]["steps"]
    checkout = next(s for s in steps if s.get("with", {}).get("path") == "governance")
    assert checkout["with"]["persist-credentials"] is False
    stale = next(s for s in steps if s["name"] == "Fail when the committed projection is stale")
    assert "exit 1" in stale["run"]
    assert "GITHUB_STEP_SUMMARY" in stale["run"]


def test_bundle_verify_runs_on_drift_triggers_with_read_only_permissions() -> None:
    workflow, triggers, text = _load(BUNDLES)
    assert DRIFT_TRIGGERS <= set(triggers)
    assert triggers["repository_dispatch"] == DISPATCH
    assert workflow["permissions"] == {"contents": "read"}
    condition = workflow["jobs"]["verify"]["if"]
    for event in ("pull_request", "push", *sorted(DRIFT_TRIGGERS)):
        assert f"github.event_name == '{event}'" in condition, event
    for forbidden in PUBLISHING:
        assert forbidden not in text, forbidden
