"""Exact-head cross-repo lifecycle proof (plan §35), against a real memory runtime.

Runs when a real memory runtime is bound: ``L9_MEMORY_DEV_CHECKOUT`` names a
``l9-graphiti-memory`` checkout whose ``.venv`` carries the package
(``runtime_mode=development_checkout``), or ``L9_MEMORY_INTERPRETER`` names an
interpreter with the pinned wheel installed (``runtime_mode=pinned_environment``,
what CI does). That is the one condition a unit environment cannot construct:
it needs the other repository's installed runtime. Everything else (store,
state, config) is disposable and isolated per test.

``L9_MEMORY_CROSS_REPO_REQUIRED=1`` turns "no runtime bound" from a skip into a
failure (audit P2-02): the required CI job
(``.github/workflows/memory-cross-repo.yml``) installs the exact wheel of the
binding's ``source.ref`` and must never pass by skipping. When
``L9_MEMORY_CROSS_REPO_EVIDENCE`` names a file, the proof records the Cursor
head, the bound memory version and runtime mode, and the wheel digest it was
handed, so the job summary is evidence and not a claim.

Sequence: bind → health → hydrate no-hit → admit a continuation capsule →
hydrate retrieves it → close (dry run, then commit, then replay) → stale
capsule loses to current repository state; then task isolation, refinement
supersession, refused supersession, lost-response retry and replay drift.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ops.graphiti.hydration import close_session as cs
from ops.graphiti.hydration.session_latches import load_close_receipt
from ops.memory.canonical_validation import (
    ENV_REQUIRE_VALIDATION as ENV_REQUIRE_CANONICAL_VALIDATION,
)
from ops.memory.control_plane_client import (
    DISTILL_CLI_OPTIONS,
    MemoryControlPlaneClient,
    OutcomeStatus,
)
from ops.memory.hook_envelope import REJECTED_PREFIX
from ops.memory.hydration import canonical_hydrate
from ops.memory.namespace_context import repository_state_digest, resolve_namespace_context
from ops.memory.runtime_binding import (
    ENV_DEV_CHECKOUT,
    ENV_INTERPRETER,
    STATUS_COMPATIBLE,
    STATUS_EXACT,
    BindingManifest,
    default_runner,
    resolve_runtime_binding,
)
from ops.memory.session_contracts import (
    ContinuationCapsuleV2,
    continuation_from_record_metadata,
)

ROOT = Path(__file__).resolve().parents[3]
ENV_REQUIRED = "L9_MEMORY_CROSS_REPO_REQUIRED"
ENV_EVIDENCE = "L9_MEMORY_CROSS_REPO_EVIDENCE"
ENV_WHEEL_SHA256 = "L9_MEMORY_WHEEL_SHA256"
ACCEPTED_MODES = frozenset({"development_checkout", "pinned_environment"})


def _required() -> bool:
    return os.environ.get(ENV_REQUIRED, "").strip() in {"1", "true", "yes"}


def _runtime_named() -> bool:
    return bool(os.environ.get(ENV_DEV_CHECKOUT) or os.environ.get(ENV_INTERPRETER))


# Optional locally (a unit environment has no memory runtime); mandatory under
# L9_MEMORY_CROSS_REPO_REQUIRED=1, where an absent runtime fails the module
# instead of skipping it — the required job must never go green by skipping.
pytestmark = pytest.mark.skipif(
    not _runtime_named() and not _required(),
    reason=(
        f"{ENV_DEV_CHECKOUT} / {ENV_INTERPRETER} unset: the cross-repo proof needs a real "
        f"memory runtime (set {ENV_REQUIRED}=1 to make that a failure, as CI does)"
    ),
)


def _cursor_head() -> str:
    for key in ("GITHUB_SHA", "L9_CURSOR_HEAD"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _record_evidence(binding, *, test: str) -> None:
    target = os.environ.get(ENV_EVIDENCE, "").strip()
    if not target:
        return
    manifest = BindingManifest.load()
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            existing = {}
    existing.setdefault("schema", "cursor.memory-cross-repo-proof/v1")
    existing.update(
        {
            "cursor_head": _cursor_head(),
            "memory_source_ref": manifest.source_ref,
            "memory_expected_version": manifest.expected_package_version,
            "memory_bound_version": binding.memory_version,
            "runtime_mode": binding.runtime_mode,
            "binding_status": binding.status,
            "artifact_provenance": binding.artifact_provenance,
            "installed_artifact_digest": binding.installed_artifact_digest,
            "expected_artifact_digest": binding.expected_artifact_digest,
            "contract_schema_digest": binding.schema_digest,
            "memory_cli": binding.memory_cli,
            "wheel_sha256": os.environ.get(ENV_WHEEL_SHA256) or None,
            "required": _required(),
            "provider_env_absent": not any(
                key in os.environ for key in ("GRAPHITI_MCP_URL", "GRAPHITI_MCP_TOKEN")
            ),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    )
    tests = list(existing.get("tests") or [])
    if test not in tests:
        tests.append(test)
    existing["tests"] = tests
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture
def runtime(tmp_path: Path, request) -> tuple[MemoryControlPlaneClient, dict[str, str]]:
    env = {
        **os.environ,
        "L9_MEMORY_DATA_DIR": str(tmp_path / "data"),
        "L9_MEMORY_STATE_DIR": str(tmp_path / "state"),
        "L9_MEMORY_JSON_LOGS": "0",
        # The point of the proof: production Cursor code runs with no provider
        # connection material in its environment (plan §34, egress tests).
    }
    env.pop("GRAPHITI_MCP_URL", None)
    env.pop("GRAPHITI_MCP_TOKEN", None)
    if not _runtime_named():
        pytest.fail(
            f"{ENV_REQUIRED}=1 but neither {ENV_DEV_CHECKOUT} nor {ENV_INTERPRETER} names a "
            "memory runtime: the required cross-repo proof cannot run, and must not skip"
        )
    if _required():
        # Every receipt must satisfy the bound release's own contract
        # (CG-P1-02): an unvalidatable receipt fails its call rather than
        # degrading to structural acceptance.
        env[ENV_REQUIRE_CANONICAL_VALIDATION] = "1"
        # ENV_REQUIRE_EXACT is deliberately NOT set here. In-place artifact
        # proof needs a PEP 610 archive hash, which pip/uv record for index
        # and URL installs but not for the local-file install this job
        # performs — so the binding cannot prove the artifact in place and
        # honestly reports `compatible`. The artifact is proved instead by
        # the job itself, and more strongly: it rebuilds the wheel from
        # source.ref and refuses any sha256 but the audited one before
        # installing. That is asserted below.
    binding = resolve_runtime_binding(env=env)
    assert binding.ok, binding.reasons
    assert binding.runtime_mode in ACCEPTED_MODES, binding.runtime_mode
    if _required():
        # The required job proves the *pinned* artifact; a development checkout
        # would prove whatever is on disk there.
        assert binding.runtime_mode == "pinned_environment", (
            f"{ENV_REQUIRED}=1 requires the pinned wheel via {ENV_INTERPRETER}, "
            f"got runtime_mode={binding.runtime_mode}"
        )
        # The artifact claim, proved where it can be: the job rebuilt the
        # wheel from the bound source ref and refused any digest but the
        # audited one, then installed exactly that.
        manifest = BindingManifest.load()
        built = os.environ.get(ENV_WHEEL_SHA256, "").strip()
        assert built and built == manifest.artifact_sha256, (
            "the job must install the audited artifact: it built "
            f"{built or '(nothing)'}, the binding records {manifest.artifact_sha256}"
        )
        # And the binding must not *claim* more than it proved: with no PEP 610
        # provenance available it reports compatible, never exact.
        assert binding.status in {STATUS_EXACT, STATUS_COMPATIBLE}, binding.status
        if not binding.is_exact:
            assert any("PEP 610" in r for r in binding.reasons), binding.reasons
        # The unit suite validates against a stand-in schema set; only this
        # proof sees the real release's contracts.
        #
        # It deliberately does NOT assert that every name in
        # CANONICAL_RECEIPT_MODELS is exported: that list is what Cursor
        # *requests*, derived from its own view classes, and a name Cursor
        # guessed wrong is not a defect in the release. The enforcement that
        # matters is behavioural and runs below — with
        # L9_MEMORY_REQUIRE_CANONICAL_VALIDATION=1 set above, any operation
        # whose receipt has no canonical schema returns VALIDATION_UNAVAILABLE
        # and fails the lifecycle assertions, naming the model. The binding
        # reasons list what the release does export, so a wrong name is
        # diagnosable rather than mute.
        assert binding.contract_schemas, (
            "the bound release exported no canonical receipt schemas, so the proof would "
            "validate nothing"
        )
    _record_evidence(binding, test=request.node.name)
    calls: list[list[str]] = []

    def recording_runner(argv, **kwargs):
        # The real CLI runs; the proof only keeps the argv so it can assert on
        # exactly what crossed the boundary (never a payload).
        calls.append([str(a) for a in argv])
        return default_runner(argv, **kwargs)

    client = MemoryControlPlaneClient(
        binding, env=env, session_id="proof-session", runner=recording_runner
    )
    client._proof_calls = calls  # type: ignore[attr-defined]
    return client, env


def test_lifecycle_against_the_real_memory_runtime(runtime, tmp_path: Path, monkeypatch) -> None:
    client, _env = runtime
    context = resolve_namespace_context(ROOT)
    namespace = context.write_namespace_hint
    assert namespace == "cursor-governance"
    workspace = str(ROOT)
    head = repository_state_digest(ROOT)
    assert head

    health = client.health()
    assert health.ok, health.error
    assert health.receipt.contract_version == "memory-control-plane/v1"
    # CG-P1-02, end to end: this receipt was validated against the schema the
    # bound release itself exported, not merely parsed by Cursor's view. Under
    # L9_MEMORY_REQUIRE_CANONICAL_VALIDATION=1 an unvalidatable receipt would
    # already have failed the call above; this pins that it validated
    # canonically rather than degrading.
    if _required():
        assert health.integration_receipt["canonical_validation"] == "canonical", (
            "health was accepted without canonical validation: "
            f"{health.integration_receipt['canonical_validation']}"
        )
        assert health.integration_receipt["contract_schema_digest"]

    empty = client.hydrate(
        "Realign memory control plane",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace,),
    )
    assert empty.status is OutcomeStatus.NO_HITS, empty.error

    capsule = ContinuationCapsuleV2(
        session_id="proof-session",
        repository_identity=context.repository_identity or "Quantum-L9/Cursor-Governance",
        objective="Realign memory control plane",
        next_action="Cut over SessionStart to canonical hydrate",
        repository_state_digest=head,
        producer_version="2.0.0",
        unfinished_work=("C4 hydration cutover",),
    )
    candidate = capsule.to_governed_candidate(
        namespace=namespace, source_sha=head, agent_id="cursor"
    )
    admitted = client.ingest_candidate(candidate, workspace=workspace)
    assert admitted.ok, admitted.error
    assert admitted.receipt.record_id
    replay = client.ingest_candidate(candidate, workspace=workspace)
    assert replay.ok and replay.receipt.status == "duplicate"
    assert replay.receipt.record_id == admitted.receipt.record_id

    hit = client.hydrate(
        "Realign memory control plane",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace,),
    )
    assert hit.ok, hit.error
    assert admitted.receipt.record_id in hit.receipt.record_ids

    # The stored record carries the capsule losslessly and current git state wins.
    raw_get = client._invoke(
        ["get", admitted.receipt.record_id, "--group-id", namespace], cwd=workspace
    )
    assert raw_get.payload is not None
    recovered = continuation_from_record_metadata(raw_get.payload["metadata"])
    assert recovered == capsule
    assert recovered.is_stale_for(head) is False
    assert recovered.is_stale_for("0" * 40) is True

    dry = client.close(
        workspace=workspace, namespace=namespace, summary="proof close", dry_run=True
    )
    assert dry.status is OutcomeStatus.NOT_COMMITTED
    committed = client.close(
        workspace=workspace,
        namespace=namespace,
        summary="proof close",
        capsule_digest=capsule.digest(),
        idempotency_key="close:proof-session",
    )
    assert committed.ok, committed.error
    assert committed.receipt.committed and committed.receipt.replayed is False
    again = client.close(
        workspace=workspace,
        namespace=namespace,
        summary="proof close",
        capsule_digest=capsule.digest(),
        idempotency_key="close:proof-session",
    )
    assert again.ok and again.receipt.replayed is True
    assert again.receipt.record_id == committed.receipt.record_id

    denied = client.hydrate(
        "anything",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace, "some-other-repo"),
    )
    assert denied.status is OutcomeStatus.UNAUTHORIZED_NAMESPACE

    # Read fan-in to memory's shared namespace is a request memory grants (C2).
    shared = client.hydrate(
        "anything",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=tuple(context.read_namespace_hints),
    )
    assert shared.status in {OutcomeStatus.OK, OutcomeStatus.NO_HITS}, shared.error
    assert "l9-workspace" in context.read_namespace_hints

    # Steps 20-23 (plan §35): a new session hydrates canonically, recovers the
    # continuation in the right namespace, and current repository truth wins
    # over a newer but stale capsule. The resume names the same task the
    # capsule was written for (audit P1-02: selection is task-scoped).
    resumed = canonical_hydrate(
        ROOT, task="Realign memory control plane", client=client, session_id="next"
    )
    assert resumed.status == "OK", resumed.error
    assert resumed.continuation is not None
    assert resumed.continuation.selection == "task_match"
    assert resumed.task_signature == capsule.task_signature
    assert resumed.namespace_context.write_namespace_hint == namespace
    assert resumed.continuation is not None
    assert resumed.continuation.record_id == admitted.receipt.record_id
    assert resumed.continuation.capsule == capsule
    assert resumed.continuation.stale is False
    assert resumed.repository_state_digest == head

    stale_capsule = ContinuationCapsuleV2(
        session_id="proof-session-2",
        repository_identity=capsule.repository_identity,
        objective="Realign memory control plane",
        next_action="Edit a file that has since moved on",
        repository_state_digest="0" * 40,
        producer_version="2.0.0",
    )
    stale_admitted = client.ingest_candidate(
        stale_capsule.to_governed_candidate(
            namespace=namespace, source_sha=head, agent_id="cursor"
        ),
        workspace=workspace,
    )
    assert stale_admitted.ok, stale_admitted.error
    resumed_again = canonical_hydrate(
        ROOT, task="Realign memory control plane", client=client, session_id="next-2"
    )
    assert resumed_again.continuation is not None
    assert resumed_again.continuation.record_id == stale_admitted.receipt.record_id
    assert resumed_again.continuation.stale is True
    assert resumed_again.continuation_candidates == 2
    # Steps 15-18 through the real close path (stage C6): capsule admitted,
    # memory.close committed, local obligation CLOSED_CANONICALLY, and a second
    # SessionEnd is one logical close.
    project = tmp_path / "proof-workspace"
    project.mkdir()
    monkeypatch.setattr(cs, "resolve_namespace_context", lambda *_a, **_k: context)
    monkeypatch.setattr(cs, "repository_state_digest", lambda _p: head)
    excerpt = (
        "user: finish C6\n"
        "assistant: Decision: the close is idempotent by key. "
        "Lesson: use the bound CLI, never PATH.\n"
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **_k: (excerpt, "test"))
    # The automatic session-end hook runs under its *own* envelope (ADR-0033
    # B7), not the operator form this fixture otherwise models. The proof
    # therefore closes through the real `cursor-session-end` surface, so the
    # bounded-distill path production hooks take is the path the bound release
    # is proved against (audit F-604-DISTILL-PROOF).
    hook = _hook_client(client, cs.DEFAULT_CLOSE_SURFACE)
    assert hook.envelope is not None and "distill" in hook.envelope.allowed_operations
    report = cs.close_session(
        project_dir=project,
        session_id="proof-close",
        agent_id="cursor",
        client=hook,
        surface=cs.DEFAULT_CLOSE_SURFACE,
    )
    assert report["status"] == "closed_canonically", report["warnings"]
    assert report["continuation"]["status"] == "admitted"
    assert report["close"]["replayed"] is False
    # ADR-0033: the redacted excerpt is distilled by memory itself, after the
    # close, through the bound release's own `l9-memory distill`. The hook lane
    # only wrote the excerpt to a bounded path; extraction, admission and every
    # record are memory's. The manifest lists `distill` under
    # bounded_hook_cli_commands because the 2.4.0 capabilities receipt does not
    # advertise it, so this is the proof that the bound release ships it.
    distill = report["distill"]
    assert distill["status"] == "OK", distill
    assert distill["extractor"]
    assert distill["candidate_count"] >= 1
    assert distill["written_count"] == len(distill["record_ids"]) >= 1
    assert next(w for w in report["writes"] if w["kind"] == "distill")["status"] == "OK"
    # The hook lane bounds max_records with the bound release's own contract:
    # a --dry-run counting pass, then the commit — both parsed by the exact
    # bound CLI (F-604-DISTILL-CAP). Every option that crossed the boundary is
    # one the bound parser defines; the unsupported --max-records never does.
    preflight, commit = _distill_argvs(hook)
    parser_options = _bound_distill_options(hook)
    assert "--max-records" not in parser_options, "the bound release grew an input cap; rebind"
    for argv in (preflight, commit):
        emitted = {a for a in argv[2:] if a.startswith("--")}
        assert emitted <= parser_options, (emitted, parser_options)
        assert emitted <= DISTILL_CLI_OPTIONS, emitted
    assert "--dry-run" in preflight and "--dry-run" not in commit
    assert Path(distill_source := commit[2]).is_file()
    assert Path(distill_source).parent == project / ".l9" / "memory" / "distill"
    assert preflight[2] == distill_source
    assert distill["candidate_count"] <= hook.envelope.max_records
    assert hook._records_committed == 1 + 1 + distill["written_count"]
    for record_id in distill["record_ids"]:
        assert _record_state(client, record_id, namespace) == "active"
    # A re-run against the same excerpt is a replay, not a second set of records:
    # memory keys each atomic write by the source digest.
    again_distill = client.distill(
        workspace=str(project),
        namespace=namespace,
        source_path=distill_source,
        repository=repository_identity_for(context),
    )
    assert again_distill.ok, again_distill.error
    assert set(again_distill.receipt.record_ids) == set(distill["record_ids"])
    obligation = load_close_receipt(project, "proof-close")
    assert obligation["status"] == "closed_canonically"
    assert obligation["canonical_operation_id"]
    again = cs.close_session(
        project_dir=project, session_id="proof-close", agent_id="cursor", client=client
    )
    assert again["status"] == "idempotent_skip"
    # The obligation retained the exact close request (audit P2-01); replaying
    # it is one logical close that memory proves payload-identical.
    assert obligation["close_summary"] and obligation["close_capsule_digest"]
    replay = client.close(
        workspace=str(project),
        namespace=namespace,
        summary=obligation["close_summary"],
        session_id="proof-close",
        capsule_digest=obligation["close_capsule_digest"],
        idempotency_key=obligation["close_idempotency_key"],
    )
    assert replay.ok and replay.receipt.replayed is True
    assert replay.receipt.replay_payload_matched is True, replay.receipt.raw
    assert replay.receipt.payload_drifted is False
    # A replay under the same key with a different summary is NOT a successful
    # close (audit CG-P1-01). This assertion used to read `drifted.ok`, which
    # is the defect written down as an expectation: memory preserves the first
    # commit and returns that record, so the receipt looks committed, and
    # treating it as this request's success lets a close that never committed
    # discharge a close obligation. Against the real runtime the outcome is an
    # idempotency conflict, and memory's own forensics are what prove it.
    drifted = client.close(
        workspace=str(project),
        namespace=namespace,
        summary="a different summary under the same key",
        session_id="proof-close",
        capsule_digest=obligation["close_capsule_digest"],
        idempotency_key=obligation["close_idempotency_key"],
    )
    assert drifted.status is OutcomeStatus.IDEMPOTENCY_CONFLICT, drifted.status
    assert drifted.ok is False
    assert "already committed a different close" in (drifted.error or "")
    assert drifted.receipt.replayed is True
    assert drifted.receipt.replay_payload_matched is False
    assert drifted.receipt.payload_drifted is True
    assert drifted.receipt.stored_digest != drifted.receipt.replay_digest
    assert any("differs" in w for w in drifted.receipt.warnings), drifted.receipt.raw
    # Memory is right to keep the first close, and it is still the record it
    # returns — it is simply not this request's.
    assert drifted.receipt.committed is True
    assert drifted.receipt.record_id == replay.receipt.record_id
    # The conflict does not consume the key: the originally committed request
    # still replays as one logical close.
    settled = client.close(
        workspace=str(project),
        namespace=namespace,
        summary=obligation["close_summary"],
        session_id="proof-close",
        capsule_digest=obligation["close_capsule_digest"],
        idempotency_key=obligation["close_idempotency_key"],
    )
    assert settled.ok and settled.receipt.replay_payload_matched is True
    # The next session of the same task recovers exactly that capsule; a
    # SessionStart with no task falls back to the newest repository capsule
    # and says so.
    resumed_close = canonical_hydrate(
        ROOT, task="Continue work in proof-workspace", client=client, session_id="after"
    )
    assert resumed_close.continuation is not None
    assert resumed_close.continuation.capsule.session_id == "proof-close"
    assert resumed_close.continuation.selection == "task_match"
    session_start = canonical_hydrate(
        ROOT,
        task="Resume session in Cursor-Governance",
        client=client,
        session_id="after-2",
        continuation_policy="repository_fallback",
    )
    assert session_start.continuation is not None
    assert session_start.continuation.selection == "repository_fallback"
    assert any("repository_fallback" in w for w in session_start.warnings)
    strict_unknown = canonical_hydrate(
        ROOT, task="Resume session in Cursor-Governance", client=client, session_id="after-3"
    )
    assert strict_unknown.continuation is None
    assert strict_unknown.continuation_excluded == strict_unknown.continuation_candidates > 0


def _distill_argvs(client: MemoryControlPlaneClient) -> list[list[str]]:
    """Every argv the client handed the real CLI for ``distill``, in order."""
    calls = getattr(client, "_proof_calls", None)
    assert calls is not None, "the proof client did not record its calls"
    return [argv for argv in calls if len(argv) > 1 and argv[1] == "distill"]


def _hook_client(operator: MemoryControlPlaneClient, surface: str) -> MemoryControlPlaneClient:
    """The same bound runtime and recorder under an automatic hook's envelope."""
    hook = MemoryControlPlaneClient(
        operator.binding,
        env=operator._env,
        session_id=operator.session_id,
        runner=operator._run,
        surface=surface,
    )
    hook._proof_calls = operator._proof_calls  # type: ignore[attr-defined]
    return hook


def _bound_distill_options(client: MemoryControlPlaneClient) -> set[str]:
    """The options the exact bound ``l9-memory distill`` parser defines.

    Read from the parser itself (``--help``), not from any Cursor-side list:
    this is the cross-repository contract the hook lane's argv must satisfy.
    """
    assert client.binding.memory_cli is not None
    completed = subprocess.run(
        [client.binding.memory_cli, "distill", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        env=client._child_env(),
        check=True,
    )
    return set(re.findall(r"(?<![\w-])(--[a-z][\w-]*)", completed.stdout))


def test_hook_distill_record_bound_holds_against_the_exact_bound_cli(
    runtime, tmp_path: Path
) -> None:
    """Audit F-604-DISTILL-CAP closure, against the real release.

    A hook with N remaining record slots cannot write more than N: the client
    counts with the bound release's own ``distill --dry-run`` (which persists
    nothing) and refuses the commit before any write when the count exceeds
    N. When it fits, the commit writes exactly what was counted.
    """
    operator, _env = runtime
    context = resolve_namespace_context(ROOT)
    namespace = context.write_namespace_hint
    hook = _hook_client(operator, cs.DEFAULT_CLOSE_SURFACE)
    assert hook.envelope is not None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    # One deterministic candidate per sentence (>= 8 chars) on this release.
    sentences = [f"Fact {i} for bound proof {stamp} requires the exact CLI." for i in range(1, 17)]
    excess = tmp_path / "excess.md"
    excess.write_text("\n".join(sentences[:13]) + "\n", encoding="utf-8")
    fits = tmp_path / "fits.md"
    fits.write_text("\n".join(sentences[13:]) + "\n", encoding="utf-8")
    assert 13 > hook.envelope.max_records >= 3

    refused = hook.distill(workspace=str(ROOT), namespace=namespace, source_path=excess)
    assert refused.status is OutcomeStatus.REJECTED, refused.error
    assert (refused.error or "").startswith(REJECTED_PREFIX)
    assert f"max_records={hook.envelope.max_records}" in refused.error
    assert "refused before write" in refused.error
    assert hook._records_committed == 0
    (counting,) = _distill_argvs(hook)
    assert "--dry-run" in counting and "--max-records" not in counting
    # Nothing was written: an operator distill of the same excerpt admits every
    # candidate fresh — had the refused hook pass persisted anything, memory
    # would answer `duplicate` under the same source-digest idempotency keys.
    proof = operator.distill(workspace=str(ROOT), namespace=namespace, source_path=excess)
    assert proof.ok, proof.error
    assert proof.receipt.candidate_count == 13
    statuses = {w["status"] for w in proof.receipt.raw["write_receipts"]}
    assert statuses == {"admitted"}, statuses

    fitting = hook.distill(workspace=str(ROOT), namespace=namespace, source_path=fits)
    assert fitting.ok, fitting.error
    assert fitting.receipt.candidate_count == fitting.receipt.written_count == 3
    assert hook._records_committed == 3 <= hook.envelope.max_records
    for record_id in fitting.receipt.record_ids:
        assert _record_state(operator, record_id, namespace) == "active"
    counting, commit = _distill_argvs(hook)[-2:]  # the recorder is shared with `operator`
    assert counting[2] == commit[2] == str(fits)
    assert "--dry-run" in counting and "--dry-run" not in commit
    parser_options = _bound_distill_options(hook)
    for argv in (counting, commit):
        assert {a for a in argv[2:] if a.startswith("--")} <= parser_options


def repository_identity_for(context) -> str:
    return context.repository_identity or "Quantum-L9/Cursor-Governance"


def _record_state(client: MemoryControlPlaneClient, record_id: str, namespace: str) -> str:
    raw = client._invoke(["get", record_id, "--group-id", namespace], cwd=str(ROOT))
    assert raw.payload is not None, raw.error_message
    return str(raw.payload["state"])


def test_task_isolation_and_refinement_supersession_against_the_real_runtime(
    runtime, tmp_path: Path, monkeypatch
) -> None:
    """Audit P1-02 / P1-03 / P2-01 against the bound memory runtime.

    Task A and Task B close against the same repository at the same HEAD;
    resuming A selects A (B excluded) and resuming B selects B. A Phase B
    refinement that names the Phase A record leaves exactly one ACTIVE
    continuation (A SUPERSEDED, B ACTIVE); a refused supersession rejects the
    refinement and keeps A ACTIVE. A close whose response was lost is retried
    with the exact recorded request and memory proves it payload-identical.
    """
    client, _env = runtime
    context = resolve_namespace_context(ROOT)
    namespace = context.write_namespace_hint
    assert namespace == "cursor-governance"
    workspace = str(ROOT)
    head = repository_state_digest(ROOT)
    repository = context.repository_identity or "Quantum-L9/Cursor-Governance"

    def capsule(session_id: str, objective: str, next_action: str) -> ContinuationCapsuleV2:
        return ContinuationCapsuleV2(
            session_id=session_id,
            repository_identity=repository,
            objective=objective,
            next_action=next_action,
            repository_state_digest=head,
            producer_version="2.0.0",
        )

    task_a = capsule("session-A", "Task A: realign hydration", "continue task A")
    task_b = capsule("session-B", "Task B: rotate the release pin", "continue task B")
    admitted_a = client.ingest_candidate(
        task_a.to_governed_candidate(namespace=namespace, source_sha=head, agent_id="cursor"),
        workspace=workspace,
    )
    assert admitted_a.ok, admitted_a.error
    admitted_b = client.ingest_candidate(
        task_b.to_governed_candidate(namespace=namespace, source_sha=head, agent_id="cursor"),
        workspace=workspace,
    )
    assert admitted_b.ok, admitted_b.error

    resume_a = canonical_hydrate(
        ROOT, task="Task A: realign hydration", client=client, session_id="resume-A"
    )
    assert resume_a.continuation is not None
    assert resume_a.continuation.record_id == admitted_a.receipt.record_id
    assert resume_a.continuation.capsule.next_action == "continue task A"
    assert resume_a.continuation.selection == "task_match"
    assert resume_a.continuation_excluded >= 1  # B (and any other task) excluded
    resume_b = canonical_hydrate(
        ROOT, task="Task B: rotate the release pin", client=client, session_id="resume-B"
    )
    assert resume_b.continuation is not None
    assert resume_b.continuation.record_id == admitted_b.receipt.record_id

    # Phase B refinement of Task A names the Phase A record: one ACTIVE left.
    refined_a = ContinuationCapsuleV2(
        session_id="session-A",
        repository_identity=repository,
        objective="Task A: realign hydration",
        next_action="continue task A — refined next step",
        repository_state_digest=head,
        producer_version="2.0.0",
        task_signature=task_a.task_signature,
        decisions=("selection is task-scoped",),
    )
    refined = client.ingest_candidate(
        refined_a.to_governed_candidate(
            namespace=namespace,
            source_sha=head,
            agent_id="cursor",
            supersedes=(admitted_a.receipt.record_id,),
        ),
        workspace=workspace,
    )
    assert refined.ok, refined.error
    assert refined.receipt.record_id != admitted_a.receipt.record_id
    assert refined.receipt.superseded_record_ids == (admitted_a.receipt.record_id,)
    assert _record_state(client, admitted_a.receipt.record_id, namespace) == "superseded"
    assert _record_state(client, refined.receipt.record_id, namespace) == "active"
    resume_a_again = canonical_hydrate(
        ROOT, task="Task A: realign hydration", client=client, session_id="resume-A2"
    )
    assert resume_a_again.continuation is not None
    assert resume_a_again.continuation.record_id == refined.receipt.record_id
    assert resume_a_again.continuation.capsule.next_action == "continue task A — refined next step"
    # The superseded Phase A record is no longer retrievable as a continuation:
    # memory's retrieval plane serves ACTIVE records only.
    continuations = client.search(
        "Task A: realign hydration",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace,),
        tags=("session_continuation",),
        limit=50,
    )
    assert continuations.ok, continuations.error
    visible = {hit.record.record_id for hit in continuations.receipt.hits}
    assert refined.receipt.record_id in visible
    assert admitted_a.receipt.record_id not in visible

    # A refused supersession (unknown target) rejects the refinement; B stays ACTIVE.
    refused = client.ingest_candidate(
        capsule("session-B", "Task B: rotate the release pin", "refined B").to_governed_candidate(
            namespace=namespace,
            source_sha=head,
            agent_id="cursor",
            supersedes=("00000000-0000-4000-8000-000000000000",),
        ),
        workspace=workspace,
    )
    assert refused.status is OutcomeStatus.REJECTED, refused.status
    assert "supersession refused" in (refused.receipt.reason or "")
    assert _record_state(client, admitted_b.receipt.record_id, namespace) == "active"
    resume_b_again = canonical_hydrate(
        ROOT, task="Task B: rotate the release pin", client=client, session_id="resume-B2"
    )
    assert resume_b_again.continuation is not None
    assert resume_b_again.continuation.record_id == admitted_b.receipt.record_id

    # Lost close response: memory committed, Cursor never saw the receipt. The
    # retry replays the exact recorded request under the recorded key.
    from ops.graphiti.hydration import pickup_write as pw

    project = tmp_path / "lost-response-workspace"
    project.mkdir()
    for module in (cs, pw):
        monkeypatch.setattr(module, "resolve_namespace_context", lambda *_a, **_k: context)
        monkeypatch.setattr(module, "repository_state_digest", lambda _p: head)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **_k: ("user: finish C13", "test"))

    class LostResponse:
        """The real client, except the first close's response never arrives."""

        def __init__(self, inner: MemoryControlPlaneClient) -> None:
            self.inner = inner
            self.lost = False

        def __getattr__(self, name: str):
            return getattr(self.inner, name)

        def close(self, **kwargs):
            outcome = self.inner.close(**kwargs)
            if not self.lost:
                self.lost = True
                return dataclasses.replace(
                    outcome, status=OutcomeStatus.TIMEOUT, receipt=None, error="lost response"
                )
            return outcome

    lossy = LostResponse(client)
    report = cs.close_session(
        project_dir=project, session_id="lost-close", agent_id="cursor", client=lossy
    )
    assert report["status"] == "close_incomplete", report["warnings"]
    obligation = load_close_receipt(project, "lost-close")
    assert obligation["status"] == "close_incomplete"
    assert obligation["close_summary"] and obligation["close_capsule_digest"]
    retried = pw.retry_close(project_dir=project, session_id="lost-close", client=lossy)
    assert retried["status"] == "closed_canonically", retried
    assert retried["replayed"] is True
    assert retried["replay_payload_matched"] is True, retried
    assert not any("drift" in w for w in retried.get("warnings", []))
    assert load_close_receipt(project, "lost-close")["status"] == "closed_canonically"
