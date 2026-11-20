#!/usr/bin/env python3
"""Session role in a /lcto swarm: is this host session a swarm child?

The CTO operating protocol (governance/cto-mode/MODE.yaml ``operating_protocol``) gives a
swarm agent no CTO, coordination, integration or merge authority, forbids it cross-session
messaging, requires coding-agent mode ACTIVE before any code change, and ends its work at
publication. Until this module, nothing outside the child's launch prompt knew a session
was a child, so every hook treated it as an operator-attended solo session.

A child registers itself as its first action (the rendered child launch prompt tells it
to): ``session_role.py register-child --cto-session <id>``. The record lives at
``$HOME/.l9/cto/roles/<host session id>.json`` (``l9.session-role/v1``) and is keyed by the
same id Claude Code puts in every hook payload (``session_id`` == ``CLAUDE_CODE_SESSION_ID``).

Trust model: a role record only NARROWS what a session may do (L9-MONOTONIC-001: a
subordinate policy may narrow permissions within its delegation). A session that declares
itself a child loses merge, cross-session messaging and handoff duties; it gains nothing.
So self-registration needs no authority, and an unregistered session is unaffected.
Hooks read it through :func:`is_child`; it never raises.

CLI: ``register-child --cto-session ID [--session-id ID]`` | ``status [--session-id ID]`` |
``clear [--session-id ID]``. ``status`` exits 0 for a child, 1 otherwise.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "l9.session-role/v1"
ROLE_CHILD = "swarm_child"
#: Same order as ops/autonomy/projection_mode.py SESSION_ENVS. The Claude hook
#: payload's ``session_id`` equals CLAUDE_CODE_SESSION_ID. Cursor agent shells
#: and Claude cloud fall through to CURSOR_CONVERSATION_ID and
#: CLAUDE_CODE_REMOTE_SESSION_ID so a mode and a role bind the same host.
SESSION_ENVS = (
    "CURSOR_SESSION_ID",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_SESSION_ID",
    "CURSOR_CONVERSATION_ID",
    "CLAUDE_CODE_REMOTE_SESSION_ID",
)
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def roles_dir(home: Path | None = None) -> Path:
    override = os.environ.get("L9_SESSION_ROLE_DIR", "").strip()
    if override:
        return Path(override)
    return (home or Path.home()) / ".l9" / "cto" / "roles"


def current_session_id(explicit: str | None = None) -> str:
    for candidate in (explicit, *(os.environ.get(name) for name in SESSION_ENVS)):
        if isinstance(candidate, str) and candidate.strip() and candidate.strip() != "default":
            return candidate.strip()
    return ""


def remote_session_id() -> str:
    """The id cross-session tools address (``session_<suffix>``), or "".

    Cloud sessions expose ``CLAUDE_CODE_REMOTE_SESSION_ID=cse_<suffix>``; create_session,
    send_message and get_session name the same session ``session_<suffix>``.
    """
    raw = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID", "").strip()
    if raw.startswith("cse_") and len(raw) > 4:
        return "session_" + raw[4:]
    return raw if raw.startswith("session_") else ""


def record_path(session_id: str, home: Path | None = None) -> Path:
    name = _SAFE.sub("_", session_id)[:160]
    return roles_dir(home) / f"{name}.json"


def read_role(session_id: str, home: Path | None = None) -> dict[str, Any] | None:
    if not session_id:
        return None
    try:
        data = json.loads(record_path(session_id, home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return None
    if data.get("session_id") != session_id:
        return None
    return data


def is_child(session_id: str | None = None, home: Path | None = None) -> bool:
    """True only for a session that registered as a swarm child. Never raises."""
    try:
        record = read_role(current_session_id(session_id), home)
    except Exception:  # noqa: BLE001 - a role probe never breaks a hook
        return False
    return bool(record and record.get("role") == ROLE_CHILD)


def child_record(session_id: str | None = None, home: Path | None = None) -> dict[str, Any]:
    try:
        record = read_role(current_session_id(session_id), home)
    except Exception:  # noqa: BLE001
        return {}
    return record if record and record.get("role") == ROLE_CHILD else {}


def register_child(
    cto_session: str, session_id: str | None = None, home: Path | None = None
) -> Path:
    sid = current_session_id(session_id)
    if not sid:
        raise ValueError("SESSION_UNRESOLVED: pass --session-id or run inside a host session")
    if not cto_session.strip():
        raise ValueError("CTO_SESSION_REQUIRED")
    path = record_path(sid, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": SCHEMA,
        "role": ROLE_CHILD,
        "session_id": sid,
        "remote_session_id": remote_session_id(),
        "cto_session": cto_session.strip(),
        "registered_at": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "effect": "narrowing only: no merge, no cross-session messaging, no handoff duty",
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("register-child", "status", "clear"))
    parser.add_argument("--cto-session", default="")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args(argv)
    if args.command == "register-child":
        try:
            path = register_child(args.cto_session, args.session_id)
        except ValueError as exc:
            print(json.dumps({"role": None, "error": str(exc)}))
            return 2
        print(json.dumps({"role": ROLE_CHILD, "record": str(path)}))
        return 0
    sid = current_session_id(args.session_id)
    if args.command == "clear":
        try:
            record_path(sid).unlink()
            removed = True
        except (OSError, ValueError):
            removed = False
        print(json.dumps({"session_id": sid, "removed": removed}))
        return 0
    record = child_record(sid)
    print(
        json.dumps(
            {"session_id": sid, "role": record.get("role") or "solo", **record}, sort_keys=True
        )
    )
    return 0 if record else 1


if __name__ == "__main__":
    sys.exit(main())
