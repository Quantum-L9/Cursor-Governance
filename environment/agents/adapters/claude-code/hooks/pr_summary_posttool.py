#!/usr/bin/env python3
"""Put what a publish shipped in front of the model, once, after `make pr`.

Registered `--class observer` on PostToolUse. `.l9/pr/pr-summary.json` is written
by ops/scripts/write_pr_summary.py at the one place that knows a PR was opened;
this hook renders it as `additionalContext` so the facts reach the turn whether
or not the agent thinks to go looking. A receipt nobody reads is a receipt that
does not exist.

Why PostToolUse on Bash rather than matching the command text: `make pr`,
`make PR`, `l9 pr`, and `make -C "$GOV" pr WS="$PWD"` are the same publish, and
the remediator reaches it by a different route again. Matching spellings would
miss most of them. Every one funnels through open_pr_after_gate.sh, so the
receipt's existence is the trigger and the command string is never parsed.

Emitted once per (pr, head_sha): a publish is one event, and repeating it on
every later Bash call would train the reader to skip it. A new push to the same
PR writes a new head_sha and legitimately emits again.

This hook reports; it does not judge. The grouping of files by intent, and what
the gate caught that the agent had not, are the agent's to write — a fact dump
is the floor, not the deliverable (rules/48).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

RECEIPT_REL = Path(".l9/pr") / "pr-summary.json"
MARKER_REL = Path(".l9/pr") / "pr-summary-emitted"
#: A receipt older than this belongs to an earlier publish, not this turn.
FRESH_SECONDS = 1800
#: Long publishes exist; the model does not need 300 filenames to report well.
MAX_FILES_RENDERED = 60

_STATUS = {
    "a": "ADD",
    "added": "ADD",
    "m": "MOD",
    "modified": "MOD",
    "d": "DEL",
    "removed": "DEL",
    "r": "REN",
    "renamed": "REN",
    "c": "COPY",
    "copied": "COPY",
    "changed": "MOD",
}


def _repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _event_workspace(event: dict[str, Any]) -> Path | None:
    """Best-effort workspace: the tool's cwd, else the process cwd."""
    candidates: list[str] = []
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("cwd", "working_directory", "workspace"):
            value = tool_input.get(key)
            if value:
                candidates.append(str(value))
    for key in ("cwd", "working_directory", "workspace"):
        value = event.get(key)
        if value:
            candidates.append(str(value))
    candidates.append(os.getcwd())
    for raw in candidates:
        try:
            path = Path(raw).expanduser().resolve()
        except OSError:
            continue
        if not path.is_dir():
            continue
        root = _repo_root(path)
        if root is not None:
            return root
    return None


def _status_label(raw: object) -> str:
    return _STATUS.get(str(raw or "").strip().lower(), str(raw or "?").upper()[:4])


def _delta(row: dict[str, Any]) -> str:
    adds, dels = row.get("additions"), row.get("deletions")
    if adds is None or dels is None:
        return ""
    return f"+{adds}/-{dels}"


def render(summary: dict[str, Any]) -> str:
    files = [f for f in summary.get("files") or [] if isinstance(f, dict)]
    head = [
        "L9 publish summary — report this to the user; do not summarise it away.",
        "",
        f"PR #{summary.get('number')}: {summary.get('url')}",
        f"  title   : {summary.get('title')}",
        f"  base    : {summary.get('base')}   head: {summary.get('head')}",
        f"  commits : {summary.get('commits')}"
        f"   files: {summary.get('changed_files')}"
        f"   +{summary.get('additions')}/-{summary.get('deletions')}",
    ]
    if summary.get("source") != "github_api":
        head.append(
            f"  NOTE    : file list came from {summary.get('source')!r}, not the GitHub API"
            " — say so rather than presenting it as the PR's own list."
        )
    head.append("")
    head.append("Changed files:")

    shown = files[:MAX_FILES_RENDERED]
    for row in shown:
        path = row.get("path")
        if row.get("previous_path"):
            path = f"{row['previous_path']} -> {path}"
        head.append(f"  {_status_label(row.get('status')):<4} {_delta(row):>12}  {path}")
    if len(files) > len(shown):
        head.append(f"  … {len(files) - len(shown)} more (see {RECEIPT_REL})")
    if summary.get("files_truncated"):
        head.append(
            "  NOTE: the API file list was truncated; the counts above remain authoritative."
        )

    head += [
        "",
        "Group these by intent and add what the gate caught that you had not"
        " (rules/48). The list alone is the floor, not the report.",
    ]
    return "\n".join(head)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict):
        return 0

    workspace = _event_workspace(event)
    if workspace is None:
        return 0
    receipt = workspace / RECEIPT_REL
    try:
        stat = receipt.stat()
    except OSError:
        return 0  # the overwhelmingly common path: no publish this turn
    if time.time() - stat.st_mtime > FRESH_SECONDS:
        return 0

    try:
        summary = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(summary, dict) or not summary.get("number"):
        return 0

    token = f"{summary.get('repo')}#{summary.get('number')}@{summary.get('head_sha')}"
    marker = workspace / MARKER_REL
    try:
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == token:
            return 0
    except OSError:
        pass

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": render(summary),
                }
            }
        )
    )
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(token + "\n", encoding="utf-8")
    except OSError:
        pass  # emitting twice beats not emitting; never fail the tool call
    return 0


if __name__ == "__main__":
    sys.exit(main())
