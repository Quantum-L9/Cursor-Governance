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
        chosen = found[-1]
    elif toplevel is not None:
        chosen = toplevel
    else:
        chosen = cwd
    return chosen


def _safe_id_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", value or "").strip("._")
    return cleaned[:80] or "unknown"


def extract_chat_id(event: dict[str, Any] | None) -> tuple[str, str]:
    """Per-chat discriminator for the write-gate receipt. Never the session id.

    Cursor payloads carry ``conversation_id``. Claude's conversation is
    ``session_id`` on the hook event; that string is still only a chat
    component — the receipt key always includes writer identity so two
    agents cannot share one pass.
    """
    if not event:
        return "", ""
    for key in ("conversation_id", "conversationId"):
        value = str(event.get(key) or "").strip()
        if value and value != "default":
            return value, key
    sid = str(event.get("session_id") or "").strip()
    if sid and sid != "default":
        return sid, "session_id"
    return "", ""


def extract_writer_agent_id(event: dict[str, Any] | None) -> str:
    if event:
        for key in ("agent_id", "agentId"):
            value = str(event.get(key) or "").strip()
            if value:
                return value
    return os.environ.get("L9_MEMORY_AGENT_ID", "").strip() or "unknown-agent"


def receipt_identity(
    *, event: dict[str, Any] | None = None, cli_arg: str | None = None
) -> tuple[str, str]:
    """The two RAW components of a writer receipt key: ``(writer_agent, chat)``.

    Both parts come back path-safe (``_safe_id_part``), so composing them with
    :func:`compose_receipt_id` is idempotent and a denial hint can name them
    verbatim as ``L9_MEMORY_AGENT_ID=<writer_agent> … --session-id <chat>``.

    ``cli_arg`` is the explicit repair override (``memory_prefetch.py
    --session-id``). It is a raw chat id; prefetch composes the key exactly
    once. A hint that carried the *composed* key was composed again on repair
    (``claude-code__claude-code__<chat>``), so the repair stamped a file the
    gate never looked up and could not unblock a governed write (audit
    P573-F1). A precomposed key whose writer prefix matches this run's writer
    is therefore accepted and reduced to its chat part rather than doubled.

    Raises :class:`ValueError` when no chat id is available.
    """
    writer_agent = _safe_id_part(extract_writer_agent_id(event))
    chat, _key = extract_chat_id(event)
    if not chat:
        chat = str(cli_arg or "").strip()
        prefix = f"{writer_agent}__"
        if chat.startswith(prefix) and len(chat) > len(prefix):
            chat = chat[len(prefix) :]
    if not chat or chat == "default":
        raise ValueError("receipt_id requires a chat id")
    return writer_agent, _safe_id_part(chat)


def compose_receipt_id(writer_agent: str, chat: str) -> str:
    """``<writer_agent>__<chat>`` — the one place the receipt key is spelled."""
    return f"{_safe_id_part(writer_agent)}__{_safe_id_part(chat)}"


def resolve_receipt_id(*, event: dict[str, Any] | None = None, cli_arg: str | None = None) -> str:
    """Writer-scoped receipt key. Distinct from SessionStart's session id.

    SessionStart runs once per session and must not authorize later chats or
    agents. Prefetch and the write gate both call this so they stamp and
    look up the same file.
    """
    writer_agent, chat = receipt_identity(event=event, cli_arg=cli_arg)
    return compose_receipt_id(writer_agent, chat)


def resolve_session_id(*, event: dict[str, Any] | None = None, cli_arg: str | None = None) -> str:
    """SessionStart session id only. Never a write-gate receipt key.

    Lock and gate paths MUST NOT default to ``unknown-session``.
    """
    if event:
        sid = str(event.get("session_id") or "").strip()
        if sid and sid != "default":
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


def workspace_for_target(tool_input: dict[str, Any] | None = None) -> Path:
    """Git root of the file being edited, else the session workspace.

    The write-gate receipt must live on the repository that is mutating.
    ``CURSOR_PROJECT_DIR`` can be a different clone (a remediator session
    opened in Cursor-Governance while editing Cognitive.Engine.Graphs), and
    stamping prefetch there writes the wrong namespace.
    """
    raw = ""
    if tool_input:
        raw = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "").strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = workspace_root() / path
        try:
            path = path.resolve()
        except OSError:
            # Broken symlink or unreadable parent: keep the unresolved Path
            # so the parent walk / git toplevel probe can still succeed.
            pass
        base = path if path.is_dir() else path.parent
        toplevel = _git_toplevel(base)
        if toplevel is not None:
            return toplevel
    return workspace_root()


def state_root(contract: dict[str, Any], workspace: Path | None = None) -> Path:
    root = contract.get("state", {}).get("root", ".l9/memory")
    path = Path(root)
    base = workspace if workspace is not None else workspace_root()
    return path if path.is_absolute() else Path(base).resolve() / path


def resolve_namespaces(contract: dict[str, Any], in_scope: list[str] | None = None) -> list[str]:
    """Namespaces this session requests: the in-scope repositories' own.

    An explicit ``L9_MEMORY_NAMESPACES`` wins. Otherwise the answer is the
    namespaces resolved from the repositories in session scope (``in_scope``,
    one per hydrated root). There is no static default: the contract used to
    carry ``default_namespaces: ["cursor-governance"]``, so every consumer
    repository's session requested and recorded the governance SSOT's
    namespace instead of its own. The SSOT is requested only when it is itself
    the repository in scope.
    """
    env = contract.get("memory", {}).get("namespace_env", "L9_MEMORY_NAMESPACES")
    raw = os.environ.get(env, "").strip()
    if raw:
        return [n.strip() for n in raw.split(",") if n.strip()]
    return list(dict.fromkeys(n for n in (in_scope or []) if n))


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


def _receipt_key_matches(data: dict[str, Any], lookup: str) -> bool:
    """Match the writer receipt key. Legacy files used session_id as the key."""
    if data.get("receipt_id") == lookup:
        return True
    return not data.get("receipt_id") and data.get("session_id") == lookup


# --- receipts ---------------------------------------------------------------
def receipt_path(contract: dict[str, Any], receipt_id: str, workspace: Path | None = None) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", receipt_id or "unknown")
    return state_root(contract, workspace) / "receipts" / f"{safe}.json"


def write_receipt(
    contract: dict[str, Any],
    receipt_id: str,
    payload: dict[str, Any],
    workspace: Path | None = None,
) -> Path:
    path = receipt_path(contract, receipt_id, workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"created_at": time.time(), **payload}
    body["receipt_id"] = receipt_id
    body.setdefault("session_id", payload.get("session_id") or "")
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def fresh_receipt(contract: dict[str, Any], receipt_id: str, workspace: Path | None = None) -> bool:
    path = receipt_path(contract, receipt_id, workspace)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    ttl = int(contract.get("state", {}).get("session_ttl_seconds", 86400))
    if not _receipt_key_matches(data, receipt_id):
        return False
    if (time.time() - float(data.get("created_at", 0))) >= ttl:
        return False
    # A receipt from a hydration that resolved no group and returned no facts is
    # not a fresh hydration. Accepting it made the precondition self-satisfying:
    # the "no -> hydrate, then continue" branch could never be taken again for
    # the whole TTL. Returning False re-runs hydration; it does NOT block the
    # write, which stays forbidden by rules/96 E7 and rules/98.
    return not data.get("degraded", False)


def usable_receipt(
    contract: dict[str, Any], receipt_id: str, workspace: Path | None = None
) -> bool:
    """True when prefetch stamped a writer receipt for this receipt_id.

    SessionStart's session id is not this key. Degraded hydrations are still
    usable for the write gate: denying on ``fresh_receipt() is False`` after a
    degraded receipt permanently blocked every governed Edit/Write for the TTL.
    Prefetch retries on the next chat; the gate continues either way.
    ``workspace`` is the repository being mutated (edited-file git root), not
    the session's ``CURSOR_PROJECT_DIR`` when those differ.
    """
    if not receipt_id:
        return False
    path = receipt_path(contract, receipt_id, workspace)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    ttl = int(contract.get("state", {}).get("session_ttl_seconds", 86400))
    if not _receipt_key_matches(data, receipt_id):
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
