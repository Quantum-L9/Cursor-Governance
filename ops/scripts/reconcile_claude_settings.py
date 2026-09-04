#!/usr/bin/env python3
"""Reconcile Claude Code settings triad from governance SSOT.

1. Sync governance committed `.claude/settings.json` + hooks from template
2. Merge-patch `~/.claude/settings.json` (preserve enabledPlugins / theme / extras)
3. Merge-patch consumer `<workspace>/.claude/settings.json` (template-managed
   keys win; consumer-owned keys such as `enabledPlugins` survive) and install
   `<workspace>/.claude/hooks/*` as real files. A git-tracked workspace
   settings file keeps its own `hooks` registrations, composed with the
   template's — never wholesale-replaced (issue #281)

Usage:
  python3 ops/scripts/reconcile_claude_settings.py --root "$HOME/.cursor-governance"
  python3 ops/scripts/reconcile_claude_settings.py --workspace /path/to/repo
  python3 ops/scripts/reconcile_claude_settings.py --check
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

TEMPLATE_REL = Path("environment/agents/adapters/claude-code/settings.template.json")
HOOKS_SRC_REL = Path("environment/agents/adapters/claude-code/hooks")
SESSION_START_NAME = "session_start_claude_governance.sh"

# Keys taken wholly from the template when reconciling managed settings.
# workflowSizeGuideline is managed: the Claude surface policy is "size the
# workflow to the task", and a personal `medium` would silently cap fan-out.
MANAGED_TOP_LEVEL = (
    "hooks",
    "permissions",
    "skillOverrides",
    "env",
    "workflowSizeGuideline",
)

# Copied into every .claude/hooks/ install (consumer + gov committed tree).
CONSUMER_HOOK_FILES = (
    SESSION_START_NAME,
    "merge_gate_wrap.py",
)

PRESERVE_USER_KEYS = ("enabledPlugins", "theme", "statusLine", "model")


def workspace_artifacts() -> tuple[str, ...]:
    """Workspace-relative paths this reconciler materializes as REAL files.

    The generated mirrors (`.claude/skills`, `.claude/rules`,
    `.claude/commands`) are symlinks into governance and the adapter installer
    already excludes them. These are the paths it writes byte-for-byte, so
    they are the ones that show as untracked dirt in a consumer that has not
    committed them. Named here, beside `CONSUMER_HOOK_FILES`, so the installer
    reads the list instead of restating it in shell.
    """
    return (".claude/settings.json", *(f".claude/hooks/{name}" for name in CONSUMER_HOOK_FILES))


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


def _is_l9_managed_hook_group(group: Any) -> bool:
    """True when a hook group was projected from governance (not repo-owned).

    Managed registrations invoke ``l9_hook_exec.sh`` from the cursor-governance
    clone. Stale copies of those groups must be dropped before compose, or a
    retired gate keeps running beside its replacement.
    """
    if not isinstance(group, dict):
        return False
    hooks = group.get("hooks")
    if not isinstance(hooks, list):
        return False
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        command = str(hook.get("command") or "")
        if "l9_hook_exec.sh" in command:
            return True
        if "/.cursor-governance/" in command and "/claude-code/hooks/" in command:
            return True
    return False


def _compose_hook_groups(
    template_hooks: dict[str, Any], existing_hooks: dict[str, Any]
) -> dict[str, Any]:
    """Union hook registrations: consumer groups first, governance appended.

    A git-tracked workspace settings.json may carry the repo's own guards —
    Cognitive.Engine.Graphs keeps a banned-pattern PreToolUse contract there —
    and wholesale template replacement silently disables them for the whole
    session (issue #281). Compose instead: keep every *consumer* group, drop
    previously projected L9 registrations, then append current template groups
    (deep-equal dedupe). That way a retired governance hook cannot linger
    beside its replacement while genuine repo-owned guards survive.
    """
    merged: dict[str, Any] = {}
    for event, existing_groups in existing_hooks.items():
        if not isinstance(existing_groups, list):
            continue
        merged[event] = [
            deepcopy(group) for group in existing_groups if not _is_l9_managed_hook_group(group)
        ]
    for event, template_groups in template_hooks.items():
        # A malformed event value is not a hook list: replace it with the
        # working governance groups instead of crashing on `append`.
        if not isinstance(merged.get(event), list):
            merged[event] = []
        groups = merged[event]
        seen = {json.dumps(group, sort_keys=True) for group in groups}
        for group in template_groups:
            key = json.dumps(group, sort_keys=True)
            if key not in seen:
                groups.append(deepcopy(group))
                seen.add(key)
    return merged


def merge_workspace_settings(
    template: dict[str, Any],
    existing: dict[str, Any] | None,
    *,
    compose_hooks: bool = False,
) -> dict[str, Any]:
    """Managed keys from the template; every consumer-owned key survives.

    Ordering is template-first so a workspace file that carries no consumer
    keys is byte-identical to `consumer_settings(template)` — the historical
    whole-file output — and reconciliation stays churn-free. Consumer keys
    (notably `enabledPlugins`, written by `claude plugin install -s project`)
    are appended, never dropped: the old whole-file write silently deleted
    them on every settings reconcile that ran after a plugin install.

    `compose_hooks` (set when the workspace settings file is git-tracked)
    unions hook registrations instead of letting the template win wholesale:
    the repo owns a tracked file, and its PreToolUse/Stop guards must survive
    reconciliation (issue #281). An untracked injected file stays wholly
    template-managed so retired governance hooks do not linger.
    """
    base = dict(existing or {})
    out = consumer_settings(template)
    if compose_hooks and isinstance(base.get("hooks"), dict):
        out["hooks"] = _compose_hook_groups(template.get("hooks", {}), base["hooks"])
    for key, value in base.items():
        if key in out or str(key).startswith("_"):
            continue
        out[key] = value
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


#: Records exactly which top-level keys L9 owns in ~/.claude/settings.json.
#: Without it, uninstall is a guess: a later release that stops managing a key
#: has no way to tell "L9 put this here" from "the user did", so it either
#: strips a user's setting or leaves its own behind forever.
USER_MANIFEST_NAME = "settings.l9-manifest.json"
MANIFEST_SCHEMA = "l9.claude-user-settings-manifest.v1"


def user_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def user_manifest_path() -> Path:
    return Path.home() / ".claude" / USER_MANIFEST_NAME


def build_manifest(template: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "managed_keys": sorted(key for key in MANAGED_TOP_LEVEL if key in template),
        "preserved_user_keys": sorted(PRESERVE_USER_KEYS),
        "note": (
            "L9 owns managed_keys in ~/.claude/settings.json. "
            "Remove them with reconcile_claude_settings.py --uninstall-user."
        ),
    }


def reconcile_user(template: dict[str, Any], *, check: bool) -> dict[str, Any]:
    """Project the managed key set into USER scope.

    This is the floor that survives a session whose project directory is not a
    repository. The audited session's project dir was the multi-repo parent
    /home/user, so the committed per-repo .claude/settings.json was read only as
    an additional-directory source — its hooks never executed and its env block
    never applied (finding B-01). User scope is read regardless of project dir.
    Repo-level settings remain authoritative when a session IS correctly scoped.
    """
    wrote: list[str] = []
    drift: list[str] = []
    user_path = user_settings_path()
    existing = load_json(user_path) if user_path.is_file() else {}
    merged = merge_user_settings(template, existing)
    drift.extend(write_if_changed(user_path, dump_json(merged), check=check, wrote=wrote))
    drift.extend(
        write_if_changed(
            user_manifest_path(), dump_json(build_manifest(template)), check=check, wrote=wrote
        )
    )
    return {
        "wrote": wrote,
        "drift": drift,
        "preserved_plugins": "enabledPlugins" in merged,
        "managed_keys": build_manifest(template)["managed_keys"],
    }


def uninstall_user(*, check: bool) -> dict[str, Any]:
    """Remove exactly the manifest's key set from ~/.claude/settings.json.

    Exactly, and nothing else: keys the user added stay, and if no manifest
    exists we refuse rather than guess at what was ours.
    """
    wrote: list[str] = []
    manifest_path = user_manifest_path()
    user_path = user_settings_path()
    if not manifest_path.is_file():
        return {"wrote": [], "drift": [], "removed": [], "reason": "no manifest — nothing claimed"}
    manifest = load_json(manifest_path)
    managed = [k for k in manifest.get("managed_keys", []) if isinstance(k, str)]
    if not user_path.is_file():
        return {"wrote": [], "drift": [], "removed": [], "reason": "no user settings file"}

    existing = load_json(user_path)
    remaining = {k: v for k, v in existing.items() if k not in managed}
    removed = [k for k in managed if k in existing]
    drift = write_if_changed(user_path, dump_json(remaining), check=check, wrote=wrote)
    if not check and manifest_path.is_file():
        manifest_path.unlink()
        wrote.append(str(manifest_path))
    return {"wrote": wrote, "drift": drift, "removed": removed}


def settings_is_git_tracked(workspace: Path) -> bool:
    """True when the workspace tracks `.claude/settings.json` (repo-owned file).

    Tracked is the ownership signal, not file presence: a container-injected
    file is untracked and wholly template-managed, while a tracked file is repo
    content whose hooks must be composed with — never replaced by — the
    template (issue #281). A workspace that is not a git repository is
    untracked by definition.
    """
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(workspace),
                "ls-files",
                "--error-unmatch",
                "--",
                ".claude/settings.json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        # git missing — fall back to the managed whole-file path.
        return False
    return proc.returncode == 0


def reconcile_workspace(
    root: Path, workspace: Path, template: dict[str, Any], *, check: bool
) -> dict[str, Any]:
    wrote: list[str] = []
    drift: list[str] = []
    claude = workspace / ".claude"
    settings_path = claude / "settings.json"
    existing = load_json(settings_path) if settings_path.is_file() else None
    tracked = settings_is_git_tracked(workspace)
    drift.extend(
        write_if_changed(
            settings_path,
            dump_json(merge_workspace_settings(template, existing, compose_hooks=tracked)),
            check=check,
            wrote=wrote,
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
        ws_resolved = workspace.resolve()
        if gov and ws_resolved == root.resolve():
            # The governance clone as its own workspace: reconcile_gov_claude
            # already owns <root>/.claude — a second writer with merge ordering
            # would only churn the same file.
            results["workspace"] = {
                "wrote": [],
                "drift": [],
                "workspace": str(ws_resolved),
                "skipped": "workspace-is-governance-root",
            }
        else:
            ws_result = reconcile_workspace(root, ws_resolved, template, check=check)
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
    parser.add_argument(
        "--uninstall-user",
        action="store_true",
        help="remove exactly the L9-managed keys from ~/.claude/settings.json",
    )
    parser.add_argument(
        "--print-workspace-artifacts",
        action="store_true",
        help="list the workspace files this reconciler writes, one per line",
    )
    args = parser.parse_args()

    if args.print_workspace_artifacts:
        for item in workspace_artifacts():
            print(item)
        return 0

    root = args.root.resolve()

    if args.uninstall_user:
        result = uninstall_user(check=args.check)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            removed = ", ".join(result.get("removed", [])) or "(nothing)"
            print(f"uninstalled L9 user-scope keys: {removed}")
            if result.get("reason"):
                print(f"  {result['reason']}")
        return 0

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
