#!/usr/bin/env python3
"""Program Execution's finish: publish a completed campaign through the SSOT `make pr`.

Law: `PROGRAM_EXECUTION_MAKE_PR_FINISH_V1` (CANONICAL_LAW.md, AGENTS.md). A
campaign whose every task is COMPLETED publishes exactly once, and only one
way: the governance SSOT's own `make pr`, run against the campaign
integration worktree. That ceremony owns the gate, the push, the org PR
template and the composer that fills it. Program Execution owns nothing of
it: it writes the intent the composer reads, authorizes the exact verified
tree for L4 release, runs the ceremony, and records what it reports.

Never here: a raw `git push`, `gh pr create`, a REST PR write, a merge, or a
`make pr` from any checkout other than the SSOT. Merge stays
/l9-pr-remediation's.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PUBLICATION_SCHEMA = "l9.program-execution.publication.v1"
PUBLICATION_RECORD = Path("runtime") / "PUBLICATION.json"
PUBLICATION_LOG = Path("runtime") / "publication.log"
PUBLICATION_ROUTE = "make_pr_ssot"
SSOT_ENV = "L9_GOVERNANCE_DIR"
MAKE_PR_TIMEOUT_S = 3600
GIT_TIMEOUT_S = 120
L4_TIMEOUT_S = 120
#: Files the SSOT must carry for its `make pr` to be the governance ceremony.
SSOT_MARKERS = (
    "Makefile",
    ".venv/bin/python",
    "ops/autonomy/l4_local.py",
    "ops/scripts/open_pr_after_gate.sh",
    "ops/scripts/compose_pr_body.py",
)
#: Variables a campaign process carries that must not leak into the ceremony.
_STRIPPED_ENV = ("L9_CAMPAIGN_TUNNEL", "PR_STACK_BASE_EXPLICIT", "OPEN_PR", "PUSH_ONLY")

Spawn = Callable[..., subprocess.CompletedProcess[str]]


class PublicationError(RuntimeError):
    """The campaign could not be published; nothing was merged."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_child() -> Spawn:
    """`campaign_exec.run_child`: the one place a campaign process is spawned."""
    path = Path(__file__).resolve().parent / "campaign_exec.py"
    spec = importlib.util.spec_from_file_location("pe_campaign_exec_publish", path)
    if spec is None or spec.loader is None:
        raise PublicationError("SPAWNER_UNAVAILABLE", f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.run_child


# -- the route ---------------------------------------------------------------


def require_route(authority: Mapping[str, Any]) -> Mapping[str, Any]:
    """The profile's publication block, or a refusal. The runner widens nothing."""
    publication = authority.get("publication")
    if not isinstance(publication, Mapping) or publication.get("route") != PUBLICATION_ROUTE:
        raise PublicationError(
            "PUBLICATION_ROUTE_UNDECLARED",
            f"campaign_execution.publication.route must be {PUBLICATION_ROUTE!r}; "
            "Program Execution publishes only through the governance SSOT make pr",
        )
    if authority.get("merge") != "forbidden":
        raise PublicationError(
            "PUBLICATION_AUTHORITY_WIDENED", "campaign_execution.merge must stay forbidden"
        )
    return publication


def governance_ssot(environ: Mapping[str, str] | None = None) -> Path:
    """The governance SSOT clone whose Makefile owns `pr`."""
    env = os.environ if environ is None else environ
    raw = str(env.get(SSOT_ENV) or "").strip()
    ssot = (Path(raw) if raw else Path.home() / ".cursor-governance").expanduser().resolve()
    missing = [marker for marker in SSOT_MARKERS if not (ssot / marker).exists()]
    if missing:
        raise PublicationError(
            "GOVERNANCE_SSOT_UNAVAILABLE",
            f"{ssot} is not a governance SSOT able to run make pr (missing {', '.join(missing)}); "
            f"set {SSOT_ENV} to the SSOT clone",
        )
    return ssot


def sanctioned_make_pr_argv(ssot: Path, workspace: Path) -> list[str]:
    """The only publication argv Program Execution may spawn."""
    return ["make", "-C", str(ssot), "pr", f"WS={workspace}"]


def is_sanctioned_make_pr(argv: list[str], ssot: Path, workspace: Path) -> bool:
    return [str(part) for part in argv] == sanctioned_make_pr_argv(ssot, workspace)


# -- the tree being published -------------------------------------------------


def _git(spawn: Spawn, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return spawn(["git", "-C", str(repo), *args], timeout=GIT_TIMEOUT_S, env=_git_env())


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def integration_worktree(spawn: Spawn, target: Path, branch: str) -> Path:
    """The working tree whose HEAD is the campaign integration branch."""
    listed = _git(spawn, target, "worktree", "list", "--porcelain")
    if listed.returncode != 0:
        raise PublicationError(
            "TARGET_UNREADABLE", f"cannot list worktrees of {target}: {listed.stderr.strip()}"
        )
    current: Path | None = None
    for line in listed.stdout.splitlines():
        if line.startswith("worktree "):
            current = Path(line.removeprefix("worktree ").strip())
        elif line.strip() == f"branch refs/heads/{branch}" and current is not None:
            return current.resolve()
    raise PublicationError(
        "INTEGRATION_BRANCH_NOT_CHECKED_OUT",
        f"no worktree of {target} has {branch} checked out; nothing verified to publish",
    )


def program_identity(blueprint: Path) -> dict[str, str]:
    """Name and objective of the program, from the accepted Blueprint."""
    try:
        document = yaml.safe_load((blueprint / "PROGRAM.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PublicationError("PROGRAM_UNREADABLE", f"{blueprint}/PROGRAM.yaml: {exc}") from exc
    program = document.get("program") if isinstance(document, dict) else None
    if not isinstance(program, dict) or not program.get("name"):
        raise PublicationError("PROGRAM_UNREADABLE", f"{blueprint}/PROGRAM.yaml names no program")
    return {
        "id": str(program.get("id") or ""),
        "name": " ".join(str(program["name"]).split()),
        "objective": " ".join(str(program.get("objective") or "").split()),
    }


def _task_lines(blueprint: Path) -> list[str]:
    """`<task id> <title>` for every task card in the accepted Blueprint."""
    try:
        document = yaml.safe_load((blueprint / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    tasks = document.get("tasks") if isinstance(document, dict) else None
    lines: list[str] = []
    for task in tasks if isinstance(tasks, list) else []:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id") or task.get("task_id") or "").strip()
        title = " ".join(str(task.get("title") or "").split())
        if task_id:
            lines.append(f"{task_id} {title}".strip())
    return lines


def write_intent(
    workspace: Path, *, head: str, program: Mapping[str, str], tasks: list[str], campaign_id: str
) -> Path:
    """`.l9/pr/pr-intent.json` (l9.pr_intent.v1) for the SSOT composer."""
    focus = (
        f"Program Execution campaign {campaign_id}: every task below was executed in its own "
        "worker window and verified by the Controller before it was integrated. " + "; ".join(tasks)
    )
    intent = {
        "schema": "l9.pr_intent.v1",
        "head": head,
        # The campaign PR title convention (campaigns/README.md): `[<id>] <name>`.
        "title": f"[{campaign_id}] {program['name']}",
        "problem": program["objective"] or program["name"],
        "reviewer_focus": focus,
    }
    path = workspace / ".l9" / "pr" / "pr-intent.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _record(pec_workspace: Path) -> dict[str, Any] | None:
    path = pec_workspace / PUBLICATION_RECORD
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) else None


def _tail(text: str, lines: int = 40) -> str:
    return "\n".join((text or "").splitlines()[-lines:])


# -- the finish ----------------------------------------------------------------


def publish_campaign(
    *,
    pec_workspace: Path,
    campaign_id: str,
    target: Path,
    blueprint: Path,
    base_ref: str,
    authority: Mapping[str, Any],
    spawn: Spawn | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Publish the verified campaign integration branch through the SSOT `make pr`.

    Idempotent per head: a record for the same head is returned as is, and
    `make pr` itself refreshes rather than duplicates an open PR.
    """
    require_route(authority)
    run = spawn or _run_child()
    env_source = os.environ if environ is None else environ
    ssot = governance_ssot(env_source)
    branch = f"campaign/{campaign_id}"
    workspace = integration_worktree(run, target, branch)

    dirty = _git(run, workspace, "status", "--porcelain", "--untracked-files=no")
    if dirty.returncode != 0 or dirty.stdout.strip():
        raise PublicationError(
            "INTEGRATION_TREE_DIRTY",
            f"{workspace} carries uncommitted tracked changes; only verified commits publish",
        )
    head = _git(run, workspace, "rev-parse", "HEAD").stdout.strip()
    if not head:
        raise PublicationError("INTEGRATION_HEAD_UNRESOLVED", f"cannot resolve HEAD of {workspace}")

    prior = _record(pec_workspace)
    if prior and prior.get("status") == "published" and prior.get("head_sha") == head:
        return prior

    remote_branch = base_ref.removeprefix("origin/")
    fetched = _git(run, workspace, "fetch", "origin", remote_branch)
    if fetched.returncode != 0:
        raise PublicationError(
            "BASE_UNFETCHABLE", f"git fetch origin {remote_branch}: {fetched.stderr.strip()}"
        )
    ahead = _git(run, workspace, "rev-list", "--count", f"{base_ref}..HEAD").stdout.strip()
    if not ahead.isdigit() or int(ahead) < 1:
        raise PublicationError(
            "NOTHING_TO_PUBLISH", f"{branch} carries no commit ahead of {base_ref}"
        )

    python = str(ssot / ".venv" / "bin" / "python")
    l4 = str(ssot / "ops" / "autonomy" / "l4_local.py")
    for step in (
        ["begin", "--contract-id", f"pe-{campaign_id}", "--base", base_ref],
        ["authorize-release"],
    ):
        released = run(
            [python, l4, "--workspace", str(workspace), *step],
            timeout=L4_TIMEOUT_S,
            cwd=workspace,
            env=_git_env(),
        )
        if released.returncode != 0:
            raise PublicationError(
                "L4_RELEASE_REFUSED",
                f"l4_local {step[0]}: {_tail(released.stderr or released.stdout, 10)}",
            )

    program = program_identity(blueprint)
    write_intent(
        workspace,
        head=head,
        program=program,
        tasks=_task_lines(blueprint),
        campaign_id=campaign_id,
    )

    argv = sanctioned_make_pr_argv(ssot, workspace)
    child_env = dict(env_source)
    for key in _STRIPPED_ENV:
        child_env.pop(key, None)
    child_env.update(
        {"PR_REMEDIATE": "0", "PR_BASE": base_ref, "PR_STACK": "", "WS": str(workspace)}
    )
    completed = run(argv, timeout=MAKE_PR_TIMEOUT_S, cwd=workspace, env=child_env)
    log_path = pec_workspace / PUBLICATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ PR_REMEDIATE=0 PR_BASE={base_ref} {' '.join(argv)}\n"
        f"exit={completed.returncode}\n--- stdout ---\n{completed.stdout}\n"
        f"--- stderr ---\n{completed.stderr}\n",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise PublicationError(
            "MAKE_PR_FAILED",
            f"SSOT make pr exited {completed.returncode}; see {log_path}\n"
            + _tail(completed.stdout + "\n" + completed.stderr),
        )
    try:
        summary = json.loads(
            (workspace / ".l9" / "pr" / "pr-summary.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationError(
            "PUBLICATION_UNREPORTED", f"make pr passed but wrote no readable pr-summary.json: {exc}"
        ) from exc
    if not summary.get("number") or not summary.get("url"):
        raise PublicationError(
            "PUBLICATION_UNREPORTED", "pr-summary.json names no pull request number and url"
        )
    ssot_revision = _git(run, ssot, "rev-parse", "HEAD").stdout.strip()
    record = {
        "schema": PUBLICATION_SCHEMA,
        "campaign_id": campaign_id,
        "status": "published",
        "route": PUBLICATION_ROUTE,
        "repository": summary.get("repo"),
        "number": summary.get("number"),
        "url": summary.get("url"),
        "base": base_ref,
        "head_branch": branch,
        "head_sha": head,
        "published_head_sha": summary.get("head_sha"),
        "summary_source": summary.get("source"),
        "workspace": str(workspace),
        "ssot": str(ssot),
        "ssot_revision": ssot_revision,
        "command": f"PR_REMEDIATE=0 PR_BASE={base_ref} {' '.join(argv)}",
        "merge": "not_performed",
        "recorded_at": _now(),
    }
    path = pec_workspace / PUBLICATION_RECORD
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
