"""Relay hook carrier (CANONICAL_LAW §8.11): hook records go to the shared store via the agent.

On a relay surface the hook lane must open no local store, queue each
envelope-admitted record with the exact account-connector arguments, report
``RELAYED`` (never ``OK``), and keep the envelope as the bound on what may be
queued. Local surfaces are unchanged.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from memory_boundary_fixtures import FakeMemoryCli

from ops.memory import relay
from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.hook_carrier import CARRIER_ENV, CarrierError, resolve_carrier
from ops.memory.runtime_binding import RuntimeBinding

NS = "cursor-governance"


@pytest.fixture
def relay_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CARRIER_ENV, "relay")


def _client(bound: RuntimeBinding, cli: FakeMemoryCli, surface: str | None = None):
    return MemoryControlPlaneClient(bound, runner=cli.run, session_id="sess-1", surface=surface)


# --- carrier decision --------------------------------------------------------


def test_carrier_defaults_to_relay_only_on_a_cloud_container() -> None:
    assert resolve_carrier({"CLAUDE_CODE_REMOTE": "true"}) == "relay"
    assert resolve_carrier({}) == "local"
    assert resolve_carrier({"CLAUDE_CODE_REMOTE": "false"}) == "local"


def test_explicit_carrier_wins_in_both_directions() -> None:
    assert resolve_carrier({CARRIER_ENV: "local", "CLAUDE_CODE_REMOTE": "true"}) == "local"
    assert resolve_carrier({CARRIER_ENV: "RELAY"}) == "relay"


def test_unknown_carrier_is_refused_not_guessed() -> None:
    with pytest.raises(CarrierError, match="names no hook carrier"):
        resolve_carrier({CARRIER_ENV: "remote"})


def test_unknown_carrier_fails_the_write_closed(bound, fake_cli, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(CARRIER_ENV, "hosted")
    outcome = _client(bound, fake_cli).write(
        "fact", workspace=str(tmp_path), namespace=NS, memory_class="decision"
    )
    assert outcome.status is OutcomeStatus.BINDING_FAILED
    assert "names no hook carrier" in (outcome.error or "")
    assert fake_cli.calls == []
    assert not relay.relay_dir(tmp_path).exists()


# --- relay: nothing local, exact connector arguments -------------------------


@pytest.mark.usefixtures("relay_env")
def test_write_is_queued_for_write_agent_and_spawns_nothing(bound, fake_cli, tmp_path) -> None:
    outcome = _client(bound, fake_cli).write(
        "Hook lane writes reach the shared store through the relay.",
        workspace=str(tmp_path),
        namespace=NS,
        memory_class="decision",
        tags=("topic:memory",),
        idempotency_key="k-1",
        source_id="PR#1",
    )
    assert outcome.status is OutcomeStatus.RELAYED
    assert not outcome.ok, "a queued record is not a committed record"
    assert outcome.fault_class == "none"
    assert fake_cli.calls == [], "a relay surface must never spawn the local runtime"
    (entry,) = relay.pending(tmp_path)
    assert entry["tool"] == "memory.write_agent"
    assert entry["arguments"] == {
        "namespace": NS,
        "content": "Hook lane writes reach the shared store through the relay.",
        "memory_class": "decision",
        "tags": ["topic:memory", "carrier:relay", "hook-surface:operator"],
        "idempotency_key": "k-1",
        "source_id": "PR#1",
    }
    assert entry["id"] in (outcome.error or "")


@pytest.mark.usefixtures("relay_env")
def test_close_and_candidate_map_to_their_connector_tools(bound, fake_cli, tmp_path) -> None:
    client = _client(bound, fake_cli)
    closed = client.close(
        workspace=str(tmp_path),
        namespace=NS,
        summary="session closed",
        capsule_digest="d" * 64,
        idempotency_key="close:1",
    )
    candidate = {"source": {"namespace": NS, "repository": "Quantum-L9/X"}, "knowledge": {}}
    admitted = client.ingest_candidate(candidate, workspace=str(tmp_path))
    assert {closed.status, admitted.status} == {OutcomeStatus.RELAYED}
    tools = {row["operation"]: row for row in relay.pending(tmp_path)}
    assert tools["close"]["tool"] == "memory.close"
    assert tools["close"]["arguments"] == {
        "namespace": NS,
        "summary": "session closed",
        "session_id": "sess-1",
        "capsule_digest": "d" * 64,
        "idempotency_key": "close:1",
    }
    assert tools["ingest_candidate"]["tool"] == "memory.ingest_governed_candidate"
    assert tools["ingest_candidate"]["arguments"] == {"candidate": candidate}
    assert fake_cli.calls == []


@pytest.mark.usefixtures("relay_env")
def test_dry_run_and_distill_open_no_store_and_queue_nothing(bound, fake_cli, tmp_path) -> None:
    client = _client(bound, fake_cli)
    dry = client.write(
        "x", workspace=str(tmp_path), namespace=NS, memory_class="decision", dry_run=True
    )
    source = tmp_path / "excerpt.txt"
    source.write_text("redacted excerpt\n", encoding="utf-8")
    distilled = client.distill(workspace=str(tmp_path), namespace=NS, source_path=source)
    assert dry.status is OutcomeStatus.NOT_COMMITTED
    assert distilled.status is OutcomeStatus.NOT_COMMITTED
    assert "relay carrier" in (distilled.error or "")
    assert fake_cli.calls == []
    assert relay.pending(tmp_path) == []


@pytest.mark.usefixtures("relay_env")
def test_the_envelope_still_bounds_what_may_be_queued(bound, fake_cli, tmp_path) -> None:
    client = _client(bound, fake_cli, surface="pr-publish")  # episodic only, max 1 record
    wrong_class = client.write(
        "x", workspace=str(tmp_path), namespace=NS, memory_class="decision", source_id="PR#1"
    )
    assert wrong_class.status is OutcomeStatus.REJECTED
    first = client.write(
        "published",
        workspace=str(tmp_path),
        namespace=NS,
        memory_class="episodic",
        source_id="PR#1",
    )
    second = client.write(
        "again", workspace=str(tmp_path), namespace=NS, memory_class="episodic", source_id="PR#1"
    )
    assert first.status is OutcomeStatus.RELAYED
    assert second.status is OutcomeStatus.REJECTED, "a queued record counts against max_records"
    assert len(relay.pending(tmp_path)) == 1
    assert relay.pending(tmp_path)[0]["surface"] == "pr-publish"


@pytest.mark.usefixtures("relay_env")
def test_the_same_record_queued_twice_is_one_obligation(bound, fake_cli, tmp_path) -> None:
    for _ in range(2):
        _client(bound, fake_cli).write(
            "same fact", workspace=str(tmp_path), namespace=NS, memory_class="insight"
        )
    assert len(relay.pending(tmp_path)) == 1


def test_local_surface_is_unchanged(bound, fake_cli, tmp_path) -> None:
    # The suite-wide conftest pins the local carrier; the CLI is spawned as before.
    fake_cli.reply("write", 1, None, "StoreError: down")
    outcome = _client(bound, fake_cli).write(
        "x", workspace=str(tmp_path), namespace=NS, memory_class="decision"
    )
    assert fake_cli.calls, "a local surface still uses the bound runtime"
    assert outcome.status is not OutcomeStatus.RELAYED
    assert not relay.relay_dir(tmp_path).exists()


# --- acknowledgements --------------------------------------------------------


def _queue(tmp_path: Path) -> str:
    entry = relay.enqueue(
        tmp_path,
        surface="pr-publish",
        operation="write",
        arguments={"namespace": NS, "content": "c"},
    )
    return str(entry["id"])


def test_ack_with_a_connector_receipt_clears_the_entry(tmp_path) -> None:
    ident = _queue(tmp_path)
    receipt = str(uuid.uuid4())
    row = relay.ack(tmp_path, ident, receipt)
    assert row["receipt_id"] == receipt
    assert relay.pending(tmp_path) == []
    assert relay.ack(tmp_path, ident, str(uuid.uuid4()))["receipt_id"] == receipt, "first ack wins"


@pytest.mark.parametrize("bad", ["", "done", "12345", "receipt-ok"])
def test_ack_refuses_anything_but_a_receipt_uuid(tmp_path, bad) -> None:
    ident = _queue(tmp_path)
    with pytest.raises(relay.RelayError, match="not a connector receipt id"):
        relay.ack(tmp_path, ident, bad)
    assert len(relay.pending(tmp_path)) == 1


def test_ack_refuses_an_unknown_entry(tmp_path) -> None:
    _queue(tmp_path)
    with pytest.raises(relay.RelayError, match="no outbox entry"):
        relay.ack(tmp_path, "0" * 16, str(uuid.uuid4()))


def test_unrelayed_operation_is_refused(tmp_path) -> None:
    with pytest.raises(relay.RelayError, match="is not relayed"):
        relay.enqueue(tmp_path, surface=None, operation="distill", arguments={})


def test_cli_ack_and_status(tmp_path, capsys) -> None:
    ident = _queue(tmp_path)
    assert relay.main(["--workspace", str(tmp_path), "ack", ident, "--receipt", "nope"]) == 1
    assert "REFUSED" in capsys.readouterr().err
    receipt = str(uuid.uuid4())
    assert relay.main(["--workspace", str(tmp_path), "ack", ident, "--receipt", receipt]) == 0
    capsys.readouterr()
    assert relay.main(["--workspace", str(tmp_path), "status"]) == 0
    assert json.loads(capsys.readouterr().out) == {"total": 1, "acked": 1, "pending": 0}


def test_instruction_names_the_tool_arguments_and_ack(tmp_path) -> None:
    ident = _queue(tmp_path)
    text = relay.instruction(tmp_path, relay.pending(tmp_path))
    assert "memory.write_agent" in text
    assert '"content": "c"' in text
    assert f"python -m ops.memory.relay ack {ident} --receipt <receipt_id>" in text
    assert "no memory.ingest, no operator CLI write" in text
