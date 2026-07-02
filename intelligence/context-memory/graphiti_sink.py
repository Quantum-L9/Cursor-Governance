"""Graphiti write sink for context-extractor.py.

Replaces the flat JSON save with an MCP call to memory_ingest_episode. The JSON
snapshot is kept as a local fallback cache, not the source of truth.
Import and call `emit_session(session_data)` where save_to_sessions_dir() was.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SESSIONS = Path(__file__).parent / "sessions"


def _as_narrative(s: dict) -> str:
    parts = [f"Project: {s.get('project','unknown')}",
             f"Summary: {s.get('summary','')}"]
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
    hour = session_data.get("hour", datetime.now(timezone.utc).strftime("%Y-%m-%d-%H"))
    (SESSIONS / f"{hour}.json").write_text(json.dumps(session_data, indent=2))  # fallback cache

    payload = {
        "body": _as_narrative(session_data),
        "source_agent_id": "cursor-context-extractor",
        "session_id": hour,
        "group_ids": [f"session:{hour}", f"agent:cursor-context-extractor"],
        "semantic_score": 1.0,
        "trust_level": "L2",
    }
    # Invoke via MCP client (stdio). Replace with in-proc call if co-located.
    proc = subprocess.run(
        ["python", "-m", "l9_ops_mcp.cli", "ingest", json.dumps(payload)],
        capture_output=True, text=True,
    )
    return {"cached": str(SESSIONS / f"{hour}.json"),
            "mcp_stdout": proc.stdout.strip(), "rc": proc.returncode}
