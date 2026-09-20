"""``python -m ops.memory.cli`` — the executable successor of the provider client (C11)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from memory_boundary_fixtures import FakeMemoryCli, health_payload, search_payload

from ops.memory import cli
from ops.memory.control_plane_client import (
    MemoryControlPlaneClient,
    OperationOutcome,
    OutcomeStatus,
)

ROOT = Path(__file__).resolve().parents[3]


def _write_payload() -> dict:
    return {
        "receipt_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "status": "admitted",
        "namespace": "cursor-governance",
        "record_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "idempotency_key": "k",
        "admission": {"reasons": ["ok"]},
        "warnings": [],
    }


def _use(monkeypatch, bound, fake_cli: FakeMemoryCli) -> None:
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    monkeypatch.setattr(cli, "_client", lambda args: client)


@pytest.fixture(autouse=True)
def _no_ambient_agent_identity(monkeypatch) -> None:
    """Keep the shell's identity out of every test in this module.

    ``--agent-id`` and the prefetch bind both default from the environment:
    ``L9_MEMORY_AGENT_ID`` adds an ``agent:<id>`` tag to a write, and it also
    selects which prefetch receipt ``read_prefetch_bind`` considers applicable.
    Every real Claude or Cursor session exports it, so assertions written
    against a bare default passed on CI and failed in any developer shell.

    Module-wide rather than per-test: the dependency is the module's, and
    tests added later inherit the isolation instead of rediscovering it.
    """
    monkeypatch.delenv("L9_MEMORY_AGENT_ID", raising=False)
    monkeypatch.delenv("CURSOR_CONVERSATION_ID", raising=False)


def test_exit_codes_follow_the_outcome_taxonomy() -> None:
    ok = OperationOutcome("search", OutcomeStatus.NO_HITS)
    refused = OperationOutcome("write", OutcomeStatus.REJECTED)
    unbound = OperationOutcome("health", OutcomeStatus.BINDING_FAILED)
    assert cli.exit_code_for(ok) == cli.EXIT_OK
    assert cli.exit_code_for(refused) == cli.EXIT_REFUSED
    assert cli.exit_code_for(unbound) == cli.EXIT_UNBOUND


def test_outcome_document_names_the_authority_and_transport() -> None:
    outcome = OperationOutcome("health", OutcomeStatus.CANONICAL_UNAVAILABLE, error="down")
    document = cli.outcome_document(outcome)
    assert document["authority"] == "l9-graphite-memory"
    assert document["transport"] == "memory-control-plane/v1"
    assert document["ok"] is False and document["error"] == "down"


def test_write_maps_legacy_kinds_and_stamps_the_agent_tag(
    monkeypatch, bound, fake_cli: FakeMemoryCli, capsys
) -> None:
    fake_cli.reply("write", 0, _write_payload())
    _use(monkeypatch, bound, fake_cli)
    monkeypatch.setattr(cli, "read_prefetch_bind", lambda _ws: None)
    # ``lesson`` is the primary legacy alias. ``error`` used to be one too, but
    # it resolved to the same class as ``lesson`` and so could not be told apart
    # from it; it is no longer aliased and callers say ``lesson`` directly.
    code = cli.main(
        ["write", "a fact", "--kind", "lesson", "--agent-id", "cursor", "--workspace", str(ROOT)]
    )
    assert code == cli.EXIT_OK
    argv, cwd, _ = fake_cli.calls[-1]
    assert argv[argv.index("--kind") + 1] == "procedural"
    assert "error" not in cli.KIND_ALIASES, (
        "error aliased a class it could not be distinguished from"
    )
    assert "agent:cursor" in argv
    assert argv[argv.index("--group-id") + 1] == "cursor-governance"
    assert cwd == str(ROOT), "the CLI runs at the repository root"
    document = json.loads(capsys.readouterr().out)
    assert document["operation"] == "write" and document["status"] == "OK"
    assert document["namespace"]["write_namespace_hint"] == "cursor-governance"


def test_pickup_context_writes_an_episodic_record_tagged_as_a_continuation(
    monkeypatch, bound, fake_cli: FakeMemoryCli
) -> None:
    """A continuation is tag-selected (hydration.py), not a MemoryClass.

    ``l9-memory write`` rejects ``session_continuation`` as a class, so the
    alias that used to emit it produced INVALID_RECEIPT on every publish.
    """

    fake_cli.reply("write", 0, _write_payload())
    _use(monkeypatch, bound, fake_cli)
    monkeypatch.setattr(cli, "read_prefetch_bind", lambda _ws: None)
    # --agent-id defaults to os.environ["L9_MEMORY_AGENT_ID"], which every real
    # Claude/Cursor session sets, and the CLI then appends an ``agent:<id>`` tag.
    # Without controlling it this exact-equality assertion passes only on a
    # machine where the variable happens to be unset.
    monkeypatch.delenv("L9_MEMORY_AGENT_ID", raising=False)
    code = cli.main(
        ["write", "PICKUP", "--kind", "pickup_context", "--workspace", str(ROOT), "--tag", "x"]
    )
    assert code == cli.EXIT_OK
    argv = fake_cli.calls[-1][0]
    assert argv[argv.index("--kind") + 1] == "episodic"
    tags = [argv[i + 1] for i, a in enumerate(argv) if a == "--tag"]
    assert tags == ["x", cli.CONTINUATION_TAG]
    assert "session_continuation" not in argv[argv.index("--kind") + 1 :][:1]


def test_every_write_alias_reaches_a_class_the_bound_release_accepts(bound) -> None:
    """KIND_ALIASES must land on memory's vocabulary in ONE hop.

    This assertion used to accept ``_LEGACY_KIND_MAP`` keys as targets too, and
    that permissiveness is what let two defects sit in the table:
    ``error`` -> ``lesson`` and ``session_summary`` -> ``session_summary``.
    Neither is a MemoryClass. They resolved only because resolution is single
    pass (``KIND_ALIASES.get(kind, kind)``) and the *package* carried a second
    table that finished the job — so ``error`` and ``lesson`` both arrived at
    ``procedural`` and became indistinguishable. Targets are canonical only.
    """

    from l9_graphite_memory.contracts import MemoryClass  # noqa: PLC0415

    canonical = {item.value for item in MemoryClass}
    for kind, target in cli.KIND_ALIASES.items():
        assert target in canonical, (
            f"--kind {kind} maps to {target!r}, which is not a MemoryClass. "
            f"Single-pass resolution sends it downstream verbatim; do not rely "
            f"on a second table to finish it. Canonical: {sorted(canonical)}"
        )
        assert target not in cli.KIND_ALIASES, (
            f"--kind {kind} points at {target!r}, which is itself an alias."
        )
        assert kind not in canonical, (
            f"{kind!r} is a canonical MemoryClass; aliasing it makes "
            f"--kind {kind} mean something other than itself."
        )


def test_search_with_no_hits_completes(monkeypatch, bound, fake_cli: FakeMemoryCli, capsys) -> None:
    fake_cli.reply("search", 0, search_payload())
    _use(monkeypatch, bound, fake_cli)
    assert cli.main(["search", "anything", "--workspace", str(ROOT), "--limit", "3"]) == 0
    argv = fake_cli.calls[-1][0]
    assert argv[argv.index("--limit") + 1] == "3"
    assert json.loads(capsys.readouterr().out)["status"] == "NO_HITS"


def test_write_unbound_group_id_runs_at_the_owning_clone(
    monkeypatch, bound, fake_cli: FakeMemoryCli, capsys, tmp_path
) -> None:
    """Remediator from CG: --group-id CEG writes CEG, it does not fall through to CG."""
    fake_cli.reply("write", 0, _write_payload())
    _use(monkeypatch, bound, fake_cli)
    # A synthetic owning clone. The path only has to be a second location that
    # is not this checkout; a developer's real clone made the test host-specific
    # for no added coverage (INVARIANTS: no hardcoded /Users or /home paths).
    ceg = tmp_path / "Cognitive.Engine.Graphs"
    ceg.mkdir()
    monkeypatch.setattr(cli, "read_prefetch_bind", lambda _ws: None)
    monkeypatch.setattr(cli, "locate_clone_for_namespace", lambda slug, from_workspace=None: ceg)
    code = cli.main(
        [
            "write",
            "PICKUP: CEG#272 closed",
            "--kind",
            "pickup_context",
            "--workspace",
            str(ROOT),
            "--group-id",
            "cognitive-engine-graphs",
            "--agent-id",
            "cursor",
        ]
    )
    assert code == cli.EXIT_OK
    argv, cwd, _ = fake_cli.calls[-1]
    assert argv[argv.index("--group-id") + 1] == "cognitive-engine-graphs"
    assert cwd == str(ceg)
    assert json.loads(capsys.readouterr().out)["status"] == "OK"


def test_write_follows_one_prefetch_bind(
    monkeypatch, bound, fake_cli: FakeMemoryCli, capsys, tmp_path
) -> None:
    fake_cli.reply("write", 0, _write_payload())
    _use(monkeypatch, bound, fake_cli)
    # Synthetic owning clone — see the sibling test above.
    ceg = tmp_path / "Cognitive.Engine.Graphs"
    ceg.mkdir()
    monkeypatch.setattr(
        cli,
        "read_prefetch_bind",
        lambda _ws: {
            "group_id": "cognitive-engine-graphs",
            "group_ids": ["cognitive-engine-graphs"],
        },
    )
    monkeypatch.setattr(cli, "locate_clone_for_namespace", lambda slug, from_workspace=None: ceg)
    code = cli.main(
        [
            "write",
            "PICKUP: CEG#272 closed",
            "--kind",
            "pickup_context",
            "--workspace",
            str(tmp_path),
            "--agent-id",
            "cursor",
        ]
    )
    assert code == cli.EXIT_OK
    argv, cwd, _ = fake_cli.calls[-1]
    assert argv[argv.index("--group-id") + 1] == "cognitive-engine-graphs"
    assert cwd == str(ceg)


def test_write_refuses_group_id_that_contradicts_prefetch_bind(
    monkeypatch, bound, fake_cli: FakeMemoryCli, capsys
) -> None:
    _use(monkeypatch, bound, fake_cli)
    monkeypatch.setattr(
        cli,
        "read_prefetch_bind",
        lambda _ws: {
            "group_id": "cognitive-engine-graphs",
            "group_ids": ["cognitive-engine-graphs"],
            "exclusive_bind": True,
        },
    )
    code = cli.main(
        [
            "write",
            "PICKUP: should stay on CEG bind",
            "--kind",
            "pickup_context",
            "--workspace",
            str(ROOT),
            "--group-id",
            "cursor-governance",
            "--agent-id",
            "cursor",
        ]
    )
    assert code == cli.EXIT_REFUSED
    assert fake_cli.calls == []
    document = json.loads(capsys.readouterr().out)
    assert document["status"] == "PREFETCH_BOUND"
    assert document["namespace"]["prefetch_bound"] == "cognitive-engine-graphs"


def test_write_accepts_group_id_that_matches_workspace(
    monkeypatch, bound, fake_cli: FakeMemoryCli, capsys
) -> None:
    fake_cli.reply("write", 0, _write_payload())
    _use(monkeypatch, bound, fake_cli)
    monkeypatch.setattr(cli, "read_prefetch_bind", lambda _ws: None)
    code = cli.main(
        [
            "write",
            "a fact",
            "--kind",
            "lesson",
            "--workspace",
            str(ROOT),
            "--group-id",
            "cursor-governance",
            "--agent-id",
            "cursor",
        ]
    )
    assert code == cli.EXIT_OK
    argv = fake_cli.calls[-1][0]
    assert argv[argv.index("--group-id") + 1] == "cursor-governance"
    assert json.loads(capsys.readouterr().out)["status"] == "OK"


def test_write_without_a_namespace_is_refused_locally(
    monkeypatch, bound, fake_cli: FakeMemoryCli, tmp_path, capsys
) -> None:
    _use(monkeypatch, bound, fake_cli)
    code = cli.main(["write", "x", "--kind", "lesson", "--workspace", str(tmp_path)])
    assert code == cli.EXIT_REFUSED
    assert fake_cli.calls == []
    assert json.loads(capsys.readouterr().out)["status"] == "NAMESPACE_UNRESOLVED"


def test_health_accepts_workspace_for_uniform_invocation(
    monkeypatch, bound, fake_cli: FakeMemoryCli
) -> None:
    fake_cli.reply("health", 0, health_payload())
    _use(monkeypatch, bound, fake_cli)
    assert cli.main(["health", "--workspace", str(ROOT)]) == cli.EXIT_OK


def test_cli_module_spells_no_provider_vocabulary() -> None:
    src = (ROOT / "ops" / "memory" / "cli.py").read_text(encoding="utf-8")
    provider_url = "GRAPHITI_MCP_" + "URL"
    provider_token = "GRAPHITI_MCP_" + "TOKEN"
    for forbidden in (provider_url, provider_token, "add_" + "memory", "urllib"):
        assert forbidden not in src


def test_the_provider_client_and_its_tombstone_are_gone() -> None:
    """C15 (ADR-0033): nothing at the historical path, not even a stub that exits 2."""
    assert not (ROOT / "ops" / "graphiti" / "graphiti_memory_client.py").exists()
    proc = subprocess.run(
        [sys.executable, "-m", "ops.memory.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert proc.returncode == 0
    assert "health" in proc.stdout


def _receipt(path: Path, *, mtime: float, **fields: object) -> None:
    """Write one receipt and pin its mtime, so recency is controllable."""
    body: dict = {"created_at": time.time(), **fields}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_prefetch_bind_ignores_a_newer_writeback_receipt(tmp_path, monkeypatch) -> None:
    """Recency does not identify a bind (F612-2).

    Write-back receipts share the receipts directory with prefetch receipts by
    design. Selecting the newest file let a write-back — which carries no
    namespace — supply the bind, so the operator write silently lost the
    exclusive bind that was still in force.
    """
    monkeypatch.setenv("L9_MEMORY_AGENT_ID", "claude-code")
    monkeypatch.delenv("CURSOR_CONVERSATION_ID", raising=False)
    receipts = tmp_path / ".l9" / "memory" / "receipts"

    _receipt(
        receipts / "claude-code__chat-1.json",
        mtime=1000.0,
        receipt_id="claude-code__chat-1",
        agent_id="claude-code",
        conversation_id="chat-1",
        status="prefetched",
        group_id="owning-repo",
        exclusive_bind=True,
    )
    _receipt(
        receipts / "chat-1.writeback.json",
        mtime=2000.0,  # newer than the prefetch receipt
        receipt_id="chat-1" + ".writeback",
        status="closed",
    )

    bind = cli.read_prefetch_bind(str(tmp_path))
    assert bind is not None, "the prefetch receipt must still be found"
    assert bind["receipt_id"] == "claude-code__chat-1"
    assert cli.bound_write_namespace(bind) == "owning-repo"


def test_prefetch_bind_ignores_another_chat_and_another_agent(tmp_path, monkeypatch) -> None:
    """A bind is this writer's, not whoever wrote most recently."""
    monkeypatch.setenv("L9_MEMORY_AGENT_ID", "claude-code")
    monkeypatch.setenv("CURSOR_CONVERSATION_ID", "chat-1")
    receipts = tmp_path / ".l9" / "memory" / "receipts"

    _receipt(
        receipts / "claude-code__chat-1.json",
        mtime=1000.0,
        receipt_id="claude-code__chat-1",
        agent_id="claude-code",
        conversation_id="chat-1",
        status="prefetched",
        group_id="mine",
    )
    _receipt(
        receipts / "claude-code__chat-2.json",
        mtime=3000.0,  # newest, but a different chat
        receipt_id="claude-code__chat-2",
        agent_id="claude-code",
        conversation_id="chat-2",
        status="prefetched",
        group_id="other-chat",
    )
    _receipt(
        receipts / "cursor__chat-1.json",
        mtime=4000.0,  # newest overall, but a different writer
        receipt_id="cursor__chat-1",
        agent_id="cursor",
        conversation_id="chat-1",
        status="prefetched",
        group_id="other-agent",
    )

    assert cli.bound_write_namespace(cli.read_prefetch_bind(str(tmp_path))) == "mine"


def test_prefetch_bind_skips_non_dict_and_expired_receipts(tmp_path, monkeypatch) -> None:
    """A rejected file must not consume the recency watermark.

    The newest entry being a JSON array used to set the result to None *and*
    advance the watermark, so a valid older receipt could never win.
    """
    monkeypatch.setenv("L9_MEMORY_AGENT_ID", "claude-code")
    monkeypatch.delenv("CURSOR_CONVERSATION_ID", raising=False)
    receipts = tmp_path / ".l9" / "memory" / "receipts"

    _receipt(
        receipts / "claude-code__chat-1.json",
        mtime=1000.0,
        receipt_id="claude-code__chat-1",
        agent_id="claude-code",
        conversation_id="chat-1",
        status="prefetched",
        group_id="mine",
    )
    receipts.mkdir(parents=True, exist_ok=True)
    not_a_dict = receipts / "zz-array.json"
    not_a_dict.write_text(json.dumps(["not", "a", "receipt"]), encoding="utf-8")
    os.utime(not_a_dict, (5000.0, 5000.0))

    expired = receipts / "claude-code__chat-old.json"
    expired.write_text(
        json.dumps(
            {
                "created_at": time.time() - (cli._PREFETCH_RECEIPT_TTL + 60),
                "receipt_id": "claude-code__chat-old",
                "agent_id": "claude-code",
                "status": "prefetched",
                "group_id": "stale",
            }
        ),
        encoding="utf-8",
    )
    os.utime(expired, (6000.0, 6000.0))

    assert cli.bound_write_namespace(cli.read_prefetch_bind(str(tmp_path))) == "mine"
