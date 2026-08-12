#!/usr/bin/env python3
"""Reconcile Claude Code settings triad from governance SSOT.

1. Sync governance committed `.claude/settings.json` + hooks from template
2. Merge-patch `~/.claude/settings.json` (preserve enabledPlugins / theme / extras)
3. Install consumer `<workspace>/.claude/{settings.json,hooks/*}` as real files

Usage:
  python3 ops/scripts/reconcile_claude_settings.py --root "$HOME/.cursor-governance"
  python3 ops/scripts/reconcile_claude_settings.py --workspace /path/to/repo
  python3 ops/scripts/reconcile_claude_settings.py --check
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

TEMPLATE_REL = Path("environment/agents/adapters/claude-code/settings.template.json")
HOOKS_SRC_REL = Path("environment/agents/adapters/claude-code/hooks")
SESSION_START_NAME = "session_start_claude_governance.sh"

# Keys taken wholly from the template when reconciling managed settings.
MANAGED_TOP_LEVEL = ("hooks", "permissions", "skillOverrides", "env")

# Copied into every .claude/hooks/ install (consumer + gov committed tree).
CONSUMER_HOOK_FILES = (
    SESSION_START_NAME,
    "merge_gate_wrap.py",
)

PRESERVE_USER_KEYS = ("enabledPlugins", "theme", "statusLine", "model")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object required: {path}")
    return data


def dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def merge_user_settings(
    template: dict[str, Any], existing: dict[str, Any] | None
) -> dict[str, Any]:
    """Template wins for managed keys; preserve plugins/theme and unknown user keys."""
    base = dict(existing or {})
    out: dict[str, Any] = {}
    # Preserve known user keys first.
    for key in PRESERVE_USER_KEYS:
        if key in base:
            out[key] = base[key]
    # Preserve other unknown keys (not managed).
    for key, value in base.items():
        if key in MANAGED_TOP_LEVEL or key in PRESERVE_USER_KEYS or key == "$schema":
            continue
        if key.startswith("_"):
            continue
        out[key] = value
    # Apply managed from template.
    if "$schema" in template:
        out["$schema"] = template["$schema"]
    for key in MANAGED_TOP_LEVEL:
        if key in template:
            out[key] = template[key]
    return out


def consumer_settings(template: dict[str, Any]) -> dict[str, Any]:
    """Committed consumer settings: template minus private comments."""
    out = {k: v for k, v in template.items() if not str(k).startswith("_")}
    return out


def write_if_changed(path: Path, content: str, *, check: bool, wrote: list[str]) -> list[str]:
    drift: list[str] = []
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return drift
    if check:
        drift.append(str(path))
        return drift
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    wrote.append(str(path))
    return drift


def sync_hook_file(src: Path, dest: Path, *, check: bool, wrote: list[str]) -> list[str]:
    if not src.is_file():
        return [f"missing-hook-source:{src}"]
    if dest.is_file() and dest.read_bytes() == src.read_bytes():
        return []
    if check:
        return [str(dest)]
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    wrote.append(str(dest))
    return []


def reconcile_gov_claude(root: Path, template: dict[str, Any], *, check: bool) -> dict[str, Any]:
    wrote: list[str] = []
    drift: list[str] = []
    gov_settings = root / ".claude" / "settings.json"
    content = dump_json(consumer_settings(template))
    drift.extend(write_if_changed(gov_settings, content, check=check, wrote=wrote))
    hooks_src = root / HOOKS_SRC_REL
    hooks_dest = root / ".claude" / "hooks"
    for name in CONSUMER_HOOK_FILES:
        drift.extend(sync_hook_file(hooks_src / name, hooks_dest / name, check=check, wrote=wrote))
    return {"wrote": wrote, "drift": drift}


def reconcile_user(template: dict[str, Any], *, check: bool) -> dict[str, Any]:
    wrote: list[str] = []
    drift: list[str] = []
    user_path = Path.home() / ".claude" / "settings.json"
    existing = load_json(user_path) if user_path.is_file() else {}
    merged = merge_user_settings(template, existing)
    drift.extend(write_if_changed(user_path, dump_json(merged), check=check, wrote=wrote))
    return {"wrote": wrote, "drift": drift, "preserved_plugins": "enabledPlugins" in merged}


def reconcile_workspace(
    root: Path, workspace: Path, template: dict[str, Any], *, check: bool
) -> dict[str, Any]:
    wrote: list[str] = []
    drift: list[str] = []
    claude = workspace / ".claude"
    settings_path = claude / "settings.json"
    drift.extend(
        write_if_changed(
            settings_path, dump_json(consumer_settings(template)), check=check, wrote=wrote
        )
    )
    hooks_src = root / HOOKS_SRC_REL
    hooks_dest = claude / "hooks"
    for name in CONSUMER_HOOK_FILES:
        drift.extend(sync_hook_file(hooks_src / name, hooks_dest / name, check=check, wrote=wrote))
    return {"wrote": wrote, "drift": drift, "workspace": str(workspace)}


def run(
    root: Path,
    *,
    workspace: Path | None,
    user: bool,
    gov: bool,
    check: bool,
) -> dict[str, Any]:
    template_path = root / TEMPLATE_REL
    if not template_path.is_file():
        raise FileNotFoundError(template_path)
    template = load_json(template_path)
    results: dict[str, Any] = {"check": check, "root": str(root)}
    all_drift: list[str] = []
    all_wrote: list[str] = []

    if gov:
        gov_result = reconcile_gov_claude(root, template, check=check)
        results["governance"] = gov_result
        all_drift.extend(gov_result["drift"])
        all_wrote.extend(gov_result["wrote"])

    if user:
        user_result = reconcile_user(template, check=check)
        results["user"] = user_result
        all_drift.extend(user_result["drift"])
        all_wrote.extend(user_result["wrote"])

    if workspace is not None:
        ws_result = reconcile_workspace(root, workspace.resolve(), template, check=check)
        results["workspace"] = ws_result
        all_drift.extend(ws_result["drift"])
        all_wrote.extend(ws_result["wrote"])

    results["drift"] = all_drift
    results["wrote"] = all_wrote
    results["ok"] = not all_drift if check else True
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skip-user", action="store_true")
    parser.add_argument("--skip-gov", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        result = run(
            root,
            workspace=args.workspace,
            user=not args.skip_user,
            gov=not args.skip_gov,
            check=args.check,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.check:
        if result["drift"]:
            print("FAIL: Claude settings drift:")
            for path in result["drift"]:
                print(f"  {path}")
            return 1
        print("PASS: Claude settings triad matches template-managed state")
    else:
        if result["wrote"]:
            print("WROTE:")
            for path in result["wrote"]:
                print(f"  {path}")
        else:
            print("CURRENT: Claude settings triad already reconciled")
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
