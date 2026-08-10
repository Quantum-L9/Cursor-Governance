#!/usr/bin/env python3
"""Stop-hook write-back via Cursor Graphiti write (front door only)."""

from __future__ import annotations

import json
import subprocess  # noqa: S404
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))

import graphiti_bridge as gb  # noqa: E402
import memory_state as st  # noqa: E402


def _git(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(  # noqa: S603
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10, check=False
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    session_id = str(event.get("session_id", "")) or "unknown-session"

    try:
        contract = st.load_contract()
    except (OSError, json.JSONDecodeError):
        return 0
    if not st.fresh_receipt(contract, session_id):
        return 0

    workspace = st.workspace_root()
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], workspace) or "?"
    head = _git(["rev-parse", "--short", "HEAD"], workspace) or "?"
    subjects = _git(["log", "--oneline", "-5", "--no-decorate"], workspace)
    content = (
        f"Claude Code session on {workspace.name} (branch {branch} @ {head}). "
        f"Recent commits:\n{subjects or '(none)'}"
    )

    try:
        gb.write_episode(
            content,
            kind="session_summary",
            workspace=workspace,
            session_id=session_id,
        )
    except Exception as exc:  # fail-open
        print(f"memory-writeback: skipped ({exc})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
