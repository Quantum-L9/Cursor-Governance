"""Canonical session close (plan §34 "Close tests", "Write tests"; attacks F/G/H)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from memory_boundary_fixtures import (
    FakeMemoryCli,
    agent_lane_record,
    close_payload,
    distill_payload,
    error_stderr,
    search_payload,
)

from ops.graphiti.hydration import close_session as cs
from ops.graphiti.hydration import compile_session_packet as comp
from ops.graphiti.hydration import pickup_write as pw
from ops.graphiti.hydration.session_latches import (
    STATUS_CLOSE_CONFLICTED,
    STATUS_CLOSE_INCOMPLETE,
    STATUS_CLOSED_CANONICALLY,
    load_close_receipt,
    receipt_is_close_gap,
    write_open_latch,
)
from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.namespace_context import NamespaceContext

RECORD = "66666666-6666-6666-6666-666666666666"


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
    monkeypatch.setenv("L9_MEMORY_SESSION_STATE_DIR", str(tmp_path / "state"))
    return project


@pytest.fixture
def scripted(fake_cli: FakeMemoryCli, bound, monkeypatch: pytest.MonkeyPatch):
    """A canonical client over the scripted CLI, injected into every close path."""
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run, session_id="sess")
    monkeypatch.setattr(cs, "memory_client", lambda *_a, **_k: client)
    fake_cli.reply("search", 0, search_payload())
    fake_cli.reply("ingest-governed-candidate", 0, candidate_payload())
    fake_cli.reply("close", 0, close_payload())
    fake_cli.reply("distill", 0, distill_payload())
    return client


def _distill_calls(fake_cli: FakeMemoryCli) -> list[list[str]]:
    return [argv for argv, _cwd, _stdin in fake_cli.calls if argv[1] == "distill"]


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
    assert [w["kind"] for w in report["writes"]] == ["session_continuation", "close", "distill"]
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
    # continuation + close; the distill rides after the obligation is persisted.
    assert receipt["write_count"] == 2
    # No provider vocabulary anywhere near the boundary.
    assert "add_memory" not in json.dumps([c[0] for c in fake_cli.calls])
    assert report["pickup"]["active_objective"] == "Continue work in Cursor-Governance"
    assert any(
        args[1] == "search" and "--recorded-after" in args for args, _c, _s in fake_cli.calls
    )


def test_close_enriches_capsule_from_agent_lane_hits(workspace, scripted, fake_cli) -> None:
    agent = agent_lane_record(
        content="decision: pin recorded_after before the 24h prefetch ships",
        memory_class="decision",
    )
    fake_cli.reply("search", 0, search_payload(agent))
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    candidate = _ingest_calls(fake_cli)[-1]
    payload = candidate["knowledge"]["structured_payload"]
    assert any("pin recorded_after" in item for item in payload["decisions"])


def test_public_close_report_is_scalar_and_names_statuses(workspace, scripted) -> None:
    from ops.graphiti.hydration.cli import _public_close_report

    public = _public_close_report(_close(workspace))
    assert public["status"] == STATUS_CLOSED_CANONICALLY
    assert public["continuation_status"] == "admitted"
    assert public["close_status"] == "OK"
    assert public["write_count"] == 3


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
    """Drift evidence is surfaced *and* the close is not canonical (CG-P1-01).

    This test previously asserted ``STATUS_CLOSED_CANONICALLY`` here: memory
    returns the historical committed record on a conflicting replay, and the
    consumer promoted it because ``receipt.committed`` was true. Reporting the
    drift beside a success is the defect, not the fix (contract §16).
    """
    fake_cli.reply(
        "close",
        0,
        close_payload(replayed=True, replay_payload_matched=False, warnings=["differs"]),
    )
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSE_CONFLICTED
    assert report["status"] != STATUS_CLOSED_CANONICALLY
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
    assert "close_incomplete" in packet["close_gap_reason"]
    # ADR-0032: an open close obligation is a lifecycle gap, not memory degradation.
    assert packet["degraded"] is False
    assert packet["memory_degraded"] is False


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


def test_close_writes_the_continuation_the_close_and_one_canonical_distill(
    workspace, scripted, fake_cli
) -> None:
    """One session leaves one continuation, one close and one distill request;
    no Cursor-side promotions ride along (memory owns cognition, ADR-0033)."""
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert "phase_b" not in report and "promoted" not in report
    kinds = [w["kind"] for w in report["writes"]]
    assert kinds == ["session_continuation", "close", "distill"]
    assert not any(args[1] == "write" for args, _c, _s in fake_cli.calls)
    assert len(_ingest_calls(fake_cli)) == 1


# ---------------------------------------------------------------------------
# Canonical distill (ADR-0033): the hook lane hands memory the redacted excerpt
# ---------------------------------------------------------------------------


def test_distill_hands_memory_the_redacted_excerpt_after_the_close(
    workspace, scripted, fake_cli
) -> None:
    report = _close(workspace)
    (argv,) = _distill_calls(fake_cli)
    source = Path(argv[2])
    assert argv[:2] == [fake_cli.last("distill")[0], "distill"]
    assert argv[argv.index("--group-id") + 1] == "cursor-governance"
    assert argv[argv.index("--repository") + 1] == "Quantum-L9/Cursor-Governance"
    assert "--dry-run" not in argv
    # The excerpt is written under the project's bounded .l9/memory/distill dir,
    # and it is the redacted transcript load_transcript_excerpt produced.
    assert source.is_file()
    assert source.parent == Path(workspace) / ".l9" / "memory" / "distill"
    assert source.read_text(encoding="utf-8").strip() == "user: ship the PR"
    # The distill is ordered after memory.close: the close is what closes.
    order = [argv[1] for argv, _c, _s in fake_cli.calls]
    assert order.index("close") < order.index("distill")
    assert report["distill"]["status"] == "OK"
    assert report["distill"]["candidate_count"] == 1
    assert report["distill"]["written_count"] == 1
    assert report["distill"]["record_ids"] == ["77777777-7777-7777-7777-777777777777"]
    assert report["distill"]["extractor"] == "deterministic-atomic/v1"


def test_distill_failure_never_unmakes_a_canonical_close(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("distill", 1, None, error_stderr("StoreError", "distill store locked"))
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert load_close_receipt(workspace, "sess")["status"] == STATUS_CLOSED_CANONICALLY
    assert report["distill"]["status"] == "CANONICAL_UNAVAILABLE"
    assert any(w.startswith("distill CANONICAL_UNAVAILABLE") for w in report["warnings"])


def test_distill_rejected_by_memory_is_reported_not_retried_locally(
    workspace, scripted, fake_cli
) -> None:
    fake_cli.reply(
        "distill",
        2,
        distill_payload(status="failed", candidate_count=2, record_ids=(), rejected_items=("x",)),
    )
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["distill"]["status"] == "REJECTED"
    assert report["distill"]["rejected_count"] == 1
    assert len(_distill_calls(fake_cli)) == 1


def test_distill_nothing_to_extract_is_no_hits_not_a_fault(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("distill", 0, distill_payload(candidate_count=0, record_ids=()))
    report = _close(workspace)
    assert report["distill"]["status"] == "NO_HITS"
    assert not any(
        w.startswith("distill NO_HITS") or "distill REJECTED" in w for w in report["warnings"]
    )


def test_distill_dry_run_is_not_committed(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("distill", 0, distill_payload(record_ids=()))
    report = _close(workspace, dry_run=True)
    (argv,) = _distill_calls(fake_cli)
    assert "--dry-run" in argv
    assert report["distill"]["status"] == "NOT_COMMITTED"


def test_distill_skips_are_named(workspace, scripted, fake_cli, monkeypatch) -> None:
    monkeypatch.setenv("L9_MEMORY_DISTILL", "0")
    report = _close(workspace)
    assert _distill_calls(fake_cli) == []
    assert "distill skipped: L9_MEMORY_DISTILL=0" in report["warnings"]
    monkeypatch.delenv("L9_MEMORY_DISTILL")
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **_k: ("", "none"))
    report = _close(workspace, session_id="sess-empty")
    assert _distill_calls(fake_cli) == []
    assert "distill skipped: empty transcript excerpt" in report["warnings"]


def test_distill_is_starved_before_the_close_is(workspace, scripted, fake_cli) -> None:
    # start, after Phase A, distill budget probe, final elapsed
    ticks = iter([0.0, 1.0, 28.0, 28.1])
    report = _close(workspace, clock=lambda: next(ticks, 28.2))
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert _distill_calls(fake_cli) == []
    assert "distill skipped: insufficient time budget" in report["warnings"]


def test_client_distill_contradictory_receipt_is_invalid(fake_cli, bound) -> None:
    fake_cli.reply("distill", 0, distill_payload(candidate_count=2, record_ids=()))
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    outcome = client.distill(
        workspace="/w", namespace="cursor-governance", source_path="/w/.l9/x.md"
    )
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT
    assert "wrote no record" in (outcome.error or "")


def test_client_distill_timeout_is_unknown_not_success(fake_cli, bound) -> None:
    fake_cli.timeout_on.add("distill")
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    outcome = client.distill(
        workspace="/w", namespace="cursor-governance", source_path="/w/.l9/x.md"
    )
    assert outcome.status is OutcomeStatus.TIMEOUT and not outcome.ok
    assert outcome.integration_receipt["operation"] == "distill"


# ---------------------------------------------------------------------------
# CG-P1-01: idempotency replay drift must fail canonical close
#
# Memory is correct to preserve the first commit under a key and to return it.
# The defect was on this side: the consumer promoted that historical record to
# CLOSED_CANONICALLY because ``receipt.committed`` was true, so a close request
# that never committed satisfied a close obligation. The contract:
#
#   first close                       -> CANONICAL_SUCCESS
#   same key + same payload           -> EXACT_IDEMPOTENT_REPLAY -> success
#   same key + different payload      -> IDEMPOTENCY_CONFLICT    -> NOT success
# ---------------------------------------------------------------------------


def _drifted() -> dict:
    return close_payload(
        replayed=True,
        replay_payload_matched=False,
        warnings=["idempotent replay payload differs from the stored record"],
    )


def test_1_first_close_succeeds(workspace, scripted, fake_cli) -> None:
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["close"]["replayed"] is False


def test_2_identical_retry_succeeds_idempotently(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "locked"))
    assert _close(workspace)["status"] == STATUS_CLOSE_INCOMPLETE
    fake_cli.reply("close", 0, close_payload(replayed=True, replay_payload_matched=True))
    report = pw.retry_close(project_dir=workspace, session_id="sess", client=scripted)
    assert report["status"] == STATUS_CLOSED_CANONICALLY
    assert report["replay_payload_matched"] is True


def test_3_changed_payload_under_the_same_key_is_a_conflict(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 0, _drifted())
    outcome = scripted.close(
        workspace=str(workspace),
        namespace="cursor-governance",
        summary="a different summary",
        session_id="sess",
        capsule_digest="f" * 64,
        idempotency_key="cursor-close:cursor-governance:sess",
    )
    assert outcome.status is OutcomeStatus.IDEMPOTENCY_CONFLICT
    assert outcome.ok is False
    # The taxonomy is precise: not a transport failure, not a generic rejection.
    assert outcome.status is not OutcomeStatus.CANONICAL_UNAVAILABLE
    assert outcome.status is not OutcomeStatus.INVALID_RECEIPT
    assert outcome.status is not OutcomeStatus.REJECTED
    assert "already committed a different close" in (outcome.error or "")
    # Memory's committed record is still visible as evidence — it is simply not
    # this request's, so it never becomes this request's success.
    assert outcome.receipt is not None and outcome.receipt.committed is True


def test_4_changed_payload_cannot_produce_closed_canonically(workspace, scripted, fake_cli) -> None:
    """The invariant, asserted on both close paths that can reach the promotion."""
    fake_cli.reply("close", 0, _drifted())
    assert _close(workspace)["status"] != STATUS_CLOSED_CANONICALLY

    # ...and the retry path, which reaches the promotion through retry_close.
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "locked"))
    assert _close(workspace, session_id="sess2")["status"] == STATUS_CLOSE_INCOMPLETE
    fake_cli.reply("close", 0, _drifted())
    assert (
        pw.retry_close(project_dir=workspace, session_id="sess2", client=scripted)["status"]
        != STATUS_CLOSED_CANONICALLY
    )


def test_5_conflict_leaves_the_close_obligation_unresolved(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 0, _drifted())
    report = _close(workspace)
    assert report["status"] == STATUS_CLOSE_CONFLICTED
    receipt = load_close_receipt(workspace, "sess")
    assert receipt["status"] == STATUS_CLOSE_CONFLICTED
    assert receipt["failure_class"] == "IDEMPOTENCY_CONFLICT"
    assert receipt["last_error_code"] == "IDEMPOTENCY_CONFLICT"
    # Visibly unresolved: the next session still sees a close gap.
    assert receipt_is_close_gap(receipt) is True


def test_6_repeated_conflicting_retry_is_deterministic(workspace, scripted, fake_cli) -> None:
    fake_cli.reply("close", 0, _drifted())
    first = _close(workspace)
    second = _close(workspace, session_id="sess-b")
    assert first["status"] == second["status"] == STATUS_CLOSE_CONFLICTED
    third = _close(workspace, session_id="sess-c")
    assert third["status"] == STATUS_CLOSE_CONFLICTED


def test_7_exact_replay_after_a_conflict_resolves_to_the_committed_payload(
    workspace, scripted, fake_cli
) -> None:
    """A conflict does not poison the key: replaying the *originally committed*
    request still resolves the obligation, and against the payload memory holds."""
    fake_cli.reply("close", 1, None, error_stderr("StoreError", "locked"))
    assert _close(workspace)["status"] == STATUS_CLOSE_INCOMPLETE
    recorded = load_close_receipt(workspace, "sess")["close_summary"]

    fake_cli.reply("close", 0, _drifted())
    assert (
        pw.retry_close(project_dir=workspace, session_id="sess", client=scripted)["status"]
        == STATUS_CLOSE_CONFLICTED
    )
    fake_cli.reply("close", 0, close_payload(replayed=True, replay_payload_matched=True))
    resolved = pw.retry_close(project_dir=workspace, session_id="sess", client=scripted)
    assert resolved["status"] == STATUS_CLOSED_CANONICALLY
    # It replayed the recorded request, never a synthesized summary.
    assert _close_summary(fake_cli) == recorded


def test_8_warning_only_handling_is_rejected(workspace, scripted, fake_cli) -> None:
    """Explicitly guards the shape §16 forbids: a warning beside a success.

    If someone reverts the promotion guard and leaves only the drift warning,
    the warning assertion still passes and this one fails.
    """
    fake_cli.reply("close", 0, _drifted())
    report = _close(workspace)
    assert any("drift" in w for w in report["warnings"])
    assert report["status"] != STATUS_CLOSED_CANONICALLY, (
        "drift was reported as a warning while the close was still promoted to "
        "CLOSED_CANONICALLY — this is exactly the defect CG-P1-01 names"
    )
    assert load_close_receipt(workspace, "sess")["status"] != STATUS_CLOSED_CANONICALLY
