#!/usr/bin/env python3
"""Stop-hook session write-back: deterministically ingest a session episode.

Captures what the session did (branch, HEAD, commit subjects) as a governed
memory record so provenance lands whether or not the agent chose to write it.
Fail-open: never blocks session end.
"""

from __future__ import annotations

import json
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory"))

import memory_state as st  # noqa: E402


def _git(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv
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
        return 0  # session never prefetched memory; nothing governed happened

    workspace = st.workspace_root()
    namespaces = st.resolve_namespaces(contract) or ["cursor-governance"]
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], workspace) or "?"
    head = _git(["rev-parse", "--short", "HEAD"], workspace) or "?"
    subjects = _git(["log", "--oneline", "-5", "--no-decorate"], workspace)
    content = (
        f"Claude Code session on {workspace.name} (branch {branch} @ {head}). "
        f"Recent commits:\n{subjects or '(none)'}"
    )

    try:
        import memory_client as mc

        mc.ingest(
            {
                "namespace": namespaces[0],
                "content": content,
                "idempotency_key": f"cc-session-{session_id}",
                "source_id": session_id,
                "tags": ["claude-code", "session-episode"],
            }
        )
    except Exception as exc:  # fail-open
        print(f"memory-writeback: skipped ({exc})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
