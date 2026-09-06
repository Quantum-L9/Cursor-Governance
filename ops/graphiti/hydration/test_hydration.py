"""Unit tests for hydrate/close pipeline (no live Graphiti required)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GRAPHITI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GRAPHITI))

from episode_contract import EpisodeContract  # noqa: E402

from ops.graphiti.hydration import close_session as cs  # noqa: E402
from ops.graphiti.hydration import compile_session_packet as comp  # noqa: E402
from ops.graphiti.hydration import identity as ident  # noqa: E402
from ops.graphiti.hydration import transcript as tr  # noqa: E402


def test_identity_requires_agent_id(monkeypatch):
    monkeypatch.delenv("L9_MEMORY_AGENT_ID", raising=False)
    with pytest.raises(ident.IdentityError):
        ident.resolve_write_identity(surface="cursor")


def test_identity_cursor_stamp():
    got = ident.resolve_write_identity(explicit_agent_id="cursor", surface="cursor")
    assert got["agent_id"] == "cursor"
    assert "agent=cursor;kind=lesson" == ident.stamp_source_description("cursor", "lesson")


def test_identity_claude_cannot_impersonate_cursor():
    with pytest.raises(ident.IdentityError):
        ident.resolve_write_identity(
            explicit_agent_id="cursor",
            explicit_user_id="cursor_agent",
            surface="claude-code",
        )


def test_episode_contract_requires_agent_id():
    with pytest.raises(Exception):
        EpisodeContract(
            name="test-episode",
            episode_body="hello world body",
            source="text",
            source_description="x",
            reference_time=datetime.now(UTC),
            group_id="cursor-governance",
            agent_id="",
        )


def test_transcript_cap_and_redact(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps({"role": "user", "content": "email me at a@b.com please"})
        + "\n"
        + json.dumps({"role": "assistant", "content": "ok"})
        + "\n",
        encoding="utf-8",
    )
    text, source = tr.load_transcript_excerpt(transcript_path=str(path), max_chars=500)
    assert source == "stdin_transcript_path"
    assert "a@b.com" not in text
    assert "EMAIL_REDACTED" in text


# ---------------------------------------------------------------------------
# Canonical hydration stubs (stage C4: the packet's evidence comes from
# ops.memory.hydration, never from a provider search)
# ---------------------------------------------------------------------------

from ops.memory import hydration as hyd  # noqa: E402
from ops.memory.namespace_context import NamespaceContext  # noqa: E402
from ops.memory.session_contracts import ContinuationCapsuleV2  # noqa: E402


def _context(namespace="cursor-governance"):
    return NamespaceContext(
        workspace="/w",
        git_root="/w",
        repository_identity="Quantum-L9/Cursor-Governance",
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace, "l9-workspace"),
        method="registry",
    )


def _hydration(status="NO_HITS", *, continuation=None, error=None, record_ids=(), sections=()):
    return hyd.CanonicalHydration(
        status=status,
        namespace_context=_context(),
        requested_namespaces=("cursor-governance",),
        repository_state_digest="a" * 40,
        task_signature="sig",
        context_sections=tuple(sections),
        record_ids=tuple(record_ids),
        continuation=continuation,
        error=error,
        calls=3,
    )


def _continuation(*, stale=False, next_action="Run unit tests then install hooks"):
    capsule = ContinuationCapsuleV2(
        session_id="sess-prev",
        repository_identity="Quantum-L9/Cursor-Governance",
        objective="Ship hydrate pipeline",
        next_action=next_action,
        repository_state_digest="b" * 40 if stale else "a" * 40,
        producer_version="2.0.0",
    )
    return hyd.ContinuationEvidence(
        record_id="66666666-6666-6666-6666-666666666666",
        capsule=capsule,
        stale=stale,
        recorded_at="2026-09-05T00:00:00+00:00",
    )


def _canonical(monkeypatch, tmp_path, hydration):
    monkeypatch.setenv("L9_MEMORY_SESSION_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(comp, "canonical_hydrate", lambda *a, **k: hydration)


def test_compile_packet_fail_open(monkeypatch, tmp_path):
    """A clean canonical no-hit is a normal empty answer, not a degraded session."""
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-1", agent_id="cursor"
    )
    assert packet["agent_id"] == "cursor"
    assert packet["group_id"] == "cursor-governance"
    assert packet["next_action_contract"]["next_action"]
    assert packet["degraded"] is False
    assert packet["hydrate_stats"]["facts_returned"] == 0
    assert packet["hydrate_stats"]["memory_status"] == "NO_HITS"
    assert packet["hydrate_stats"]["search_queries_used"] == 3
    assert packet["memory"]["transport"] == "cli"
    ctx = comp.format_additional_context(packet)
    assert ctx.startswith("### memory hydrate")
    assert "next=" in ctx
    assert "facts_returned=" in ctx
    assert "status=NO_HITS" in ctx
    assert "memory-bank" not in ctx
    assert "hydrate_stats" in ctx
    assert (tmp_path / "state").is_dir()


def test_compile_packet_transport_failure_is_not_empty_search(monkeypatch, tmp_path):
    """CANONICAL_UNAVAILABLE is never collapsed into an empty answer (S-07)."""
    _canonical(
        monkeypatch,
        tmp_path,
        _hydration("CANONICAL_UNAVAILABLE", error="StoreError: store unreachable"),
    )
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-unreachable", agent_id="cursor"
    )
    reason = packet["hydrate_stats"]["degrade_reason"]
    assert packet["degraded"] is True
    assert reason.startswith("CANONICAL_UNAVAILABLE:")
    assert "store unreachable" in reason
    assert "unavailable" in packet["active_objective"].lower()
    ctx = comp.format_additional_context(packet)
    assert "CANONICAL_UNAVAILABLE" in ctx
    assert "status=CANONICAL_UNAVAILABLE DEGRADED" in ctx


def test_search_facts_raising_client_is_unreachable(monkeypatch):
    import types

    def _boom(*_a, **_k):
        raise ConnectionError("tunnel down")

    fake = types.ModuleType("graphiti_memory_client")
    fake.load_env = lambda: None  # type: ignore[attr-defined]
    fake.call_tool = _boom  # type: ignore[attr-defined]
    fake.resolve_read_groups = lambda group_id: [group_id]  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "graphiti_memory_client", fake)
    with pytest.raises(comp.SearchFactsError, match="tunnel down"):
        comp._search_facts("cursor-governance", "PICKUP", limit=2)


def test_compile_packet_with_pickup(monkeypatch, tmp_path):
    """A typed canonical continuation drives objective, next action, and anchors."""
    _canonical(
        monkeypatch,
        tmp_path,
        _hydration(
            "OK",
            continuation=_continuation(),
            record_ids=("66666666-6666-6666-6666-666666666666",),
            sections=(("semantic", "Realign memory control plane | next: Run unit tests"),),
        ),
    )
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-2", agent_id="cursor"
    )
    assert packet["active_objective"] == "Ship hydrate pipeline"
    assert "Run unit tests" in packet["next_action_contract"]["next_action"]
    assert "canonical continuation 66666666" in packet["next_action_contract"]["rationale"]
    assert packet["anchors"] == []
    assert packet["hydrate_stats"]["facts_returned"] == 1
    assert packet["hydrate_stats"]["pickup_parsed"] is True
    assert packet["hydrate_stats"]["continuation_source"] == "canonical"
    assert packet["hydrate_stats"]["continuation_stale"] is False
    ctx = comp.format_additional_context(packet)
    assert "next=" in ctx
    assert "facts_returned=1" in ctx
    assert "pickup_parsed=yes" in ctx
    assert "continuation: record=66666666 source=canonical" in ctx
    assert "memory-bank" not in ctx
    assert '"hydrate_stats"' in ctx


def test_compile_packet_stale_continuation_says_repository_wins(monkeypatch, tmp_path):
    _canonical(monkeypatch, tmp_path, _hydration("OK", continuation=_continuation(stale=True)))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-3", agent_id="cursor"
    )
    assert packet["hydrate_stats"]["continuation_stale"] is True
    assert "STALE" in packet["next_action_contract"]["rationale"]
    assert "current git state wins" in packet["next_action_contract"]["rationale"]
    assert " STALE" in comp.format_additional_context(packet)


def test_compile_packet_never_reads_the_legacy_provider_by_default(monkeypatch, tmp_path):
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    monkeypatch.delenv("MEMORY_LEGACY_SHADOW", raising=False)
    monkeypatch.delenv("MEMORY_LEGACY_CONTINUATION", raising=False)

    def _boom(*_a, **_k):
        raise AssertionError("legacy provider read must not run")

    monkeypatch.setattr(comp, "_search_facts", _boom)
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-4", agent_id="cursor"
    )
    assert "shadow" not in packet["memory"]


def test_legacy_continuation_is_tagged_unverified_and_only_fills_a_gap(monkeypatch, tmp_path):
    """Migration window (plan 13): the legacy read may fill a canonical gap, never replace."""
    monkeypatch.setenv("MEMORY_LEGACY_CONTINUATION", "1")
    monkeypatch.setattr(
        comp,
        "_search_facts",
        lambda *a, **k: [{"fact": "PICKUP|objective=Old objective|next=Old next|session=x"}],
    )
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-5", agent_id="cursor"
    )
    assert packet["active_objective"] == "Old objective"
    assert packet["next_action_contract"]["next_action"] == "Old next"
    assert packet["hydrate_stats"]["continuation_source"] == "legacy_unverified"
    assert packet["memory"]["shadow"]["agreement"] == "legacy_only"
    assert packet["memory"]["shadow"]["authority"] == "canonical"
    assert (tmp_path / ".l9" / "memory" / "shadow" / "sess-5.json").is_file()

    # A canonical continuation is never displaced by the legacy read.
    _canonical(monkeypatch, tmp_path, _hydration("OK", continuation=_continuation()))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-6", agent_id="cursor"
    )
    assert packet["active_objective"] == "Ship hydrate pipeline"
    assert packet["hydrate_stats"]["continuation_source"] == "canonical"
    assert packet["memory"]["shadow"]["agreement"] == "differs"


def test_extract_pickup_pipe_line():
    facts = [
        {
            "fact": (
                "PICKUP|objective=Validate hydrate close|next=Re-run sessionStart|"
                "agent=cursor|session=abc"
            )
        }
    ]
    got = comp._extract_pickup(facts)
    assert got["active_objective"] == "Validate hydrate close"
    assert got["next_action"] == "Re-run sessionStart"


def test_extract_pickup_graphiti_paraphrase():
    facts = [
        {
            "fact": (
                "The objective is to continue work in Cursor-Governance by "
                "resuming from the latest Graphiti PICKUP."
            )
        }
    ]
    got = comp._extract_pickup(facts)
    assert "Cursor-Governance" in got["active_objective"]
    assert "resuming from" in got["next_action"].lower()


# ---------------------------------------------------------------------------
# Canonical close stubs (stage C6): every close crosses the memory boundary
# ---------------------------------------------------------------------------

_BOUNDARY_FIXTURES = ROOT / "tests" / "ops" / "memory"
if str(_BOUNDARY_FIXTURES) not in sys.path:
    sys.path.insert(0, str(_BOUNDARY_FIXTURES))
from memory_boundary_fixtures import FakeMemoryCli, close_payload  # noqa: E402

from ops.memory.control_plane_client import MemoryControlPlaneClient  # noqa: E402
from ops.memory.runtime_binding import STATUS_EXACT, RuntimeBinding  # noqa: E402


def _candidate_payload(status="admitted", record_id="66666666-6666-6666-6666-666666666666"):
    return {
        "status": status,
        "candidate_id": "cursor-continuation:x",
        "namespace": "cursor-governance",
        "record_id": record_id,
        "write_receipt_id": "55555555-5555-5555-5555-555555555555",
        "storage_committed": status != "rejected",
        "memory_state": "active",
        "reason": None,
    }


def _scripted_close(monkeypatch, tmp_path):
    """Route close_session at a scripted memory CLI; return the fake for assertions."""
    fake = FakeMemoryCli()
    fake.reply("ingest-governed-candidate", 0, _candidate_payload())
    fake.reply("close", 0, close_payload())
    cli = tmp_path / "bin" / "l9-memory"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli.chmod(0o755)
    binding = RuntimeBinding(
        status=STATUS_EXACT,
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version="x",
        expected_contract_version="memory-control-plane/v1",
        manifest_path="m",
        interpreter=str(tmp_path / "bin" / "python"),
        memory_cli=str(cli),
        memory_version="x",
        contract_version="memory-control-plane/v1",
    )
    client = MemoryControlPlaneClient(binding, runner=fake.run, session_id="sess")
    monkeypatch.setattr(cs, "memory_client", lambda *a, **k: client)
    monkeypatch.setattr(cs, "resolve_namespace_context", lambda *a, **k: _context())
    monkeypatch.setattr(cs, "repository_state_digest", lambda _p: "a" * 40)
    monkeypatch.setattr(cs, "already_closed", lambda *a, **k: False)
    monkeypatch.setattr(cs, "write_receipt", lambda *a, **k: None)
    return fake


def test_phase_a_without_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("MEMORY_PHASE_B_RESOLVE_SM", "0")
    monkeypatch.delenv("MEMORY_DISTILL_S3_BUCKET", raising=False)
    fake = _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: finish the PR", "test"))
    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-1",
        reason="user_close",
        agent_id="cursor",
        dry_run=True,
    )
    assert report["phase_a"] is True
    assert report["phase_b"] is False
    assert any(w["kind"] == "session_continuation" for w in report["writes"])
    assert any("openai_key" in w for w in report["warnings"])
    assert any(args[1] == "ingest-governed-candidate" for args, _c, _s in fake.calls)


def test_phase_b_success_with_mocked_transport(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("MEMORY_DISTILL_S3_BUCKET", raising=False)
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "0")
    fake = _scripted_close(monkeypatch, tmp_path)
    fake.reply(
        "write",
        0,
        {
            "receipt_id": "88888888-8888-8888-8888-888888888888",
            "status": "admitted",
            "namespace": "cursor-governance",
            "record_id": "99999999-9999-9999-9999-999999999999",
            "admission": {"reasons": []},
        },
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: ship phase b", "test"))

    packet = {
        "packet_id": "abcdef0123456789",
        "session_id": "close-b",
        "promotion_decisions": [
            {
                "kind": "lesson",
                "body": "Use fixed-host OpenAI helper for Phase B.",
                "decision": "promote",
                "score": 0.9,
            }
        ],
        "pickup": {
            "active_objective": "Finish Phase B restore",
            "next_action": "Open PR after pr-check",
            "context_slice": "phase b",
            "blockers": [],
        },
        "do_not_promote": [],
    }
    monkeypatch.setattr(cs, "_distill_signal_packet", lambda **k: (packet, ""))
    monkeypatch.setattr(cs, "should_persist_derived_episode", lambda *a, **k: True)

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-b",
        agent_id="cursor",
        dry_run=True,
    )
    assert report["phase_a"] is True
    assert report["phase_b"] is True
    assert report["receipt"]["phase_b"] is True
    assert report.get("promoted") == 1
    assert report["continuation"]["refined"] is True


def test_enqueue_fail_loud(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMORY_PHASE_B", "0")
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "1")
    monkeypatch.setenv("MEMORY_DISTILL_S3_BUCKET", "l9-test-distill")
    _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: enqueue me", "test"))

    def boom(**kwargs):
        raise RuntimeError("s3 put-object failed: AccessDenied")

    import ops.graphiti.distill_queue.enqueue as enq

    monkeypatch.setattr(enq, "enqueue_job", boom)

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-enq",
        agent_id="cursor",
        dry_run=False,
    )
    assert report["phase_a"] is True
    assert report["enqueue_ok"] is False
    assert report["receipt"]["enqueue_ok"] is False
    assert any("enqueue failed" in w for w in report["warnings"])
    # An enqueue failure never turns a canonical close into a non-close.
    assert report["status"] == "closed_canonically"


def test_idempotent_reclose(monkeypatch, tmp_path):
    fake = _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("x", "test"))
    monkeypatch.setattr(cs, "already_closed", lambda *a, **k: True)
    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-2",
        agent_id="cursor",
        dry_run=False,
    )
    assert report["status"] == "idempotent_skip"
    assert fake.calls == []


def test_phase_a_kept_when_phase_b_would_exceed_budget(monkeypatch, tmp_path):
    """Synthetic clock: after Phase A, remaining budget < 3s -> skip B."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: hi", "test"))
    ticks = iter([0.0, 0.0, 28.5, 28.6, 28.7, 28.8, 29.0, 29.1, 29.2, 29.3, 29.4, 29.5])

    def clock():
        return next(ticks, 30.0)

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-3",
        agent_id="cursor",
        dry_run=True,
        clock=clock,
    )
    assert report["phase_a"] is True
    assert report["phase_b"] is False
    assert any("insufficient time budget" in w for w in report["warnings"])


def test_unresolved_namespace_close_is_skipped_with_warning(monkeypatch, tmp_path):
    """No write namespace hint: the close is skipped, memory is never called."""
    from ops.memory.namespace_context import NamespaceContext

    fake = _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(
        cs,
        "resolve_namespace_context",
        lambda *a, **k: NamespaceContext(
            workspace=str(tmp_path),
            git_root=None,
            repository_identity=None,
            write_namespace_hint=None,
            read_namespace_hints=("l9-workspace",),
            method="unresolved",
            warnings=("no repository match",),
        ),
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("", "none"))
    report = cs.close_session(
        project_dir=tmp_path, session_id="ro-1", agent_id="cursor", dry_run=True
    )
    assert report["status"] == "skipped"
    assert any("close blocked" in w for w in report["warnings"])
    assert fake.calls == []


def test_resolve_session_id_order(monkeypatch):
    from ops.graphiti.hydration.session_latches import resolve_session_id

    monkeypatch.delenv("CURSOR_CONVERSATION_ID", raising=False)
    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    assert resolve_session_id() == "default"
    monkeypatch.setenv("CURSOR_SESSION_ID", "sess-env")
    assert resolve_session_id() == "sess-env"
    monkeypatch.setenv("CURSOR_CONVERSATION_ID", "conv-env")
    assert resolve_session_id() == "conv-env"
    assert resolve_session_id(explicit="explicit-1") == "explicit-1"


def test_orchestrator_opens_latch_before_graphiti_enabled() -> None:
    text = (ROOT / "ops" / "hooks" / "session_start_memory_orchestrator.sh").read_text(
        encoding="utf-8"
    )
    assert text.index("cli open") < text.index("if graphiti_enabled")
    assert text.index("if graphiti_enabled") < text.index("cli compile")


def test_background_open_does_not_rotate_last_opened(tmp_path):
    from ops.graphiti.hydration.session_latches import (
        read_last_opened,
        write_open_latch,
    )

    write_open_latch(tmp_path, "parent-sess", background=False)
    parent = read_last_opened(tmp_path)
    assert parent and parent["session_id"] == "parent-sess"
    write_open_latch(tmp_path, "bg-sess", background=True)
    assert read_last_opened(tmp_path)["session_id"] == "parent-sess"


def test_compile_close_gap_missing_receipt(monkeypatch, tmp_path):
    from ops.graphiti.hydration.session_latches import write_open_latch

    write_open_latch(tmp_path, "old-sess", background=False)
    write_open_latch(tmp_path, "new-sess", background=False)
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="new-sess", agent_id="cursor"
    )
    assert packet["degraded"] is True
    assert packet["close_gap"] is True
    ctx = comp.format_additional_context(packet)
    assert ctx.startswith("DEGRADED")
    assert "REPAIR: /end-session" in ctx


def test_compile_close_gap_write_count_zero(monkeypatch, tmp_path):
    from ops.graphiti.hydration.session_latches import write_open_latch, write_receipt

    write_open_latch(tmp_path, "old-zero", background=False)
    write_receipt(
        tmp_path,
        "old-zero",
        {"status": "close_failed", "write_count": 0, "phase_a": False},
    )
    write_open_latch(tmp_path, "new-zero", background=False)
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="new-zero", agent_id="cursor"
    )
    assert packet["close_gap"] is True
    assert comp.format_additional_context(packet).startswith("DEGRADED")


def test_compile_enqueue_failed_is_not_close_gap(monkeypatch, tmp_path):
    from ops.graphiti.hydration.session_latches import write_open_latch, write_receipt

    write_open_latch(tmp_path, "old-enq", background=False)
    write_receipt(
        tmp_path,
        "old-enq",
        {"status": "closed_enqueue_failed", "write_count": 2, "phase_a": True},
    )
    write_open_latch(tmp_path, "new-enq", background=False)
    _canonical(monkeypatch, tmp_path, _hydration("OK", continuation=_continuation()))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="new-enq", agent_id="cursor"
    )
    assert packet["close_gap"] is False
    ctx = comp.format_additional_context(packet)
    assert not ctx.startswith("DEGRADED")


def test_compile_first_session_no_receipt_gap(monkeypatch, tmp_path):
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="first", agent_id="cursor"
    )
    assert packet.get("close_gap") is False
    assert packet["hydrate_stats"]["degrade_reason"] == ""
    assert packet["hydrate_stats"]["memory_status"] == "NO_HITS"
    assert not comp.format_additional_context(packet).startswith("DEGRADED")


def test_retry_close_discharges_an_open_obligation(monkeypatch, tmp_path):
    """The hook's fallback is now a canonical close retry under the recorded key."""
    from ops.graphiti.hydration import pickup_write as pw
    from ops.graphiti.hydration.session_latches import load_close_receipt, write_receipt

    write_receipt(
        tmp_path,
        "fb-1",
        {
            "status": "close_incomplete",
            "write_count": 1,
            "canonical_namespace_requested": "cursor-governance",
            "close_idempotency_key": "cursor-close:cursor-governance:fb-1:abc",
            "payload_digest": "d" * 64,
            "continuation_status": "admitted",
            "continuation_reference": "66666666-6666-6666-6666-666666666666",
        },
    )
    fake = _scripted_close(monkeypatch, tmp_path)
    client = cs.memory_client("fb-1")
    report = pw.retry_close(project_dir=tmp_path, session_id="fb-1", client=client)
    assert report["status"] == "closed_canonically"
    assert report["write_count"] == 1
    receipt = load_close_receipt(tmp_path, "fb-1")
    assert receipt and receipt["status"] == "closed_canonically"
    close_argv = fake.last("close")
    assert close_argv[close_argv.index("--idempotency-key") + 1] == (
        "cursor-close:cursor-governance:fb-1:abc"
    )


def test_repair_skips_when_already_closed(monkeypatch, tmp_path):
    from ops.graphiti.hydration.pickup_write import repair_close
    from ops.graphiti.hydration.session_latches import write_receipt

    write_receipt(
        tmp_path,
        "rep-1",
        {
            "status": "closed_canonically",
            "write_count": 2,
            "phase_a": True,
            "canonical_operation_id": "44444444-4444-4444-4444-444444444444",
        },
    )
    report = repair_close(
        project_dir=tmp_path,
        session_id="rep-1",
        objective="done",
        next_action="nothing",
        agent_id="cursor",
    )
    assert report["status"] == "skipped_already_closed"
    assert report["written"] is False


def test_unresolved_namespace_close_writes_fail_receipt(monkeypatch, tmp_path):
    from ops.memory.namespace_context import NamespaceContext

    unresolved = NamespaceContext(
        workspace=str(tmp_path),
        git_root=None,
        repository_identity=None,
        write_namespace_hint=None,
        read_namespace_hints=("l9-workspace",),
        method="unresolved",
        warnings=("no repository match",),
    )
    monkeypatch.setattr(cs, "resolve_namespace_context", lambda *a, **k: unresolved)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("", "none"))
    report = cs.close_session(
        project_dir=tmp_path, session_id="ro-receipt", agent_id="cursor", dry_run=False
    )
    from ops.graphiti.hydration.session_latches import load_close_receipt

    receipt = load_close_receipt(tmp_path, "ro-receipt")
    assert report["status"] == "skipped"
    assert receipt is not None
    assert receipt["status"] == "close_failed"
    assert int(receipt["write_count"]) == 0


def test_adr_0028_required_sections():
    path = ROOT / "docs" / "decisions" / "ADR-0028-session-hydrate-close-visibility.md"
    text = path.read_text(encoding="utf-8")
    for heading in (
        "## Status",
        "## Date",
        "## Context",
        "## Options Considered",
        "## Decision",
        "## Consequences",
        "## Related",
    ):
        assert heading in text
    assert "ADR-0005" in text
    assert "ADR-0006" in text
    assert "Does not supersede" in text or "does not supersede" in text.lower()
    assert "Option A" in text
    assert "Option F" in text
    assert "hydration.cli close" in text
    assert "memory-bank" in text


# --- close_session budget parameter -----------------------------------------
# TOTAL_BUDGET is a PER-CALL ceiling. A caller that closes several repositories
# inside one hook window (memory_writeback.py on a multi-repo container) must
# divide its own allowance between them: six calls at the 30 s default overrun a
# Stop hook by an order of magnitude, and the hook is killed mid-write with no
# record of how far it got.


def _close_with_budget(monkeypatch, tmp_path, budget):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("MEMORY_PHASE_B", "1")
    monkeypatch.delenv("MEMORY_DISTILL_S3_BUCKET", raising=False)
    _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: ship it", "test"))
    monkeypatch.setattr(cs, "_distill_signal_packet", lambda **k: (None, "stubbed"))
    return cs.close_session(
        project_dir=tmp_path,
        session_id="budget-1",
        reason="user_close",
        agent_id="cursor",
        dry_run=True,
        budget=budget,
    )


def test_small_budget_starves_phase_b_but_keeps_phase_a(monkeypatch, tmp_path):
    """Phase A (the PICKUP write) survives a starved budget; only Phase B yields."""
    report = _close_with_budget(monkeypatch, tmp_path, budget=2.0)
    assert report["phase_a"] is True, "the PICKUP write must not be sacrificed to the budget"
    assert any("insufficient time budget" in w for w in report["warnings"])


def test_default_budget_is_unchanged_when_not_passed(monkeypatch, tmp_path):
    """budget=None keeps TOTAL_BUDGET, so every existing single-repo caller is untouched."""
    report = _close_with_budget(monkeypatch, tmp_path, budget=None)
    assert report["phase_a"] is True
    assert not any("insufficient time budget" in w for w in report["warnings"])


def test_budget_is_accepted_as_a_keyword(monkeypatch, tmp_path):
    import inspect

    params = inspect.signature(cs.close_session).parameters
    assert "budget" in params
    assert params["budget"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["budget"].default is None
