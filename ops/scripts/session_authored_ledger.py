"""Session-scoped authored-path ledger.

Records paths this conversation mutated under its own workspace. sessionEnd
preserve reads only this ledger — never porcelain — so another chat's dirt
cannot be scooped.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.session-authored.v1"
SAFE_SESSION = re.compile(r"[^A-Za-z0-9._-]+")
LEDGER_HOME = Path.home() / ".cursor" / "l9" / "sessions"


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
) -> dict[str, Any]:
    """Append this event's in-workspace paths. Foreign workspaces are ignored."""
    session_id = session_id_from_event(event)
    workspace = workspace_from_event(event)
    if not session_id or workspace is None:
        return {"ok": False, "reason": "no_session_or_workspace", "paths": []}
    rels = written_rels(event, workspace)
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
