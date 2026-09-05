#!/usr/bin/env python3
"""Cursor workspaceOpen hook: per-workspace-class addon plugin loader.

Reads ``{"workspace_roots": [...]}`` (plus other workspaceOpen fields, ignored)
on stdin and emits ``{"pluginPaths": [...]}`` on stdout, per the Cursor
workspaceOpen hook contract (https://cursor.com/docs/hooks).

The ``l9-governance`` core plugin does NOT depend on this hook -- it loads
unconditionally via the static ``~/.cursor/plugins/local/l9-governance``
symlink (see ops/scripts/setup_workspace_symlinks.sh). This hook only adds
class-gated addon plugins on top of that baseline, driven by
environment/plugins/{policy.json,exceptions.yaml,render.cursor.json}.

Cursor's workspaceOpen hook has a documented reliability gap on some builds
(registered but never executed) -- see rules/84-cursor-governance-wiring.mdc
v3.0.0. This script is therefore designed to fail open: any error, missing
governance clone, or unparsable config yields an empty pluginPaths list
rather than blocking workspace open or raising.

Also usable as a plain classifier CLI: ``workspace_open_plugin_loader.py
--classify <path>`` prints just the class name (core_default / odoo_plasticos
/ aws_infra / zep_memory) for one workspace on stdout. setup_claude_code_plugins.sh
calls this mode so the classification logic has exactly one implementation
shared by both the Cursor and Claude Code adapters.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Any


def resolve_governance_root() -> Path | None:
    """SSOT: the local GitHub clone at $HOME/.cursor-governance, and only that."""
    root = Path.home() / ".cursor-governance"
    if (root / "skills").is_dir() and (root / "CANONICAL_LAW.md").is_file():
        return root
    return None


def load_yaml_dict(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def load_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


_SKIP_DIRS = {"node_modules", "venv", ".venv", "__pycache__"}


def has_marker(workspace: Path, pattern: str, max_depth: int) -> bool:
    """True if a file/dir matching `pattern` (glob or literal) exists within
    `max_depth` levels of `workspace`. Skips hidden dirs and common vendor dirs
    so this never turns into an accidental full-tree walk."""
    for dirpath, dirnames, filenames in os.walk(workspace):
        rel = Path(dirpath).relative_to(workspace)
        depth = 0 if rel == Path(".") else len(rel.parts)
        if depth >= max_depth:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in _SKIP_DIRS]
        if any(fnmatch.fnmatch(name, pattern) for name in filenames + dirnames):
            return True
    return False


def classify_workspace(workspace: Path, exceptions: dict[str, Any]) -> str:
    """First-match-wins classification: odoo_plasticos -> aws_infra ->
    zep_memory -> core_default. Mirrors environment/ide/exceptions.yaml's
    two-step (explicit names, then marker heuristic) pattern."""
    basename = workspace.name
    path_segments = set(workspace.parts)
    heuristic = exceptions.get("heuristic") or {}
    heuristic_enabled = bool(heuristic.get("enabled", True))
    max_depth = int(heuristic.get("max_depth", 2))

    categories = [
        ("odoo_plasticos", "odoo_plasticos_repos", "odoo_plasticos_markers"),
        ("aws_infra", "aws_infra_repos", "aws_infra_markers"),
        ("zep_memory", "zep_memory_repos", "zep_memory_markers"),
    ]
    for class_name, repos_key, markers_key in categories:
        repos = exceptions.get(repos_key) or []
        if basename in repos or (path_segments & set(repos)):
            return class_name
        if heuristic_enabled:
            for marker in heuristic.get(markers_key) or []:
                if has_marker(workspace, marker, max_depth):
                    return class_name
    return "core_default"


def addon_plugin_paths_for_class(
    class_name: str, gov_root: Path, policy: dict[str, Any], render: dict[str, Any]
) -> list[str]:
    capabilities = render.get("capabilities") or {}
    class_def = (policy.get("classes") or {}).get(class_name) or {}
    plugin_paths: list[str] = []
    for capability in class_def.get("additional_capabilities") or []:
        entry = capabilities.get(capability)
        if not isinstance(entry, dict):
            continue
        plugin_path = entry.get("pluginPath")
        if not plugin_path:
            continue
        resolved = (gov_root / plugin_path).resolve()
        if resolved.is_dir():
            plugin_paths.append(str(resolved))
    return plugin_paths


def compute_plugin_paths(workspace_roots: list[str]) -> list[str]:
    gov_root = resolve_governance_root()
    if gov_root is None or not workspace_roots:
        return []

    plugins_dir = gov_root / "environment" / "plugins"
    exceptions = load_yaml_dict(plugins_dir / "exceptions.yaml")
    policy = load_json_dict(plugins_dir / "policy.json")
    render = load_json_dict(plugins_dir / "render.cursor.json")

    seen: set[str] = set()
    plugin_paths: list[str] = []
    for root_str in workspace_roots:
        workspace = Path(root_str)
        if not workspace.is_dir():
            continue
        class_name = classify_workspace(workspace, exceptions)
        for path in addon_plugin_paths_for_class(class_name, gov_root, policy, render):
            if path not in seen:
                seen.add(path)
                plugin_paths.append(path)
    return plugin_paths


def classify_only(workspace_arg: str) -> int:
    """`--classify <path>` mode: print just the class name for one workspace.

    Shared by non-Cursor consumers (e.g. setup_claude_code_plugins.sh) so the
    odoo_plasticos/aws_infra/zep_memory/core_default decision has exactly one
    implementation (classify_workspace above), not a second bash port of it.
    Fails open to "core_default" on any error, same policy as the hook path.
    """
    # The fail-open policy above is the contract, so the catch is deliberately
    # broad.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        workspace = Path(workspace_arg).resolve()
        gov_root = resolve_governance_root()
        if gov_root is None or not workspace.is_dir():
            print("core_default")
            return 0
        exceptions = load_yaml_dict(gov_root / "environment" / "plugins" / "exceptions.yaml")
        print(classify_workspace(workspace, exceptions))
    except Exception:
        print("core_default")
    return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--classify":
        return classify_only(sys.argv[2])

    # Fail open: workspace open must never block on this hook, so any payload
    # or resolution fault degrades to an empty plugin list.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        payload = json.load(sys.stdin)
        workspace_roots = payload.get("workspace_roots") or []
        plugin_paths = compute_plugin_paths(workspace_roots)
    except Exception:
        # Fail open: workspace open must never block on this hook.
        plugin_paths = []
    print(json.dumps({"pluginPaths": plugin_paths}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
