#!/usr/bin/env python3
"""One answer to: which repositories is this session working in?

A cloud container puts several repositories side by side under a single
workspace root, and `WORKSPACE` then names the *container*, not a checkout.
Three bootstrap planes consume that value. Only one of them — memory hydration
— ever iterated the repositories inside it; the other two acted on the
container root directly, where no manifest and no consumed mirror exists:

    session_deps_cloud.sh   fingerprinted manifests at the container root,
                            found none, and installed nothing while reporting
                            `toolchain ready`.
    project-scope skill /   targeted `<container>/.claude`, so per-repository
    command projection      mirrors were outside every reconciler's target set
                            and kept symlinks to skills the SSOT had removed.

Both defects have the same shape, so they get one definition here rather than a
third private re-derivation. `workspace_roots` is the repository set;
`projection_roots` is the mount set, which additionally keeps the container root
because a session opened *at* the container still reads `<container>/.claude`.

A workspace that is itself a repository returns exactly itself, so single-repo
callers keep their existing behaviour byte-for-byte.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

#: Hydrating or provisioning each repository costs real time, so the count is
#: capped rather than unbounded. Callers report the cap, because a silent
#: truncation reads as "everything was covered".
DEFAULT_MAX_ROOTS = 6


def is_repository(path: Path) -> bool:
    """True when `path` is a git checkout root.

    `.git` is a directory in a normal clone and a file in a worktree, so this
    tests for existence rather than for a directory.
    """
    try:
        return (path / ".git").exists()
    except OSError:
        return False


def workspace_roots(
    workspace: Path,
    *,
    cap: int = DEFAULT_MAX_ROOTS,
    predicate: Callable[[Path], bool] | None = None,
) -> list[Path]:
    """Repository roots inside `workspace`, in resolution order.

    When `workspace` is itself a repository the result is `[workspace]` and
    `predicate` is not consulted — the caller named a checkout, and filtering it
    out would leave nothing to act on.

    When `workspace` is a container, its immediate children carrying a `.git`
    entry are returned sorted, filtered by `predicate` when given, and truncated
    to `cap`. A container with no usable child falls back to `[workspace]`, so a
    caller always receives at least one root and never has to special-case an
    empty list.
    """
    if is_repository(workspace):
        return [workspace]
    try:
        children = sorted(child for child in workspace.iterdir() if is_repository(child))
    except OSError:
        children = []
    usable = [child for child in children if predicate is None or predicate(child)]
    return usable[:cap] or [workspace]


def projection_roots(workspace: Path, *, cap: int = DEFAULT_MAX_ROOTS) -> list[Path]:
    """Mount roots a project-scope projection must reconcile.

    Identical to `workspace_roots` for a repository workspace. For a container
    the container root is kept *in addition to* the repositories inside it: a
    session opened at the container reads `<container>/.claude`, so dropping it
    would deactivate the mirror the session actually consumes. Adding the
    repositories is what lets the reconciler's existing obsolete-entry sweep
    reach mirrors an earlier single-repo session left behind.
    """
    if is_repository(workspace):
        return [workspace]
    repos = workspace_roots(workspace, cap=cap)
    if repos == [workspace]:
        return [workspace]
    return [workspace, *repos]
