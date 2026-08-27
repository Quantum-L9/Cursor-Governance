"""Live proof that two concurrent same-repository children never share state.

RC-6 of the PE/swarm/memory remediation program. The preceding audit read the
isolation code statically and found the defensive pattern correct, but ran no
concurrent execution, so `one_mutating_task_one_worktree` and
`no_shared_git_index_between_concurrent_mutators` were UNKNOWN at runtime.

These tests execute the real primitives concurrently in a disposable sandbox
repository rather than inspecting them:

- `GitWorktreeLane` (peer_execution/autonomy/worker_lane.py) is the per-action
  isolation unit. `run_campaign.py::isolate_worktree` isolates a whole campaign
  from the primary clone; it is *not* the per-child boundary, so proving
  concurrency there would prove the wrong thing.
- `Scheduler` (autonomy/runtime/scheduler.py) is the canonical claim owner for
  overlapping resource claims.

The overlapping-claim case is asserted as *attributed serialization*, not
rejection: the scheduler admits one claimant and reports every other under the
`blocked_claim` counter. Serializing with a structured reason is the correct
behavior for a resource claim; a silent drop is the defect this guards against.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

import pytest

_PE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _PE_ROOT.parents[1]
for _path in (str(_REPO_ROOT), str(_PE_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from peer_execution.autonomy.worker_lane import GitWorktreeLane  # noqa: E402

CAMPAIGN = "rc6-concurrency-proof"


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
def sandbox() -> Any:
    """A disposable clone. Nothing here touches the source repository."""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        _git(repo, "init", "--initial-branch=main")
        _git(repo, "config", "user.email", "rc6@example.com")
        _git(repo, "config", "user.name", "RC6 Proof")
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-m", "base")
        yield repo, root / "lanes"


def _lane(repo: Path, lane_root: Path, action_id: str) -> GitWorktreeLane:
    return GitWorktreeLane(
        repo=repo,
        lane_root=lane_root,
        campaign_id=CAMPAIGN,
        action_id=action_id,
    )


def _create_concurrently(
    repo: Path,
    lane_root: Path,
    action_ids: tuple[str, ...],
) -> tuple[dict[str, GitWorktreeLane], dict[str, Path], dict[str, BaseException]]:
    """Create every lane on its own thread, released by one barrier.

    The barrier is what makes this a concurrency proof: without it the threads
    would almost certainly serialize on scheduling alone and the test would pass
    for the wrong reason.
    """

    lanes = {action_id: _lane(repo, lane_root, action_id) for action_id in action_ids}
    created: dict[str, Path] = {}
    errors: dict[str, BaseException] = {}
    barrier = threading.Barrier(len(action_ids))
    guard = threading.Lock()

    def worker(action_id: str) -> None:
        try:
            barrier.wait(timeout=30)
            path = lanes[action_id].create(branch=f"lane-{action_id}")
        except BaseException as exc:  # noqa: BLE001 - recorded, re-raised by caller
            with guard:
                errors[action_id] = exc
            return
        with guard:
            created[action_id] = path

    threads = [
        threading.Thread(target=worker, args=(action_id,), name=f"lane-{action_id}")
        for action_id in action_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
        assert not thread.is_alive(), f"lane thread {thread.name} did not finish"
    return lanes, created, errors


def _resolved_git_dir(worktree: Path) -> Path:
    """The real gitdir behind a worktree's `.git` file."""

    pointer = worktree / ".git"
    assert pointer.is_file(), f"worktree {worktree} has no .git pointer file"
    text = pointer.read_text(encoding="utf-8").strip()
    assert text.startswith("gitdir:"), f"unexpected .git pointer: {text!r}"
    return Path(text.split(":", 1)[1].strip()).resolve()


# ----------------------------------------------------------------------
# worktree isolation under real concurrency
# ----------------------------------------------------------------------


def test_two_children_hold_distinct_worktrees_simultaneously(sandbox: Any) -> None:
    repo, lane_root = sandbox
    lanes, created, errors = _create_concurrently(repo, lane_root, ("child-a", "child-b"))
    assert not errors, f"concurrent lane creation failed: {errors}"
    assert set(created) == {"child-a", "child-b"}

    # Both must exist *at the same time*, not merely have existed in turn.
    assert created["child-a"].is_dir()
    assert created["child-b"].is_dir()
    assert created["child-a"] != created["child-b"]

    listed = _git(repo, "worktree", "list", "--porcelain")
    for path in created.values():
        assert str(path.resolve()) in listed

    for lane in lanes.values():
        lane.remove(force=True)


def test_concurrent_children_never_share_a_git_index(sandbox: Any) -> None:
    repo, lane_root = sandbox
    lanes, created, errors = _create_concurrently(repo, lane_root, ("child-a", "child-b"))
    assert not errors, f"concurrent lane creation failed: {errors}"

    git_dirs = {name: _resolved_git_dir(path) for name, path in created.items()}
    assert git_dirs["child-a"] != git_dirs["child-b"]

    indexes = {name: git_dir / "index" for name, git_dir in git_dirs.items()}
    assert indexes["child-a"] != indexes["child-b"]

    # A shared index with the primary clone is the P0 condition this guards.
    primary_index = (repo / ".git" / "index").resolve()
    for index in indexes.values():
        assert index.resolve() != primary_index

    for lane in lanes.values():
        lane.remove(force=True)


def test_concurrent_children_mutate_without_cross_contamination(sandbox: Any) -> None:
    repo, lane_root = sandbox
    lanes, created, errors = _create_concurrently(repo, lane_root, ("child-a", "child-b"))
    assert not errors, f"concurrent lane creation failed: {errors}"

    barrier = threading.Barrier(len(created))
    failures: dict[str, BaseException] = {}
    guard = threading.Lock()

    def mutate(action_id: str) -> None:
        try:
            worktree = created[action_id]
            (worktree / f"{action_id}.txt").write_text(f"{action_id}\n", encoding="utf-8")
            barrier.wait(timeout=30)
            _git(worktree, "add", f"{action_id}.txt")
            _git(worktree, "commit", "-m", f"{action_id} write")
        except BaseException as exc:  # noqa: BLE001 - recorded, asserted by caller
            with guard:
                failures[action_id] = exc

    threads = [
        threading.Thread(target=mutate, args=(action_id,), name=f"mutate-{action_id}")
        for action_id in created
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
        assert not thread.is_alive(), f"mutation thread {thread.name} did not finish"
    assert not failures, f"concurrent mutation failed: {failures}"

    for action_id, worktree in created.items():
        tracked = _git(worktree, "ls-tree", "--name-only", "HEAD").split()
        assert f"{action_id}.txt" in tracked
        for other in created:
            if other != action_id:
                assert f"{other}.txt" not in tracked

    for lane in lanes.values():
        lane.remove(force=True)


def test_duplicate_lane_claim_is_refused_not_silently_reused(sandbox: Any) -> None:
    repo, lane_root = sandbox
    first = _lane(repo, lane_root, "child-a")
    path = first.create(branch="lane-child-a")
    assert path.is_dir()

    duplicate = _lane(repo, lane_root, "child-a")
    with pytest.raises(FileExistsError):
        duplicate.create(branch="lane-child-a-again")

    first.remove(force=True)


def test_unsafe_action_id_cannot_escape_the_lane_root(sandbox: Any) -> None:
    repo, lane_root = sandbox
    with pytest.raises(ValueError):
        _lane(repo, lane_root, "../escape")


# ----------------------------------------------------------------------
# canonical claim owner: overlapping claims are attributed, never dropped
# ----------------------------------------------------------------------


def _swarm_runtime(database: Path, *, mutations: int, shared_key: bool) -> Any:
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
    actions_data = actions_payload(mutations=mutations, shared_mutation_key=shared_key)
    compiled = compile_graph(
        CampaignAuthorization.from_dict(campaign_data),
        DeploymentManifest.from_dict(deployment_data),
        actions_data,
    )
    runtime = AutonomyRuntime.from_repository(
        repository_root=_REPO_ROOT,
        database_path=database,
        signing_key="rc6-proof-signing-key",
    )
    runtime.bootstrap(
        campaign_payload=campaign_data,
        deployment_payload=deployment_data,
        graph_payload=compiled.to_dict(),
    )
    return runtime


def _complete(runtime: Any, action_id: str) -> None:
    from autonomy.tests.swarm_fixtures import CAMPAIGN_ID

    runtime.store.set_action_status(
        campaign_id=CAMPAIGN_ID,
        action_id=action_id,
        status="COMPLETED",
    )


def test_disjoint_children_are_admitted_concurrently(tmp_path: Path) -> None:
    from autonomy.tests.swarm_fixtures import CAMPAIGN_ID

    runtime = _swarm_runtime(tmp_path / "runtime.sqlite3", mutations=2, shared_key=False)
    _complete(runtime, "coordinate")
    _complete(runtime, "synthesize")
    cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
    mutations = [item for item in cycle.selected if item.mutation]
    assert len(mutations) == 2
    assert cycle.blocked_claim == 0


def test_overlapping_child_claim_is_attributed_not_silently_dropped(tmp_path: Path) -> None:
    from autonomy.tests.swarm_fixtures import CAMPAIGN_ID

    runtime = _swarm_runtime(tmp_path / "runtime.sqlite3", mutations=2, shared_key=True)
    _complete(runtime, "coordinate")
    _complete(runtime, "synthesize")
    cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
    mutations = [item for item in cycle.selected if item.mutation]

    # One claimant proceeds; the other is serialized behind it with a reason.
    assert len(mutations) == 1
    assert cycle.blocked_claim == 1

    # Nothing may vanish between READY and a terminal disposition.
    accounted = cycle.selected_count + sum(
        getattr(cycle, name)
        for name in dir(cycle)
        if name.startswith("blocked_") and isinstance(getattr(cycle, name), int)
    )
    assert accounted >= cycle.ready
