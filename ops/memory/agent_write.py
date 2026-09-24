"""The agent memory write contract — ``l9.agent_memory_write.v1``.

A model-authored durable fact is not freehand text. It is one atomic fact in a
fixed shape: the ARGUMENTS of the MCP tool ``memory_write_agent`` (or
``memory_write_governed`` when a ``task_signature`` is present), built and
checked here, then passed to the tool unchanged.

    python -m ops.memory.agent_write build --namespace cursor-governance \\
        --class decision --content "Stop hooks gate on usable_receipt, not fresh_receipt" \\
        --tag hooks --source-id Quantum-L9/Cursor-Governance#651
    python -m ops.memory.agent_write validate payload.json

What this module is and is not (CANONICAL_LAW §8.6, ADR-0033, INV-03b):

* It is the agent's own contract: the agent builds or validates its payload
  and keeps the verdict. It does no memory I/O, constructs no memory client,
  and sits in front of no tool call — no hook, matcher, deny list or receipt
  stands between the agent and ``memory_write_agent``.
* ``MemoryService`` still decides identity, namespace grants, admission and
  quarantine; nothing here widens or narrows that.

Machine form: ``ops/memory/schemas/l9.agent_memory_write.v1.schema.json``
(held to this module by ``tests/ops/memory/test_agent_write_schema.py``).
Contract: ``ops/memory/AGENT_WRITE_CONTRACT.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ops.memory.agent_identity import RETIRED, resolve_agent_id

SCHEMA_ID = "l9.agent_memory_write.v1"
WRITE_TOOL = "mcp__l9-graphite-memory__memory_write_agent"
GOVERNED_TOOL = "mcp__l9-graphite-memory__memory_write_governed"

#: The agent-lane classes this contract admits, in canonical (not alias) form.
#: ``write_governed`` has no alias table in the 2.4.0 package, so a canonical
#: class is the only form valid on both tools. ``preference``/``identity`` need
#: a consent object memory admission checks; ``meta`` is the continuation
#: record's class (hook lane); ``procedural`` is not on the write_agent allowlist.
CLASSES = ("decision", "insight", "observation", "constraint", "episodic", "semantic")
#: Legacy words the builder maps; the payload itself always carries the class.
ALIASES = {"lesson": "insight", "note": "observation", "rule": "decision"}
REFUSED_CLASSES = {
    "procedural": "not on the memory_write_agent allowlist; use insight",
    "preference": "needs a consent object memory admission checks; not an agent-lane fact",
    "identity": "needs a consent object memory admission checks; not an agent-lane fact",
    "meta": "the continuation record's class (hook lane); use episodic",
    "error": "not a memory class; use insight",
}

#: Never write targets: shared, default or ambiguous namespaces.
FORBIDDEN_NAMESPACES = ("main", "master", "default", "test", "l9-workspace")
NAMESPACE_RE = r"^[a-z0-9][a-z0-9-]{1,62}$"

MIN_CONTENT = 12
MAX_CONTENT = 600
#: One line — a fact, not a blob.
ONE_LINE_RE = r"^[^\r\n]+$"
#: A SESSION: / WORK: / LESSONS: style preamble marks a prose summary.
PREAMBLE_RE = r"^[A-Z][A-Z ]{2,20}:"
#: Credential shapes that must never reach memory.
SECRET_RE = r"(ghp_|gho_|ghs_|github_pat_|xox[bap]-|sk-[A-Za-z0-9]{20}|AKIA[0-9A-Z]{16}|-----BEGIN)"

TAG_RE = r"^[a-z0-9][a-z0-9_.:/-]{0,79}$"
AGENT_TAG_RE = r"^agent:[a-z0-9][a-z0-9-]{1,40}$"
MIN_TAGS, MAX_TAGS = 2, 12
IDEMPOTENCY_RE = r"^[A-Za-z0-9._:/#@-]{8,200}$"
MAX_TEXT_FIELD = 300
MAX_REFS = 20

REQUIRED = ("namespace", "content", "memory_class", "tags", "idempotency_key")
OPTIONAL = (
    "source_id",
    "subject",
    "predicate",
    "object",
    "supersedes",
    "references",
    "confidence",
    "valid_from",
    "valid_to",
    "task_signature",
    "dry_run",
)
KEYS = frozenset(REQUIRED + OPTIONAL)
ASSERTION = ("subject", "predicate", "object")


class AgentWriteError(ValueError):
    """The payload does not satisfy l9.agent_memory_write.v1."""


def _string(value: Any, field: str, *, max_len: int = MAX_TEXT_FIELD) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentWriteError(f"{field} must be a non-empty string")
    if len(value) > max_len:
        raise AgentWriteError(f"{field} is {len(value)} characters; at most {max_len}")
    return value


def _uuids(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_REFS:
        raise AgentWriteError(f"{field} must be a list of at most {MAX_REFS} record ids")
    for item in value:
        try:
            uuid.UUID(str(item))
        except ValueError as exc:
            raise AgentWriteError(f"{field} item {item!r} is not a record id (UUID)") from exc
    return value


def _timestamp(value: Any, field: str) -> str:
    text = _string(value, field)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AgentWriteError(f"{field} must be an ISO 8601 date-time") from exc
    return text


def validate(payload: Any) -> dict[str, Any]:
    """Return the payload unchanged when it satisfies the contract; raise otherwise."""
    if not isinstance(payload, dict):
        raise AgentWriteError("payload must be a JSON object of tool arguments")
    unknown = sorted(set(payload) - KEYS)
    if unknown:
        raise AgentWriteError(f"unknown field(s) {', '.join(unknown)}")
    missing = [key for key in REQUIRED if key not in payload]
    if missing:
        raise AgentWriteError(f"missing required field(s) {', '.join(missing)}")

    namespace = _string(payload["namespace"], "namespace", max_len=63)
    if not re.search(NAMESPACE_RE, namespace):
        raise AgentWriteError(f"namespace {namespace!r} is not a repository namespace slug")
    if namespace in FORBIDDEN_NAMESPACES:
        raise AgentWriteError(f"namespace {namespace!r} is never a write target")

    content = payload["content"]
    if not isinstance(content, str):
        raise AgentWriteError("content must be a string")
    if not MIN_CONTENT <= len(content) <= MAX_CONTENT:
        raise AgentWriteError(
            f"content is {len(content)} characters; one fact is {MIN_CONTENT}-{MAX_CONTENT}"
        )
    if not re.search(ONE_LINE_RE, content):
        raise AgentWriteError("content must be one line: one fact per write")
    if re.search(PREAMBLE_RE, content):
        raise AgentWriteError("content starts with a SESSION:/WORK:-style preamble: write the fact")
    if re.search(SECRET_RE, content):
        raise AgentWriteError("content looks like it carries a credential; never write secrets")

    memory_class = payload["memory_class"]
    if memory_class not in CLASSES:
        hint = REFUSED_CLASSES.get(str(memory_class)) or (
            f"alias of {ALIASES[memory_class]}; write the canonical class"
            if memory_class in ALIASES
            else f"one of {', '.join(CLASSES)}"
        )
        raise AgentWriteError(f"memory_class {memory_class!r} refused: {hint}")

    tags = payload["tags"]
    if not isinstance(tags, list) or not MIN_TAGS <= len(tags) <= MAX_TAGS:
        raise AgentWriteError(
            f"tags must be a list of {MIN_TAGS}-{MAX_TAGS} tags: agent:<id> plus at least one topic"
        )
    if len(set(map(str, tags))) != len(tags):
        raise AgentWriteError("tags must be unique")
    for tag in tags:
        if not isinstance(tag, str) or not re.search(TAG_RE, tag):
            raise AgentWriteError(f"tag {tag!r} is not a lowercase tag (a-z0-9 _ . : / -)")
    agent_tags = [t for t in tags if re.search(AGENT_TAG_RE, t)]
    if len(agent_tags) != 1:
        raise AgentWriteError("tags must carry exactly one agent:<id> tag")
    if agent_tags[0].removeprefix("agent:") in RETIRED:
        raise AgentWriteError(
            "agent:claude-code is the retired single identity and names no surface; "
            "the builder stamps the derived identity (claude-code-desktop / claude-code-mobile)"
        )

    key = payload["idempotency_key"]
    if not isinstance(key, str) or not re.search(IDEMPOTENCY_RE, key):
        raise AgentWriteError("idempotency_key must be 8-200 characters of [A-Za-z0-9._:/#@-]")

    present = [name for name in ASSERTION if name in payload]
    if present and len(present) != len(ASSERTION):
        raise AgentWriteError("subject, predicate and object are given together or not at all")
    for name in ("source_id", "task_signature", *ASSERTION):
        if name in payload:
            _string(payload[name], name)
    for name in ("supersedes", "references"):
        if name in payload:
            _uuids(payload[name], name)
    for name in ("valid_from", "valid_to"):
        if name in payload:
            _timestamp(payload[name], name)
    if "confidence" in payload:
        confidence = payload["confidence"]
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, int | float)
            or not 0 <= confidence <= 1
        ):
            raise AgentWriteError("confidence must be a number from 0 to 1")
    if "dry_run" in payload and not isinstance(payload["dry_run"], bool):
        raise AgentWriteError("dry_run must be true or false")
    return payload


def fact_key(namespace: str, memory_class: str, content: str) -> str:
    """The default idempotency key: the same fact in the same namespace is one record."""
    normalized = " ".join(content.split()).casefold()
    digest = hashlib.sha256(f"{memory_class}\x1f{normalized}".encode()).hexdigest()[:16]
    return f"agent:{namespace}:{digest}"


def build(
    *,
    namespace: str,
    memory_class: str,
    content: str,
    agent_id: str,
    tags: list[str] | tuple[str, ...] = (),
    source_id: str | None = None,
    task_signature: str | None = None,
    supersedes: list[str] | tuple[str, ...] = (),
    idempotency_key: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build a contract-conforming payload (aliases mapped, agent tag and key added)."""
    memory_class = ALIASES.get(memory_class, memory_class)
    content = " ".join(str(content).split())
    all_tags = [f"agent:{agent_id}", *[t for t in tags if t != f"agent:{agent_id}"]]
    payload: dict[str, Any] = {
        "namespace": namespace,
        "content": content,
        "memory_class": memory_class,
        "tags": list(dict.fromkeys(all_tags)),
        "idempotency_key": idempotency_key or fact_key(namespace, memory_class, content),
    }
    if source_id:
        payload["source_id"] = source_id
    if task_signature:
        payload["task_signature"] = task_signature
    if supersedes:
        payload["supersedes"] = list(supersedes)
    if dry_run:
        payload["dry_run"] = True
    return validate(payload)


def tool_for(payload: dict[str, Any]) -> str:
    """The MCP tool these arguments are for."""
    return GOVERNED_TOOL if payload.get("task_signature") else WRITE_TOOL


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps({"tool": tool_for(payload), "arguments": payload}, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ops.memory.agent_write", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build a conforming payload and print tool + arguments")
    b.add_argument("--namespace", required=True, help="from `ops.memory.cli resolve`")
    b.add_argument("--class", dest="memory_class", required=True, help=", ".join(CLASSES))
    b.add_argument("--content", required=True, help="one atomic fact, one line")
    b.add_argument("--tag", action="append", default=[], help="topic tag (repeatable)")
    b.add_argument(
        "--agent-id",
        default=resolve_agent_id() or None,
        help="default: this process's DERIVED identity (ops/memory/agent_identity.py)",
    )
    b.add_argument("--source-id", help="evidence: PR, commit, ADR, file path")
    b.add_argument("--task-signature", help="present => memory_write_governed")
    b.add_argument("--supersedes", action="append", default=[], help="record id replaced")
    b.add_argument("--idempotency-key")
    b.add_argument("--dry-run", action="store_true")
    v = sub.add_parser("validate", help="validate tool arguments from a file or stdin (-)")
    v.add_argument("path")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            derived = resolve_agent_id()
            if derived and args.agent_id != derived:
                raise AgentWriteError(
                    f"identity drift: --agent-id {args.agent_id!r} but this process is "
                    f"{derived!r}; the author is derived, never chosen"
                )
            if not args.agent_id:
                raise AgentWriteError(
                    "no memory identity for this process (ops/memory/agent_identity.py)"
                )
            payload = build(
                namespace=args.namespace,
                memory_class=args.memory_class,
                content=args.content,
                agent_id=args.agent_id,
                tags=args.tag,
                source_id=args.source_id,
                task_signature=args.task_signature,
                supersedes=args.supersedes,
                idempotency_key=args.idempotency_key,
                dry_run=args.dry_run,
            )
        else:
            text = sys.stdin.read() if args.path == "-" else Path(args.path).read_text("utf-8")
            data = json.loads(text)
            payload = validate(data.get("arguments", data) if isinstance(data, dict) else data)
    except (AgentWriteError, json.JSONDecodeError, OSError) as exc:
        print(f"REFUSED ({SCHEMA_ID}): {exc}", file=sys.stderr)
        return 1
    _emit(payload)
    return 0


__all__ = [
    "ALIASES",
    "CLASSES",
    "FORBIDDEN_NAMESPACES",
    "GOVERNED_TOOL",
    "KEYS",
    "REQUIRED",
    "SCHEMA_ID",
    "WRITE_TOOL",
    "AgentWriteError",
    "build",
    "fact_key",
    "main",
    "tool_for",
    "validate",
]

if __name__ == "__main__":
    raise SystemExit(main())
