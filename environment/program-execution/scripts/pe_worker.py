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

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

PE_ROOT = Path(__file__).resolve().parents[1]
_WIRING_MODULE = (
    PE_ROOT / "core/program-execution-controller-template/scripts/pec/workspace_wiring.py"
)


@lru_cache(maxsize=1)
def workspace_wiring() -> Any:
    """The controller's own definition of what PE generated in a worktree.

    Loaded from the controller template rather than restated here: the worker's
    copy of this predicate and the controller's had already drifted, and a
    handoff that disagrees with verification about what counts as a change is
    the bug that produces both false refusals and false passes.
    """
    spec = importlib.util.spec_from_file_location("pec_workspace_wiring", _WIRING_MODULE)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging fault
        raise WorkerError(f"cannot load workspace wiring contract: {_WIRING_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WORKER_COMMAND_ENV = "L9_PE_WORKER_CMD"
WORKER_TIMEOUT_ENV = "L9_PE_WORKER_TIMEOUT_S"
DEFAULT_WORKER_TIMEOUT_S = 1800
INSPECTION_KINDS = {"analysis", "inspection", "decision", "program_control", "review"}
CURSOR_FOREGROUND_ADAPTER = "cursor-foreground"


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


def configured_worker_command(env: dict[str, str] | None = None) -> str:
    """Return the detached-worker template, or empty for cursor-foreground."""
    source = os.environ if env is None else env
    return str(source.get(WORKER_COMMAND_ENV, "") or "").strip()


def worker_binding(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Record how this campaign will implement tasks.

    Campaign initialization does not invent a subprocess worker. Unset
    ``L9_PE_WORKER_CMD`` means the bound Cursor peer (cursor-foreground).
    Operators may export the env var before ``make campaign`` when they want a
    detached command; PE forwards it, it does not synthesize one.
    """
    command = configured_worker_command(env)
    if command:
        return {
            "adapter": "subprocess",
            "env_var": WORKER_COMMAND_ENV,
            "command": command,
            "mode": "detached_worker",
        }
    return {
        "adapter": CURSOR_FOREGROUND_ADAPTER,
        "env_var": WORKER_COMMAND_ENV,
        "command": None,
        "mode": "peer_session",
    }


def is_inspection_only(task: dict[str, Any]) -> bool:
    """True when verifying an unmodified worktree is the task's actual intent."""
    return str(task.get("execution_kind") or "").strip().lower() in INSPECTION_KINDS


def _status_path(line: str) -> str:
    """The path out of one `git status --porcelain=v1` line."""
    text = line.rstrip("\n")
    if len(text) > 3 and text[2] == " ":
        text = text[3:]
    path = text.strip()
    # Renames and copies report `old -> new`; the new path is the product.
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip().strip('"')


def candidate_changed_paths(worktree: Path, base_sha: str) -> list[str]:
    """Everything this tree shows as touched, generated wiring excluded.

    Committed work since the contract base *and* uncommitted work, because the
    worker contract allows either style.
    """
    paths: list[str] = []
    dirty = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain=v1", "--untracked-files=all"],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if dirty.returncode == 0:
        paths.extend(_status_path(line) for line in dirty.stdout.splitlines() if line.strip())
    if base_sha:
        committed = subprocess.run(
            ["git", "-C", str(worktree), "diff", "--name-only", f"{base_sha}..HEAD"],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        if committed.returncode == 0:
            paths.extend(line.strip() for line in committed.stdout.splitlines() if line.strip())
    return workspace_wiring().product_paths(paths, worktree)


def worktree_already_implements(worktree: Path, contract: dict[str, Any]) -> bool:
    """True when a prior worker already implemented *this* task in this tree.

    L9_PE_WORKER_CMD is a subprocess adapter; the bound Cursor peer is this
    session, so a tree that already carries the task's work needs no second
    handoff. But `HEAD != base_sha` was never evidence of that: an unrelated
    commit already on the branch satisfies it just as well, and the task then
    went to verification with nothing of its own written.

    The evidence is the intersection of what changed with what the contract
    authorized this task to write, under the same changed-path semantics the
    controller verifies with. A task whose declared intent is to write nothing
    is exempt -- there is no intersection to find.
    """
    base = str(contract.get("base_sha") or "").strip()
    writable = [str(path) for path in (contract.get("writable_paths") or []) if str(path).strip()]
    changed = candidate_changed_paths(worktree, base)
    if not writable:
        # Nothing declared: fall back to "did anything at all happen here",
        # which is all the contract gives us to go on.
        return bool(changed)
    return bool(workspace_wiring().relevant_changed_paths(changed, writable, worktree))


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
        if worktree_already_implements(worktree, contract):
            return WorkerOutcome(
                invoked=False,
                changed=True,
                reason="worktree_already_modified",
                detail=f"brief written to {brief_path}; worktree already diverged from base",
            )
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
        binding = worker_binding()
        if binding["mode"] == "peer_session":
            return (
                f"{task_id} is an implementation task ({task.get('execution_kind')}) and the "
                f"bound adapter is {CURSOR_FOREGROUND_ADAPTER}, so its worktree at {worktree} "
                "is unmodified. This is an error, not a warning: verifying now would certify "
                "zero implementation. Implement the task in that worktree (brief already "
                f"written), then rerun `make campaign`. Do not set {WORKER_COMMAND_ENV} unless "
                "you intend a detached subprocess worker "
                "(placeholders: {task_id}, {worktree}, {brief}). "
                f"Worker brief: {outcome.detail}. Retry is safe."
            )
        return (
            f"{task_id} is an implementation task ({task.get('execution_kind')}) but the "
            f"configured {WORKER_COMMAND_ENV} was not invoked, so its worktree at {worktree} "
            "is unmodified. Verifying it now would certify zero implementation. Worker brief: "
            f"{outcome.detail}. Retry is safe."
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
