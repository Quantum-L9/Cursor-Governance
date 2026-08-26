#!/usr/bin/env python3
"""Point every configured .md LLM peer at the generated llm-rules mount.

SSOT for rule *content*: governance `rules/*.mdc`.
Generated mount: `environment/generated/llm-rules/` (Claude-facing `.md`).
Adapters get a **directory symlink** to that generated folder.

Cursor continues to load `rules/*.mdc` via the `l9-governance` plugin
(rule 84 forbids recreating `~/.cursor/rules` or repo `.cursor/rules`
whole-dir symlinks).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def is_tracked(path: Path) -> bool:
    """True when `path` is a git-tracked file/dir in its own repository.

    CI-002 ownership guard: a repository-owned (committed) ``.claude/rules`` tree
    must never be replaced by a generated symlink — doing so deletes the tracked
    files and dirties the checkout. Tracked status is asked of git, never
    inferred from cwd, branch, or mtime. A path outside any repo, or git being
    unavailable, is "not tracked" (the reconciler then behaves as before).
    """
    parent = path.parent
    if not parent.exists():
        return False
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(parent), "ls-files", "--error-unmatch", path.name],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0

ADAPTER_CONFIG_REL = Path("environment/skill-adapters/LLM_RULE_ADAPTER_ROOTS.yaml")


def expand_path(raw: str, workspace: Path) -> Path:
    """Return the mount path without following a final-component symlink.

    Resolving `.claude/rules` when it already points at governance `rules/` would
    make the reconciler treat the SSOT as the mount target and replace it.
    """
    expanded = os.path.expanduser(str(raw))
    path = Path(expanded)
    if not path.is_absolute():
        path = workspace / path
    return path.parent.resolve() / path.name


def load_config(root: Path) -> dict[str, Any]:
    path = root / ADAPTER_CONFIG_REL
    if not path.is_file():
        raise FileNotFoundError(f"missing rule adapter config: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("LLM_RULE_ADAPTER_ROOTS.yaml must be a mapping")
    return data


def same_link(path: Path, source: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        return path.resolve(strict=False) == source.resolve(strict=False)
    except OSError:
        return False


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def assert_safe_mount(target: Path, ssot: Path, root: Path) -> None:
    """Refuse to mutate authored SSOT directories (rules/, skills/)."""
    root = root.resolve()
    ssot_resolved = ssot.resolve()
    protected = {
        (root / "rules").resolve(),
        (root / "skills").resolve(),
        (root / "ops").resolve(),
        (root / "commands").resolve(),
    }
    # Mount identity is the path we would unlink — not where a current symlink points.
    mount = target.parent.resolve() / target.name
    if mount in protected:
        raise RuntimeError(
            f"refusing to replace protected governance path with rule mount: {mount}"
        )
    if mount == ssot_resolved:
        raise RuntimeError(f"refusing to use generated mount as its own adapter target: {mount}")


def reconcile_one(target: Path, ssot: Path, *, root: Path, check: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "target": str(target),
        "ssot": str(ssot),
        "status": "ok",
        "action": None,
    }
    try:
        assert_safe_mount(target, ssot, root)
    except RuntimeError as exc:
        result["status"] = "error"
        result["action"] = str(exc)
        return result

    if ssot.is_symlink():
        result["status"] = "error"
        result["action"] = f"generated mount must be a real directory, not a symlink: {ssot}"
        return result
    if not ssot.is_dir():
        result["status"] = "error"
        result["action"] = f"missing SSOT: {ssot}"
        return result

    if same_link(target, ssot):
        result["action"] = "current"
        return result

    # CI-002 ownership guard: never replace a repository-owned (git-tracked)
    # target with a generated symlink. A consumer that commits its own
    # `.claude/rules` keeps it; the governance mount is not forced over tracked
    # content. (In this repo `.claude/rules` is gitignored, so this never fires
    # and behavior is unchanged.)
    if is_tracked(target):
        result["status"] = "blocked"
        result["action"] = (
            "refusing to replace repository-tracked path with generated symlink "
            "(repository-owned .claude tree — project rules to a non-owned path instead)"
        )
        return result

    if check:
        if target.exists() or target.is_symlink():
            result["status"] = "drift"
            result["action"] = "would-replace-with-generated-symlink"
        else:
            result["status"] = "drift"
            result["action"] = "would-create-generated-symlink"
        return result

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        remove_path(target)
        result["action"] = "replaced-with-generated-symlink"
    else:
        result["action"] = "created-generated-symlink"
    target.symlink_to(ssot.resolve(), target_is_directory=True)
    return result


def reconcile_adapters(
    root: Path,
    *,
    workspace: Path | None,
    check: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    workspace = (workspace or Path.cwd()).resolve()
    config = load_config(root)
    mode = str(config.get("mode") or "directory-symlink")
    if mode != "directory-symlink":
        raise ValueError("rule adapters must use mode: directory-symlink")

    ssot = root / str(config.get("ssot_relative") or "environment/generated/llm-rules")
    results: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for adapter in config.get("adapters") or []:
        if not isinstance(adapter, dict):
            continue
        adapter_id = str(adapter.get("id") or "unknown")
        kind = str(adapter.get("kind") or "")
        raw_path = adapter.get("path")
        if raw_path in (None, "", "null"):
            skipped.append({"id": adapter_id, "reason": "null-path"})
            continue
        if kind == "project" and workspace is None:
            skipped.append({"id": adapter_id, "reason": "workspace-required"})
            continue

        target = expand_path(str(raw_path), workspace)
        payload = reconcile_one(target, ssot, root=root, check=check)
        payload["adapter_id"] = adapter_id
        payload["surface"] = adapter.get("surface")
        payload["kind"] = kind
        results.append(payload)

    return {
        "ssot": str(ssot.resolve()) if ssot.exists() else str(ssot),
        "mode": mode,
        "results": results,
        "skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Consumer workspace for project-scoped adapters (default: cwd)",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        payload = reconcile_adapters(
            args.root,
            workspace=(args.workspace or Path.cwd()).resolve(),
            check=args.check,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # Always emit JSON on stdout — callers (skill-adapter reconcile, PR gate)
    # parse it even when --quiet is set for human-facing wrappers.
    print(json.dumps(payload, indent=2, sort_keys=True))

    bad = any(r["status"] in {"error", "drift", "blocked"} for r in payload["results"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
