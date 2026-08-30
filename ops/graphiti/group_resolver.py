"""Resolve repo cwd to Graphiti group_id via group_registry.yaml."""

from __future__ import annotations

import os
import subprocess
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

_REGISTRY_PATH = Path(__file__).resolve().parent / "group_registry.yaml"


def load_registry() -> dict[str, Any]:
    with open(_REGISTRY_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _git_toplevel(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.TimeoutExpired):
        # Best-effort probe: any git/OS failure (git absent, cwd outside a repo,
        # timeout, permission error) is treated as "not resolvable from cwd" so
        # the caller falls back to a different resolution strategy.
        return None
    return None


def _child_git_roots(cwd: Path) -> list[Path]:
    """Immediate child directories that are git work trees.

    ``$HOME`` is never a workspace: scanning its child clones matches every
    sibling repo and returns an ambiguous ``group_id``.
    """
    try:
        resolved = cwd.resolve()
        if resolved == Path.home().resolve():
            return []
    except OSError:
        return []
    roots: list[Path] = []
    try:
        for child in resolved.iterdir():
            if child.is_dir() and (child / ".git").exists():
                roots.append(child.resolve())
    except OSError:
        return []
    return roots


def _git_remote_url(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _repo_matches(registry: dict[str, Any], cwd: Path) -> list[str]:
    """Return the sorted set of registry slugs matching cwd (remote + path hints).

    Path hints are anchored to whole path segments — a hint matches only if it
    equals one of cwd's directory components, never as an arbitrary substring.
    """
    repos: dict[str, Any] = registry.get("repos") or {}
    remote = _git_remote_url(cwd) or ""
    cwd_parts = set(cwd.parts)
    matches: list[str] = []

    for slug, cfg in repos.items():
        for pattern in cfg.get("remote_patterns") or []:
            if remote and fnmatch(remote, pattern):
                matches.append(slug)
                break
        for hint in cfg.get("path_hints") or []:
            if hint in cwd_parts:
                matches.append(slug)
                break

    return sorted(set(matches))


def resolve_group_id(cwd: Path | None = None, explicit: str | None = None) -> dict[str, Any]:
    registry = load_registry()
    forbidden = set(registry.get("forbidden_groups") or [])
    cwd = (cwd or Path.cwd()).resolve()

    unique = _repo_matches(registry, cwd)
    if not unique:
        toplevel = _git_toplevel(cwd)
        if toplevel is not None and toplevel != cwd:
            unique = _repo_matches(registry, toplevel)
    # True when the only matches came from repositories *beneath* cwd — i.e. cwd
    # is a multi-repository container root, not a repository. A cloud session is
    # rooted there, so this is the common case, not an edge case.
    from_container_root = False
    if not unique:
        child_hits: list[str] = []
        for root in _child_git_roots(cwd):
            child_hits.extend(_repo_matches(registry, root))
        unique = sorted(set(child_hits))
        from_container_root = bool(unique)

    override = explicit or os.environ.get("GRAPHITI_GROUP_ID", "").strip() or None
    if override:
        method = "explicit_env" if explicit else "GRAPHITI_GROUP_ID"
        if override in forbidden:
            return {"group_id": None, "error": f"forbidden group_id: {override}", "readonly": True}
        # An override must agree with what the repo actually is: reject it if it
        # contradicts a resolved match. With no repo match at all it is allowed
        # (e.g. CI runners in generic checkout dirs).
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
        # Refusing to pick is correct: a group_id is repository identity, and
        # collapsing several repositories onto one namespace is the failure this
        # guard exists to prevent. What was wrong was the remedy. "set
        # GRAPHITI_GROUP_ID" reads as an account-level pin, which the environment
        # contract forbids for exactly the reason above. Name the situation and
        # the two legitimate remedies instead of implying the forbidden one.
        if from_container_root:
            error = (
                f"{cwd} is a multi-repository container root, not a repository; "
                f"it matches {len(unique)} groups: {unique}. A group_id is repository "
                "identity — run this command from one repository directory, or pass "
                "--group-id for that single invocation. Do not pin GRAPHITI_GROUP_ID "
                "in the environment: it would file every repository under one group."
            )
        else:
            error = (
                f"ambiguous group match: {unique} — the registry matches this one "
                "repository under several groups; fix the overlapping entry in "
                "ops/graphiti/group_registry.yaml, or pass --group-id for this "
                "invocation."
            )
        return {
            "group_id": None,
            "error": error,
            "readonly": True,
            "candidates": unique,
            "container_root": from_container_root,
        }

    on_failure = (registry.get("resolution") or {}).get("on_failure", "abort_write_allow_readonly")
    workspace = registry.get("workspace_group", "igor-workspace")
    if on_failure == "abort_write_allow_readonly":
        return {
            "group_id": workspace,
            "method": "fallback_readonly",
            "readonly": True,
            "warning": "no repo match",
        }
    return {"group_id": None, "error": "no group match", "readonly": True}
