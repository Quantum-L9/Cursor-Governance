"""Canonical session close (plan §34 "Close tests", "Write tests"; attacks F/G/H)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from memory_boundary_fixtures import FakeMemoryCli, close_payload, error_stderr

from ops.graphiti.hydration import close_session as cs
from ops.graphiti.hydration import compile_session_packet as comp
from ops.graphiti.hydration import pickup_write as pw
from ops.graphiti.hydration.session_latches import (
    STATUS_CLOSE_INCOMPLETE,
    STATUS_CLOSED_CANONICALLY,
    load_close_receipt,
    write_open_latch,
)
from ops.memory.control_plane_client import MemoryControlPlaneClient
from ops.memory.namespace_context import NamespaceContext

RECORD = "66666666-6666-6666-6666-666666666666"


REFINED = "99999999-9999-9999-9999-999999999999"


def candidate_payload(
    *,
    status: str = "admitted",
    record_id: str | None = RECORD,
    superseded: tuple[str, ...] = (),
    reason: str | None = None,
) -> dict:
    return {
        "status": status,
        "candidate_id": "cursor-continuation:x",
        "namespace": "cursor-governance",
        "record_id": record_id,
        "write_receipt_id": "55555555-5555-5555-5555-555555555555",
        "storage_committed": status != "rejected",
        "memory_state": "active" if status in {"admitted", "duplicate"} else status,
        "reason": reason
        if reason is not None
        else (None if status in {"admitted", "duplicate"} else f"admission {status}"),
        "superseded_record_ids": list(superseded),
    }


PHASE_B_PACKET = {
    "packet_id": "abcdef0123456789",
    "session_id": "sess",
    "promotion_decisions": [
        {
            "kind": "lesson",
            "body": "Use the bound CLI, never PATH.",
            "decision": "promote",
            "score": 0.9,
        },
        {
            "kind": "decision",
            "body": "Close is idempotent by key.",
            "decision": "promote",
            "score": 0.8,
        },
        {"kind": "insight", "body": "low", "decision": "promote", "score": 0.1},
    ],
    "pickup": {
        "active_objective": "Finish close cutover",
        "next_action": "Open the PR",
        "context_slice": "",
        "blockers": [],
    },
    "do_not_promote": [],
}


def _enable_phase_b(monkeypatch: pytest.MonkeyPatch, packet: dict = PHASE_B_PACKET) -> None:
    monkeypatch.setenv("MEMORY_PHASE_B", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(cs, "_distill_signal_packet", lambda **_k: (packet, ""))
    monkeypatch.setattr(cs, "should_persist_derived_episode", lambda *_a, **_k: True)


def _ingest_calls(fake_cli: FakeMemoryCli) -> list[dict]:
    return [
        json.loads(stdin)
        for argv, _cwd, stdin in fake_cli.calls
        if argv[1] == "ingest-governed-candidate" and stdin
    ]


def _close_summary(fake_cli: FakeMemoryCli, call: list[str] | None = None) -> str:
    argv = call or fake_cli.last("close")
    return argv[argv.index("--summary") + 1]


def write_payload(*, status: str = "admitted", record_id: str | None = RECORD) -> dict:
    return {
        "receipt_id": "88888888-8888-8888-8888-888888888888",
        "status": status,
        "namespace": "cursor-governance",
        "record_id": record_id,
        "idempotency_key": "k",
        "admission": {"reasons": ["candidate satisfies admission policy"]},
        "warnings": [],
    }


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project = tmp_path / "Cursor-Governance"
    project.mkdir()
    context = NamespaceContext(
        workspace=str(project),
        git_root=str(project),
        repository_identity="Quantum-L9/Cursor-Governance",
        write_namespace_hint="cursor-governance",
        read_namespace_hints=("cursor-governance", "l9-workspace"),
        method="registry",
    )
    for module in (cs, pw):
        monkeypatch.setattr(module, "resolve_namespace_context", lambda *_a, **_k: context)
        monkeypatch.setattr(module, "repository_state_digest", lambda _p: "c" * 40)
    monkeypatch.setattr(pw, "resolve_namespace_context", lambda *_a, **_k: context, raising=False)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **_k: ("user: ship the PR", "test"))
    monkeypatch.setenv("MEMORY_PHASE_B", "0")
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "0")
    monkeypatch.setenv("L9_MEMORY_SESSION_STATE_DIR", str(tmp_path / "state"))
    return project


@pytest.fixture
def scripted(fake_cli: FakeMemoryCli, bound, monkeypatch: pytest.MonkeyPatch):
    """A canonical client over the scripted CLI, injected into every close path."""
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run, session_id="sess")
    monkeypatch.setattr(cs, "memory_client", lambda *_a, **_k: client)
    fake_cli.reply("ingest-governed-candidate", 0, candidate_payload())
    fake_cli.reply("close", 0, close_payload())
    return client


def _close(project: Path, session_id: str = "sess", **kwargs: Any) -> dict:
    return cs.close_session(project_dir=project, session_id=session_id, agent_id="cursor", **kwargs)


# ---------------------------------------------------------------------------
# Normal close
# ---------------------------------------------------------------------------


def test_normal_close_admits_capsule_then_closes_canonically(workspace, scripted, fake_cli) -> None:
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["phase_a"] is True
    assert report["continuation"]["status"] == "admitted"
    assert report["continuation"]["record_id"] == RECORD
    assert report["close"]["status"] == "OK" and report["close"]["replayed"] is False
    assert [w["kind"] for w in report["writes"]] == ["session_continuation", "close"]
    # The candidate crossed the boundary as the governed envelope, on stdin.
    argv, _cwd, stdin = next(c for c in fake_cli.calls if c[0][1] == "ingest-governed-candidate")
    candidate = json.loads(stdin)
    assert candidate["knowledge"]["primary_class"] == "session_continuation"
    assert candidate["knowledge"]["structured_payload"]["schema"] == "cursor.continuation/v2"
    assert candidate["source"]["namespace"] == "cursor-governance"
    close_argv = fake_cli.last("close")
    assert "--idempotency-key" in close_argv and "--capsule-digest" in close_argv
    assert close_argv[close_argv.index("--idempotency-key") + 1].startswith(
        "cursor-close:cursor-governance:sess:"
    )
    # Local obligation is CLOSED_CANONICALLY only because a CloseReceipt was validated.
    receipt = load_close_receipt(workspace, "sess")
    assert receipt["status"] == STATUS_CLOSED_CANONICALLY
    assert receipt["canonical_operation_id"] == "44444444-4444-4444-4444-444444444444"
    assert receipt["continuation_reference"] == RECORD
    assert receipt["authority"] == "none"
    assert receipt["write_count"] == 2
    # No provider vocabulary anywhere near the boundary.
    assert "add_memory" not in json.dumps([c[0] for c in fake_cli.calls])


def test_public_close_report_is_scalar_and_names_statuses(workspace, scripted) -> None:
    from ops.graphiti.hydration.cli import _public_close_report

    public = _public_close_report(_close(workspace))
    assert public["status"] == STATUS_CLOSED_CANONICALLY
    assert public["continuation_status"] == "admitted"
    assert public["close_status"] == "OK"
    assert public["write_count"] == 2


# ---------------------------------------------------------------------------
# Duplicate close (attack F): exactly one logical close
# ---------------------------------------------------------------------------


def test_second_session_end_is_an_idempotent_skip_locally(workspace, scripted, fake_cli) -> None:
    first = _close(workspace)
    assert first["status"] == STATUS_CLOSED_CANONICALLY
    calls_after_first = len(fake_cli.calls)
    second = _close(workspace)
    assert second["status"] == "idempotent_skip"
    assert len(fake_cli.calls) == calls_after_first


def test_replayed_close_is_reported_as_one_logical_close(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 0, close_payload(replayed=True))
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["close"]["replayed"] is True


# ---------------------------------------------------------------------------
# Continuation verdicts stay visible; the close is never falsified
# ---------------------------------------------------------------------------


def test_rejected_continuation_still_closes_with_visible_status(
    workspace, scripted, fake_cli
) -> None:
    fake_cli.reply(
        "ingest-governed-candidate", 7, candidate_payload(status="rejected", record_id=None)
    )
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["phase_a"] is False
    assert report["continuation"] == {
        "status": "rejected",
        "record_id": None,
        "capsule_digest": report["continuation"]["capsule_digest"],
        "session_id": "sess",
        "task_signature": report["continuation"]["task_signature"],
    }
    receipt = load_close_receipt(workspace, "sess")
    assert receipt["continuation_status"] == "rejected"
    assert receipt["continuation_reference"] is None


def test_quarantined_continuation_is_visible(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("ingest-governed-candidate", 0, candidate_payload(status="quarantined"))
    report = _close(workspace)
    assert report["continuation"]["status"] == "quarantined"
    assert any("quarantined" in w for w in report["warnings"])
    assert report["status"] == STATUS_CLOSED_CANONICALLY


# ---------------------------------------------------------------------------
# Close failure and interruption (attacks G/H)
# ---------------------------------------------------------------------------


def test_canonical_store_failure_leaves_close_incomplete(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "database is locked"))
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSE_INCOMPLETE
    receipt = load_close_receipt(workspace, "sess")
    assert receipt["status"] == STATUS_CLOSE_INCOMPLETE
    assert receipt["failure_class"] == "CANONICAL_UNAVAILABLE"
    assert receipt["continuation_reference"] == RECORD
    assert receipt["close_idempotency_key"].startswith("cursor-close:")


def test_zero_exit_without_committed_receipt_is_not_a_close(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 0, close_payload(status="partial", record_id=None))
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSE_INCOMPLETE
    assert report["close"]["status"] == "INVALID_RECEIPT"


def test_kill_between_candidate_and_close_leaves_obligation_not_success(
    workspace, scripted, fake_cli
) -> None:
    """Attack G: the obligation is on disk before memory.close runs."""

    def killed(_argv, _stdin):
        raise KeyboardInterrupt

    fake_cli.on("close", killed)
    with pytest.raises(KeyboardInterrupt):
        _close(workspace)
    receipt = load_close_receipt(workspace, "sess")
    assert receipt["status"] == STATUS_CLOSE_INCOMPLETE
    assert receipt["failure_class"] == "pending_close"
    assert receipt["continuation_reference"] == RECORD


def test_retry_after_interruption_replays_the_same_close(workspace, scripted, fake_cli) -> None:
    """Attack H: the retry reuses the recorded key; memory replays one close."""
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "locked"))
    assert _close(workspace)["status"] == STATUS_CLOSE_INCOMPLETE
    key = load_close_receipt(workspace, "sess")["close_idempotency_key"]

    fake_cli.reply("close", 0, close_payload(replayed=True))
    report = pw.retry_close(project_dir=workspace, session_id="sess", client=scripted)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["replayed"] is True
    assert fake_cli.last("close")[fake_cli.last("close").index("--idempotency-key") + 1] == key
    assert not any(c[0][1] == "ingest-governed-candidate" for c in fake_cli.calls[-1:])
    receipt = load_close_receipt(workspace, "sess")
    assert receipt["status"] == STATUS_CLOSED_CANONICALLY and receipt["retry_count"] == 1


# ---------------------------------------------------------------------------
# Exact close replay (audit P2-01): the retry replays the recorded request
# ---------------------------------------------------------------------------


def test_retry_replays_the_exact_original_close_request(workspace, scripted, fake_cli) -> None:
    """The obligation retains the close request; the retry sends *that* summary
    and capsule digest — never a synthesized 'retry of interrupted close'."""
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "locked"))
    assert _close(workspace)["status"] == STATUS_CLOSE_INCOMPLETE
    original = fake_cli.last("close")
    original_summary = _close_summary(fake_cli, original)
    original_digest = original[original.index("--capsule-digest") + 1]
    obligation = load_close_receipt(workspace, "sess")
    assert obligation["close_summary"] == original_summary
    assert obligation["close_capsule_digest"] == original_digest
    assert obligation["close_session_id"] == "sess"

    fake_cli.reply("close", 0, close_payload(replayed=True, replay_payload_matched=True))
    report = pw.retry_close(project_dir=workspace, session_id="sess", client=scripted)
    replay = fake_cli.last("close")
    assert _close_summary(fake_cli, replay) == original_summary
    assert replay[replay.index("--capsule-digest") + 1] == original_digest
    assert "retry of interrupted close" not in _close_summary(fake_cli, replay)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["replayed"] is True and report["replay_payload_matched"] is True
    assert report["warnings"] == []
    # The obligation keeps the request material after the retry too.
    assert load_close_receipt(workspace, "sess")["close_summary"] == original_summary


def test_retry_surfaces_memory_payload_drift_evidence(workspace, scripted, fake_cli) -> None:
    """A replay memory proves different from the stored close is reported, not
    hidden behind the idempotent status."""
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "locked"))
    assert _close(workspace)["status"] == STATUS_CLOSE_INCOMPLETE
    fake_cli.reply(
        "close",
        0,
        close_payload(
            replayed=True,
            replay_payload_matched=False,
            warnings=["idempotent replay payload differs from the stored record"],
        ),
    )
    report = pw.retry_close(project_dir=workspace, session_id="sess", client=scripted)
    assert report["replayed"] is True and report["replay_payload_matched"] is False
    assert any("payload drift" in w for w in report["warnings"])
    assert any("differs from the stored record" in w for w in report["warnings"])


def test_close_reports_replay_drift_from_the_receipt(workspace, scripted, fake_cli) -> None:
    fake_cli.reply(
        "close",
        0,
        close_payload(replayed=True, replay_payload_matched=False, warnings=["differs"]),
    )
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["close"]["replayed"] is True
    assert report["close"]["replay_payload_matched"] is False
    assert report["close"]["warnings"] == ["differs"]
    assert any("close replay payload drift" in w for w in report["warnings"])


def test_close_receipt_without_forensics_is_not_drift(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 0, close_payload(replayed=True))
    report = _close(workspace)
    assert report["close"]["replay_payload_matched"] is True
    assert not any("drift" in w for w in report["warnings"])


def test_legacy_obligation_without_the_close_request_gets_a_full_close(
    workspace, scripted, fake_cli
) -> None:
    """An obligation written before the request material existed cannot be
    replayed exactly; the retry runs the full canonical close instead of
    guessing a summary."""
    from ops.graphiti.hydration.session_latches import write_receipt

    write_receipt(
        workspace,
        "sess",
        {
            "status": STATUS_CLOSE_INCOMPLETE,
            "canonical_namespace_requested": "cursor-governance",
            "close_idempotency_key": "cursor-close:cursor-governance:sess:legacy",
            "payload_digest": "f" * 64,
            "continuation_status": "admitted",
            "continuation_reference": RECORD,
            "failure_class": "pending_close",
        },
    )
    assert load_close_receipt(workspace, "sess").get("close_summary") is None
    report = pw.retry_close(
        project_dir=workspace, session_id="sess", agent_id="cursor", client=scripted
    )
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert any(c[0][1] == "ingest-governed-candidate" for c in fake_cli.calls)
    assert "retry of interrupted close" not in _close_summary(fake_cli)


def test_kill_during_close_leaves_the_exact_request_on_disk(workspace, scripted, fake_cli) -> None:
    def killed(_argv, _stdin):
        raise KeyboardInterrupt

    fake_cli.on("close", killed)
    with pytest.raises(KeyboardInterrupt):
        _close(workspace)
    obligation = load_close_receipt(workspace, "sess")
    assert obligation["status"] == STATUS_CLOSE_INCOMPLETE
    assert obligation["close_summary"].startswith("session sess completed:")
    assert obligation["close_capsule_digest"] == obligation["payload_digest"]


# ---------------------------------------------------------------------------
# Task-scoped continuation (audit P1-02): the capsule names the session's task
# ---------------------------------------------------------------------------


def test_capsule_carries_the_task_signature_the_session_hydrated_under(
    workspace, scripted, fake_cli
) -> None:
    from ops.memory.session_state import set_task_signature

    set_task_signature("sess", "0123456789abcdef0123456789abcdef")
    _close(workspace)
    capsule = _ingest_calls(fake_cli)[0]["knowledge"]["structured_payload"]
    assert capsule["task_signature"] == "0123456789abcdef0123456789abcdef"


def test_capsule_without_session_state_derives_its_own_signature(
    workspace, scripted, fake_cli
) -> None:
    from ops.memory.session_contracts import task_signature_for

    _close(workspace)
    capsule = _ingest_calls(fake_cli)[0]["knowledge"]["structured_payload"]
    assert capsule["task_signature"] == task_signature_for(
        capsule["objective"], "Quantum-L9/Cursor-Governance"
    )


# ---------------------------------------------------------------------------
# Phase B supersedes Phase A (audit P1-03): one ACTIVE continuation per session
# ---------------------------------------------------------------------------


def test_phase_b_refinement_supersedes_the_phase_a_record(
    workspace, scripted, fake_cli, monkeypatch
) -> None:
    _enable_phase_b(monkeypatch)
    fake_cli.reply("write", 0, write_payload())
    verdicts = iter(
        [
            candidate_payload(),  # Phase A admitted -> RECORD
            candidate_payload(record_id=REFINED, superseded=(RECORD,)),  # Phase B
        ]
    )
    fake_cli.on("ingest-governed-candidate", lambda _a, _s: (0, next(verdicts), ""))
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    phase_a, phase_b = _ingest_calls(fake_cli)
    assert "supersedes" not in phase_a
    assert phase_b["supersedes"] == [RECORD]
    assert phase_b["candidate_id"] != phase_a["candidate_id"]
    assert (
        phase_b["knowledge"]["structured_payload"]["task_signature"]
        == phase_a["knowledge"]["structured_payload"]["task_signature"]
    )
    assert report["continuation"]["refined"] is True
    assert report["continuation"]["record_id"] == REFINED
    assert report["continuation"]["supersedes"] == [RECORD]
    assert report["continuation"]["superseded_record_ids"] == [RECORD]
    # The close names the refined capsule, and the obligation points at it.
    assert load_close_receipt(workspace, "sess")["continuation_reference"] == REFINED


def test_rejected_refinement_keeps_phase_a_active(
    workspace, scripted, fake_cli, monkeypatch
) -> None:
    _enable_phase_b(monkeypatch)
    fake_cli.reply("write", 0, write_payload())
    verdicts = iter(
        [
            (0, candidate_payload(), ""),
            (
                7,
                candidate_payload(
                    status="rejected",
                    record_id=None,
                    reason="supersession refused: record not found",
                ),
                "",
            ),
        ]
    )
    fake_cli.on("ingest-governed-candidate", lambda _a, _s: next(verdicts))
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["continuation"]["record_id"] == RECORD
    assert report["continuation"].get("refined") is None
    assert any("Phase A continuation stays active" in w for w in report["warnings"])
    assert load_close_receipt(workspace, "sess")["continuation_reference"] == RECORD


def test_refinement_names_nothing_when_phase_a_was_not_admitted(
    workspace, scripted, fake_cli, monkeypatch
) -> None:
    _enable_phase_b(monkeypatch)
    fake_cli.reply("write", 0, write_payload())
    verdicts = iter(
        [
            (7, candidate_payload(status="rejected", record_id=None), ""),
            (0, candidate_payload(record_id=REFINED), ""),
        ]
    )
    fake_cli.on("ingest-governed-candidate", lambda _a, _s: next(verdicts))
    report = _close(workspace)
    _phase_a, phase_b = _ingest_calls(fake_cli)
    assert "supersedes" not in phase_b
    assert report["continuation"]["supersedes"] == []
    assert report["continuation"]["record_id"] == REFINED


def test_restart_with_open_obligation_is_a_close_gap(
    workspace, scripted, fake_cli, monkeypatch
) -> None:
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "locked"))
    write_open_latch(workspace, "sess", background=False)
    assert _close(workspace)["status"] == STATUS_CLOSE_INCOMPLETE
    write_open_latch(workspace, "next", background=False)
    from ops.memory import hydration as hyd

    monkeypatch.setattr(
        comp,
        "canonical_hydrate",
        lambda *a, **k: hyd.CanonicalHydration(
            status="NO_HITS",
            namespace_context=cs.resolve_namespace_context(workspace),
            requested_namespaces=("cursor-governance",),
            repository_state_digest="c" * 40,
            task_signature="sig",
        ),
    )
    packet = comp.compile_session_packet(project_dir=workspace, conversation_id="next")
    assert packet["close_gap"] is True
    assert "close_incomplete" in packet["degrade_reason"]


def test_retry_when_already_closed_is_a_skip(workspace, scripted) -> None:
    _close(workspace)
    report = pw.retry_close(project_dir=workspace, session_id="sess", client=scripted)
    assert report["status"] == "skipped_already_closed"


# ---------------------------------------------------------------------------
# Forced /end-session repair
# ---------------------------------------------------------------------------


def test_repair_close_is_a_canonical_close_with_an_explicit_capsule(
    workspace, scripted, fake_cli
) -> None:
    report = pw.repair_close(
        project_dir=workspace,
        session_id="forced",
        objective="Finish the cutover",
        next_action="Run make pr",
        files="ops/memory/hydration.py,ops/memory/session_state.py",
        blocker="CI red",
        agent_id="cursor",
        client=scripted,
    )
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["continuation"]["status"] == "admitted"
    _argv, _cwd, stdin = next(c for c in fake_cli.calls if c[0][1] == "ingest-governed-candidate")
    capsule = json.loads(stdin)["knowledge"]["structured_payload"]
    assert capsule["objective"] == "Finish the cutover"
    assert capsule["active_files"] == ["ops/memory/hydration.py", "ops/memory/session_state.py"]
    assert capsule["blockers"] == ["CI red"]
    assert load_close_receipt(workspace, "forced")["status"] == STATUS_CLOSED_CANONICALLY


def test_repair_skips_a_closed_session_unless_superseding(
    workspace, scripted, fake_cli, monkeypatch
) -> None:
    # Identity is explicit, never ambient: the test must not depend on the
    # shell exporting L9_MEMORY_AGENT_ID (CI does not; a Cursor session does).
    monkeypatch.delenv("L9_MEMORY_AGENT_ID", raising=False)
    _close(workspace)
    skipped = pw.repair_close(
        project_dir=workspace,
        session_id="sess",
        objective="o",
        next_action="n",
        agent_id="cursor",
        client=scripted,
    )
    assert skipped["status"] == "skipped_already_closed"
    superseded = pw.repair_close(
        project_dir=workspace,
        session_id="sess",
        objective="o",
        next_action="n",
        supersede=True,
        agent_id="cursor",
        client=scripted,
    )
    assert superseded["status"] == STATUS_CLOSED_CANONICALLY
    key = fake_cli.last("close")[fake_cli.last("close").index("--idempotency-key") + 1]
    assert ":repair:" in key


# ---------------------------------------------------------------------------
# Dry run, binding, namespace
# ---------------------------------------------------------------------------


def test_dry_run_commits_nothing_and_persists_no_obligation(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 3, close_payload(status="partial", record_id=None))
    report = _close(workspace, dry_run=True)
    assert report["status"] == "dry_run"
    assert load_close_receipt(workspace, "sess") is None
    assert "--dry-run" in fake_cli.last("close")


def test_unbound_runtime_is_close_incomplete_without_spawning(
    workspace, monkeypatch, fake_cli
) -> None:
    from ops.memory.runtime_binding import STATUS_UNBOUND, RuntimeBinding

    unbound = RuntimeBinding(
        status=STATUS_UNBOUND,
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version="x",
        expected_contract_version="memory-control-plane/v1",
        manifest_path="m",
        reasons=("not importable",),
    )
    client = MemoryControlPlaneClient(unbound, runner=fake_cli.run)
    monkeypatch.setattr(cs, "memory_client", lambda *_a, **_k: client)
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSE_INCOMPLETE
    assert fake_cli.calls == []
    assert load_close_receipt(workspace, "sess")["failure_class"] == "BINDING_FAILED"


def test_unresolved_namespace_never_calls_memory(
    workspace, scripted, fake_cli, monkeypatch
) -> None:
    unresolved = NamespaceContext(
        workspace=str(workspace),
        git_root=None,
        repository_identity=None,
        write_namespace_hint=None,
        read_namespace_hints=("l9-workspace",),
        method="unresolved",
        warnings=("no repository match",),
    )
    monkeypatch.setattr(cs, "resolve_namespace_context", lambda *_a, **_k: unresolved)
    report = _close(workspace)
    assert report["status"] == "skipped" and fake_cli.calls == []
    assert load_close_receipt(workspace, "sess")["status"] == "close_failed"


# ---------------------------------------------------------------------------
# Write taxonomy (plan §34 "Write tests") through the generic write
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "payload", "stderr", "expected"),
    [
        (0, write_payload(), "", "OK"),
        (0, write_payload(status="duplicate"), "", "OK"),
        (2, write_payload(status="rejected", record_id=None), "", "REJECTED"),
        (0, write_payload(status="quarantined"), "", "QUARANTINED"),
        (1, None, error_stderr("StoreError", "down"), "CANONICAL_UNAVAILABLE"),
        (0, {"receipt_id": "x"}, "", "INVALID_RECEIPT"),
    ],
)
def test_generic_write_verdicts(fake_cli, bound, code, payload, stderr, expected) -> None:
    fake_cli.reply("write", code, payload, stderr)
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    outcome = client.write(
        "a durable lesson", workspace="/w", namespace="cursor-governance", memory_class="insight"
    )
    assert outcome.status.value == expected


def test_generic_write_timeout_is_unknown_not_success(fake_cli, bound) -> None:
    fake_cli.timeout_on.add("write")
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    outcome = client.write(
        "x", workspace="/w", namespace="cursor-governance", memory_class="insight"
    )
    assert outcome.status.value == "TIMEOUT" and not outcome.ok


def test_phase_b_promotions_use_the_generic_write_with_idempotency(
    workspace, scripted, fake_cli, monkeypatch
) -> None:
    _enable_phase_b(monkeypatch)
    fake_cli.reply("write", 0, write_payload())
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["phase_b"] is True and report["promoted"] == 2
    kinds = [w["kind"] for w in report["writes"]]
    assert kinds == ["session_continuation", "session_continuation", "lesson", "decision", "close"]
    assert report["continuation"]["refined"] is True
    argv = fake_cli.last("write")
    assert "--idempotency-key" in argv
    assert argv[argv.index("--kind") + 1] == "decision"
