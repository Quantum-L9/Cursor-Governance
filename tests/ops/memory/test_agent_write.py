"""ops/memory/agent_write.py — building and checking one agent memory write."""

from __future__ import annotations

import json

import pytest

from ops.memory import agent_write as aw


def _build(**extra: object) -> dict:
    args = {
        "namespace": "cursor-governance",
        "memory_class": "lesson",
        "content": "  Stop hooks gate on usable_receipt,\tnot fresh_receipt  ",
        "agent_id": "claude-code-desktop",
        "tags": ["hooks"],
        **extra,
    }
    return aw.build(**args)  # type: ignore[arg-type]


def test_build_maps_aliases_collapses_whitespace_and_stamps_agent_and_key() -> None:
    payload = _build()
    assert payload["memory_class"] == "insight"
    assert payload["content"] == "Stop hooks gate on usable_receipt, not fresh_receipt"
    assert payload["tags"] == ["agent:claude-code-desktop", "hooks"]
    assert payload["idempotency_key"].startswith("agent:cursor-governance:")


def test_the_same_fact_gets_the_same_key_whatever_its_spacing_or_case() -> None:
    one = aw.fact_key("ns-a", "decision", "Use usable_receipt")
    assert one == aw.fact_key("ns-a", "decision", "  use   USABLE_RECEIPT ")
    assert one != aw.fact_key("ns-b", "decision", "Use usable_receipt")
    assert one != aw.fact_key("ns-a", "insight", "Use usable_receipt")


def test_the_tool_follows_the_task_signature() -> None:
    assert aw.tool_for(_build()) == aw.WRITE_TOOL
    assert aw.tool_for(_build(task_signature="t")) == aw.GOVERNED_TOOL


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ({"namespace": "default"}, "never a write target"),
        ({"memory_class": "procedural"}, "not on the memory_write_agent allowlist"),
        ({"memory_class": "meta"}, "hook lane"),
        ({"tags": []}, "at least one topic"),
        ({"content": "WORK: fixed things and more things"}, "preamble"),
    ],
)
def test_refusals_explain_themselves(extra: dict, message: str) -> None:
    with pytest.raises(aw.AgentWriteError, match=message):
        _build(**extra)


def _desktop(monkeypatch: pytest.MonkeyPatch) -> None:
    """The builder stamps the DERIVED identity; state the surface (Claude Code Desktop)."""
    for name in (
        "CURSOR_AGENT",
        "CLAUDE_CODE_REMOTE",
        "CLAUDE_CODE_ENTRYPOINT",
        "L9_MEMORY_AGENT_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")


def test_the_cli_prints_tool_and_arguments(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _desktop(monkeypatch)
    code = aw.main(
        [
            "build",
            "--namespace",
            "cursor-governance",
            "--class",
            "decision",
            "--content",
            "Memory permissions use underscore tool names",
            "--tag",
            "claude-settings",
            "--agent-id",
            "claude-code-desktop",
        ]
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tool"] == aw.WRITE_TOOL
    assert out["arguments"]["tags"] == ["agent:claude-code-desktop", "claude-settings"]


def test_the_cli_refuses_loudly(capsys: pytest.CaptureFixture[str], tmp_path) -> None:
    bad = tmp_path / "p.json"
    bad.write_text(json.dumps({"arguments": {"namespace": "main", "content": "x"}}))
    assert aw.main(["validate", str(bad)]) == 1
    assert "REFUSED (l9.agent_memory_write.v1)" in capsys.readouterr().err


def test_the_module_does_no_memory_io() -> None:
    """The contract is the agent's own: it imports no client, no process spawner."""
    import ast  # noqa: PLC0415

    with open(aw.__file__, encoding="utf-8") as source:
        tree = ast.parse(source.read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert imported <= {
        "__future__",
        "argparse",
        "hashlib",
        "json",
        "os",
        "re",
        "sys",
        "uuid",
        "datetime",
        "pathlib",
        "typing",
        "ops.memory.agent_identity",  # pure resolver, no I/O
    }, sorted(imported)


def test_the_cli_refuses_an_agent_id_that_is_not_this_process(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _desktop(monkeypatch)
    code = aw.main(
        [
            "build",
            "--namespace",
            "cursor-governance",
            "--class",
            "decision",
            "--content",
            "An author chosen by the caller is drift",
            "--tag",
            "identity",
            "--agent-id",
            "claude-code-mobile",
        ]
    )
    assert code == 1
    assert "identity drift" in capsys.readouterr().err
