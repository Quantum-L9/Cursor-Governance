# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/deployment/validate.py
#   layer: library
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-12
"""Validate Cursor subagent deployment readiness (effective definition + shadows)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .renderers import cursor as cursor_renderer

STATUS_READY = "DEPLOYMENT_READY"
STATUS_BLOCKED = "BLOCKED"


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def evaluate_role(
    *,
    filename: str,
    expected_text: str,
    global_dir: Path,
    project_dir: Path | None,
) -> dict[str, Any]:
    """Evaluate one role's effective runtime definition."""
    expected_digest = cursor_renderer.content_digest(expected_text)
    global_path = global_dir / filename
    project_path = (project_dir / filename) if project_dir is not None else None

    global_text = _read_text(global_path)
    project_text = _read_text(project_path) if project_path is not None else None

    shadow = project_text is not None
    if shadow:
        effective_path = project_path
        effective_text = project_text
        effective_scope = "project"
    else:
        effective_path = global_path
        effective_text = global_text
        effective_scope = "global"

    evidence: dict[str, Any] = {
        "filename": filename,
        "expected_digest": expected_digest,
        "global_path": str(global_path),
        "project_path": str(project_path) if project_path is not None else None,
        "shadow": shadow,
        "effective_scope": effective_scope,
        "effective_path": str(effective_path) if effective_path is not None else None,
    }

    if effective_text is None:
        evidence["reason"] = "missing_effective_definition"
        evidence["managed"] = False
        evidence["digest_match"] = False
        return {"ok": False, "status": STATUS_BLOCKED, **evidence}

    managed = cursor_renderer.is_managed(effective_text)
    digest = cursor_renderer.content_digest(effective_text)
    digest_match = digest == expected_digest
    evidence["managed"] = managed
    evidence["effective_digest"] = digest
    evidence["digest_match"] = digest_match

    if shadow and not (managed and digest_match):
        evidence["reason"] = "project_shadow_blocks_managed_role"
        return {"ok": False, "status": STATUS_BLOCKED, **evidence}

    if not managed:
        evidence["reason"] = "unmanaged_effective_definition"
        return {"ok": False, "status": STATUS_BLOCKED, **evidence}

    if not digest_match:
        evidence["reason"] = "stale_or_divergent_managed_definition"
        return {"ok": False, "status": STATUS_BLOCKED, **evidence}

    evidence["reason"] = "effective_managed_match"
    return {"ok": True, "status": STATUS_READY, **evidence}


def validate_deployment(
    *,
    expected: dict[str, str],
    global_dir: Path,
    project_dir: Path | None,
    collisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return DEPLOYMENT_READY iff every role's effective definition is L9-managed."""
    role_checks: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for filename in sorted(expected):
        check = evaluate_role(
            filename=filename,
            expected_text=expected[filename],
            global_dir=global_dir,
            project_dir=project_dir,
        )
        role_checks.append(check)
        if not check["ok"]:
            blocked.append(check)

    for collision in collisions or []:
        blocked.append({**collision, "ok": False, "status": STATUS_BLOCKED})

    status = STATUS_READY if not blocked else STATUS_BLOCKED
    return {
        "status": status,
        "role_checks": role_checks,
        "blocked": blocked,
        "shadow_checks": [c for c in role_checks if c.get("shadow")],
        "effective_definition_checks": role_checks,
    }
