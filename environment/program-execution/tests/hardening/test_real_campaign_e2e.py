"""Real campaign E2E: admission through memory-candidate submission status.

RC-7 of the PE/swarm/memory remediation program. Before this module the
repository had no test that crossed the whole seam — campaign admission,
concurrent children, mutation authority, worktree isolation, generated-data
validation, and the memory handoff were each covered in isolation, so a
regression in any join between them could land unnoticed.

The scenario, in order:

1. campaign admission through `AutonomyRuntime`
2. bounded concurrency: two disjoint children admitted in one cycle
3. mutation authority granted *before* dispatch, never after
4. two distinct worktrees with no shared git index
5. one controlled child failure with successful-sibling survival
6. result harvesting and raw-evidence preservation
7. generated-data packet validation (valid admitted, invalid refused)
8. a memory-candidate submission status
9. an explicit assertion that zero push / PR / merge activity occurred

On (9): every subprocess launched anywhere in this module is recorded and
screened, so the no-publication boundary is *proven for this run* rather than
assumed from the fact that nobody wrote a push.

On (8): first-hop `submitted` still means `enqueued` to the file outbox.
`test_enqueued_is_not_reported_as_persisted` then drains with a fake accept
command and asserts the drained end state. Enqueue is never persistence.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

_PE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _PE_ROOT.parents[1]
_GENERATED_DATA = _REPO_ROOT / "environment" / "agents" / "generated-data"
for _path in (
    str(_REPO_ROOT),
    str(_PE_ROOT),
    str(_GENERATED_DATA / "orchestration"),
    str(_PE_ROOT / "integrations" / "subagent-generated-data"),
):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from peer_execution.autonomy.worker_lane import GitWorktreeLane  # noqa: E402
from test_concurrent_worktree_isolation import (  # noqa: E402
    create_lanes_concurrently,
)

BASE_SHA = "abc1234"
LANE_CAMPAIGN = "rc7-real-campaign-e2e"
# Inside the w7 fixture campaign's declared `allowed_paths`. Authority is scoped
# by path as well as by role, so an out-of-scope path would be denied for a
# reason unrelated to the capability under test.
IN_SCOPE_PATH = "autonomy/README.md"

# Any argv matching one of these is a remote publication attempt. Program
# Execution is permanently local-commit-only, so a hit is a hard failure.
PUBLICATION_SIGNATURES: tuple[tuple[str, ...], ...] = (
    ("git", "push"),
    ("git", "push-all"),
    ("gh", "pr", "create"),
    ("gh", "pr", "merge"),
    ("gh", "pr", "edit"),
    ("gh", "release", "create"),
    ("make", "push"),
)
# Force flags only implicate publication on a push. `git worktree remove
# --force` is ordinary local cleanup and must not trip the wire.
PUBLICATION_TOKENS = ("--force-with-lease", "--force", "-f")


# ----------------------------------------------------------------------
# publication tripwire
# ----------------------------------------------------------------------


class SubprocessLedger:
    """Records every subprocess argv so publication can be screened."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._guard = threading.Lock()

    def record(self, argv: Any) -> None:
        if isinstance(argv, str):
            parts: tuple[str, ...] = (argv,)
        elif isinstance(argv, (list, tuple)):
            parts = tuple(str(item) for item in argv)
        else:
            parts = (str(argv),)
        with self._guard:
            self.calls.append(parts)

    def publication_attempts(self) -> list[tuple[str, ...]]:
        hits: list[tuple[str, ...]] = []
        for argv in self.calls:
            if not argv:
                continue
            stem = (Path(argv[0]).name,) + argv[1:]
            for signature in PUBLICATION_SIGNATURES:
                if len(stem) >= len(signature) and stem[: len(signature)] == signature:
                    hits.append(argv)
                    break
            else:
                if (
                    stem[0] == "git"
                    and "push" in stem
                    and any(token in stem for token in PUBLICATION_TOKENS)
                ):
                    hits.append(argv)
        return hits


@pytest.fixture(autouse=True)
def publication_tripwire(monkeypatch: pytest.MonkeyPatch) -> Iterator[SubprocessLedger]:
    """Screen every subprocess this test launches, then fail on publication.

    The real callables still run — this observes, it does not stub. A test that
    stubbed git would prove nothing about the boundary.
    """

    ledger = SubprocessLedger()
    real_run = subprocess.run
    real_popen = subprocess.Popen
    real_check_output = subprocess.check_output
    real_call = subprocess.call

    def run(argv: Any, *args: Any, **kwargs: Any) -> Any:
        ledger.record(argv)
        return real_run(argv, *args, **kwargs)

    def popen(argv: Any, *args: Any, **kwargs: Any) -> Any:
        ledger.record(argv)
        return real_popen(argv, *args, **kwargs)

    def check_output(argv: Any, *args: Any, **kwargs: Any) -> Any:
        ledger.record(argv)
        return real_check_output(argv, *args, **kwargs)

    def call(argv: Any, *args: Any, **kwargs: Any) -> Any:
        ledger.record(argv)
        return real_call(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(subprocess, "check_output", check_output)
    monkeypatch.setattr(subprocess, "call", call)

    yield ledger

    attempts = ledger.publication_attempts()
    assert not attempts, f"campaign run attempted remote publication: {attempts}"


# ----------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
        timeout=60,
    )
    return completed.stdout.strip()


@pytest.fixture
def sandbox() -> Iterator[tuple[Path, Path]]:
    """A disposable clone; the source repository is never touched."""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        _git(repo, "init", "--initial-branch=main")
        _git(repo, "config", "user.email", "rc7@example.com")
        _git(repo, "config", "user.name", "RC7 E2E")
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-m", "base")
        yield repo, root / "lanes"


@pytest.fixture
def campaign(tmp_path: Path) -> Any:
    """An admitted campaign with two disjoint mutation children."""

    from autonomy.compiler.graph_compiler import compile_graph
    from autonomy.models import CampaignAuthorization, DeploymentManifest
    from autonomy.runtime.engine import AutonomyRuntime
    from autonomy.tests.swarm_fixtures import (
        actions_payload,
        campaign_payload,
        deployment_payload,
    )

    campaign_data = campaign_payload()
    deployment_data = deployment_payload()
    actions_data = actions_payload(mutations=2, shared_mutation_key=False)
    compiled = compile_graph(
        CampaignAuthorization.from_dict(campaign_data),
        DeploymentManifest.from_dict(deployment_data),
        actions_data,
    )
    runtime = AutonomyRuntime.from_repository(
        repository_root=_REPO_ROOT,
        database_path=tmp_path / "runtime.sqlite3",
        signing_key="rc7-e2e-signing-key",
    )
    runtime.bootstrap(
        campaign_payload=campaign_data,
        deployment_payload=deployment_data,
        graph_payload=compiled.to_dict(),
    )
    return runtime


def _campaign_id() -> str:
    from autonomy.tests.swarm_fixtures import CAMPAIGN_ID

    return CAMPAIGN_ID


def _graph_id(runtime: Any) -> str:
    return str(runtime.store.get_campaign(_campaign_id())["graph_id"])


def _complete(runtime: Any, action_id: str) -> None:
    runtime.store.set_action_status(
        campaign_id=_campaign_id(),
        action_id=action_id,
        status="COMPLETED",
    )


def _reach_mutation_stage(runtime: Any) -> None:
    _complete(runtime, "coordinate")
    _complete(runtime, "synthesize")
    runtime.scheduler.refresh_readiness(_campaign_id())


def _acknowledged_lease(runtime: Any, action_id: str, agent_id: str) -> Any:
    lease = runtime.leases.issue(
        campaign_id=_campaign_id(),
        action_id=action_id,
        agent_id=agent_id,
    )
    runtime.leases.acknowledge(
        lease_id=lease.lease_id,
        agent_id=agent_id,
        accepted_capabilities=[
            "repository.read",
            "repository.write_scoped",
            "test.run",
            "git.diff",
            "git.commit_local",
            "artifact.write_execution_result",
        ],
    )
    return lease


# ----------------------------------------------------------------------
# 1-2. admission and bounded concurrency
# ----------------------------------------------------------------------


def test_campaign_admission_yields_a_scheduled_graph(campaign: Any) -> None:
    status = campaign.status(_campaign_id())
    assert status["campaign_id"] == _campaign_id()
    campaign.scheduler.refresh_readiness(_campaign_id())
    cycle = campaign.scheduler.next_cycle(_campaign_id())
    assert cycle.ready >= 1
    assert cycle.selected_count >= 1


def test_two_disjoint_children_are_admitted_in_one_bounded_cycle(campaign: Any) -> None:
    _reach_mutation_stage(campaign)
    cycle = campaign.scheduler.next_cycle(_campaign_id())
    mutations = [item for item in cycle.selected if item.mutation]
    assert len(mutations) == 2
    assert cycle.blocked_claim == 0

    # Bounded, not unbounded: admission stays inside the declared ceiling.
    assert cycle.selected_count <= campaign.scheduler.worker_concurrency_ceiling

    # Every ready action reached a disposition; none vanished.
    assert cycle.selected_count + cycle.blocked_claim == cycle.ready


# ----------------------------------------------------------------------
# 3. mutation authority is granted before dispatch, never after
# ----------------------------------------------------------------------


def test_unacknowledged_lease_cannot_mutate(campaign: Any) -> None:
    _reach_mutation_stage(campaign)
    lease = campaign.leases.issue(
        campaign_id=_campaign_id(),
        action_id="mutate-000",
        agent_id="executor-a",
    )
    decision = campaign.gateway.authorize(
        lease_id=lease.lease_id,
        agent_id="executor-a",
        capability="repository.write_scoped",
        resource="README.md",
    )
    assert not decision.allowed
    assert decision.code == "LEASE_NOT_ACKNOWLEDGED"


def test_acknowledged_executor_may_mutate_but_never_publish(campaign: Any) -> None:
    _reach_mutation_stage(campaign)
    lease = _acknowledged_lease(campaign, "mutate-000", "executor-a")

    allowed = campaign.gateway.authorize(
        lease_id=lease.lease_id,
        agent_id="executor-a",
        capability="repository.write_scoped",
        resource=IN_SCOPE_PATH,
    )
    assert allowed.allowed

    for capability in ("git.push", "pr.create", "pr.merge", "pr.admin_merge", "git.force_push"):
        denied = campaign.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="executor-a",
            capability=capability,
            resource=IN_SCOPE_PATH,
        )
        assert not denied.allowed, f"executor was granted {capability}"


# ----------------------------------------------------------------------
# 4. distinct worktrees, no shared git index
# ----------------------------------------------------------------------


def test_children_execute_in_distinct_worktrees(sandbox: tuple[Path, Path]) -> None:
    """Reuses the concurrent two-child fixture proven for RC-6.

    The E2E asserts the isolation property as one stage of the whole scenario;
    `test_concurrent_worktree_isolation` owns the exhaustive proof. Sharing the
    barrier-released creation helper keeps the two from drifting apart.
    """

    repo, lane_root = sandbox
    lanes, created, errors = create_lanes_concurrently(
        repo,
        lane_root,
        ("mutate-000", "mutate-001"),
        campaign_id=LANE_CAMPAIGN,
    )
    assert not errors, f"concurrent lane creation failed: {errors}"
    assert created["mutate-000"] != created["mutate-001"]
    assert all(path.is_dir() for path in created.values())

    git_dirs = set()
    for path in created.values():
        pointer = (path / ".git").read_text(encoding="utf-8").strip()
        assert pointer.startswith("gitdir:")
        git_dirs.add(Path(pointer.split(":", 1)[1].strip()).resolve())
    assert len(git_dirs) == 2
    assert (repo / ".git" / "index").resolve() not in {d / "index" for d in git_dirs}

    for lane in lanes.values():
        lane.remove(force=True)


# ----------------------------------------------------------------------
# 5. one controlled child failure, successful sibling survives
# ----------------------------------------------------------------------


def _execution_result(runtime: Any, lease: Any, action_id: str, agent_id: str) -> str:
    artifact_id = f"artifact-{uuid.uuid4().hex}"
    runtime.artifacts.submit(
        lease_id=lease.lease_id,
        agent_id=agent_id,
        artifact={
            "artifact_id": artifact_id,
            "kind": "ExecutionResult",
            "campaign_id": _campaign_id(),
            "graph_id": _graph_id(runtime),
            "action_id": action_id,
            "lease_id": lease.lease_id,
            "producer_agent_id": agent_id,
            "base_sha": BASE_SHA,
            "input_artifacts": [],
            "payload": {"base_sha": BASE_SHA, "action_id": action_id},
        },
    )
    return artifact_id


def test_one_child_failure_does_not_take_down_its_sibling(campaign: Any) -> None:
    _reach_mutation_stage(campaign)

    healthy_lease = _acknowledged_lease(campaign, "mutate-000", "executor-a")
    failing_lease = _acknowledged_lease(campaign, "mutate-001", "executor-b")

    # The healthy child completes normally.
    _execution_result(campaign, healthy_lease, "mutate-000", "executor-a")

    # The failing child submits an artifact missing the required base_sha.
    from autonomy.errors import AutonomyError

    with pytest.raises(AutonomyError):
        campaign.artifacts.submit(
            lease_id=failing_lease.lease_id,
            agent_id="executor-b",
            artifact={
                "artifact_id": f"artifact-{uuid.uuid4().hex}",
                "kind": "ExecutionResult",
                "campaign_id": _campaign_id(),
                "graph_id": _graph_id(campaign),
                "action_id": "mutate-001",
                "lease_id": failing_lease.lease_id,
                "producer_agent_id": "executor-b",
                "base_sha": BASE_SHA,
                "input_artifacts": [],
                "payload": {"action_id": "mutate-001"},
            },
        )

    healthy = campaign.store.get_action(_campaign_id(), "mutate-000")
    failed = campaign.store.get_action(_campaign_id(), "mutate-001")
    assert healthy["status"] == "COMPLETED"
    assert failed["status"] != "COMPLETED"

    # Sibling survival is only meaningful if the campaign is still coherent.
    status = campaign.status(_campaign_id())
    assert status["campaign_id"] == _campaign_id()


# ----------------------------------------------------------------------
# 6-7. harvesting, raw-evidence preservation, generated-data validation
# ----------------------------------------------------------------------


def _pipeline(tmp_path: Path) -> tuple[Any, Any, Path]:
    from processor import GeneratedDataProcessor, ProcessingConfiguration
    from state_store import PipelineStateStore

    database = tmp_path / "pipeline.sqlite3"
    store = PipelineStateStore(database)
    processor = GeneratedDataProcessor(
        ProcessingConfiguration(
            # The repository root locates the prior-wave runtime modules
            # (packet_validator, harvester, ...). Only the database and the
            # outboxes are redirected into the temporary directory.
            repository_root=str(_REPO_ROOT),
            database_path=str(database),
        ),
        store=store,
    )
    return processor, store, database


def _valid_packet() -> dict[str, Any]:
    path = _GENERATED_DATA / "tests" / "fixtures" / "valid-recon-packet.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _invalid_packet() -> dict[str, Any]:
    path = _GENERATED_DATA / "tests" / "fixtures" / "invalid-missing-evidence-packet.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_generated_data_packet_is_admitted_and_harvested(tmp_path: Path) -> None:
    processor, store, _ = _pipeline(tmp_path)
    result = processor.process_packet(
        _valid_packet(),
        actor="rc7-e2e",
        independent_validation_present=True,
        designated_authority_approval=True,
        recurrence_counts={"unit-repo-fact-001": 2, "unit-contract-gap-001": 2},
    )
    assert result.job.job_id

    # Raw evidence must survive validation, not be replaced by a verdict: the
    # per-stage snapshots are the preserved evidence, so assert them by stage
    # rather than merely asserting the job row exists.
    with store.connect() as connection:
        stages = {
            row["stage"]
            for row in connection.execute(
                "SELECT stage FROM stage_snapshots WHERE job_id = ?",
                (result.job.job_id,),
            )
        }
    assert {"HARVESTED", "ROUTED", "PROMOTION_DECIDED", "DELIVERY_PENDING"} <= stages


def test_invalid_generated_data_packet_is_refused(tmp_path: Path) -> None:
    from processor import ProcessingError

    processor, _, _ = _pipeline(tmp_path)
    with pytest.raises(ProcessingError):
        processor.process_packet(
            _invalid_packet(),
            actor="rc7-e2e",
            independent_validation_present=True,
            designated_authority_approval=True,
        )


# ----------------------------------------------------------------------
# 8. memory-candidate submission status
# ----------------------------------------------------------------------


def _deliver_to_outbox(tmp_path: Path) -> tuple[Any, Path]:
    from delivery_worker import DeliveryWorker, DeliveryWorkerConfiguration

    processor, store, database = _pipeline(tmp_path)
    processing = processor.process_packet(
        _valid_packet(),
        actor="rc7-e2e",
        independent_validation_present=True,
        designated_authority_approval=True,
        recurrence_counts={"unit-repo-fact-001": 2, "unit-contract-gap-001": 2},
    )
    outbox = tmp_path / "outbox" / "memory"
    worker = DeliveryWorker(
        DeliveryWorkerConfiguration(
            repository_root=str(_REPO_ROOT),
            database_path=str(database),
            memory_mode="outbox",
            memory_outbox=str(outbox),
            route_outbox_root=str(tmp_path / "routes"),
        ),
        store=store,
    )
    delivery = worker.run_once(actor="rc7-e2e", job_id=processing.job.job_id)
    return delivery, outbox


def test_memory_candidate_reaches_a_submission_status(tmp_path: Path) -> None:
    delivery, outbox = _deliver_to_outbox(tmp_path)
    assert delivery is not None
    assert delivery.attempted >= 1

    # A submission status must be backed by a durable artifact on disk.
    assert outbox.is_dir()
    candidates = sorted(outbox.glob("memcand-*.json"))
    assert candidates, "no memory candidate was durably enqueued"
    payload = json.loads(candidates[0].read_text(encoding="utf-8"))
    assert payload["kind"] == "MemoryCandidate"
    assert payload["governance"]["route"] == "memory"
    assert payload["governance"]["authority_class"] == "advisory"


def test_enqueued_is_not_reported_as_persisted(tmp_path: Path) -> None:
    """`enqueued` is a submission status, never a persistence claim.

    After the first hop the candidate is in the sibling outbox and the summary
    must still report persisted=UNKNOWN. Drain with a fake accept command
    advances DESTINATION_SUBMITTED and removes the file. Acceptance is still
    not a Graphiti persistence proof.
    """

    from campaign_summary import build_summary
    from delivery_worker import DeliveryWorker, DeliveryWorkerConfiguration
    from state_store import PipelineState, PipelineStateStore

    delivery, outbox = _deliver_to_outbox(tmp_path)
    assert delivery is not None
    assert delivery.enqueued >= 1
    assert delivery.accepted == 0, "outbox delivery must not claim destination acceptance"
    assert sorted(outbox.glob("memcand-*.json"))

    summary = build_summary(
        database_path=tmp_path / "pipeline.sqlite3",
        campaign_id=_valid_packet()["identity"]["campaign_id"],
    )
    memory = summary["memory"]
    assert memory["memory_units_persisted"] is None
    assert memory["memory_units_retrievable"] is None
    assert memory["memory_candidates_accepted"] == 0
    assert memory["outbox_backlog_count"] >= 1

    accept = [
        sys.executable,
        "-c",
        "import json,sys; json.dump({'status':'accepted','memory_id':'m-e2e','write_receipt_id':'w-e2e'}, sys.stdout)",
    ]
    store = PipelineStateStore(tmp_path / "pipeline.sqlite3")
    drain_worker = DeliveryWorker(
        DeliveryWorkerConfiguration(
            repository_root=str(_REPO_ROOT),
            database_path=str(tmp_path / "pipeline.sqlite3"),
            memory_mode="command",
            memory_command=tuple(accept),
            memory_outbox=str(outbox),
            route_outbox_root=str(tmp_path / "routes"),
        ),
        store=store,
    )
    drained = drain_worker.drain_memory_outbox(actor="rc7-e2e")
    assert drained and drained[0]["status"] == "accepted"
    assert not list(outbox.glob("memcand-*.json"))
    job = store.get_job(delivery.job_id)
    assert job.state is PipelineState.DESTINATION_ACCEPTED

    drained_summary = build_summary(
        database_path=tmp_path / "pipeline.sqlite3",
        campaign_id=_valid_packet()["identity"]["campaign_id"],
    )
    drained_memory = drained_summary["memory"]
    assert drained_memory["memory_units_persisted"] is None
    assert drained_memory["memory_candidates_accepted"] >= 1
    assert drained_memory["outbox_backlog_count"] == 0


# ----------------------------------------------------------------------
# 9. the no-publication boundary, asserted rather than assumed
# ----------------------------------------------------------------------


def test_program_execution_refuses_every_publication_verb() -> None:
    sys.path.insert(0, str(_PE_ROOT / "scripts"))
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "rc7_run_campaign",
        _PE_ROOT / "scripts" / "run_campaign.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec: run_campaign defines dataclasses, and dataclass
    # field resolution looks the defining module up in sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.release_authorized() is False
    for verb in (
        "open a host pull request",
        "authorize and merge a pull request",
        "push the campaign integration branch",
        "publish the campaign",
    ):
        with pytest.raises(module.CampaignError) as excinfo:
            module.refuse_publication(verb)
        assert "local-commit-only" in str(excinfo.value)


def test_no_role_may_hold_a_publication_capability() -> None:
    from autonomy.policy_loader import load_policy

    policy = load_policy("role-capabilities")
    forbidden = set(policy["globally_forbidden_capabilities"])
    assert {"pr.merge", "pr.admin_merge", "git.force_push"} <= forbidden

    publication = {"git.push", "pr.create", "pr.merge", "pr.admin_merge", "git.force_push"}
    for role, config in policy.get("roles", {}).items():
        granted = set(config.get("capabilities", []))
        assert not (granted & publication), f"role {role} holds publication capability"


def test_the_run_recorded_no_publication_subprocess(
    publication_tripwire: SubprocessLedger,
    sandbox: tuple[Path, Path],
) -> None:
    """The tripwire is only credible if it observes real git traffic."""

    repo, lane_root = sandbox
    lane = GitWorktreeLane(
        repo=repo,
        lane_root=lane_root,
        campaign_id=LANE_CAMPAIGN,
        action_id="tripwire",
    )
    lane.create(branch="lane-tripwire")
    lane.run(["git", "status", "--short"])
    lane.remove(force=True)

    git_calls = [argv for argv in publication_tripwire.calls if Path(argv[0]).name == "git"]
    assert git_calls, "tripwire observed no git traffic; it would not catch a push"
    assert not publication_tripwire.publication_attempts()
