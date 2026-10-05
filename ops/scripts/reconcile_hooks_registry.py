#!/usr/bin/env python3
"""Reconcile the machine hook registry (``~/.cursor/hooks.json`` + ``~/.cursor/hooks``).

Owner of two pieces of machine-global state that no workspace can repair for
itself: which hooks Cursor is told to run, and the link farm those commands
resolve through.

The template is authoritative for what governance *adds*, but never for what
survives: agents and debug sessions register their own ``./hooks/`` commands,
so an entry missing from the template is not thereby stale. Removal is decided
by liveness instead -- a command whose script is gone can only ever exit 127,
and when that entry carries ``failClosed`` it refuses the tool it guards in
every workspace on the machine until something drops it.

``--check`` answers the same liveness question without writing, so
``check_governance_wiring.sh`` cannot drift from what the reconcile enforces.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

HOOKS_PREFIX = "./hooks/"

BOOTSTRAP_CMD = "./hooks/session-start-bootstrap.sh"
CANONICAL_SUBAGENT_START = "./hooks/lifecycle-subagent-start.sh subagent_start"
CANONICAL_SUBAGENT_STOP = "./hooks/lifecycle-subagent-stop.sh"
COMBINED_BSE = "./hooks/before-shell-execution-gate.sh"

# Per-event retirements. These predate the general liveness prune below and are
# kept because they also remove an entry whose script still exists -- a
# superseded hook that runs is not dead, just wrong.
RETIRED_SESSION_END = {"./hooks/session-end-repo-hygiene.sh"}
RETIRED_BEFORE_SHELL = {
    "./hooks/graphiti-gate-shell.sh",
    "./hooks/l4-local-execution-gate-shell.sh",
    "./hooks/plan-kernel-execute-gate.sh",
}
RETIRED_SUBAGENT_START = {
    "./hooks/graphiti-gate-subagent.sh",
    "./hooks/lifecycle-subagent-start.sh",
}
# The WIP subsystem was retired by PR #677 (merged 2026-10-01 as ec787c58).
# That PR deleted the hook's purpose and its script, but nothing removed the
# two preToolUse entries naming it, so every Write/StrReplace on the machine
# was refused with exit 127. Listed explicitly as well as caught by liveness,
# because the script still exists on an unmerged branch in a second clone and
# would otherwise come back to life -- enforcing a policy that no longer exists
# -- the moment that branch is checked out.
RETIRED_PRE_TOOL_USE = {"./hooks/sacred-wip-transport.sh"}


def hook_script(command: str, hooks_dir: Path) -> Path | None:
    """Resolve the script a ``./hooks/`` command runs, or None if it has none.

    Matches the first ``./hooks/`` token rather than requiring the command to
    start with it, so an interpreter prefix (``bash ./hooks/x.sh``) resolves
    too. A command with no such token is some other tool's (an absolute path,
    a binary on PATH) and is never judged here.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    for token in tokens:
        if token.startswith(HOOKS_PREFIX):
            return hooks_dir / token[len(HOOKS_PREFIX) :]
    return None


def dead_entries(hooks: dict[str, list[Any]], hooks_dir: Path) -> list[tuple[str, str, bool]]:
    """Registered entries whose script is missing, as (event, command, fail_closed)."""
    dead: list[tuple[str, str, bool]] = []
    for event, entries in hooks.items():
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            command = entry.get("command") or ""
            script = hook_script(command, hooks_dir)
            # is_file() follows symlinks, so a dangling link counts as missing.
            if script is None or script.is_file():
                continue
            dead.append((event, command, bool(entry.get("failClosed"))))
    return dead


def _without(entries: list[Any], retired: set[str]) -> list[dict[str, Any]]:
    return [e for e in entries if isinstance(e, dict) and (e.get("command") or "") not in retired]


def _first(
    entries: list[dict[str, Any]], entry: dict[str, Any], marker: str
) -> list[dict[str, Any]]:
    """Put ``entry`` first and drop every other entry mentioning ``marker``."""
    return [entry] + [e for e in entries if marker not in (e.get("command") or "")]


def merge_template(data: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    """Append template entries this machine does not have yet."""
    if data.get("version") != 1:
        data = {"version": 1, "hooks": data.get("hooks", {})}
    merged_hooks = data.setdefault("hooks", {})
    for event, entries in template.get("hooks", {}).items():
        merged = merged_hooks.setdefault(event, [])
        known = {e.get("command") for e in merged if isinstance(e, dict)}
        for entry in entries:
            cmd = entry.get("command") if isinstance(entry, dict) else None
            if cmd and cmd not in known:
                merged.append(entry)
                known.add(cmd)
    return data


def apply_retirements(hooks: dict[str, list[Any]]) -> None:
    """Collapse each event onto its canonical entry and drop superseded ones."""
    # sessionStart: bootstrap first; retire the orchestrator-only entry. Match
    # by substring so env-var-prefixed variants collapse too -- otherwise they
    # survive every reconcile and double the cost of everything bootstrap does.
    ss = [e for e in hooks.setdefault("sessionStart", []) if isinstance(e, dict)]
    ss = [e for e in ss if e.get("command") != "./hooks/session-start-memory-orchestrator.sh"]
    hooks["sessionStart"] = _first(
        ss, {"command": BOOTSTRAP_CMD, "timeout": 60}, "session-start-bootstrap.sh"
    )

    # sessionEnd: dirt-close + auto-hygiene scooped other chats on a shared clone.
    hooks["sessionEnd"] = [
        e
        for e in _without(hooks.setdefault("sessionEnd", []), RETIRED_SESSION_END)
        if "session-end-repo-hygiene.sh" not in (e.get("command") or "")
    ]

    # preToolUse: see RETIRED_PRE_TOOL_USE.
    hooks["preToolUse"] = _without(hooks.setdefault("preToolUse", []), RETIRED_PRE_TOOL_USE)

    # beforeShellExecution: one combined gate, not four processes.
    bse = _without(hooks.setdefault("beforeShellExecution", []), RETIRED_BEFORE_SHELL)
    hooks["beforeShellExecution"] = _first(
        bse, {"command": COMBINED_BSE, "timeout": 10}, COMBINED_BSE
    )

    # subagentStart: one lifecycle command. The start script already runs
    # graphiti_gate_runner; the predecessors were a triple fire that fail-closed.
    starts = _without(hooks.setdefault("subagentStart", []), RETIRED_SUBAGENT_START)
    hooks["subagentStart"] = _first(
        starts,
        {"command": CANONICAL_SUBAGENT_START, "timeout": 30, "failClosed": True},
        CANONICAL_SUBAGENT_START,
    )

    stops = [e for e in hooks.setdefault("subagentStop", []) if isinstance(e, dict)]
    hooks["subagentStop"] = _first(
        stops,
        {"command": CANONICAL_SUBAGENT_STOP, "timeout": 45, "failClosed": True},
        CANONICAL_SUBAGENT_STOP,
    )


def prune_dead_entries(hooks: dict[str, list[Any]], hooks_dir: Path) -> list[str]:
    """Drop every entry whose script is missing. Returns report lines."""
    pruned: list[str] = []
    dead = {(event, command) for event, command, _ in dead_entries(hooks, hooks_dir)}
    for event, entries in list(hooks.items()):
        live: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            command = entry.get("command") or ""
            if (event, command) in dead:
                pruned.append(f"PRUNED: {event} {command} (target missing)")
                continue
            live.append(entry)
        hooks[event] = live
    return pruned


def prune_dangling_links(hooks_dir: Path) -> list[str]:
    """Remove ``~/.cursor/hooks`` symlinks into a governance clone that resolve nowhere.

    The link farm is written one name at a time and never swept, so a link
    whose source was deleted -- or that only ever existed on a branch that did
    not merge -- outlives it. Scoped to governance targets: a dangling link to
    anything else belongs to another tool.
    """
    removed: list[str] = []
    if not hooks_dir.is_dir():
        return removed
    governance_roots = (str(Path.home() / ".cursor-governance"),)
    for link in sorted(hooks_dir.iterdir()):
        if not link.is_symlink() or link.exists():
            continue
        target = str(Path(link).readlink())
        owned = target.startswith(governance_roots) or "/Cursor-Governance/" in target
        if not owned:
            continue
        link.unlink()
        removed.append(f"REMOVED: dangling {hooks_dir.name}/{link.name} -> {target}")
    return removed


def reconcile(hooks_json: Path, template_path: Path, hooks_dir: Path) -> list[str]:
    report = prune_dangling_links(hooks_dir)

    data: dict[str, Any] = json.loads(template_path.read_text())
    if hooks_json.exists():
        try:
            existing = json.loads(hooks_json.read_text())
        except json.JSONDecodeError:
            existing = {"version": 1, "hooks": {}}
        data = merge_template(existing, data)

    hooks: dict[str, list[Any]] = data.setdefault("hooks", {})
    apply_retirements(hooks)
    report += prune_dead_entries(hooks, hooks_dir)

    hooks_json.parent.mkdir(parents=True, exist_ok=True)
    hooks_json.write_text(json.dumps({"version": 1, "hooks": hooks}, indent=2) + "\n")
    report.append(f"OK: governance hooks registered in {hooks_json}")
    return report


def check(hooks_json: Path, hooks_dir: Path) -> list[str]:
    if not hooks_json.is_file():
        return []
    try:
        hooks = json.loads(hooks_json.read_text()).get("hooks", {})
    except json.JSONDecodeError:
        return [f"{hooks_json} is not valid JSON"]
    return [
        f"{event} {command} "
        + ("(failClosed: blocks every guarded tool)" if fail_closed else "(fails open)")
        for event, command, fail_closed in dead_entries(hooks, hooks_dir)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hooks-json", type=Path, required=True)
    parser.add_argument("--hooks-dir", type=Path, required=True)
    parser.add_argument("--template", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report registered commands whose script is missing; exit 1 if any",
    )
    args = parser.parse_args(argv)

    if args.check:
        dead = check(args.hooks_json, args.hooks_dir)
        for line in dead:
            print(line)
        return 1 if dead else 0

    if args.template is None:
        parser.error("--template is required unless --check is given")
    for line in reconcile(args.hooks_json, args.template, args.hooks_dir):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
