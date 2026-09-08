"""Filesystem mechanics for PEC task execution residue. No state authority.

An interrupted task leaves three filesystem things behind that each fail
differently on the next attempt: the worktree directory, git's registration of
that worktree, and the `pec/...` task branch. Cleaning two of the three produces
the familiar `fatal: a branch named 'pec/.../task-...' already exists`, so all
three are cleaned here, together, and never inline in the runner.

What this module deliberately does NOT do any more (PEC-P0-001): decide lease
revocation, task reopening, attempt fencing or successor eligibility. Those are
Controller recovery decisions (`controller.recover_execution`), and every
destructive entry point here is reached only through it, after the evidence a
recovery must preserve has been captured.

Every entry point is safe to call repeatedly: residue that is already gone is
reported as `absent`, not raised.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from .common import resolve_within, run_git

PEC_BRANCH_PREFIX = "pec/"
# `refs/heads/pec/*` does not fnmatch a nested name like `pec/w0/task-001`;
# a literal prefix up to a slash does.
PEC_BRANCH_REFSPEC = "refs/heads/pec"


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
        PEC_BRANCH_REFSPEC,
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
) -> dict[str, Any]:
    """Leave the repository able to recreate every task worktree immediately.

    Filesystem mechanics only. The Controller calls this AFTER recovery has
    fenced every affected attempt and preserved its evidence; calling it any
    other way destroys evidence a recovery may still need.

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
        discovered = [_validated_task_id(workspace, task_id) for task_id in task_ids]

    cleaned: list[dict[str, Any]] = []
    for task_id in discovered:
        for branch in task_branches(repo, task_id) or [None]:  # type: ignore[list-item]
            cleaned.append(clean_task_execution(workspace, repo, task_id, branch=branch))

    orphaned: dict[str, str] = {}
    if task_ids is None:
        # Whole-workspace reset only. A worktree directory can survive with no
        # git registration at all; sweep whatever is left so recreation does
        # not trip on a non-empty path. Scoped to named tasks, this sweep and
        # the orphan pass below destroyed every OTHER task's dirty worktree and
        # its verified-but-unintegrated candidate branch.
        if worktrees_dir.is_dir():
            for item in sorted(worktrees_dir.iterdir()):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
    run_git(repo, "worktree", "prune", check=False)

    if task_ids is None:
        # Any pec branch with no worktree left is residue by definition.
        live = {branch for branch in _registered_worktrees(repo).values() if branch}
        listing = run_git(
            repo,
            "for-each-ref",
            "--format=%(refname:short)",
            PEC_BRANCH_REFSPEC,
            check=False,
        )
        if listing.returncode == 0:
            for name in listing.stdout.splitlines():
                branch = name.strip()
                if branch and branch not in live:
                    orphaned[branch] = _delete_branch(repo, branch)

    return {
        "workspace": str(workspace),
        "repository": str(repo),
        "tasks_cleaned": cleaned,
        "orphaned_branches": orphaned,
    }


_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _validated_task_id(workspace: Path, task_id: str) -> str:
    """A task id that names a worktree INSIDE this workspace, and a known task.

    `--task-id` reached `shutil.rmtree(workspace / "worktrees" / task_id)`
    unchecked; `../..` resolved above the workspace.
    """
    value = str(task_id).strip()
    if not _TASK_ID_RE.fullmatch(value):
        raise ValueError(f"invalid task id for fresh-workspace: {task_id!r}")
    resolve_within(workspace / "worktrees", workspace / "worktrees" / value)
    db_path = workspace / "runtime" / "state.sqlite"
    if db_path.is_file():
        from .state import StateDB

        db = StateDB(db_path)
        try:
            if db.task(value) is None:
                raise ValueError(f"unknown task id for fresh-workspace: {value}")
        finally:
            db.close()
    return value
