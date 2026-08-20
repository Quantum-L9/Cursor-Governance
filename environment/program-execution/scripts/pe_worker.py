#!/usr/bin/env python3
"""The step between claiming a task and verifying it: something writes code.

`default_execute` used to go claim → worktree → commit-whatever-is-there →
verify. For an implementation task nothing had written anything, so the commit
step raised `refuse stub output` and the campaign stopped — or, worse, an
already-satisfied tree verified with zero implementation.

This module is the handoff. It is intentionally an adapter, not an
orchestration framework: it renders a concise worker contract, invokes whatever
worker the operator configured, and reports whether the worktree actually
changed. When no worker is configured, an implementation task fails *here*,
before verification, with a message that says what to configure.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKER_COMMAND_ENV = "L9_PE_WORKER_CMD"
WORKER_TIMEOUT_ENV = "L9_PE_WORKER_TIMEOUT_S"
DEFAULT_WORKER_TIMEOUT_S = 1800
INSPECTION_KINDS = {"analysis", "inspection", "decision", "program_control", "review"}


class WorkerError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkerOutcome:
    invoked: bool
    changed: bool
    reason: str
    duration_s: float = 0.0
    exit_code: int | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoked": self.invoked,
            "changed": self.changed,
            "reason": self.reason,
            "duration_s": round(self.duration_s, 3),
            "exit_code": self.exit_code,
            "detail": self.detail[-2000:],
        }


def is_inspection_only(task: dict[str, Any]) -> bool:
    """True when verifying an unmodified worktree is the task's actual intent."""
    return str(task.get("execution_kind") or "").strip().lower() in INSPECTION_KINDS


def worktree_fingerprint(worktree: Path) -> str:
    """Cheap signal for 'did anything change here', tracked or not."""
    status = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain=v1", "--untracked-files=all"],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    head = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    return f"{head.stdout.strip()}|{status.stdout.strip()}"


def render_worker_brief(task: dict[str, Any], contract: dict[str, Any], worktree: Path) -> str:
    """A concise brief a worker can act on without reading the whole blueprint."""
    writable = [str(path) for path in (contract.get("writable_paths") or []) if path]
    commands = [str(item) for item in (contract.get("validation_commands") or []) if item]
    acceptance = task.get("acceptance") or []
    lines = [
        f"# {task.get('id')} — {task.get('title') or task.get('id')}",
        "",
        f"Worktree: {worktree}",
        f"Base SHA: {contract.get('base_sha')}",
        "",
        "## Objective",
        str(task.get("objective") or "").strip() or "(none declared)",
        "",
        "## Writable paths (nothing outside this list)",
        *([f"- {path}" for path in writable] or ["- (none declared)"]),
        "",
        "## Done when these pass",
        *([f"- `{command}`" for command in commands] or ["- (no executable validation declared)"]),
    ]
    if acceptance:
        lines += ["", "## Acceptance"]
        lines += [
            f"- {item.get('statement') if isinstance(item, dict) else item}" for item in acceptance
        ]
    return "\n".join(lines) + "\n"


def worker_argv(command: str, *, task_id: str, worktree: Path, brief: Path) -> list[str]:
    """Expand the configured worker command template.

    Placeholders keep the operator's command shape intact instead of imposing a
    calling convention: {task_id}, {worktree}, {brief}.

    The template is split into argv *before* substitution, so a value carrying
    quotes or spaces stays one argument instead of becoming extra ones.
    """
    fields = {"task_id": task_id, "worktree": str(worktree), "brief": str(brief)}
    argv = [token.format(**fields) for token in shlex.split(command)]
    if not argv:
        raise WorkerError(f"{WORKER_COMMAND_ENV} expands to an empty command: {command!r}")
    resolved = shutil.which(argv[0], path=os.environ.get("PATH"))
    if resolved is None:
        raise WorkerError(
            f"{WORKER_COMMAND_ENV} names a worker that is not executable on PATH: {argv[0]!r}"
        )
    return [resolved, *argv[1:]]


def invoke_worker(
    task: dict[str, Any],
    contract: dict[str, Any],
    worktree: Path,
    *,
    workspace: Path,
    command: str | None = None,
    env: dict[str, str] | None = None,
) -> WorkerOutcome:
    """Hand the task to a worker and report whether the worktree changed.

    Returns rather than raises for "no worker configured": the caller decides
    whether an untouched worktree is a defect for this task kind.
    """
    task_id = str(task.get("id") or "TASK")
    brief_path = workspace / "runtime" / "worker" / f"{task_id}.BRIEF.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(render_worker_brief(task, contract, worktree), encoding="utf-8")

    configured = command if command is not None else os.environ.get(WORKER_COMMAND_ENV, "").strip()
    if not configured:
        return WorkerOutcome(
            invoked=False,
            changed=False,
            reason="no_worker_configured",
            detail=f"brief written to {brief_path}",
        )

    argv = worker_argv(configured, task_id=task_id, worktree=worktree, brief=brief_path)
    child_env = dict(os.environ if env is None else env)
    child_env.update(
        {
            "L9_PE_TASK_ID": task_id,
            "L9_PE_WORKTREE": str(worktree),
            "L9_PE_BRIEF": str(brief_path),
            "L9_PE_CONTRACT": json.dumps(contract, sort_keys=True),
        }
    )
    timeout = int(os.environ.get(WORKER_TIMEOUT_ENV, DEFAULT_WORKER_TIMEOUT_S))
    before = worktree_fingerprint(worktree)
    started = time.monotonic()
    try:
        # argv form, no shell; argv[0] is PATH-resolved and interpolated values
        # cannot split into extra arguments. The command itself is operator
        # configuration: whoever sets it already controls this process.
        completed = subprocess.run(  # noqa: S603
            argv,  # nosemgrep: dangerous-subprocess-use-tainted-env-args
            cwd=str(worktree),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
            env=child_env,
        )
    except subprocess.TimeoutExpired:
        return WorkerOutcome(
            invoked=True,
            changed=worktree_fingerprint(worktree) != before,
            reason="worker_timeout",
            duration_s=time.monotonic() - started,
            exit_code=124,
            detail=f"worker exceeded {timeout}s",
        )
    duration = time.monotonic() - started
    changed = worktree_fingerprint(worktree) != before
    detail = ((completed.stdout or "") + (completed.stderr or "")).strip()
    if completed.returncode != 0:
        return WorkerOutcome(
            invoked=True,
            changed=changed,
            reason="worker_failed",
            duration_s=duration,
            exit_code=completed.returncode,
            detail=detail,
        )
    return WorkerOutcome(
        invoked=True,
        changed=changed,
        reason="worker_completed" if changed else "worker_made_no_change",
        duration_s=duration,
        exit_code=0,
        detail=detail,
    )


def unexecuted_task_message(task: dict[str, Any], outcome: WorkerOutcome, worktree: Path) -> str:
    """Say why an implementation task reached verification with no work done."""
    task_id = str(task.get("id") or "TASK")
    if not outcome.invoked:
        return (
            f"{task_id} is an implementation task ({task.get('execution_kind')}) but no worker "
            f"is configured, so its worktree at {worktree} is unmodified. Verifying it now would "
            "certify zero implementation. Set "
            f"{WORKER_COMMAND_ENV} to a command template (placeholders: {{task_id}}, "
            "{worktree}, {brief}), or declare the task as an inspection kind if verifying an "
            f"unmodified tree is the intent. Worker brief: {outcome.detail}. Retry is safe."
        )
    if outcome.reason == "worker_failed":
        return (
            f"{task_id} worker exited {outcome.exit_code} after {outcome.duration_s:.1f}s "
            f"in {worktree}. Expected: worker edits the declared writable paths and exits 0. "
            f"Worker output tail: {outcome.detail[-800:]}. Retry is safe after the worker is fixed."
        )
    return (
        f"{task_id} worker ran for {outcome.duration_s:.1f}s and exited 0 but changed nothing in "
        f"{worktree}. Either the task is already satisfied at this base — in which case declare it "
        "as an inspection kind — or the worker did not receive the brief."
    )
