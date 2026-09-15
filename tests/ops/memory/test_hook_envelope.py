"""Hook-lane capability envelopes (ADR-0033 B7, INV-03b).

Two properties, one per lane:

* **Hook lane** — an automatic caller runs ``MemoryControlPlaneClient`` under
  its surface's envelope. Anything outside it is ``REJECTED`` *before a
  process is spawned*, and every receipt is stamped ``principal.type=hook``.
* **Lane classification** — every caller in this repository that constructs
  the client, or reaches ``ops.memory.cli`` by subprocess, names a declared
  surface; the operator form stays unstamped; agent-lane readers never touch
  the client at all.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from memory_boundary_fixtures import FakeMemoryCli, close_payload, distill_payload

from ops.memory import cli, hook_envelope
from ops.memory.control_plane_client import (
    FAULT_CANONICAL,
    MemoryControlPlaneClient,
    OutcomeStatus,
)
from ops.memory.hook_envelope import (
    REJECTED_PREFIX,
    HookEnvelope,
    UnknownHookSurface,
    envelope_for,
    hook_surfaces,
    load_envelopes,
)

ROOT = Path(__file__).resolve().parents[3]
WS = "/tmp/workspace"

WRITE_OK = {
    "receipt_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
    "status": "admitted",
    "namespace": "cursor-governance",
    "record_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
    "idempotency_key": "k",
    "admission": {"reasons": ["ok"]},
    "warnings": [],
}


def _client(bound, fake_cli: FakeMemoryCli, surface: str | None) -> MemoryControlPlaneClient:
    return MemoryControlPlaneClient(bound, runner=fake_cli.run, session_id="s-1", surface=surface)


def _candidate(primary_class: str = "session_continuation") -> dict:
    return {
        "schema_version": "1.0",
        "kind": "MemoryCandidate",
        "candidate_id": "cursor-continuation:x",
        "source": {"repository": "Quantum-L9/Cursor-Governance", "namespace": "cursor-governance"},
        "knowledge": {"primary_class": primary_class, "statement": "x", "confidence": 1.0},
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_declares_every_surface_the_pipeline_map_names() -> None:
    surfaces = set(hook_surfaces())
    assert surfaces == {
        "cursor-session-start",
        "claude-session-start",
        "cursor-session-end",
        "claude-session-end",
        "plan-prefetch",
        "pr-publish",
        "pe-sgd-ingest",
    }
    for envelope in load_envelopes().values():
        assert envelope.callers, f"{envelope.surface} names no caller"
        assert envelope.provenance_required is True


def test_read_only_surfaces_carry_no_write_capability() -> None:
    document = json.loads(hook_envelope.ENVELOPES_PATH.read_text(encoding="utf-8"))
    writes = set(document["write_operations"])
    for name in ("cursor-session-start", "claude-session-start", "plan-prefetch"):
        envelope = envelope_for(name)
        assert not (envelope.allowed_operations & writes)
        assert envelope.max_records == 0 and envelope.max_bytes == 0
        assert not envelope.record_classes


def test_unknown_surface_fails_at_construction_not_first_call(bound, fake_cli) -> None:
    with pytest.raises(UnknownHookSurface):
        _client(bound, fake_cli, "not-a-surface")
    assert fake_cli.calls == []


def test_malformed_registry_is_refused(tmp_path: Path) -> None:
    bad = tmp_path / "env.json"
    bad.write_text(
        json.dumps(
            {
                "read_operations": ["hydrate"],
                "write_operations": ["write"],
                "surfaces": {"x": {"allowed_operations": ["write"], "max_records": 0}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="max_records<=0"):
        load_envelopes(bad)
    bad.write_text(
        json.dumps(
            {
                "read_operations": ["hydrate"],
                "write_operations": ["write"],
                "surfaces": {"x": {"allowed_operations": ["merge"]}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not declare"):
        load_envelopes(bad)


# ---------------------------------------------------------------------------
# Enforcement — before a process is spawned
# ---------------------------------------------------------------------------


def test_read_surface_cannot_write_and_nothing_is_spawned(bound, fake_cli) -> None:
    client = _client(bound, fake_cli, "cursor-session-start")
    outcome = client.write(
        "a fact", workspace=WS, namespace="cursor-governance", memory_class="insight"
    )
    assert outcome.status is OutcomeStatus.REJECTED
    assert outcome.error is not None and outcome.error.startswith(REJECTED_PREFIX)
    assert "cursor-session-start" in outcome.error and "'write'" in outcome.error
    assert fake_cli.calls == [], "an envelope refusal must never reach the memory CLI"
    assert outcome.fault_class == FAULT_CANONICAL
    assert outcome.environment_fault is False
    assert outcome.integration_receipt["principal"] == {
        "type": "hook",
        "surface": "cursor-session-start",
        "max_records": 0,
        "max_bytes": 0,
        "provenance_required": True,
    }


def test_record_class_outside_the_envelope_is_rejected(bound, fake_cli) -> None:
    client = _client(bound, fake_cli, "pr-publish")
    outcome = client.write(
        "PICKUP", workspace=WS, namespace="cursor-governance", memory_class="insight", source_id="k"
    )
    assert outcome.status is OutcomeStatus.REJECTED
    assert "record class 'insight'" in (outcome.error or "")
    assert fake_cli.calls == []


def test_provenance_is_mandatory_on_hook_writes(bound, fake_cli) -> None:
    client = _client(bound, fake_cli, "pr-publish")
    outcome = client.write(
        "PICKUP", workspace=WS, namespace="cursor-governance", memory_class="session_continuation"
    )
    assert outcome.status is OutcomeStatus.REJECTED
    assert "requires provenance" in (outcome.error or "")


def test_max_bytes_bounds_one_payload(bound, fake_cli) -> None:
    client = _client(bound, fake_cli, "pr-publish")
    outcome = client.write(
        "x" * 5000,
        workspace=WS,
        namespace="cursor-governance",
        memory_class="session_continuation",
        source_id="k",
    )
    assert outcome.status is OutcomeStatus.REJECTED
    assert "max_bytes=4096" in (outcome.error or "")


def test_max_records_is_a_running_tally_of_committed_records(bound, fake_cli) -> None:
    fake_cli.reply("write", 0, WRITE_OK)
    client = _client(bound, fake_cli, "pr-publish")
    first = client.write(
        "PICKUP one",
        workspace=WS,
        namespace="cursor-governance",
        memory_class="session_continuation",
        source_id="k1",
    )
    assert first.status is OutcomeStatus.OK
    second = client.write(
        "PICKUP two",
        workspace=WS,
        namespace="cursor-governance",
        memory_class="session_continuation",
        source_id="k2",
    )
    assert second.status is OutcomeStatus.REJECTED
    assert "max_records=1" in (second.error or "")
    assert len([c for c in fake_cli.calls if c[0][1] == "write"]) == 1


def test_a_refused_write_does_not_consume_the_tally(bound, fake_cli) -> None:
    fake_cli.reply("write", 0, {**WRITE_OK, "status": "rejected", "record_id": None})
    client = _client(bound, fake_cli, "pr-publish")
    refused = client.write(
        "PICKUP",
        workspace=WS,
        namespace="cursor-governance",
        memory_class="session_continuation",
        source_id="k1",
    )
    assert refused.status is OutcomeStatus.REJECTED
    fake_cli.reply("write", 0, WRITE_OK)
    again = client.write(
        "PICKUP",
        workspace=WS,
        namespace="cursor-governance",
        memory_class="session_continuation",
        source_id="k2",
    )
    assert again.status is OutcomeStatus.OK, "memory's refusal committed nothing"


def test_session_end_envelope_admits_the_close_path_end_to_end(bound, fake_cli, tmp_path) -> None:
    fake_cli.reply(
        "ingest-governed-candidate",
        0,
        {
            "status": "admitted",
            "candidate_id": "cursor-continuation:x",
            "namespace": "cursor-governance",
            "record_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "write_receipt_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "storage_committed": True,
            "memory_state": "active",
            "reason": None,
        },
    )
    fake_cli.reply("close", 0, close_payload())
    fake_cli.reply("distill", 0, distill_payload(written_count=2))
    excerpt = tmp_path / "excerpt.md"
    excerpt.write_text("redacted\n", encoding="utf-8")
    client = _client(bound, fake_cli, "claude-session-end")
    assert client.ingest_candidate(_candidate(), workspace=WS).status is OutcomeStatus.OK
    assert (
        client.close(
            workspace=WS, namespace="cursor-governance", summary="done", session_id="s-1"
        ).status
        is OutcomeStatus.OK
    )
    distilled = client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt)
    assert distilled.status is OutcomeStatus.OK
    assert client._records_committed == 1 + 1 + 2
    for argv, _cwd, _stdin in fake_cli.calls:
        assert argv[1] in {"ingest-governed-candidate", "close", "distill"}


def test_claude_session_end_may_not_generic_write(bound, fake_cli) -> None:
    client = _client(bound, fake_cli, "claude-session-end")
    outcome = client.write(
        "a fact", workspace=WS, namespace="cursor-governance", memory_class="insight", source_id="k"
    )
    assert outcome.status is OutcomeStatus.REJECTED
    assert fake_cli.calls == []


def test_candidate_class_outside_the_envelope_is_rejected(bound, fake_cli) -> None:
    client = _client(bound, fake_cli, "claude-session-end")
    outcome = client.ingest_candidate(_candidate("procedural"), workspace=WS)
    assert outcome.status is OutcomeStatus.REJECTED
    assert "record class 'procedural'" in (outcome.error or "")
    assert fake_cli.calls == []


def test_operator_form_has_no_envelope_and_is_stamped_operator(bound, fake_cli) -> None:
    fake_cli.reply("write", 0, WRITE_OK)
    client = _client(bound, fake_cli, None)
    outcome = client.write(
        "a fact", workspace=WS, namespace="cursor-governance", memory_class="insight"
    )
    assert outcome.status is OutcomeStatus.OK
    assert outcome.integration_receipt["principal"] == {"type": "operator", "surface": None}


def test_unbound_runtime_still_wins_over_the_envelope(bound, fake_cli) -> None:
    from dataclasses import replace

    from ops.memory.runtime_binding import STATUS_UNBOUND

    unbound = replace(bound, status=STATUS_UNBOUND, memory_cli=None, reasons=("no interpreter",))
    client = MemoryControlPlaneClient(unbound, runner=fake_cli.run, surface="plan-prefetch")
    outcome = client.write("x", workspace=WS, namespace="n", memory_class="insight")
    assert outcome.status is OutcomeStatus.BINDING_FAILED
    assert outcome.environment_fault is True


def test_envelope_violation_reasons_are_specific() -> None:
    envelope = HookEnvelope(
        surface="t",
        allowed_operations=frozenset({"write"}),
        record_classes=frozenset({"insight"}),
        max_records=2,
        max_bytes=10,
        provenance_required=True,
    )
    assert envelope.violation("hydrate") is not None
    assert envelope.violation("write", memory_class="insight", records=1, provenance=True) is None
    assert "max_records" in (
        envelope.violation("write", memory_class="insight", records_used=2, records=1) or ""
    )
    assert "max_bytes" in (envelope.violation("write", memory_class="insight", byte_size=11) or "")
    assert envelope.violation("write", memory_class="insight", provenance=None) is None


# ---------------------------------------------------------------------------
# CLI: --surface is the subprocess form of the same envelope
# ---------------------------------------------------------------------------


def test_cli_surface_flag_binds_the_envelope(monkeypatch, bound, fake_cli, capsys) -> None:
    built: list[MemoryControlPlaneClient] = []
    real = cli.MemoryControlPlaneClient

    def capture(binding, **kwargs):
        client = real(binding, runner=fake_cli.run, **{k: v for k, v in kwargs.items()})
        built.append(client)
        return client

    monkeypatch.setattr(cli, "resolve_runtime_binding", lambda: bound)
    monkeypatch.setattr(cli, "MemoryControlPlaneClient", capture)
    code = cli.main(
        [
            "--surface",
            "plan-prefetch",
            "write",
            "a fact",
            "--kind",
            "insight",
            "--group-id",
            "cursor-governance",
            "--workspace",
            str(ROOT),
        ]
    )
    assert code == cli.EXIT_REFUSED
    assert built and built[0].surface == "plan-prefetch"
    document = json.loads(capsys.readouterr().out)
    assert document["status"] == "REJECTED"
    assert document["error"].startswith(REJECTED_PREFIX)
    assert fake_cli.calls == []


def test_cli_unknown_surface_is_refused_as_a_wiring_fault(monkeypatch, bound, capsys) -> None:
    monkeypatch.setattr(cli, "resolve_runtime_binding", lambda: bound)
    code = cli.main(["--surface", "nope", "health"])
    assert code == cli.EXIT_REFUSED
    document = json.loads(capsys.readouterr().out)
    assert document["status"] == "REJECTED" and "unknown hook surface" in document["error"]


# ---------------------------------------------------------------------------
# Lane classification of every caller in this repository
# ---------------------------------------------------------------------------

#: Every automatic caller and the surface it must name. A new constructor or
#: subprocess caller has to be placed here deliberately (ADR-0033 "Lane
#: classification of every caller").
HOOK_LANE_CALLERS: dict[str, str] = {
    "ops/graphiti/hydration/compile_session_packet.py": "cursor-session-start",
    "ops/graphiti/hydration/close_session.py": "cursor-session-end",
    "environment/agents/adapters/claude-code/hooks/memory_writeback.py": "claude-session-end",
    "environment/agents/adapters/claude-code/memory/memory_bridge.py": "claude-session-start",
    "ops/hooks/plan_memory_prefetch.py": "plan-prefetch",
    "ops/hooks/pr_publish_memory_write.py": "pr-publish",
    "environment/agents/generated-data/adapters/ingest_memory_candidate.py": "pe-sgd-ingest",
}

#: Constructs the client with no surface on purpose.
OPERATOR_FORM = {
    "ops/memory/cli.py",  # the human / deterministic-adapter form; --surface opts in
    "ops/memory/diagnostics.py",  # readiness probe run by make memory-readiness
    "ops/memory/hydration.py",  # factory; surface is threaded by the caller
    "ops/memory/legacy_reconciliation.py",  # human-run one-shot on a provider export
}

#: Agent-lane readers: public ``l9-memory`` only, never the hook client.
AGENT_LANE = {
    "environment/program-execution/integrations/graphiti/context_reader.py",
}

_CONSTRUCTOR = re.compile(r"MemoryControlPlaneClient\(")
_SUBPROCESS = re.compile(r"[\"']ops\.memory\.cli[\"']")


def _production_sources() -> list[Path]:
    out: list[Path] = []
    for base in ("ops", "environment"):
        for path in (ROOT / base).rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "/tests/" in f"/{rel}" or Path(rel).name.startswith("test_"):
                continue
            if "/_archived/" in f"/{rel}" or "/fixtures/" in f"/{rel}":
                continue
            out.append(path)
    return out


def test_every_hook_lane_caller_names_its_declared_surface() -> None:
    declared = set(hook_surfaces())
    for rel, surface in HOOK_LANE_CALLERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert surface in declared, f"{rel}: {surface} is not in memory-hook-envelopes.json"
        assert f'"{surface}"' in text, f"{rel} does not name its surface {surface!r}"
        assert "graphiti_memory_client" not in text


def test_no_unclassified_caller_constructs_the_client_or_spawns_the_operator_cli() -> None:
    placed = set(HOOK_LANE_CALLERS) | OPERATOR_FORM | AGENT_LANE
    unplaced: list[str] = []
    for path in _production_sources():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if rel == "ops/memory/control_plane_client.py":
            continue
        if _CONSTRUCTOR.search(text) or _SUBPROCESS.search(text):
            if rel not in placed:
                unplaced.append(rel)
    assert not unplaced, (
        "every caller of the hook-lane client must be classified in HOOK_LANE_CALLERS, "
        f"OPERATOR_FORM or AGENT_LANE (ADR-0033): {unplaced}"
    )


def test_agent_lane_readers_never_touch_the_hook_client() -> None:
    for rel in AGENT_LANE:
        text = (ROOT / rel).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith(("#", "``"))
        )
        assert "import" not in code or "control_plane_client" not in code
        assert "MemoryControlPlaneClient(" not in code
        assert "ops.memory.cli" not in code
        assert "--surface" not in code
        assert "resolve_runtime_binding" in text, "the binding locates the interpreter only"
        assert '"search"' in text


def test_close_session_default_and_claude_surfaces_are_declared() -> None:
    from ops.graphiti.hydration import close_session

    assert close_session.DEFAULT_CLOSE_SURFACE in hook_surfaces()
    writeback = (
        ROOT / "environment/agents/adapters/claude-code/hooks/memory_writeback.py"
    ).read_text(encoding="utf-8")
    assert 'surface="claude-session-end"' in writeback
