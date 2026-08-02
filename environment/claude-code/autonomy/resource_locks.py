"""Deterministic resource conflict detection for concurrent action lanes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import ResourceLock


@dataclass(frozen=True, slots=True)
class LockConflict:
    left_key: str
    right_key: str
    reason: str


def locks_conflict(left: ResourceLock, right: ResourceLock) -> bool:
    """Return True when two declared locks cannot safely coexist.

    Canonical keys define ownership. Different non-empty isolation keys permit
    parallel writes to the same logical key only when both callers explicitly
    declared isolation. This is intended for separate Git worktrees/branches,
    not for shared files or shared external state.
    """

    if left.key != right.key:
        return False
    if left.mode == "read" and right.mode == "read":
        return False
    if left.isolation_key and right.isolation_key and left.isolation_key != right.isolation_key:
        return False
    return True


def first_conflict(
    requested: Iterable[ResourceLock],
    held: Iterable[ResourceLock],
) -> LockConflict | None:
    for request in requested:
        for existing in held:
            if locks_conflict(request, existing):
                return LockConflict(
                    left_key=request.key,
                    right_key=existing.key,
                    reason=(
                        f"{request.mode} lock conflicts with {existing.mode} lock "
                        f"on {request.key!r}"
                    ),
                )
    return None


def flatten_locks(lock_groups: Iterable[Iterable[ResourceLock]]) -> tuple[ResourceLock, ...]:
    return tuple(lock for group in lock_groups for lock in group)
