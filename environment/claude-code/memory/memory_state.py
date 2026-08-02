#!/usr/bin/env python3
"""Local state + contract matching shared by the memory enforcement hooks.

Receipts and locks are small JSON artifacts under `<workspace>/.l9/memory/`.
Receipts assert that a SessionStart prefetch ran (trust-on-write, low stakes).
Locks record a server-issued phase-lock keyed by (namespace, task_signature);
the gate re-verifies locks against the memory server, so a forged lock file
without a real server claim does not pass. Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "memory-enforcement.contract.json"


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def workspace_root() -> Path:
    """Resolve the session workspace root that anchors ``.l9/memory``.

    ``CLAUDE_PROJECT_DIR`` (injected by the Claude Code harness for hooks and the
    PreToolUse gate) always wins. When it is unset — e.g. the ``memory_lock.py``
    CLI invoked from a Bash tool after ``cd`` into a repo subdirectory — fall back
    to walking up from the cwd to the nearest ancestor that already carries a
    ``.l9/memory`` tree. This keeps the CLI's receipt/lock/task-signature anchor
    identical to the gate's, so a lock acquired from a subdir is honored by the
    gate (and vice versa) instead of silently pointing at a different state root.
    If no ancestor has ``.l9/memory``, preserve the prior behavior (cwd).
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    for base in (cwd, *cwd.parents):
        if (base / ".l9" / "memory").is_dir():
            return base
    return cwd


def state_root(contract: dict[str, Any]) -> Path:
    root = contract.get("state", {}).get("root", ".l9/memory")
    path = Path(root)
    return path if path.is_absolute() else workspace_root() / path


def resolve_namespaces(contract: dict[str, Any]) -> list[str]:
    env = contract.get("memory", {}).get("namespace_env", "L9_MEMORY_NAMESPACES")
    raw = os.environ.get(env, "").strip()
    if raw:
        return [n.strip() for n in raw.split(",") if n.strip()]
    return list(contract.get("memory", {}).get("default_namespaces", []))


def task_signature(namespace: str) -> str:
    """Stable per-namespace claim for this workspace (not the session).

    Two agents working the same namespace/workspace collide on purpose; the
    conflict check is the point. Includes the resolved workspace so distinct
    checkouts do not share a claim.
    """
    seed = f"{namespace}|{workspace_root()}"
    return "cc-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


# --- receipts ---------------------------------------------------------------
def receipt_path(contract: dict[str, Any], session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "unknown")
    return state_root(contract) / "receipts" / f"{safe}.json"


def write_receipt(contract: dict[str, Any], session_id: str, payload: dict[str, Any]) -> Path:
    path = receipt_path(contract, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"session_id": session_id, "created_at": time.time(), **payload}
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def fresh_receipt(contract: dict[str, Any], session_id: str) -> bool:
    path = receipt_path(contract, session_id)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    ttl = int(contract.get("state", {}).get("session_ttl_seconds", 86400))
    return (
        data.get("session_id") == session_id
        and (time.time() - float(data.get("created_at", 0))) < ttl
    )


# --- locks ------------------------------------------------------------------
def lock_path(contract: dict[str, Any], namespace: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", namespace)
    return state_root(contract) / "locks" / f"{safe}.json"


def write_lock(contract: dict[str, Any], namespace: str, session_id: str, signature: str) -> Path:
    path = lock_path(contract, namespace)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "namespace": namespace,
        "task_signature": signature,
        "session_id": session_id,
        "acquired_at": time.time(),
    }
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_lock(contract: dict[str, Any], namespace: str) -> dict[str, Any] | None:
    path = lock_path(contract, namespace)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    ttl = int(contract.get("state", {}).get("lock_ttl_seconds", 3600))
    if (time.time() - float(data.get("acquired_at", 0))) >= ttl:
        return None
    return data


# --- operator break-glass audit --------------------------------------------
def record_override(contract: dict[str, Any], rule_id: str, reason: str) -> None:
    path = state_root(contract) / "overrides.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"at": time.time(), "event": "breakglass_override", "rule": rule_id, "reason": reason}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


# --- governed-write classification ------------------------------------------
def _glob_match(rel: str, pattern: str) -> bool:
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        return rel == pattern[:-3] or rel.startswith(pattern[:-2])
    if "*" not in pattern:
        return rel == pattern
    regex = "^" + re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*") + "$"
    return re.match(regex, rel) is not None


def _rel_path(raw: str) -> str:
    if not raw:
        return ""
    p = Path(raw)
    root = workspace_root()
    try:
        return str(p.resolve().relative_to(root)) if p.is_absolute() else str(p)
    except ValueError:
        return str(p)


def classify(
    contract: dict[str, Any], tool_name: str, tool_input: dict[str, Any]
) -> dict[str, Any] | None:
    """Return the first governed_writes rule matching this tool call, or None."""
    for rule in contract.get("governed_writes", []):
        match = rule.get("match", {})
        if tool_name not in match.get("tools", []):
            continue
        globs = match.get("path_globs")
        if globs is not None:
            rel = _rel_path(
                str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
            )
            if not any(_glob_match(rel, g) for g in globs):
                continue
        patterns = match.get("command_patterns")
        if patterns is not None:
            command = str(tool_input.get("command", ""))
            if not any(re.search(p, command) for p in patterns):
                continue
        return rule
    return None
