"""Execution-attempt identity and the immutable pre-dispatch effect baseline.

An execution attempt is the Controller's durable record that a worker window
was (or was about to be) dispatched for one task under one lease with one
rendered contract. It is distinct from the task, from the lease, and from the
provider's transport job: a task has many attempts, a lease may carry several
after retries, and a provider job may never report back.

The baseline is what the worktree looked like immediately before the attempt
was dispatched. It is captured once, written atomically under runtime state,
digest-bound, and never recreated: after an interruption the only honest
answer to "which effects did this attempt cause?" is a diff against THAT
snapshot, never against the tree as it happens to look now (PEC-P0-003).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from .common import ControllerError, digest_object, load_json, run_git, utc_now, write_json

BASELINE_SCHEMA = "program-execution-controller.execution-baseline.v1"

#: Attempt lifecycle. Live states may hold mutation authority; every other
#: state is settled and a result arriving for it is refused.
ATTEMPT_BASELINED = "BASELINED"
ATTEMPT_DISPATCHING = "DISPATCHING"
ATTEMPT_RUNNING = "RUNNING"
ATTEMPT_TERMINAL = "TERMINAL"
ATTEMPT_ORPHANED = "ORPHANED"
ATTEMPT_FENCED = "FENCED"
ATTEMPT_ABANDONED = "ABANDONED"
LIVE_ATTEMPT_STATES = frozenset({ATTEMPT_BASELINED, ATTEMPT_DISPATCHING, ATTEMPT_RUNNING})
SETTLED_ATTEMPT_STATES = frozenset(
    {ATTEMPT_TERMINAL, ATTEMPT_ORPHANED, ATTEMPT_FENCED, ATTEMPT_ABANDONED}
)

FENCE_NONE = "none"
FENCE_FENCED = "fenced"


def _changed_paths(worktree: Path) -> list[str]:
    """Everything git reports as changed, tracked or untracked, renames both sides."""
    raw = run_git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    paths: set[str] = set()
    parts = raw.split("\0")
    index = 0
    while index < len(parts):
        entry = parts[index]
        if not entry:
            index += 1
            continue
        code = entry[:2]
        paths.add(entry[3:].replace("\\", "/"))
        if code[0] in {"R", "C"} and index + 1 < len(parts):
            index += 1
            paths.add(parts[index].replace("\\", "/"))
        index += 1
    return sorted(path for path in paths if path)


def path_fingerprint(worktree: Path, relative: str) -> str:
    """Enough of one path's state to tell "changed again" from "unchanged"."""
    target = worktree / relative
    if target.is_symlink():
        return "link:" + os.readlink(target)
    if target.is_dir():
        return "dir"
    try:
        return "file:" + hashlib.sha256(target.read_bytes()).hexdigest()
    except OSError:
        return "absent"


def capture_baseline(worktree: Path) -> dict[str, str]:
    """Fingerprints of everything already changed in the worktree, right now.

    Correct exactly once per attempt: before its window opens. Wiring links and
    plan directories the Controller or the runner placed are its own writes,
    fingerprinted so a worker rewriting one of them is still an effect.
    """
    if not worktree.is_dir():
        raise ControllerError(f"cannot baseline a missing worktree: {worktree}")
    return {path: path_fingerprint(worktree, path) for path in _changed_paths(worktree)}


def baseline_artifact_path(workspace: Path, task_id: str, attempt_id: str) -> Path:
    return workspace / "runtime" / "execution-attempts" / task_id / attempt_id / "baseline.json"


def write_baseline_artifact(
    workspace: Path,
    *,
    task_id: str,
    attempt_id: str,
    lease_id: str,
    program_digest: str,
    contract_digest: str,
    base_sha: str,
    worktree: Path,
    baseline: dict[str, str],
) -> tuple[Path, str]:
    """Persist the baseline atomically; returns (path, digest of the payload)."""
    payload: dict[str, Any] = {
        "schema": BASELINE_SCHEMA,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
        "program_digest": program_digest,
        "contract_digest": contract_digest,
        "base_sha": base_sha,
        "worktree": str(worktree.resolve()),
        "captured_at": utc_now(),
        "baseline": dict(sorted(baseline.items())),
    }
    payload["baseline_digest"] = digest_object(payload)
    path = baseline_artifact_path(workspace, task_id, attempt_id)
    write_json(path, payload)  # temp file + atomic replace
    return path, payload["baseline_digest"]


def load_baseline_artifact(path: Path, *, attempt: dict[str, Any]) -> dict[str, str]:
    """The baseline this attempt was dispatched under, or a fail-closed refusal.

    Every binding is re-checked against the attempt row: a baseline for a
    different task, lease, contract, base revision or worktree proves nothing
    about this attempt, and a corrupted artifact proves nothing at all.
    """
    if not path.is_file():
        raise ControllerError(
            f"execution baseline missing for attempt {attempt.get('attempt_id')}: {path}",
            error_code="EXECUTION_BASELINE_MISSING",
        )
    try:
        payload = load_json(path)
    except (OSError, ValueError) as exc:
        raise ControllerError(
            f"execution baseline unreadable: {path}: {exc}",
            error_code="EXECUTION_BASELINE_MISSING",
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != BASELINE_SCHEMA:
        raise ControllerError(
            f"execution baseline has the wrong schema: {path}",
            error_code="EXECUTION_BASELINE_MISSING",
        )
    body = dict(payload)
    claimed = body.pop("baseline_digest", None)
    if digest_object(body) != claimed or claimed != attempt.get("baseline_digest"):
        raise ControllerError(
            f"execution baseline digest mismatch for attempt {attempt.get('attempt_id')}",
            error_code="EXECUTION_BASELINE_MISSING",
        )
    for key in ("task_id", "attempt_id", "lease_id", "contract_digest", "base_sha", "worktree"):
        if str(payload.get(key) or "") != str(attempt.get(key) or ""):
            raise ControllerError(
                f"execution baseline {key} {payload.get(key)!r} does not bind attempt "
                f"{attempt.get('attempt_id')} ({attempt.get(key)!r})",
                error_code="EXECUTION_BASELINE_MISSING",
            )
    baseline = payload.get("baseline")
    if not isinstance(baseline, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in baseline.items()
    ):
        raise ControllerError(
            f"execution baseline carries no path fingerprints: {path}",
            error_code="EXECUTION_BASELINE_MISSING",
        )
    return dict(baseline)


def effected_paths(worktree: Path, baseline: dict[str, str]) -> list[str]:
    """Paths the attempt created or altered relative to its own baseline."""
    return sorted(
        path
        for path in _changed_paths(worktree)
        if baseline.get(path) != path_fingerprint(worktree, path)
    )
