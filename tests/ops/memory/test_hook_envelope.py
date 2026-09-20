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
        "manus-session-start",
        "cursor-session-end",
        "claude-session-end",
        "manus-session-end",
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
    for name in (
        "cursor-session-start",
        "claude-session-start",
        "manus-session-start",
        "plan-prefetch",
    ):
        envelope = envelope_for(name)
        assert not (envelope.allowed_operations & writes)
        assert envelope.max_records == 0 and envelope.max_bytes == 0
        assert not envelope.record_classes


def test_write_surfaces_admit_only_classes_the_bound_release_accepts() -> None:
    """An envelope that admits a class ``l9-memory write`` refuses is a dead lane.

    ``session_continuation`` is the governed-candidate class (ingest_candidate /
    close judge ``knowledge.primary_class``); it is not a MemoryClass, so a
    surface whose *only* write operation is ``write`` must not list it.
    """

    from l9_graphite_memory.cli import _LEGACY_KIND_MAP  # noqa: PLC0415
    from l9_graphite_memory.contracts import MemoryClass  # noqa: PLC0415

    accepted = {item.value for item in MemoryClass} | set(_LEGACY_KIND_MAP)
    document = json.loads(hook_envelope.ENVELOPES_PATH.read_text(encoding="utf-8"))
    writes = set(document["write_operations"])
    for envelope in load_envelopes().values():
        ops = envelope.allowed_operations & writes
        if ops == {"write"}:
            bad = set(envelope.record_classes) - accepted
            assert not bad, f"{envelope.surface} admits {sorted(bad)}; l9-memory write refuses them"


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
        "PICKUP", workspace=WS, namespace="cursor-governance", memory_class="episodic"
    )
    assert outcome.status is OutcomeStatus.REJECTED
    assert "requires provenance" in (outcome.error or "")


def test_max_bytes_bounds_one_payload(bound, fake_cli) -> None:
    client = _client(bound, fake_cli, "pr-publish")
    outcome = client.write(
        "x" * 5000,
        workspace=WS,
        namespace="cursor-governance",
        memory_class="episodic",
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
        memory_class="episodic",
        source_id="k1",
    )
    assert first.status is OutcomeStatus.OK
    second = client.write(
        "PICKUP two",
        workspace=WS,
        namespace="cursor-governance",
        memory_class="episodic",
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
        memory_class="episodic",
        source_id="k1",
    )
    assert refused.status is OutcomeStatus.REJECTED
    fake_cli.reply("write", 0, WRITE_OK)
    again = client.write(
        "PICKUP",
        workspace=WS,
        namespace="cursor-governance",
        memory_class="episodic",
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
    closed = client.close(
        workspace=WS, namespace="cursor-governance", summary="done", session_id="s-1"
    )
    assert closed.status is OutcomeStatus.OK
    distilled = client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt)
    assert distilled.status is OutcomeStatus.OK
    assert client._records_committed == 1 + 1 + 2
    for argv, _cwd, _stdin in fake_cli.calls:
        assert argv[1] in {"ingest-governed-candidate", "close", "distill"}


# ---------------------------------------------------------------------------
# Hook-lane distill record bound (audit F-604-DISTILL-CAP)
#
# The bound release's `distill` parses path, --group-id, --repository and
# --dry-run — no input record cap. The hook lane proves its max_records bound
# with memory's own cognition: the same deterministic distill under --dry-run
# counts the candidates the committing pass would write, and the commit is
# refused before any write when that count exceeds the remaining allowance.
# ---------------------------------------------------------------------------


def _scripted_distill(fake_cli: FakeMemoryCli, *, candidates: int, source_digest: str = "f" * 64):
    """Answer the dry-run pass with a count and the commit pass with records."""

    def handler(argv, _stdin):
        payload = distill_payload(
            candidate_count=candidates,
            record_ids=tuple(f"7777777{i}-7777-7777-7777-777777777777" for i in range(candidates)),
        )
        payload["source_digest"] = source_digest
        if "--dry-run" in argv:
            payload["written_count"] = 0
            payload["write_receipts"] = []
        return 0, payload, ""

    fake_cli.on("distill", handler)


def _distill_argvs(fake_cli: FakeMemoryCli) -> list[list[str]]:
    return [argv for argv, _cwd, _stdin in fake_cli.calls if argv[1] == "distill"]


def test_hook_distill_emits_only_options_the_bound_release_parses(
    bound, fake_cli, tmp_path
) -> None:
    from ops.memory.control_plane_client import DISTILL_CLI_OPTIONS

    _scripted_distill(fake_cli, candidates=2)
    excerpt = tmp_path / "excerpt.md"
    excerpt.write_text("redacted\n", encoding="utf-8")
    client = _client(bound, fake_cli, "cursor-session-end")
    outcome = client.distill(
        workspace=WS, namespace="cursor-governance", source_path=excerpt, repository="o/r"
    )
    assert outcome.status is OutcomeStatus.OK
    preflight, commit = _distill_argvs(fake_cli)
    for argv in (preflight, commit):
        options = {a for a in argv[2:] if a.startswith("--")}
        assert options <= DISTILL_CLI_OPTIONS, options
        assert "--max-records" not in argv
        assert argv[2] == str(excerpt) and argv[argv.index("--group-id") + 1] == "cursor-governance"
    assert "--dry-run" in preflight and "--dry-run" not in commit
    assert client._records_committed == 2
    # The declared contract and the client's mirror of it agree.
    binding = json.loads((ROOT / "ops/config/memory-binding.json").read_text(encoding="utf-8"))
    declared = binding["bounded_hook_cli_commands"]["distill"]
    assert set(declared["options"]) == DISTILL_CLI_OPTIONS
    assert declared["record_bound"] == "preflight-dry-run"


def test_hook_distill_refuses_before_write_when_candidates_exceed_remaining(
    bound, fake_cli, tmp_path
) -> None:
    fake_cli.reply("close", 0, close_payload())
    _scripted_distill(fake_cli, candidates=8)
    excerpt = tmp_path / "excerpt.md"
    excerpt.write_text("redacted\n", encoding="utf-8")
    client = _client(bound, fake_cli, "claude-session-end")  # max_records=8
    close_outcome = client.close(
        workspace=WS, namespace="cursor-governance", summary="done", session_id="s-1"
    )
    assert close_outcome.status is OutcomeStatus.OK
    outcome = client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt)
    assert outcome.status is OutcomeStatus.REJECTED
    assert outcome.fault_class == FAULT_CANONICAL
    assert (outcome.error or "").startswith(REJECTED_PREFIX)
    assert "max_records=8" in outcome.error and "requested 8" in outcome.error
    assert "refused before write" in outcome.error
    # Only the counting pass crossed the boundary; nothing was asked to commit.
    (only,) = _distill_argvs(fake_cli)
    assert "--dry-run" in only
    assert client._records_committed == 1


def test_hook_distill_commits_when_the_count_fits_the_remaining_allowance(
    bound, fake_cli, tmp_path
) -> None:
    fake_cli.reply("close", 0, close_payload())
    _scripted_distill(fake_cli, candidates=7)
    excerpt = tmp_path / "excerpt.md"
    excerpt.write_text("redacted\n", encoding="utf-8")
    client = _client(bound, fake_cli, "claude-session-end")  # max_records=8, 1 used by close
    client.close(workspace=WS, namespace="cursor-governance", summary="done", session_id="s-1")
    outcome = client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt)
    assert outcome.status is OutcomeStatus.OK
    assert client._records_committed == 8
    # The surface is now full: the next distill is refused before spawn.
    fake_cli.calls.clear()
    again = client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt)
    assert again.status is OutcomeStatus.REJECTED and fake_cli.calls == []


def test_hook_distill_preflight_verdict_stands_when_there_is_nothing_to_commit(
    bound, fake_cli, tmp_path
) -> None:
    excerpt = tmp_path / "excerpt.md"
    excerpt.write_text("redacted\n", encoding="utf-8")
    client = _client(bound, fake_cli, "cursor-session-end")
    _scripted_distill(fake_cli, candidates=0)
    assert (
        client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt).status
        is OutcomeStatus.NO_HITS
    )
    assert len(_distill_argvs(fake_cli)) == 1, "no candidates: the commit pass is not spawned"
    fake_cli.calls.clear()
    fake_cli.reply(
        "distill", 2, distill_payload(status="failed", record_ids=(), rejected_items=("x",))
    )
    assert (
        client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt).status
        is OutcomeStatus.REJECTED
    )
    assert len(_distill_argvs(fake_cli)) == 1
    assert client._records_committed == 0


def test_hook_distill_reports_a_source_that_moved_between_count_and_commit(
    bound, fake_cli, tmp_path
) -> None:
    excerpt = tmp_path / "excerpt.md"
    excerpt.write_text("redacted\n", encoding="utf-8")

    def handler(argv, _stdin):
        payload = distill_payload(candidate_count=1)
        payload["source_digest"] = ("a" if "--dry-run" in argv else "b") * 64
        if "--dry-run" in argv:
            payload["written_count"], payload["write_receipts"] = 0, []
        return 0, payload, ""

    fake_cli.on("distill", handler)
    client = _client(bound, fake_cli, "cursor-session-end")
    outcome = client.distill(workspace=WS, namespace="cursor-governance", source_path=excerpt)
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT
    assert "changed between the counting pass and the commit" in (outcome.error or "")
    assert client._records_committed == 1, "what memory wrote is still charged to the surface"


def test_operator_distill_has_no_preflight(bound, fake_cli, tmp_path) -> None:
    _scripted_distill(fake_cli, candidates=3)
    excerpt = tmp_path / "excerpt.md"
    excerpt.write_text("redacted\n", encoding="utf-8")
    outcome = _client(bound, fake_cli, None).distill(
        workspace=WS, namespace="cursor-governance", source_path=excerpt
    )
    assert outcome.status is OutcomeStatus.OK
    (only,) = _distill_argvs(fake_cli)
    assert "--dry-run" not in only and "--max-records" not in only


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
    "environment/agents/adapters/manus/memory_lifecycle.py": "manus-session-start",
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

#: Names the operator module only to *recognise* it in someone else's argv
#: (the B8 gate exemption); never spawns it.
RECOGNIZERS = {
    "ops/autonomy/memory_lane_exemption.py",
}

_CONSTRUCTOR = re.compile(r"MemoryControlPlaneClient\(")
_SUBPROCESS = re.compile(r"[\"']ops\.memory\.cli[\"']")
_SPAWN_CALL = re.compile(r"subprocess\.|Popen\(|os\.exec|os\.system\(")


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
    placed = set(HOOK_LANE_CALLERS) | OPERATOR_FORM | AGENT_LANE | RECOGNIZERS
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
        f"OPERATOR_FORM, AGENT_LANE or RECOGNIZERS (ADR-0033): {unplaced}"
    )
    for rel in RECOGNIZERS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert not _CONSTRUCTOR.search(text), f"{rel} is a recognizer, not a client"
        assert not _SPAWN_CALL.search(text), f"{rel} is a recognizer, it must not spawn"


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
