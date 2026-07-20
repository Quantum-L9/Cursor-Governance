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


def resolve_group_id(cwd: Path | None = None, explicit: str | None = None) -> dict[str, Any]:
    registry = load_registry()
    forbidden = set(registry.get("forbidden_groups") or [])
    cwd = (cwd or Path.cwd()).resolve()

    if explicit:
        if explicit in forbidden:
            return {"group_id": None, "error": f"forbidden group_id: {explicit}", "readonly": True}
        return {"group_id": explicit, "method": "explicit_env", "readonly": False}

    env_gid = os.environ.get("GRAPHITI_GROUP_ID", "").strip()
    if env_gid:
        if env_gid in forbidden:
            return {"group_id": None, "error": f"forbidden group_id: {env_gid}", "readonly": True}
        return {"group_id": env_gid, "method": "GRAPHITI_GROUP_ID", "readonly": False}

    repos: dict[str, Any] = registry.get("repos") or {}
    remote = _git_remote_url(cwd) or ""
    cwd_str = str(cwd)
    matches: list[str] = []

    for slug, cfg in repos.items():
        for pattern in cfg.get("remote_patterns") or []:
            if remote and fnmatch(remote, pattern):
                matches.append(slug)
                break
        for hint in cfg.get("path_hints") or []:
            if hint in cwd_str:
                matches.append(slug)
                break

    unique = sorted(set(matches))
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
    if on_failure == "abort_write_allow_readonly":
        return {
            "group_id": workspace,
            "method": "fallback_readonly",
            "readonly": True,
            "warning": "no repo match",
        }
    return {"group_id": None, "error": "no group match", "readonly": True}
