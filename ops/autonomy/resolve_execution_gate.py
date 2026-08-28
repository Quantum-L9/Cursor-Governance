#!/usr/bin/env python3
"""Resolve the one ``local_execution_gate.py`` every harness consumer must load.

Cursor ``beforeShellExecution``, Claude PreToolUse, and the bootstrap probe
used to pick the file independently. The hook preferred a path next to itself
(usually the live SSOT) and failed open when Python crashed; the wrap preferred
``$HOME/.cursor-governance`` and skipped when the file was missing; a
governance worktree edit therefore did not govern the session that authored it.

This module is the only resolution algorithm. Order:

1. ``L9_EXECUTION_GATE`` — tests / ops only; must be an existing file
2. Workspace checkout — only when it is a governance identity tree
   (``ssot`` or ``ssot_checkout``). Consumer copies never win.
3. Hook-adjacent ``ops/autonomy/local_execution_gate.py`` (realpath of the
   Cursor hook script)
4. ``$HOME/.cursor-governance/ops/autonomy/local_execution_gate.py``

Missing is an error (exit 2), never an implicit allow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

GATE_REL = Path("ops/autonomy/local_execution_gate.py")
OVERRIDE_ENV = "L9_EXECUTION_GATE"
IDENTITY_FILES = (
    "CANONICAL_LAW.md",
    "skills/AUTONOMY_MANIFEST.yaml",
    "rules/RULES-MANIFEST.yaml",
    "ops/scripts/check_governance_wiring.sh",
)


def is_governance_identity_tree(root: Path) -> bool:
    """Same identity test as ``ops/scripts/lib/workspace_kind.sh`` plus the gate."""
    try:
        resolved = root.resolve()
    except OSError:
        return False
    if not all((resolved / rel).is_file() for rel in IDENTITY_FILES):
        return False
    return (resolved / GATE_REL).is_file()


def _existing_file(path: Path) -> Path | None:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return None
    return resolved if resolved.is_file() else None


def workspace_from_event(event: Mapping[str, object] | None) -> Path | None:
    if not isinstance(event, Mapping):
        return None
    raw = event.get("cwd") or event.get("workspace") or event.get("workspace_path")
    if not raw:
        return None
    try:
        return Path(str(raw)).expanduser()
    except (OSError, TypeError, ValueError):
        return None


def resolve_gate(
    *,
    workspace: Path | str | None = None,
    hook_file: Path | str | None = None,
    home: Path | str | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Return the gate file path or raise ``FileNotFoundError``."""
    environ = env if env is not None else os.environ
    override = str(environ.get(OVERRIDE_ENV, "")).strip()
    if override:
        found = _existing_file(Path(override))
        if found is None:
            raise FileNotFoundError(f"{OVERRIDE_ENV} does not point at a file: {override}")
        return found

    if workspace:
        ws = Path(workspace)
        if is_governance_identity_tree(ws):
            found = _existing_file(ws / GATE_REL)
            if found is not None:
                return found

    if hook_file:
        try:
            hook = Path(hook_file).expanduser().resolve()
        except OSError:
            hook = None
        if hook is not None:
            adjacent = hook.parent.parent / "autonomy" / GATE_REL.name
            found = _existing_file(adjacent)
            if found is not None:
                return found

    home_path = Path(home) if home is not None else Path.home()
    ssot = _existing_file(home_path / ".cursor-governance" / GATE_REL)
    if ssot is not None:
        return ssot

    raise FileNotFoundError(
        "local execution gate could not be resolved "
        "(no identity checkout, no hook-adjacent file, no SSOT copy)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hook", default="", help="realpath of the Cursor hook script")
    parser.add_argument("--workspace", default="", help="workspace / project root")
    parser.add_argument(
        "--event-json",
        default="",
        help="path to a hook payload, or '-' to read stdin (cwd/workspace fields)",
    )
    args = parser.parse_args(argv)

    workspace: Path | str | None = args.workspace or None
    event_raw = ""
    if args.event_json == "-":
        event_raw = sys.stdin.read()
    elif args.event_json:
        event_raw = Path(args.event_json).read_text(encoding="utf-8")
    if event_raw and not workspace:
        try:
            payload = json.loads(event_raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            payload = None
        extracted = workspace_from_event(payload if isinstance(payload, dict) else None)
        if extracted is not None:
            workspace = extracted

    try:
        print(resolve_gate(workspace=workspace, hook_file=args.hook or None))
    except FileNotFoundError as exc:
        print(f"resolve_execution_gate: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
