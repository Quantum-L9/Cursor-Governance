#!/usr/bin/env python3
"""Thin Claude adapter → Cursor Graphiti front door.

Single egress for agent episodic memory (CANONICAL_LAW §8 / ADR-0005 / §2.1):
all Claude lifecycle hooks call ``ops/graphiti/graphiti_memory_client.py`` via the
governance locked venv. No HTTP ``L9_MEMORY_*`` client. No second store.
"""

from __future__ import annotations

import json
import os
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path
from typing import Any

CLIENT_REL = Path("ops/graphiti/graphiti_memory_client.py")
TUNNEL_REL = Path("ops/hooks/ensure_graphiti_tunnel.sh")


def find_governance_root() -> Path:
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / CLIENT_REL).is_file():
            return candidate
    home = Path.home() / ".cursor-governance"
    if (home / CLIENT_REL).is_file():
        return home
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / CLIENT_REL).is_file():
            return parent
    return home


def _python(root: Path) -> str:
    locked = root / ".venv" / "bin" / "python3"
    if locked.is_file() and os.access(locked, os.X_OK):
        return str(locked)
    return sys.executable


def ensure_tunnel(workspace: Path | None = None) -> None:
    root = find_governance_root()
    tunnel = root / TUNNEL_REL
    if not tunnel.is_file():
        return
    subprocess.run(  # noqa: S603
        ["bash", str(tunnel)],
        cwd=str(workspace or Path.cwd()),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )


def run_graphiti(
    args: list[str],
    *,
    workspace: Path | None = None,
    session_id: str | None = None,
    timeout: float = 60.0,
    ensure: bool = True,
) -> dict[str, Any]:
    """Run Cursor Graphiti CLI; return parsed JSON stdout (or raise)."""
    root = find_governance_root()
    client = root / CLIENT_REL
    if not client.is_file():
        raise RuntimeError(f"Cursor Graphiti CLI missing: {client}")
    cwd = workspace or Path.cwd()
    if ensure:
        ensure_tunnel(cwd)
    env = os.environ.copy()
    if session_id:
        env.setdefault("CURSOR_CONVERSATION_ID", session_id)
    proc = subprocess.run(  # noqa: S603
        [_python(root), str(client), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"graphiti {' '.join(args)} failed: {detail[:400]}")
    text = (proc.stdout or "").strip()
    if not text:
        return {}
    # Some commands print multiple JSON objects; take the last object.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        chunks = [c for c in text.split("\n{") if c.strip()]
        if not chunks:
            raise
        last = chunks[-1] if chunks[-1].startswith("{") else "{" + chunks[-1]
        return json.loads(last)


def inject(task: str, *, workspace: Path, session_id: str) -> dict[str, Any]:
    return run_graphiti(["inject", task], workspace=workspace, session_id=session_id)


def conflicts(*, workspace: Path, session_id: str) -> dict[str, Any]:
    return run_graphiti(["conflicts"], workspace=workspace, session_id=session_id)


def phase_lock(*, workspace: Path, session_id: str) -> dict[str, Any]:
    return run_graphiti(["phase-lock"], workspace=workspace, session_id=session_id)


def write_episode(
    body: str,
    *,
    kind: str = "session_summary",
    workspace: Path,
    session_id: str,
) -> dict[str, Any]:
    return run_graphiti(
        ["write", body, "--kind", kind],
        workspace=workspace,
        session_id=session_id,
        timeout=90.0,
    )


def phase_lock_satisfied(session_id: str) -> bool:
    """True when Cursor Graphiti state shows gmp:phase_lock for this session."""
    conv = session_id or os.environ.get("CURSOR_CONVERSATION_ID") or "default"
    path = Path.home() / ".cursor" / "graphiti-state" / f"{conv}.json"
    if not path.is_file():
        # Also accept default conversation state when Claude session ids differ.
        alt = Path.home() / ".cursor" / "graphiti-state" / "default.json"
        path = alt if alt.is_file() else path
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return "gmp:phase_lock" in (data.get("memory_satisfied_for") or [])
