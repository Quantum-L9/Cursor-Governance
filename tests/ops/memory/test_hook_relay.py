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


@pytest.fixture(autouse=True)
def _repository_root(tmp_path: Path) -> None:
    """The relay places its outbox only in a repository root (relay_dir bound)."""
    (tmp_path / ".git").mkdir()


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
    assert json.loads(capsys.readouterr().out) == {
        "total": 1,
        "acked": 1,
        "pending": 0,
        "refused": 0,
    }


def test_instruction_names_the_tool_arguments_and_ack(tmp_path) -> None:
    ident = _queue(tmp_path)
    text = relay.instruction(tmp_path, relay.pending(tmp_path))
    assert "memory.write_agent" in text
    assert '"content": "c"' in text
    assert f"python -m ops.memory.relay ack {ident} --receipt <receipt_id>" in text
    assert "no memory.ingest, no operator CLI write" in text


# --- connector refusals (rule 42 satisfiability) ------------------------------

REASON = "namespace did not match any write grant"


def test_refused_entry_stays_listed_with_its_refusal(tmp_path) -> None:
    ident = _queue(tmp_path)
    receipt = str(uuid.uuid4())
    row = relay.refuse(tmp_path, ident, receipt, REASON)
    assert row == {**row, "id": ident, "receipt_id": receipt, "reason": REASON}
    owed = relay.pending(tmp_path)
    assert [r["id"] for r in owed] == [ident], "a refusal discharges nothing"
    assert owed[0]["refusal"]["receipt_id"] == receipt
    assert relay.acks(tmp_path) == {}, "a refusal is never recorded as an ack"


def test_status_counts_refused_entries_as_still_pending(tmp_path, capsys) -> None:
    ident = _queue(tmp_path)
    relay.enqueue(
        tmp_path, surface="s", operation="write", arguments={"namespace": NS, "content": "o"}
    )
    assert (
        relay.main(
            [
                "refuse",
                ident,
                "--receipt",
                str(uuid.uuid4()),
                "--reason",
                REASON,
                "--workspace",
                str(tmp_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert relay.main(["--workspace", str(tmp_path), "status"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "total": 2,
        "acked": 0,
        "pending": 2,
        "refused": 1,
    }


def test_ack_after_refusal_supersedes_it(tmp_path) -> None:
    ident = _queue(tmp_path)
    relay.refuse(tmp_path, ident, str(uuid.uuid4()), REASON)
    receipt = str(uuid.uuid4())
    assert relay.ack(tmp_path, ident, receipt)["receipt_id"] == receipt
    assert relay.pending(tmp_path) == []


def test_a_refusal_never_supersedes_an_ack(tmp_path) -> None:
    ident = _queue(tmp_path)
    relay.ack(tmp_path, ident, str(uuid.uuid4()))
    with pytest.raises(relay.RelayError, match="already acknowledged"):
        relay.refuse(tmp_path, ident, str(uuid.uuid4()), REASON)
    assert relay.refusals(tmp_path) == {}


@pytest.mark.parametrize("bad", ["", "  ", "rejected", "12345"])
def test_refusal_without_a_receipt_is_rejected(tmp_path, bad) -> None:
    ident = _queue(tmp_path)
    with pytest.raises(relay.RelayError, match="not a connector receipt id"):
        relay.refuse(tmp_path, ident, bad, REASON)
    assert relay.refusals(tmp_path) == {}
    assert "refusal" not in relay.pending(tmp_path)[0]


def test_cli_refusal_without_a_receipt_is_rejected(tmp_path, capsys) -> None:
    ident = _queue(tmp_path)
    with pytest.raises(SystemExit) as exc:
        relay.main(["refuse", ident, "--reason", REASON, "--workspace", str(tmp_path)])
    assert exc.value.code == 2
    assert "--receipt" in capsys.readouterr().err
    assert relay.refusals(tmp_path) == {}


@pytest.mark.parametrize("bad", ["", "   \n "])
def test_refusal_without_a_reason_is_rejected(tmp_path, bad) -> None:
    ident = _queue(tmp_path)
    with pytest.raises(relay.RelayError, match="must state the connector's reason"):
        relay.refuse(tmp_path, ident, str(uuid.uuid4()), bad)
    assert relay.refusals(tmp_path) == {}


def test_refusal_of_an_unknown_entry_is_rejected(tmp_path) -> None:
    _queue(tmp_path)
    with pytest.raises(relay.RelayError, match="no outbox entry"):
        relay.refuse(tmp_path, "0" * 16, str(uuid.uuid4()), REASON)


def test_refusals_are_append_only_and_the_latest_is_shown(tmp_path) -> None:
    ident = _queue(tmp_path)
    first, second = str(uuid.uuid4()), str(uuid.uuid4())
    relay.refuse(tmp_path, ident, first, REASON)
    assert relay.refuse(tmp_path, ident, first, "again")["reason"] == REASON, "same receipt: no-op"
    relay.refuse(tmp_path, ident, second, REASON)
    lines = (relay.relay_dir(tmp_path) / relay.REFUSALS_NAME).read_text().splitlines()
    assert [json.loads(line)["receipt_id"] for line in lines] == [first, second]
    assert relay.pending(tmp_path)[0]["refusal"]["receipt_id"] == second


def test_instruction_names_the_refuse_verb_and_it_parses_as_printed(tmp_path, capsys) -> None:
    import shlex

    ident = _queue(tmp_path)
    text = relay.instruction(tmp_path, relay.pending(tmp_path))
    line = next(row for row in text.splitlines() if "ops.memory.relay refuse" in row)
    argv = shlex.split(line.split("refuses:", 1)[1])[3:]  # drop "python -m ops.memory.relay"
    receipt = str(uuid.uuid4())
    argv = [receipt if part == "<receipt_id>" else part for part in argv]
    assert relay.main(argv) == 0
    assert ident in capsys.readouterr().out
    assert relay.pending(tmp_path)[0]["refusal"]["receipt_id"] == receipt
    shown = relay.instruction(tmp_path, relay.pending(tmp_path))
    assert f"REFUSED by the connector (receipt {receipt})" in shown


# --- review findings on #1008 -------------------------------------------------


def test_workspace_is_accepted_before_or_after_the_subcommand(tmp_path, capsys) -> None:
    ident = _queue(tmp_path)
    receipt = str(uuid.uuid4())
    # The order the Stop hook's instruction uses, and the order this module documents.
    assert relay.main(["ack", ident, "--receipt", receipt, "--workspace", str(tmp_path)]) == 0
    capsys.readouterr()
    assert relay.main(["--workspace", str(tmp_path), "status"]) == 0
    assert json.loads(capsys.readouterr().out)["pending"] == 0


def test_the_instruction_command_parses_as_printed(tmp_path, capsys) -> None:
    import shlex

    ident = _queue(tmp_path)
    text = relay.instruction(tmp_path, relay.pending(tmp_path))
    line = next(row for row in text.splitlines() if "ops.memory.relay" in row)
    argv = shlex.split(line.split("then:", 1)[1])[3:]  # drop "python -m ops.memory.relay"
    receipt = str(uuid.uuid4())
    argv = [receipt if part == "<receipt_id>" else part for part in argv]
    assert relay.main(argv) == 0
    assert relay.pending(tmp_path) == []
    assert ident in capsys.readouterr().out


def _obligation(tmp_path: Path, *, key: str) -> None:
    from ops.graphiti.hydration import session_latches as latches

    latches.write_receipt(
        tmp_path,
        "sess-1",
        {
            "status": latches.STATUS_CLOSE_INCOMPLETE,
            "close_idempotency_key": key,
            "failure_class": "pending_close",
            "write_count": 0,
        },
    )


def test_acking_a_relayed_close_discharges_the_session_obligation(tmp_path) -> None:
    from ops.graphiti.hydration import session_latches as latches

    _obligation(tmp_path, key="close:1")
    entry = relay.enqueue(
        tmp_path,
        surface="claude-session-end",
        operation="close",
        arguments={
            "namespace": NS,
            "summary": "s",
            "session_id": "sess-1",
            "idempotency_key": "close:1",
        },
    )
    assert latches.receipt_is_close_gap(latches.load_close_receipt(tmp_path, "sess-1"))
    receipt = str(uuid.uuid4())
    relay.ack(tmp_path, str(entry["id"]), receipt)
    closed = latches.load_close_receipt(tmp_path, "sess-1")
    assert latches.receipt_is_successful_close(closed)
    assert closed["canonical_operation_id"] == receipt


def test_a_close_ack_for_another_key_leaves_the_obligation_open(tmp_path) -> None:
    from ops.graphiti.hydration import session_latches as latches

    _obligation(tmp_path, key="close:other")
    entry = relay.enqueue(
        tmp_path,
        surface="claude-session-end",
        operation="close",
        arguments={
            "namespace": NS,
            "summary": "s",
            "session_id": "sess-1",
            "idempotency_key": "close:1",
        },
    )
    relay.ack(tmp_path, str(entry["id"]), str(uuid.uuid4()))
    assert latches.receipt_is_close_gap(latches.load_close_receipt(tmp_path, "sess-1"))


# --- path bounds (SonarCloud S2083 / S8707 on #1008) --------------------------


def test_relay_dir_refuses_a_directory_that_is_not_a_repository(tmp_path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(relay.RelayError, match="not a repository root"):
        relay.relay_dir(plain)


def test_relay_dir_refuses_a_relay_path_that_escapes_the_repository(tmp_path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / ".l9").mkdir()
    (tmp_path / ".l9" / "memory").symlink_to(outside, target_is_directory=True)
    with pytest.raises(relay.RelayError, match="escapes"):
        relay.relay_dir(tmp_path)


@pytest.mark.parametrize("name", ["../outbox.jsonl", "other.json", "/etc/passwd"])
def test_relay_file_opens_only_its_fixed_names(tmp_path, name) -> None:
    with pytest.raises(relay.RelayError):
        relay.relay_file(relay.relay_dir(tmp_path), name)


def test_cli_refuses_a_workspace_that_is_not_a_repository(tmp_path, capsys) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert relay.main(["--workspace", str(plain), "status"]) == 1
    assert "not a repository root" in capsys.readouterr().err
