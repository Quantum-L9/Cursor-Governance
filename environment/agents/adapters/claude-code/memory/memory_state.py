#!/usr/bin/env python3
"""Local state + contract matching shared by the memory enforcement hooks.

Receipts are small JSON artifacts under `<workspace>/.l9/memory/receipts/`.
A receipt asserts that a SessionStart prefetch ran (trust-on-write, low stakes)
and is the *only* memory precondition on a governed write.

There are no lock artifacts. Repository-write authority is Git's: a dedicated
worktree isolates writers, a branch isolates history, and the publication gate
detects collisions. Memory state never authorizes, denies, or serializes
repository mutation (rules/96-multi-agent-main-bound-execution.mdc, E7/E10).
Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "memory-enforcement.contract.json"

sys.path.insert(0, str(HERE))
from errors import MemoryWriteDenied  # noqa: E402


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _git_toplevel(start: Path) -> Path | None:
    """Active git toplevel, or None if start is not inside a work tree."""
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def _non_workspace_ancestors() -> frozenset[Path]:
    """``$HOME`` and IDE homes are never a session workspace.

    ``$HOME/.l9/memory`` exists as the machine isolate store. Walking to it
    made every checkout resolve as home, then ``resolve_group_id($HOME)``
    scanned sibling repos and returned no ``group_id``.
    """
    home = Path.home().resolve()
    return frozenset({home, home / ".cursor", home / ".claude"})


def workspace_root() -> Path:
    """Resolve the session workspace root that anchors ``.l9/memory``.

    ``CLAUDE_PROJECT_DIR`` / ``CURSOR_PROJECT_DIR`` (harness project dir) always
    wins. When unset, if both a workspace and a nested path carry ``.l9/memory``,
    use the *outermost* ancestor that is not ``$HOME`` / ``~/.cursor`` /
    ``~/.claude`` and that stays inside the current git toplevel (a parent
    clone with its own ``.l9/memory`` is a different workspace). If no
    ancestor has ``.l9/memory``, use the active git toplevel, else cwd.
    """
    for key in ("CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"):
        env = os.environ.get(key)
        if env:
            return Path(env).resolve()
    cwd = Path.cwd().resolve()
    skip = _non_workspace_ancestors()
    found = [
        base
        for base in (cwd, *cwd.parents)
        if (base / ".l9" / "memory").is_dir() and base not in skip
    ]
    toplevel = _git_toplevel(cwd)
    if toplevel is not None:
        found = [base for base in found if base == toplevel or toplevel in base.parents]
    if found:
        return found[-1]
    if toplevel is not None:
        return toplevel
    return cwd


def resolve_session_id(*, event: dict[str, Any] | None = None, cli_arg: str | None = None) -> str:
    """Authoritative session id: hook event first, else required CLI arg.

    Lock and gate paths MUST NOT default to ``unknown-session``.
    """
    if event:
        sid = str(event.get("session_id") or "").strip()
        if sid:
            return sid
    sid = str(cli_arg or "").strip()
    if sid:
        return sid
    raise ValueError("session_id required (hook event or --session-id)")


def graphiti_state_path(session_id: str) -> Path:
    return Path.home() / ".cursor" / "graphiti-state" / f"{session_id}.json"


def identity_snapshot(contract: dict[str, Any], session_id: str) -> dict[str, str]:
    return {
        "session_id": session_id,
        "workspace_root": str(workspace_root()),
        "memory_state_root": str(state_root(contract)),
        "graphiti_state_file": str(graphiti_state_path(session_id)),
    }


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


# --- writer identity (runtime attribution enforcement) ----------------------
# Identities reserved for the Cursor surface. Claude Code shares the memory
# namespace with Cursor but must never write under Cursor's writer identity.
RESERVED_WRITER_IDENTITIES = frozenset({"cursor_agent", "cursor-agent"})


def resolve_writer_identity(
    contract: dict[str, Any] | None = None, *, require_explicit: bool = True
) -> dict[str, str]:
    """Resolve the memory writer's identity from the environment.

    ``agent_id`` comes from the contract-declared ``agent_id_env`` (default
    ``L9_MEMORY_AGENT_ID``); ``user_id`` comes from ``USER_ID``. When
    ``require_explicit`` is True — every write path — an unset value is returned
    as an empty string so :func:`validate_memory_writer` denies it. The contract
    defaults are applied only for read/bootstrap resolution
    (``require_explicit=False``); this keeps a missing runtime identity from
    being silently defaulted into a valid write, so ``test_missing_agent_id``
    can actually deny.
    """
    mem = (contract or {}).get("memory", {})
    agent_env = mem.get("agent_id_env", "L9_MEMORY_AGENT_ID")
    default_agent = mem.get("default_agent_id", "claude-code")
    agent_id = os.environ.get(agent_env, "").strip()
    user_id = os.environ.get("USER_ID", "").strip()
    if not require_explicit:
        agent_id = agent_id or default_agent
        user_id = user_id or "claude_code_agent"
    return {"agent_id": agent_id, "user_id": user_id}


def validate_memory_writer(identity: dict[str, str]) -> None:
    """Deny a memory write whose attribution is missing or reserved.

    Fail-closed guard invoked before any server-bound write. Raises
    :class:`MemoryWriteDenied` when ``namespace`` or a core identity field is
    absent, or when the agent/user identity is one reserved for another surface
    (Cursor). This is the runtime complement of the static template check in
    ``validate_claude_env.check_memory_identity_distinct``.
    """
    missing = [field for field in ("namespace", "agent_id", "user_id") if not identity.get(field)]
    if missing:
        msg = f"memory write denied: missing writer attribution: {', '.join(missing)}"
        raise MemoryWriteDenied(msg)
    for field in ("agent_id", "user_id"):
        if identity[field] in RESERVED_WRITER_IDENTITIES:
            msg = (
                f"memory write denied: {field}={identity[field]!r} is reserved for the Cursor "
                "surface; Claude Code must write under a distinct identity"
            )
            raise MemoryWriteDenied(msg)


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
    if data.get("session_id") != session_id:
        return False
    if (time.time() - float(data.get("created_at", 0))) >= ttl:
        return False
    # A receipt from a hydration that resolved no group and returned no facts is
    # not a fresh hydration. Accepting it made the precondition self-satisfying:
    # the "no -> hydrate, then continue" branch could never be taken again for
    # the whole TTL. Returning False re-runs hydration; it does NOT block the
    # write, which stays forbidden by rules/96 E7 and rules/98.
    return not data.get("degraded", False)


def usable_receipt(contract: dict[str, Any], session_id: str) -> bool:
    """True when this session already ran SessionStart prefetch.

    Degraded hydrations are still usable for the write gate: denying on
    ``fresh_receipt() is False`` after a degraded receipt permanently blocked
    every governed Edit/Write for the TTL. Prefetch retries on the next
    SessionStart; the gate continues either way.
    """
    path = receipt_path(contract, session_id)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    ttl = int(contract.get("state", {}).get("session_ttl_seconds", 86400))
    if data.get("session_id") != session_id:
        return False
    return (time.time() - float(data.get("created_at", 0))) < ttl


# --- operator break-glass audit --------------------------------------------
def record_override(contract: dict[str, Any], rule_id: str, reason: str) -> None:
    path = state_root(contract) / "overrides.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"at": time.time(), "event": "breakglass_override", "rule": rule_id, "reason": reason}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


# --- precondition validation (E7 fail-closed) --------------------------------
#: The only precondition a governed write may carry. A contract that names any
#: other precondition -- notably a Graphiti ``phase_lock`` -- is non-conformant
#: with the L9 Multi-Agent Main-Bound Execution Contract and must not be honored
#: silently: the gate raises, and its handler denies with the reason.
ALLOWED_PRECONDITIONS = frozenset({"session_prefetch"})


def validate_requires(rule: dict[str, Any]) -> list[str]:
    """Return a governed rule's preconditions, rejecting non-conformant ones.

    Raises :class:`ValueError` when the rule requires anything beyond session
    hydration. Reintroducing ``phase_lock`` as a repository-write precondition
    therefore fails loudly rather than quietly re-coupling memory state to
    repository authority.
    """
    requires = list(rule.get("requires", []))
    illegal = [r for r in requires if r not in ALLOWED_PRECONDITIONS]
    if illegal:
        msg = (
            f"non-conformant precondition(s) {illegal} on governed write "
            f"{rule.get('id', '<unknown>')!r}: repository-write authority comes from Git "
            "isolation, not memory state (E7). Allowed: "
            f"{sorted(ALLOWED_PRECONDITIONS)}"
        )
        raise ValueError(msg)
    return requires


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
