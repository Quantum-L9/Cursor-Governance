"""Legacy resolver shim: repository identity for callers retired at stage C11.

Since realignment stage C2 the one producer of identity and namespace hints
is ``ops/memory/namespace_context.py``; this module keeps the dict shape the
legacy hydration and close paths consume and delegates every match to the
same registry matching. The ``readonly`` key it returns was never an
authorization (memory decides that on every request, INV-07); read it as
"identity confidence is not high enough for Cursor to request a write".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.memory import namespace_context as _nc  # noqa: E402

_REGISTRY_PATH = _nc.REGISTRY_PATH


def load_registry() -> dict[str, Any]:
    return _nc.load_registry(_REGISTRY_PATH)


def _git_toplevel(cwd: Path) -> Path | None:
    return _nc.git_toplevel(cwd)


def _child_git_roots(cwd: Path) -> list[Path]:
    return _nc.child_git_roots(cwd)


def _git_remote_url(cwd: Path) -> str | None:
    return _nc.git_remote_url(cwd)


def _repo_matches(registry: dict[str, Any], cwd: Path) -> list[str]:
    """Sorted registry slugs matching ``cwd`` (remote patterns + path hints)."""

    # Resolved through this module's own name so a caller may substitute the
    # remote probe (the legacy tests do) and still exercise the shared matcher.
    return _nc.match_registry_slugs(
        registry, remote=_git_remote_url(cwd), path_parts=set(cwd.parts)
    )


def resolve_group_id(cwd: Path | None = None, explicit: str | None = None) -> dict[str, Any]:
    registry = load_registry()
    forbidden = set(registry.get("forbidden_groups") or [])
    cwd = (cwd or Path.cwd()).resolve()

    unique = _repo_matches(registry, cwd)
    if not unique:
        toplevel = _git_toplevel(cwd)
        if toplevel is not None and toplevel != cwd:
            unique = _repo_matches(registry, toplevel)
    if not unique:
        child_hits: list[str] = []
        for root in _child_git_roots(cwd):
            child_hits.extend(_repo_matches(registry, root))
        unique = sorted(set(child_hits))

    override = explicit or os.environ.get("GRAPHITI_GROUP_ID", "").strip() or None
    if override:
        method = "explicit_env" if explicit else "GRAPHITI_GROUP_ID"
        if override in forbidden:
            return {"group_id": None, "error": f"forbidden group_id: {override}", "readonly": True}
        # A request that contradicts the checkout's identity is not forwarded
        # as a write hint. With no repository match at all it is allowed (CI
        # runners in generic checkout dirs); memory still decides.
        if unique and override not in unique:
            resolved = unique[0] if len(unique) == 1 else f"one of {unique}"
            return {
                "group_id": None,
                "error": (
                    f"explicit group_id '{override}' contradicts resolved repo match '{resolved}'"
                ),
                "readonly": True,
            }
        return {"group_id": override, "method": method, "readonly": False}

    if len(unique) == 1:
        return {"group_id": unique[0], "method": "registry", "readonly": False}
    if len(unique) > 1:
        return {
            "group_id": None,
            "error": f"ambiguous group match: {unique} — set GRAPHITI_GROUP_ID",
            "readonly": True,
        }

    on_failure = (registry.get("resolution") or {}).get("on_failure", "abort_write_allow_readonly")
    workspace = registry.get("workspace_group", "igor-workspace")
    if on_failure in {"abort_write_allow_readonly", "no_write_hint"}:
        return {
            "group_id": workspace,
            "method": "fallback_readonly",
            "readonly": True,
            "warning": "no repo match",
        }
    return {"group_id": None, "error": "no group match", "readonly": True}
