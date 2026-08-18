"""One canonical cleanup for PEC task execution residue.

An interrupted task leaves four things behind that each fail differently on the
next attempt: the worktree directory, git's registration of that worktree, the
`pec/...` task branch, and the lease that still names them. Cleaning three of
the four produces the familiar `fatal: a branch named 'pec/.../task-...'
already exists`, so all four are cleaned here, together, and never inline in
the runner.

Every entry point is safe to call repeatedly: residue that is already gone is
reported as `absent`, not raised.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .common import run_git

PEC_BRANCH_PREFIX = "pec/"


def _registered_worktrees(repo: Path) -> dict[str, str]:
    """Map worktree path -> branch, as git currently has it registered."""
    listing = run_git(repo, "worktree", "list", "--porcelain", check=False)
    if listing.returncode != 0:
        return {}
    registered: dict[str, str] = {}
    path = ""
    for line in listing.stdout.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree ") :].strip()
            registered.setdefault(path, "")
        elif line.startswith("branch ") and path:
            registered[path] = line[len("branch ") :].strip().replace("refs/heads/", "")
    return registered


def _remove_worktree(repo: Path, worktree: Path) -> str:
    """Detach one worktree from git and from disk. Returns what was done."""
    removed = run_git(repo, "worktree", "remove", "--force", str(worktree), check=False)
    if removed.returncode == 0:
        return "removed"
    # git refuses when the directory is already gone or was never registered;
    # the directory itself may still exist, so clear both independently.
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)
        return "rmtree"
    return "absent"


def _delete_branch(repo: Path, branch: str) -> str:
    exists = run_git(repo, "rev-parse", "--verify", f"refs/heads/{branch}", check=False)
    if exists.returncode != 0:
        return "absent"
    deleted = run_git(repo, "branch", "-D", branch, check=False)
    return "deleted" if deleted.returncode == 0 else "retained"


def clean_task_execution(
    workspace: Path,
    repo: Path,
    task_id: str,
    *,
    branch: str | None = None,
) -> dict[str, Any]:
    """Remove every trace of one task's execution attempt. Idempotent."""
    worktree = workspace / "worktrees" / task_id
    registered = _registered_worktrees(repo)
    branches: set[str] = set()
    if branch:
        branches.add(branch)
    for path, path_branch in registered.items():
        if path_branch and Path(path) == worktree and path_branch.startswith(PEC_BRANCH_PREFIX):
            branches.add(path_branch)
    worktree_action = _remove_worktree(repo, worktree)
    # Pruning between removal and branch deletion is what makes the branch
    # deletable: git refuses to delete a branch a registered worktree checks out.
    run_git(repo, "worktree", "prune", check=False)
    branch_actions = {name: _delete_branch(repo, name) for name in sorted(branches)}
    return {
        "task_id": task_id,
        "worktree": str(worktree),
        "worktree_action": worktree_action,
        "branches": branch_actions,
    }


def task_branches(repo: Path, task_id: str) -> list[str]:
    """Every `pec/...` branch whose name ends in this task id."""
    listing = run_git(
        repo,
        "for-each-ref",
        "--format=%(refname:short)",
        f"refs/heads/{PEC_BRANCH_PREFIX}*",
        check=False,
    )
    if listing.returncode != 0:
        return []
    suffix = task_id.lower()
    return [
        name.strip()
        for name in listing.stdout.splitlines()
        if name.strip() and name.strip().lower().endswith(suffix)
    ]


def fresh_execution_workspace(
    workspace: Path,
    repo: Path,
    *,
    task_ids: list[str] | None = None,
    release_leases: bool = True,
) -> dict[str, Any]:
    """Leave the repository able to recreate every task worktree immediately.

    Safe to invoke repeatedly, and safe to invoke on a workspace that never
    executed anything.
    """
    workspace = Path(workspace)
    repo = Path(repo)
    worktrees_dir = workspace / "worktrees"
    discovered: list[str] = []
    if task_ids is None:
        if worktrees_dir.is_dir():
            discovered = sorted(item.name for item in worktrees_dir.iterdir() if item.is_dir())
    else:
        discovered = list(task_ids)

    cleaned: list[dict[str, Any]] = []
    for task_id in discovered:
        for branch in task_branches(repo, task_id) or [None]:  # type: ignore[list-item]
            cleaned.append(clean_task_execution(workspace, repo, task_id, branch=branch))

    # A worktree directory can survive with no git registration at all; sweep
    # whatever is left so recreation does not trip on a non-empty path.
    if worktrees_dir.is_dir():
        for item in sorted(worktrees_dir.iterdir()):
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
    run_git(repo, "worktree", "prune", check=False)

    # Any pec branch with no worktree left is residue by definition.
    orphaned: dict[str, str] = {}
    live = {branch for branch in _registered_worktrees(repo).values() if branch}
    listing = run_git(
        repo,
        "for-each-ref",
        "--format=%(refname:short)",
        f"refs/heads/{PEC_BRANCH_PREFIX}*",
        check=False,
    )
    if listing.returncode == 0:
        for name in listing.stdout.splitlines():
            branch = name.strip()
            if branch and branch not in live:
                orphaned[branch] = _delete_branch(repo, branch)

    released = 0
    if release_leases:
        released = _release_open_leases(workspace)

    return {
        "workspace": str(workspace),
        "repository": str(repo),
        "tasks_cleaned": cleaned,
        "orphaned_branches": orphaned,
        "leases_released": released,
    }


def _release_open_leases(workspace: Path) -> int:
    """Drop leases that point at worktrees this reset just removed."""
    db_path = workspace / "runtime" / "state.sqlite"
    if not db_path.is_file():
        return 0
    from .state import StateDB

    db = StateDB(db_path)
    try:
        released = 0
        for lease in db.active_leases():
            db.release_lease(str(lease["lease_id"]))
            task_id = str(lease.get("task_id") or "")
            task = db.task(task_id) if task_id else None
            # The task can no longer be mid-flight once its worktree is gone;
            # returning it to ELIGIBLE is what lets execution recreate it.
            if task is not None and task["runtime_state"] not in {"COMPLETED", "CANCELLED"}:
                db.transition_task(task_id, "STALE", last_error="workspace_reset")
                db.transition_task(task_id, "ELIGIBLE")
            released += 1
        return released
    finally:
        db.close()
