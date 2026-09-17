"""``python -m ops.memory.cli`` — the executable successor of the provider client (C11)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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
    code = cli.main(
        ["write", "a fact", "--kind", "error", "--agent-id", "cursor", "--workspace", str(ROOT)]
    )
    assert code == cli.EXIT_OK
    argv, cwd, _ = fake_cli.calls[-1]
    assert argv[argv.index("--kind") + 1] == "lesson"
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
    """KIND_ALIASES only exists to land on memory's vocabulary; prove it does."""

    from l9_graphite_memory.cli import _LEGACY_KIND_MAP  # noqa: PLC0415
    from l9_graphite_memory.contracts import MemoryClass  # noqa: PLC0415

    accepted = {item.value for item in MemoryClass} | set(_LEGACY_KIND_MAP)
    for kind, target in cli.KIND_ALIASES.items():
        assert target in accepted, f"--kind {kind} maps to {target!r}, which memory refuses"


def test_search_with_no_hits_completes(monkeypatch, bound, fake_cli: FakeMemoryCli, capsys) -> None:
    fake_cli.reply("search", 0, search_payload())
    _use(monkeypatch, bound, fake_cli)
    assert cli.main(["search", "anything", "--workspace", str(ROOT), "--limit", "3"]) == 0
    argv = fake_cli.calls[-1][0]
    assert argv[argv.index("--limit") + 1] == "3"
    assert json.loads(capsys.readouterr().out)["status"] == "NO_HITS"


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
