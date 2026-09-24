"""l9.agent_memory_write.v1 — the agent memory write contract.

The JSON Schema is what an agent or operator reads; ops/memory/agent_write.py is
what the builder enforces. Every case is judged by BOTH and must get the same
verdict, so the schema never documents a contract nobody runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from ops.memory import agent_write as aw

SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "ops/memory/schemas/l9.agent_memory_write.v1.schema.json"
    ).read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def _ok(**extra: Any) -> dict[str, Any]:
    base = {
        "namespace": "cursor-governance",
        "content": "Stop hooks gate on usable_receipt so degraded sessions still close",
        "memory_class": "decision",
        "tags": ["agent:claude-code-desktop", "hooks"],
        "idempotency_key": "agent:cursor-governance:0123456789abcdef",
    }
    base.update(extra)
    return {k: v for k, v in base.items() if v is not None}


def _code_accepts(doc: Any) -> bool:
    try:
        aw.validate(doc)
    except aw.AgentWriteError:
        return False
    return True


CASES: list[tuple[str, Any]] = [
    ("minimal", _ok()),
    ("with evidence and supersedes", _ok(source_id="Org/repo#7", supersedes=[ID])),
    ("assertion triple", _ok(subject="hook", predicate="gates on", object="usable_receipt")),
    ("governed", _ok(task_signature="post-publish-handoff")),
    ("dry run", _ok(dry_run=True)),
    ("confidence", _ok(confidence=0.8)),
    ("forbidden namespace main", _ok(namespace="main")),
    ("shared workspace namespace", _ok(namespace="l9-workspace")),
    ("namespace not a slug", _ok(namespace="Cursor Governance")),
    ("content two lines", _ok(content="first fact here\nsecond fact here")),
    ("content too short", _ok(content="too short")),
    ("content too long", _ok(content="x" * (aw.MAX_CONTENT + 1))),
    ("session preamble", _ok(content="SESSION: did a lot of things today")),
    ("credential", _ok(content="the token is ghp_abcdefghijklmnopqrstuvwxyz0123")),
    ("alias class", _ok(memory_class="lesson")),
    ("procedural class", _ok(memory_class="procedural")),
    ("preference class", _ok(memory_class="preference")),
    ("no agent tag", _ok(tags=["hooks", "memory"])),
    ("two agent tags", _ok(tags=["agent:cursor", "agent:claude-code-desktop"])),
    ("only agent tag", _ok(tags=["agent:claude-code-desktop"])),
    ("uppercase tag", _ok(tags=["agent:claude-code-desktop", "Hooks"])),
    ("family agent tag names no surface", _ok(tags=["agent:claude-code", "hooks"])),
    ("mobile identity", _ok(tags=["agent:claude-code-mobile", "hooks"])),
    ("duplicate tags", _ok(tags=["agent:claude-code-desktop", "hooks", "hooks"])),
    ("no idempotency key", _ok(idempotency_key=None)),
    ("short idempotency key", _ok(idempotency_key="k")),
    ("partial assertion", _ok(subject="hook")),
    ("unknown field", _ok(consent={"subject_id": "x"})),
    ("source_trust not agent-set", _ok(source_trust=1)),
    ("bad supersedes id", _ok(supersedes=["not-a-uuid"])),
    ("confidence out of range", _ok(confidence=2)),
    ("dry_run not boolean", _ok(dry_run="yes")),
    ("not an object", ["namespace", "content"]),
]


def test_the_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_schema_fields_and_limits_match_the_code() -> None:
    assert set(SCHEMA["properties"]) == set(aw.KEYS)
    assert SCHEMA["required"] == list(aw.REQUIRED)
    assert SCHEMA["properties"]["memory_class"]["enum"] == list(aw.CLASSES)
    content = SCHEMA["properties"]["content"]
    assert (content["minLength"], content["maxLength"]) == (aw.MIN_CONTENT, aw.MAX_CONTENT)
    assert SCHEMA["properties"]["namespace"]["not"]["enum"] == list(aw.FORBIDDEN_NAMESPACES)


@pytest.mark.parametrize(("label", "doc"), CASES, ids=[c[0] for c in CASES])
def test_code_and_schema_give_the_same_verdict(label: str, doc: Any) -> None:
    assert VALIDATOR.is_valid(doc) == _code_accepts(doc), label


def test_the_embedded_example_validates_and_matches_the_builder() -> None:
    for example in SCHEMA["examples"]:
        VALIDATOR.validate(example)
        assert aw.validate(example) == example


def test_every_payload_field_is_an_argument_the_memory_tool_accepts() -> None:
    """The payload is passed to the tool unchanged, so it may only use real arguments."""
    from l9_graphite_memory import mcp_tools  # noqa: PLC0415 - the locked, vendored package

    tools = {tool["name"]: tool for tool in mcp_tools.tool_definitions()}
    agent_args = set(tools["memory.write_agent"]["inputSchema"]["properties"])
    governed_args = set(tools["memory.write_governed"]["inputSchema"]["properties"])
    assert set(aw.KEYS) - {"task_signature"} <= agent_args
    assert set(aw.KEYS) <= governed_args | {"dry_run"}
