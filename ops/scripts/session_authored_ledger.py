"""Session-scoped authored-path ledger.

Records paths this conversation mutated under its own workspace. sessionEnd
preserve reads only this ledger — never porcelain — so another chat's dirt
cannot be scooped.

Two authoring routes feed it, both workspace-confined:

- ``postToolUse`` for the named edit tools (Write / StrReplace / Delete …):
  the path is the tool input.
- ``afterShellExecution`` for shell-authored writes (generators, formatters,
  heredocs, ``sed -i``, ``rm``): the paths are the workspace inventory
  entries whose mtime falls inside that command's execution window
  (``duration`` from the Cursor payload plus a small slack), and tracked
  paths that vanished while their parent directory changed in the window.
  Dirt written before the window is never attributed. The one residual
  over-attribution is a tracked file another chat deleted earlier from a
  directory this command also changed; the consumer is copy-only, so the
  cost is an extra tombstone on this session's preserve ref, never a
  mutation of anyone's worktree.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.session-authored.v1"
SAFE_SESSION = re.compile(r"[^A-Za-z0-9._-]+")
LEDGER_HOME = Path.home() / ".cursor" / "l9" / "sessions"
SHELL_EVENTS = frozenset({"afterShellExecution", "after_shell_execution"})
SHELL_WINDOW_SLACK_S = 2.0
#: Below the hook's own 10s budget so a slow inventory returns "nothing"
#: cleanly instead of being killed mid-write.
INVENTORY_TIMEOUT_S = 8


def safe_session_id(session_id: str) -> str:
    cleaned = SAFE_SESSION.sub("_", (session_id or "").strip())[:120]
    return cleaned or "unknown"


def ledger_path(session_id: str, *, home: Path | None = None) -> Path:
    root = home if home is not None else LEDGER_HOME
    return root / safe_session_id(session_id) / "authored.json"


def session_id_from_event(event: dict[str, Any]) -> str:
    for key in (
        "session_id",
        "conversation_id",
        "CURSOR_CONVERSATION_ID",
        "CURSOR_SESSION_ID",
    ):
        raw = event.get(key)
        if raw:
            return str(raw)
    env = os.environ.get("CURSOR_CONVERSATION_ID") or os.environ.get("CURSOR_SESSION_ID")
    return str(env or "")


def workspace_from_event(event: dict[str, Any]) -> Path | None:
    roots = event.get("workspace_roots") or event.get("workspaceRoots") or []
    if isinstance(roots, list) and roots:
        candidate = Path(str(roots[0])).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    for key in ("cwd", "workspace", "workspace_root", "project_dir"):
        raw = event.get(key)
        if raw:
            candidate = Path(str(raw)).expanduser()
            if candidate.is_dir():
                return candidate.resolve()
    return None


def written_rels(event: dict[str, Any], workspace: Path) -> list[str]:
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    candidates: list[object] = []
    if isinstance(tool_input, dict):
        candidates.extend(
            [
                tool_input.get("path"),
                tool_input.get("file_path"),
                tool_input.get("filePath"),
                tool_input.get("target_file"),
            ]
        )
        files = tool_input.get("files")
        if isinstance(files, list):
            candidates.extend(files)
    for key in ("file_path", "path"):
        if event.get(key):
            candidates.append(event.get(key))
    rels: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        if not raw:
            continue
        path = Path(str(raw)).expanduser()
        if not path.is_absolute():
            path = workspace / path
        try:
            resolved = path.resolve()
        except OSError:
            continue
        try:
            rel = resolved.relative_to(workspace)
        except ValueError:
            continue
        text = rel.as_posix()
        if text.startswith("..") or text in seen:
            continue
        seen.add(text)
        rels.append(text)
    return rels


def is_shell_event(event: dict[str, Any]) -> bool:
    """True for a Cursor ``afterShellExecution`` payload (command + duration)."""
    name = str(event.get("hook_event_name") or event.get("hookEventName") or "")
    if name in SHELL_EVENTS:
        return True
    return isinstance(event.get("command"), str) and "duration" in event


def shell_window_start(event: dict[str, Any], *, now: float | None = None) -> float:
    """Epoch seconds at which this shell command may have started writing."""
    end = time.time() if now is None else now
    try:
        duration_ms = max(float(event.get("duration") or 0.0), 0.0)
    except (TypeError, ValueError):
        duration_ms = 0.0
    return end - duration_ms / 1000.0 - SHELL_WINDOW_SLACK_S


def _workspace_inventory(workspace: Path) -> list[str] | None:
    """Tracked plus untracked-unignored paths. None when git cannot answer."""
    try:
        proc = subprocess.run(  # noqa: S603
            [
                "git",
                "-C",
                str(workspace),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=INVENTORY_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return [rel for rel in proc.stdout.split("\0") if rel]


def _dir_changed_since(
    directory: Path, workspace: Path, start_ns: int, cache: dict[Path, bool]
) -> bool:
    """Nearest existing ancestor (inside the workspace) had its entries changed."""
    current = directory
    while True:
        if current in cache:
            return cache[current]
        try:
            changed = current.lstat().st_mtime_ns >= start_ns
        except FileNotFoundError:
            if current == workspace or current.parent == current:
                changed = False
            else:
                changed = _dir_changed_since(current.parent, workspace, start_ns, cache)
        except OSError:
            changed = False
        cache[current] = changed
        return changed


def shell_written_rels(
    event: dict[str, Any],
    workspace: Path,
    *,
    now: float | None = None,
) -> list[str]:
    """Workspace paths written or deleted inside this shell command's window."""
    start_ns = int(shell_window_start(event, now=now) * 1_000_000_000)
    inventory = _workspace_inventory(workspace)
    if inventory is None:
        return []
    rels: list[str] = []
    dir_cache: dict[Path, bool] = {}
    for rel in inventory:
        path = workspace / rel
        try:
            stat = path.lstat()
        except FileNotFoundError:
            if _dir_changed_since(path.parent, workspace, start_ns, dir_cache):
                rels.append(rel)
            continue
        except OSError:
            continue
        if stat.st_mtime_ns >= start_ns:
            rels.append(rel)
    return sorted(rels)


def load_ledger(session_id: str, *, home: Path | None = None) -> dict[str, Any]:
    path = ledger_path(session_id, home=home)
    if not path.is_file():
        return {
            "schema": SCHEMA,
            "session_id": session_id,
            "workspace": "",
            "paths": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema": SCHEMA,
            "session_id": session_id,
            "workspace": "",
            "paths": [],
        }
    if not isinstance(data, dict):
        return {
            "schema": SCHEMA,
            "session_id": session_id,
            "workspace": "",
            "paths": [],
        }
    paths = [str(p) for p in (data.get("paths") or []) if p]
    return {
        "schema": SCHEMA,
        "session_id": str(data.get("session_id") or session_id),
        "workspace": str(data.get("workspace") or ""),
        "paths": paths,
        "updated_at": data.get("updated_at"),
    }


def record_event(
    event: dict[str, Any],
    *,
    home: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Append this event's in-workspace paths. Foreign workspaces are ignored."""
    session_id = session_id_from_event(event)
    workspace = workspace_from_event(event)
    if not session_id or workspace is None:
        return {"ok": False, "reason": "no_session_or_workspace", "paths": []}
    rels = written_rels(event, workspace)
    if is_shell_event(event):
        known = set(rels)
        for rel in shell_written_rels(event, workspace, now=now):
            if rel not in known:
                rels.append(rel)
                known.add(rel)
    if not rels:
        return {"ok": True, "reason": "no_paths", "session_id": session_id, "paths": []}
    current = load_ledger(session_id, home=home)
    bound = current.get("workspace") or ""
    if bound and Path(bound).resolve() != workspace:
        return {
            "ok": False,
            "reason": "workspace_mismatch",
            "session_id": session_id,
            "paths": [],
        }
    merged = list(current.get("paths") or [])
    seen = set(merged)
    for rel in rels:
        if rel not in seen:
            merged.append(rel)
            seen.add(rel)
    payload = {
        "schema": SCHEMA,
        "session_id": session_id,
        "workspace": str(workspace),
        "paths": merged,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    dest = ledger_path(session_id, home=home)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "session_id": session_id, "workspace": str(workspace), "paths": rels}
