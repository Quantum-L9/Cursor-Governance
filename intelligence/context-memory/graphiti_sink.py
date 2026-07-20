"""Graphiti write sink for context-extractor.py.

Replaces the flat JSON save with an MCP call to memory_ingest_episode. The JSON
snapshot is kept as a local fallback cache, not the source of truth.
Import and call `emit_session(session_data)` where save_to_sessions_dir() was.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SESSIONS = Path(__file__).parent / "sessions"


def _as_narrative(s: dict) -> str:
    parts = [f"Project: {s.get('project','unknown')}", f"Summary: {s.get('summary','')}"]
    if s.get("key_actions"):
        parts.append("Actions: " + "; ".join(s["key_actions"]))
    if s.get("decisions"):
        parts.append("Decisions: " + "; ".join(s["decisions"]))
    if s.get("files_modified"):
        parts.append("Files: " + ", ".join(s["files_modified"]))
    if s.get("next_steps"):
        parts.append("Next: " + "; ".join(s["next_steps"]))
    return "\n".join(parts)


def emit_session(session_data: dict) -> dict:
    """Feed a session as a Graphiti episode via the L9-Ops-MCP tool; cache JSON."""
    SESSIONS.mkdir(parents=True, exist_ok=True)
    hour = session_data.get("hour", datetime.now(UTC).strftime("%Y-%m-%d-%H"))
    # Write local JSON cache with explicit UTF-8 encoding
    cache_path = SESSIONS / f"{hour}.json"
    cache_path.write_text(json.dumps(session_data, indent=2), encoding="utf-8")

    payload = {
        "body": _as_narrative(session_data),
        "source_agent_id": "cursor-context-extractor",
        "session_id": hour,
        "group_ids": [f"session:{hour}", "agent:cursor-context-extractor"],
        "semantic_score": 1.0,
        "trust_level": "L2",
    }
    # Invoke via MCP client (stdio). Use sys.executable for interpreter consistency.
    proc = subprocess.run(
        [sys.executable, "-m", "l9_ops_mcp.cli", "ingest", json.dumps(payload)],
        capture_output=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if proc.returncode != 0:
        return {
            "cached": str(cache_path),
            "mcp_stdout": proc.stdout.strip(),
            "mcp_stderr": proc.stderr.strip(),
            "rc": proc.returncode,
            "status": "failed",
        }

    return {
        "cached": str(cache_path),
        "mcp_stdout": proc.stdout.strip(),
        "rc": proc.returncode,
        "status": "ok",
    }
