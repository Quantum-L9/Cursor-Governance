"""Unit tests for hydrate/close pipeline (no live Graphiti required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GRAPHITI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GRAPHITI))

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
        calls=4,
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
    assert packet["hydrate_stats"]["search_queries_used"] == 4
    assert packet["memory"]["transport"] == "cli"
    ctx = comp.format_additional_context(packet)
    assert ctx.startswith("### memory hydrate")
    assert "next=" in ctx
    assert "facts_returned=" in ctx
    assert "status=NO_HITS" in ctx
    assert "memory-bank" not in ctx
    assert "hydrate_stats" in ctx
    assert (tmp_path / "state").is_dir()
    receipts = tmp_path / ".l9" / "memory" / "receipts"
    assert not receipts.exists() or not any(receipts.glob("*.json"))


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


# ---------------------------------------------------------------------------
# Canonical close stubs (stage C6): every close crosses the memory boundary
# ---------------------------------------------------------------------------

_BOUNDARY_FIXTURES = ROOT / "tests" / "ops" / "memory"
if str(_BOUNDARY_FIXTURES) not in sys.path:
    sys.path.insert(0, str(_BOUNDARY_FIXTURES))
from memory_boundary_fixtures import FakeMemoryCli, close_payload, distill_payload  # noqa: E402

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
    fake.reply("distill", 0, distill_payload())
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


def test_phase_a_needs_no_provider_key(monkeypatch, tmp_path):
    """The close never touches a provider: no OpenAI key, no provider warning (ADR-0033)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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
    assert "phase_b" not in report
    assert "phase_b" not in report["receipt"]
    assert any(w["kind"] == "session_continuation" for w in report["writes"])
    assert not any("openai" in w.lower() for w in report["warnings"])
    assert any(args[1] == "ingest-governed-candidate" for args, _c, _s in fake.calls)


def test_close_session_has_no_local_cognition_surface():
    """Phase B (local distill / promote / scoring) is gone; memory owns cognition."""
    for name in (
        "_distill_signal_packet",
        "_promote",
        "_load_rules",
        "_phase_b_enabled",
        "PHASE_B_BUDGET",
        "_PROMOTION_CLASSES",
    ):
        assert not hasattr(cs, name), f"{name} is Cursor-local memory cognition (ADR-0033)"


def test_close_has_no_s3_queue_surface(monkeypatch, tmp_path):
    """The S3 distill queue is retired at C15: no enqueue fields, no exit-2 path (ADR-0033)."""
    _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: enqueue me", "test"))
    report = cs.close_session(
        project_dir=tmp_path, session_id="close-enq", agent_id="cursor", dry_run=False
    )
    assert report["status"] == "closed_canonically"
    assert "enqueue_ok" not in report
    assert "enqueue_ok" not in report["receipt"]
    assert not any("enqueue" in w for w in report["warnings"])
    from ops.graphiti.hydration.cli import _public_close_report

    public = _public_close_report(report)
    assert "enqueue_ok" not in public
    assert public["distill_status"] == report["distill"]["status"]


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


def test_over_budget_close_is_reported_not_failed(monkeypatch, tmp_path):
    """Synthetic clock: a slow close still commits Phase A and names the overrun."""
    _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: hi", "test"))
    # start -> after Phase A -> final elapsed
    ticks = iter([0.0, 28.5, 31.0])

    def clock():
        return next(ticks, 31.0)

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-3",
        agent_id="cursor",
        dry_run=True,
        clock=clock,
    )
    assert report["phase_a"] is True
    assert any("Phase A over budget" in w for w in report["warnings"])
    assert any("close over budget" in w for w in report["warnings"])


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
    monkeypatch.delenv("L9_HOOK_PAYLOAD", raising=False)
    assert resolve_session_id() == "default"
    monkeypatch.setenv("CURSOR_SESSION_ID", "sess-env")
    assert resolve_session_id() == "sess-env"
    monkeypatch.setenv("CURSOR_CONVERSATION_ID", "conv-env")
    assert resolve_session_id() == "sess-env"
    assert resolve_session_id(explicit="explicit-1") == "explicit-1"


def test_resolve_session_id_ignores_conversation_id_payload(monkeypatch):
    from ops.graphiti.hydration.session_latches import resolve_session_id

    monkeypatch.delenv("CURSOR_CONVERSATION_ID", raising=False)
    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    monkeypatch.setenv(
        "L9_HOOK_PAYLOAD",
        json.dumps({"conversation_id": "aab87627-ee20-4502-89f2-ecc73082b566"}),
    )
    assert resolve_session_id(explicit="default") == "default"
    monkeypatch.setenv("L9_HOOK_PAYLOAD", json.dumps({"session_id": "sess-from-payload"}))
    assert resolve_session_id(explicit="default") == "sess-from-payload"


def test_compile_does_not_stamp_write_gate_receipt(monkeypatch, tmp_path):
    """SessionStart writes session state only. Prefetch owns the write-gate receipt."""
    _canonical(monkeypatch, tmp_path, _hydration("OK"))
    monkeypatch.delenv("CURSOR_CONVERSATION_ID", raising=False)
    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    monkeypatch.setenv(
        "L9_HOOK_PAYLOAD",
        json.dumps({"session_id": "sess-once", "conversation_id": "chat-later"}),
    )
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="default", agent_id="cursor"
    )
    assert packet["conversation_id"] == "sess-once"
    receipts = tmp_path / ".l9" / "memory" / "receipts"
    assert not receipts.exists() or not any(receipts.glob("*.json"))


def test_orchestrator_reads_hook_payload_before_defaulting() -> None:
    text = (ROOT / "ops" / "hooks" / "session_start_memory_orchestrator.sh").read_text(
        encoding="utf-8"
    )
    assert "L9_HOOK_PAYLOAD" in text
    assert 'CURSOR_SESSION_ID="${CURSOR_SESSION_ID:-default}"' in text
    assert (
        'CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-${CURSOR_SESSION_ID:-default}}"'
        not in text
    )
    assert '--session-id "$CURSOR_SESSION_ID"' in text
    assert '--session-id "$CURSOR_CONVERSATION_ID"' not in text


def test_orchestrator_opens_latch_before_graphiti_enabled() -> None:
    text = (ROOT / "ops" / "hooks" / "session_start_memory_orchestrator.sh").read_text(
        encoding="utf-8"
    )
    assert text.index("cli open") < text.index("if graphiti_enabled")
    assert text.index("if graphiti_enabled") < text.index("cli compile")


def test_orchestrator_resolves_one_lifecycle_id_before_open() -> None:
    """Audit P573-F2: the id handed to `cli open` is the id `cli compile` gets.

    A conversation-only payload used to open ``opens/default.json`` while the
    compiler generated a UUID for itself; now the orchestrator resolves once
    (SessionStart mode: ``rotate=True``) before either call.
    """
    text = (ROOT / "ops" / "hooks" / "session_start_memory_orchestrator.sh").read_text(
        encoding="utf-8"
    )
    assert "resolve_or_create_session_id" in text
    assert "rotate=True" in text
    assert text.index("resolve_or_create_session_id") < text.index("cli open")
    assert text.count('--session-id "$CURSOR_SESSION_ID"') == 2
    # Copilot: the payload parsers name the failures they tolerate.
    assert "except Exception" not in text
    assert text.count("except (json.JSONDecodeError, TypeError)") == 2


def test_conversation_only_payload_yields_one_lifecycle_id_and_rotates(monkeypatch, tmp_path):
    """Audit P573-F2 regression: open, compile and the pointer share ONE id.

    Two SessionStarts with the documented conversation-only payload and no
    close in between must (1) never fall back to ``default``, (2) rotate
    ``previous_opened.json``, and (3) surface the missed close as a close-gap.
    """
    from ops.graphiti.hydration.session_latches import (
        persisted_session_id,
        read_last_opened,
        read_previous_opened,
        resolve_or_create_session_id,
        write_open_latch,
    )

    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    monkeypatch.setenv("L9_HOOK_PAYLOAD", json.dumps({"conversation_id": "conv-1"}))
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))

    first = resolve_or_create_session_id(
        tmp_path, explicit="default", rotate=True, conversation_id="conv-1"
    )
    assert first not in {"", "default", "conv-1"}
    assert persisted_session_id(tmp_path) == first
    pointer = json.loads((tmp_path / ".l9" / "memory" / "session.json").read_text())
    assert pointer["conversation_id"] == "conv-1"
    write_open_latch(tmp_path, first)
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id=first, agent_id="cursor"
    )
    assert packet["conversation_id"] == first
    assert read_last_opened(tmp_path)["session_id"] == first
    assert packet["close_gap"] is False
    assert not any(w.startswith("session id not persisted") for w in packet["warnings"])

    second = resolve_or_create_session_id(
        tmp_path, explicit="default", rotate=True, conversation_id="conv-1"
    )
    assert second not in {"", "default", first}
    assert persisted_session_id(tmp_path) == second
    write_open_latch(tmp_path, second)
    assert read_previous_opened(tmp_path)["session_id"] == first
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id=second, agent_id="cursor"
    )
    assert packet["conversation_id"] == second
    assert packet["close_gap"] is True
    assert first in packet["close_gap_reason"]
    assert packet["degraded"] is False
    assert packet["hydrate_stats"]["degrade_reason"] == ""
    assert comp.format_additional_context(packet).startswith("CLOSE_GAP\nREPAIR: /end-session")


def test_lifecycle_id_reuses_pointer_unless_rotating(monkeypatch, tmp_path):
    from ops.graphiti.hydration.session_latches import (
        persisted_session_id,
        resolve_or_create_session_id,
        resolve_session_lifecycle,
    )

    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    monkeypatch.delenv("L9_HOOK_PAYLOAD", raising=False)
    first = resolve_or_create_session_id(tmp_path, explicit="default", rotate=True)
    # Later callers in the same session (compile, prefetch) reuse the pointer.
    assert resolve_or_create_session_id(tmp_path, explicit="default") == first
    assert resolve_session_lifecycle(tmp_path, explicit=None) == (first, "")
    # A real id always wins and never touches the pointer.
    assert resolve_session_lifecycle(tmp_path, explicit="real-1", rotate=True) == ("real-1", "")
    assert persisted_session_id(tmp_path) == first


@pytest.mark.parametrize("fault", ["mkdir", "write", "readonly"])
def test_lifecycle_id_persistence_faults_are_fail_open(monkeypatch, tmp_path, fault):
    """Audit P573-F3: persistence faults return a usable id; compile never raises."""
    from ops.graphiti.hydration import session_latches as latches

    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    monkeypatch.delenv("L9_HOOK_PAYLOAD", raising=False)
    memory_dir = tmp_path / ".l9" / "memory"
    if fault == "mkdir":
        memory_dir.parent.mkdir(parents=True)
        memory_dir.write_text("not a directory\n", encoding="utf-8")
        expected = {"FileExistsError", "NotADirectoryError"}
    elif fault == "write":
        (memory_dir / "session.json").mkdir(parents=True)
        expected = {"IsADirectoryError"}
    else:
        memory_dir.mkdir(parents=True)
        original = Path.write_text

        def read_only(self, *args, **kwargs):
            if self.name == "session.json":
                raise PermissionError(13, "Permission denied", str(self))
            return original(self, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", read_only)
        expected = {"PermissionError"}

    session_id, error = latches.resolve_session_lifecycle(tmp_path, explicit="default", rotate=True)
    assert session_id not in {"", "default"}
    assert error in expected
    assert latches.resolve_or_create_session_id(tmp_path, explicit="default") not in {"", "default"}

    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="default", agent_id="cursor"
    )
    assert packet["conversation_id"] not in {"", "default"}
    assert any(w == f"session id not persisted: {error}" for w in packet["warnings"])
    assert packet["degraded"] is False


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
    # ADR-0032: the prior session not closing is a lifecycle gap; canonical
    # memory answered NO_HITS cleanly, so nothing about memory is degraded.
    assert packet["degraded"] is False
    assert packet["memory_degraded"] is False
    assert packet["environment_fault"] is False
    assert packet["close_gap"] is True
    assert packet["close_gap_reason"]
    assert packet["hydrate_stats"]["close_gap_reason"] == packet["close_gap_reason"]
    assert packet["hydrate_stats"]["degrade_reason"] == ""
    assert packet["next_action_contract"]["next_action"] == "/end-session"
    ctx = comp.format_additional_context(packet)
    assert ctx.startswith("CLOSE_GAP\nREPAIR: /end-session\n### memory hydrate")
    assert "DEGRADED" not in ctx.split("```")[0]
    assert "status=NO_HITS CLOSE_GAP" in ctx
    assert "close-gap: " in ctx


def test_compile_environment_fault_is_typed_and_leads(monkeypatch, tmp_path):
    """An unbound runtime never reached memory: ENVIRONMENT_FAULT, not DEGRADED."""
    hydration = hyd.CanonicalHydration(
        status="BINDING_FAILED",
        namespace_context=_context(),
        requested_namespaces=("cursor-governance",),
        repository_state_digest="a" * 40,
        task_signature="sig",
        error="package version 2.3.1 does not match expected 2.4.0",
        environment_heal="skipped:repo-write-lock-held",
    )
    _canonical(monkeypatch, tmp_path, hydration)
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="env-fault", agent_id="cursor"
    )
    assert packet["environment_fault"] is True
    assert packet["memory_degraded"] is False
    assert packet["degraded"] is False
    assert packet["close_gap"] is False
    stats = packet["hydrate_stats"]
    assert stats["fault_class"] == "environment"
    assert stats["environment_heal"] == "skipped:repo-write-lock-held"
    assert "2.3.1" in stats["environment_fault_reason"]
    assert "heal=skipped:repo-write-lock-held" in stats["environment_fault_reason"]
    assert stats["degrade_reason"] == ""
    assert "environment fault" in packet["active_objective"]
    ctx = comp.format_additional_context(packet)
    assert ctx.startswith(
        "ENVIRONMENT_FAULT\nREPAIR: make -C ~/.cursor-governance memory-readiness"
    )
    assert "status=BINDING_FAILED ENVIRONMENT_FAULT" in ctx
    assert "environment fault: BINDING_FAILED:" in ctx
    assert "hydration degraded" not in ctx
    fence = json.loads(ctx.split("```json\n")[1].split("\n```")[0])
    assert fence["environment_fault"] is True
    assert fence["memory_degraded"] is False
    assert fence["degraded"] is False


def test_compile_mixed_conditions_lead_by_class(monkeypatch, tmp_path):
    """Environment fault + close-gap together: both typed, neither is DEGRADED."""
    from ops.graphiti.hydration.session_latches import write_open_latch

    write_open_latch(tmp_path, "old-mixed", background=False)
    write_open_latch(tmp_path, "new-mixed", background=False)
    hydration = hyd.CanonicalHydration(
        status="BINDING_FAILED",
        namespace_context=_context(),
        requested_namespaces=("cursor-governance",),
        repository_state_digest="a" * 40,
        task_signature="sig",
        error="not importable",
    )
    _canonical(monkeypatch, tmp_path, hydration)
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="new-mixed", agent_id="cursor"
    )
    assert packet["environment_fault"] is True
    assert packet["close_gap"] is True
    assert packet["memory_degraded"] is False
    assert packet["degraded"] is False
    ctx = comp.format_additional_context(packet)
    lead = ctx.split("### memory hydrate")[0].splitlines()
    assert lead == [
        "ENVIRONMENT_FAULT",
        "REPAIR: make -C ~/.cursor-governance memory-readiness",
        "CLOSE_GAP",
        "REPAIR: /end-session",
    ]
    assert "status=BINDING_FAILED ENVIRONMENT_FAULT CLOSE_GAP" in ctx


def _validate_packet_schema(packet) -> None:
    import jsonschema
    import yaml

    schema = yaml.safe_load(
        (GRAPHITI / "hydration" / "session_hydration_packet.schema.yaml").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator(schema).validate(packet)


def test_compiled_packets_validate_against_the_declared_schema(monkeypatch, tmp_path):
    """The schema is additionalProperties:false — every typed field must be declared."""
    from ops.graphiti.hydration.session_latches import write_open_latch

    write_open_latch(tmp_path, "old-schema", background=False)
    write_open_latch(tmp_path, "new-schema", background=False)
    cases = [
        _hydration("NO_HITS"),
        _hydration("OK", continuation=_continuation(stale=True)),
        _hydration("CANONICAL_UNAVAILABLE", error="store unreachable"),
        hyd.CanonicalHydration(
            status="BINDING_FAILED",
            namespace_context=_context(),
            requested_namespaces=("cursor-governance",),
            repository_state_digest="a" * 40,
            task_signature="sig",
            error="not importable",
            environment_heal="failed",
        ),
    ]
    for hydration in cases:
        _canonical(monkeypatch, tmp_path, hydration)
        packet = comp.compile_session_packet(
            project_dir=tmp_path, conversation_id="new-schema", agent_id="cursor"
        )
        assert packet["close_gap"] is True
        _validate_packet_schema(packet)


def test_compile_canonical_degradation_still_leads_degraded(monkeypatch, tmp_path):
    _canonical(monkeypatch, tmp_path, _hydration("TIMEOUT", error="memory.hydrate exceeded 20s"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="slow", agent_id="cursor"
    )
    assert packet["memory_degraded"] is True
    assert packet["degraded"] is True
    assert packet["environment_fault"] is False
    assert packet["hydrate_stats"]["fault_class"] == "canonical"
    ctx = comp.format_additional_context(packet)
    assert ctx.startswith("DEGRADED\n### memory hydrate")
    assert "hydration degraded: TIMEOUT: memory.hydrate exceeded 20s" in ctx


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
    assert packet["degraded"] is False
    assert comp.format_additional_context(packet).startswith("CLOSE_GAP\nREPAIR: /end-session")


def test_compile_legacy_enqueue_failed_receipt_still_parses_as_a_close(monkeypatch, tmp_path):
    """closed_enqueue_failed is parse-only since C15: old receipts stay closes, none is written."""
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
    assert ctx.startswith("### memory hydrate")


def test_compile_first_session_no_receipt_gap(monkeypatch, tmp_path):
    _canonical(monkeypatch, tmp_path, _hydration("NO_HITS"))
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="first", agent_id="cursor"
    )
    assert packet.get("close_gap") is False
    assert packet["close_gap_reason"] == ""
    assert packet["hydrate_stats"]["degrade_reason"] == ""
    assert packet["hydrate_stats"]["memory_status"] == "NO_HITS"
    assert comp.format_additional_context(packet).startswith("### memory hydrate")


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
            # The exact close request the interrupted attempt recorded
            # (audit P2-01): the retry replays this, never a synthesized summary.
            "close_summary": "session fb-1 completed: objective | next: step",
            "close_capsule_digest": "d" * 64,
            "close_session_id": "fb-1",
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
    assert close_argv[close_argv.index("--summary") + 1] == (
        "session fb-1 completed: objective | next: step"
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


def _close_with_budget(monkeypatch, tmp_path, budget, *, clock=None):
    _scripted_close(monkeypatch, tmp_path)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: ship it", "test"))
    return cs.close_session(
        project_dir=tmp_path,
        session_id="budget-1",
        reason="user_close",
        agent_id="cursor",
        dry_run=True,
        budget=budget,
        clock=clock,
    )


def test_small_budget_keeps_phase_a_and_names_the_overrun(monkeypatch, tmp_path):
    """Phase A (the continuation write) survives a starved budget; the overrun is reported."""
    ticks = iter([0.0, 1.0, 2.5])
    report = _close_with_budget(monkeypatch, tmp_path, budget=2.0, clock=lambda: next(ticks, 2.5))
    assert report["phase_a"] is True, "the continuation write must not be sacrificed to the budget"
    assert any("close over budget" in w for w in report["warnings"])


def test_default_budget_is_unchanged_when_not_passed(monkeypatch, tmp_path):
    """budget=None keeps TOTAL_BUDGET, so every existing single-repo caller is untouched."""
    report = _close_with_budget(monkeypatch, tmp_path, budget=None)
    assert report["phase_a"] is True
    assert not any("over budget" in w for w in report["warnings"])


def test_budget_is_accepted_as_a_keyword(monkeypatch, tmp_path):
    import inspect

    params = inspect.signature(cs.close_session).parameters
    assert "budget" in params
    assert params["budget"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["budget"].default is None
