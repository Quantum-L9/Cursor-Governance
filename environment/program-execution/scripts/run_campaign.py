#!/usr/bin/env python3
"""Operator front door for PE campaign activation.

Sealed stages: isolate → emit → blueprint → collect → accept →
pec bootstrap (no draft) → pec reconcile → contract/claim TASK-001 →
execute every task → stacked task PRs → pec+host close → COMPLETED/.

program-execution.intent.v1 and pe-<hash> workspaces are not this path.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import pe_trace  # noqa: E402 - sibling module, imported after the sys.path guard

PE_ROOT = Path(__file__).resolve().parents[1]
GOV_ROOT = PE_ROOT.parents[1]
ACTIVATE_SCRIPT = GOV_ROOT / "skills/l9-pe-campaign-activate/scripts/compile_activation_files.py"
NUGGET_SCRIPT = GOV_ROOT / "skills/l9-pe-nuggets/scripts/extract_nuggets.py"
AUTHORIZE_SCRIPT = GOV_ROOT / "skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py"
BRIEF_SCRIPT = GOV_ROOT / "skills/l9-pe-campaign-activate/scripts/compile_brief.py"
COMPILE_SOURCE = PE_ROOT / "scripts/compile_campaign_source.py"
CAMPAIGN_INPUT = PE_ROOT / "scripts/campaign_input.py"
COLLECT_EVIDENCE = PE_ROOT / "scripts/collect_evidence.py"
ACCEPT_BLUEPRINT = PE_ROOT / "scripts/accept_blueprint.py"
VALIDATE_BLUEPRINT = (
    PE_ROOT / "core/program-execution-blueprint-template/scripts/validate_blueprint.py"
)
PEC = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
PEC_SCRIPTS = PEC.parent
ALLOWED_CAMPAIGN_FILES = {"CAMPAIGN_SOURCE.yaml", "source-integrity-receipt.json"}
UNTIL_STAGES = (
    "activate",
    "blueprint",
    "admit",
    "bootstrap",
    "arm",
    "execute",
    "pr",
    "close",
)
UNTIL_ALIASES = {"merge": "close", "bootstrap": "arm"}
STAGE_INDEX = {name: index for index, name in enumerate(UNTIL_STAGES)}
HOST_REPO_DEFAULT = "Quantum-L9/Cursor-Governance"
HASH_PROGRAM_RE = re.compile(r"^pe-[0-9a-f]{8,}$")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
FIRST_TASK_ID = "TASK-001"
PE_MODE_ENV = "L9_PE_MODE"
# Autonomous Program Execution is local-commit-only. It prepares, executes,
# validates, verifies, and commits — then stops. Pushing a branch, opening or
# updating a pull request, and merging are release actions, not campaign
# stages, and only run under an explicit governed release transition.
PE_RELEASE_ENV = "L9_PE_RELEASE_AUTHORIZED"
AUTONOMOUS_LAST_STAGE = "execute"
PUBLICATION_STAGES = ("pr", "close")
PREPARATION_STAGES = (
    "stack_proof",
    "isolate",
    "plan_window",
    "emit",
    "compile",
    "validate_blueprint",
    "launchability",
    "admission_evidence",
    "accept",
    "bootstrap",
    "arm",
)


def fast_mode(explicit: bool | None = None) -> bool:
    """Fast mode relaxes preparation ceremony, never an authority boundary."""
    if explicit is not None:
        return explicit
    return os.environ.get(PE_MODE_ENV, "").strip().lower() == "fast"


VALIDATION_TIMEOUT_S = 300
GIT_TIMEOUT_S = 45
PEC_TIMEOUT_S = 30
CLONE_TIMEOUT_S = 90
GH_TIMEOUT_S = 45
MAKE_PR_TIMEOUT_S = 180
COMPILE_TIMEOUT_S = 60
TASK_BUDGET_MINUTES = 15


class CampaignError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2, error_code: str | None = None) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        # Telemetry aggregates failures by code; without one every campaign
        # failure collapses into the single label "CampaignError".
        self.error_code = error_code


def release_authorized() -> bool:
    """True only under an explicit governed release transition.

    Publication is deliberately not a campaign stage. An autonomous run leaves
    the work as local commits; a human or `/l9-pr-remediation` carries it to the
    remote under its own authority.
    """
    return bool(os.environ.get(PE_RELEASE_ENV, "").strip())


def refuse_publication(action: str) -> None:
    """Fail closed on any remote publication outside a release transition."""
    if release_authorized():
        return
    raise CampaignError(
        f"autonomous Program Execution is local-commit-only; refusing to {action}. "
        f"Campaign execution ends at '{AUTONOMOUS_LAST_STAGE}' with local commits. "
        f"Publication is a separate governed release transition (set "
        f"{PE_RELEASE_ENV}=<reason>); merge authority belongs to /l9-pr-remediation."
    )


_PUBLICATION_GIT_SUBCOMMANDS = frozenset({"push"})
_PUBLICATION_GH_PR_SUBCOMMANDS = frozenset({"create", "merge", "edit", "ready", "close", "reopen"})
_MUTATING_HTTP_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


def _git_subcommand(rest: list[str]) -> str:
    """First non-option token, skipping the global options that take a value."""
    index = 0
    while index < len(rest):
        token = rest[index]
        if token in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return ""


def publication_command(cmd: list[str]) -> str | None:
    """Name the remote-publication action a command performs, else None.

    Every campaign subprocess funnels through `run_cmd`, so classifying here
    catches a publication path added anywhere on the execution path — including
    one added later by a refactor that forgets this boundary exists.
    """
    argv = [str(part) for part in cmd]
    if not argv:
        return None
    exe = Path(argv[0]).name
    rest = argv[1:]
    if exe == "git" and _git_subcommand(rest) in _PUBLICATION_GIT_SUBCOMMANDS:
        return "push a branch to a remote"
    if exe == "gh":
        if rest[:1] == ["pr"] and len(rest) >= 2 and rest[1] in _PUBLICATION_GH_PR_SUBCOMMANDS:
            return f"run gh pr {rest[1]}"
        if rest[:1] == ["api"]:
            for index, token in enumerate(rest):
                if token in {"-X", "--method"} and index + 1 < len(rest):
                    if rest[index + 1].upper() in _MUTATING_HTTP_METHODS:
                        return "mutate GitHub through the REST API"
        return None
    if exe == "make":
        for token in rest:
            if token.startswith("-") or ENV_ASSIGN_RE.match(token):
                continue
            if token == "pr":
                return "invoke the make pr publish path"
        return None
    # Merge authorization is a publication act wherever it is spawned from.
    if any(Path(part).name == "authorize_campaign_merge.py" for part in argv):
        return "write a merge authorization receipt"
    if any(Path(part).name == "authorize_merge.py" for part in argv):
        return "write a merge authorization receipt"
    return None


@dataclass
class Hooks:
    compile_activation: Callable[[Path, Path], dict[str, Any]] | None = None
    compile_source: Callable[[Path, Path], None] | None = None
    validate_blueprint: Callable[[Path], list[str]] | None = None
    pec_bootstrap: Callable[[Path, Path], dict[str, Any]] | None = None
    admit: Callable[[Path], dict[str, Any]] | None = None
    arm: Callable[[Path, str], dict[str, Any]] | None = None
    execute: Callable[[Path, str], dict[str, Any]] | None = None
    close: Callable[[Path, str], dict[str, Any]] | None = None
    make_pr: Callable[[Path, str], dict[str, Any]] | None = None
    push_integration: Callable[[Path, str], None] | None = None
    open_task_pr: Callable[[Path, str, dict[str, Any]], dict[str, Any]] | None = None
    pr_status: Callable[[str, int | None], dict[str, Any]] | None = None
    authorize_and_merge: Callable[[str, int], dict[str, Any]] | None = None
    git: Callable[..., str] | None = None
    context7_stack: Callable[[dict[str, Any], Path], dict[str, Any]] | None = None
    write_task_output: Callable[[Path, str, str], str] | None = None
    plan_window: Callable[[dict[str, Any], Path, Path], dict[str, Any]] | None = None


@dataclass
class CampaignReport:
    campaign_id: str
    until: str
    worktree: str
    primary: str
    blueprint: str = ""
    pec_workspace: str = ""
    host_pr: str = ""
    host_pr_number: int | None = None
    merge_sha: str = ""
    pec_note: str = ""
    activation_blockers: list[str] = field(default_factory=list)
    program_blockers: list[str] = field(default_factory=list)
    stages_completed: list[str] = field(default_factory=list)
    mode: str = "standard"
    timings: dict[str, Any] = field(default_factory=dict)
    launchability: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "timings": dict(self.timings),
            "launchability": dict(self.launchability),
            "campaign_id": self.campaign_id,
            "until": self.until,
            "worktree": self.worktree,
            "primary": self.primary,
            "blueprint": self.blueprint,
            "pec_workspace": self.pec_workspace,
            "host_pr": self.host_pr,
            "host_pr_number": self.host_pr_number,
            "merge_sha": self.merge_sha,
            "pec_note": self.pec_note,
            "activation_blockers": list(self.activation_blockers),
            "program_blockers": list(self.program_blockers),
            "stages_completed": list(self.stages_completed),
        }


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(message: str) -> None:
    print(f"campaign: {message}", flush=True)


@contextmanager
def traced(
    trace: pe_trace.ExecutionTrace | None,
    category: str,
    operation: str,
    **kwargs: Any,
) -> Iterator[dict[str, Any]]:
    """trace.span() when a trace is present, otherwise a no-op.

    Telemetry is additive: a stage that is handed no trace runs exactly as
    it did before, and never fails because tracing is unavailable.
    """
    if trace is None:
        yield {}
        return
    with trace.span(category, operation, **kwargs) as carrier:
        yield carrier


def emit(
    trace: pe_trace.ExecutionTrace | None,
    event_type: str,
    category: str,
    operation: str,
    **kwargs: Any,
) -> None:
    if trace is not None:
        trace.event(event_type, category, operation, **kwargs)


@contextmanager
def trace_stepped_aside(trace: pe_trace.ExecutionTrace | None, workspace: Path) -> Iterator[None]:
    """Hold telemetry outside `workspace` while pec bootstrap rebuilds it."""
    if trace is None:
        yield
        return
    staging = workspace.parent / f".{workspace.name}.trace-staging"
    with trace.stepped_aside(staging):
        yield


def blueprint_fingerprint(blueprint: Path) -> str:
    """SHA-256 over the compiled Blueprint pair.

    Blueprint validation and pec bootstrap both consume this directory, so
    two runs over an unchanged Blueprint share a fingerprint and the
    harvester can count the repeat.

    MANIFEST.yaml is skipped: it is nothing but a per-file sha256 index of
    the very files hashed here, taken before emission timestamps are
    normalised away. Including it would add no information and would make
    every recompilation look like a different input.
    """
    try:
        files = sorted(
            item for item in blueprint.rglob("*") if item.is_file() and item.name != "MANIFEST.yaml"
        )
    except OSError:
        return pe_trace.fingerprint(str(blueprint), "<unreadable>")
    return pe_trace.fingerprint(
        *[part for item in files for part in (str(item.relative_to(blueprint)), item)]
    )


def auto_harvest(trace: pe_trace.ExecutionTrace | None) -> None:
    """Write run-summary.{json,md} beside the events on the way out.

    A harvest failure must never replace the campaign result that is
    already on its way to the operator, so every error is a warning here.
    """
    if trace is None or trace.path is None:
        return
    workspace = trace.path.parent.parent
    try:
        pe_trace.harvest_and_write(workspace)
    except Exception as exc:  # noqa: BLE001 - telemetry never masks the run
        print(f"pe-trace: harvest failed for {workspace}: {exc}", file=sys.stderr)


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    env["GCM_INTERACTIVE"] = "never"
    return env


def run_cmd(
    cmd: list[str],
    *,
    timeout: int,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    # Single choke point: no campaign subprocess reaches a remote unless a
    # governed release transition is open.
    action = publication_command(cmd)
    if action is not None:
        refuse_publication(action)
    child_env = os.environ.copy() if env is None else dict(env)
    child_env.setdefault("L9_CAMPAIGN_TUNNEL", "1")
    try:
        return subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd is not None else None,
            env=child_env,
        )
    except subprocess.TimeoutExpired as exc:
        raise CampaignError(f"timed out after {timeout}s: {' '.join(cmd[:6])}") from exc


def load_yaml(path: Path) -> Any:
    if yaml is None:
        raise CampaignError("PyYAML required")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# File paths only. Never interpolate a caller string into import_module.
_PEC_MODULE_FILES: dict[str, Path] = {
    "exec_env": PEC_SCRIPTS / "pec" / "exec_env.py",
}


def load_pec_module(name: str) -> Any:
    """Load an allowlisted pec module from its file.

    The controller normally runs as a subprocess, but validation-environment and
    workspace-recovery logic must be identical on the campaign side; copying it
    is how the two drifted apart in the first place. The name is a whitelist
    key, not a package path — `import_module(f"pec.{name}")` is refused.
    """
    source = _PEC_MODULE_FILES.get(name)
    if source is None:
        raise CampaignError(f"refused pec module {name!r}; not in allowlist")
    path = source.resolve()
    pec_dir = (PEC_SCRIPTS / "pec").resolve()
    if path.parent != pec_dir or path.suffix != ".py" or not path.is_file():
        raise CampaignError(f"pec module is not an allowlisted file under pec/: {path}")
    module_name = f"pec.{path.stem}"
    cached = sys.modules.get(module_name)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() == path:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise CampaignError(f"cannot load pec module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def dump_yaml(path: Path, value: Any) -> None:
    if yaml is None:
        raise CampaignError("PyYAML required")
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )


def load_activate_seed(path: Path) -> dict[str, Any]:
    """Parse an *activate seed*. Only valid after classification says ACTIVATE.

    This is not a general campaign-input parser and must not be used as one: a
    campaign-source.v2 keeps `campaign_id` under `metadata` and would be
    rejected here even though it is a supported input. Route through
    `classify_campaign_input()` first.
    """
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        raise CampaignError("intent must be a mapping")
    schema = str(raw.get("schema") or "")
    if schema == "program-execution.intent.v1":
        raise CampaignError(
            "program-execution.intent.v1 is not an activate seed; "
            "need campaign_id, title, objective, and tasks"
        )
    campaign_id = str(raw.get("campaign_id") or "").strip()
    title = str(raw.get("title") or "").strip()
    objective = str(raw.get("objective") or "").strip()
    tasks = raw.get("tasks")
    if not campaign_id:
        raise CampaignError("campaign_id is required")
    if not title:
        raise CampaignError("title is required")
    if not objective:
        raise CampaignError("objective is required")
    if not isinstance(tasks, list) or not tasks:
        raise CampaignError("tasks must be a non-empty list")
    return raw


def host_campaign_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    allow = root / "environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml"
    if allow.is_file():
        for item in (load_yaml(allow) or {}).get("campaign_ids") or []:
            ids.add(str(item))
    status = root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
    if status.is_file():
        for item in (load_yaml(status) or {}).get("campaigns") or []:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            life = str(item.get("lifecycle") or "")
            if life in {"complete", "cancelled"}:
                ids.add(str(item["id"]))
    completed = root / "environment/program-execution/campaigns/COMPLETED"
    if completed.is_dir():
        for path in completed.iterdir():
            if path.is_dir() and path.name not in {"stale"}:
                ids.add(path.name)
    return ids


def resolve_operator_intent(
    path: Path,
    *,
    host_root: Path,
    target_override: str | None = None,
    primed_dir: Path | None = None,
) -> Path:
    """Return an activate-seed path. Memos are compiled; YAML seeds pass through.

    Restricted to the BRIEF and ACTIVATE routes. A campaign-source.v2 never
    reaches here — it goes straight to the campaign-source compiler so its task
    definitions, dependencies, validations, gates, and authority data are not
    rebuilt from a weaker representation.
    """
    raw: Any = None
    try:
        raw = load_yaml(path)
    except (CampaignError, Exception):
        raw = None
    if isinstance(raw, dict) and str(raw.get("schema") or "") == "program-execution.intent.v1":
        raise CampaignError(
            "program-execution.intent.v1 is not an activate seed; "
            "pass a memo .md or an activate YAML"
        )
    if (
        isinstance(raw, dict)
        and str(raw.get("campaign_id") or "").strip()
        and str(raw.get("title") or "").strip()
        and str(raw.get("objective") or "").strip()
        and isinstance(raw.get("tasks"), list)
        and raw.get("tasks")
    ):
        return path
    loader = importlib.util.spec_from_file_location("compile_brief", BRIEF_SCRIPT)
    if loader is None or loader.loader is None:
        raise CampaignError(f"cannot load {BRIEF_SCRIPT}")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    try:
        result = module.compile_brief(
            path,
            primed_dir=primed_dir,
            existing_ids=host_campaign_ids(host_root),
            target_override=target_override,
        )
    except module.BriefError as exc:
        raise CampaignError(str(exc), exit_code=getattr(exc, "exit_code", 2)) from exc
    resolved = Path(result["output"])
    log(f"brief compiled {path.name} → {resolved}")
    return resolved


def is_dirty(repo: Path) -> bool:
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        return False
    result = run_cmd(
        ["git", "-C", str(repo), "status", "--porcelain"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    return bool(result.stdout.strip())


def refuse_write_to_dirty_primary(primary: Path, write_root: Path) -> None:
    if write_root.resolve() != primary.resolve():
        return
    if is_dirty(primary):
        raise CampaignError(
            f"refuse writing dirty primary clone {primary}; "
            "use an exclusive worktree from origin/main"
        )


def _git(repo: Path, *args: str) -> str:
    result = run_cmd(
        ["git", "-C", str(repo), *args],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if result.returncode != 0:
        raise CampaignError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def ensure_workspace_wired(workspace: Path) -> None:
    """Wire gitignored .cursor links after worktree create/reuse. Not sessionStart."""
    script = GOV_ROOT / "ops/scripts/ensure_workspace_wired.sh"
    if not script.is_file() or not workspace.is_dir():
        return
    env = os.environ.copy()
    env["L9_WIRE_LINKS_ONLY"] = "1"
    run_cmd(["bash", str(script), str(workspace)], timeout=60, env=env)


def isolate_worktree(
    primary: Path,
    campaign_id: str,
    worktree: Path,
    *,
    git_fn: Callable[..., str] | None = None,
    trace: pe_trace.ExecutionTrace | None = None,
) -> Path:
    git = git_fn or (lambda *args, repo=primary: _git(repo, *args))
    git("fetch", "origin", "main")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    branch = f"feat/{campaign_id}"
    if worktree.exists():
        dirty = is_dirty(worktree)
        current = run_cmd(
            ["git", "-C", str(worktree), "rev-parse", "--abbrev-ref", "HEAD"],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if not dirty and current.returncode == 0 and current.stdout.strip() == branch:
            log(f"isolate reuse worktree {worktree}")
            ensure_workspace_wired(worktree)
            return worktree
        log(f"isolate quarantine dirty or unexpected worktree {worktree}")
        quarantine_occupied(worktree, trace=trace)
        git("worktree", "prune")
    existing = run_cmd(
        ["git", "-C", str(primary), "rev-parse", "--verify", branch],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if existing.returncode == 0:
        git("worktree", "add", str(worktree), branch)
    else:
        git("worktree", "add", "-b", branch, str(worktree), "origin/main")
    campaign_branch = f"campaign/{campaign_id}"
    has_campaign = run_cmd(
        ["git", "-C", str(worktree), "rev-parse", "--verify", f"origin/{campaign_branch}"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if has_campaign.returncode != 0:
        local = run_cmd(
            ["git", "-C", str(worktree), "rev-parse", "--verify", campaign_branch],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if local.returncode != 0:
            _git(worktree, "branch", campaign_branch, "origin/main")
    log(f"isolate worktree {worktree}")
    ensure_workspace_wired(worktree)
    return worktree


def campaign_input_module() -> Any:
    return _load_script("campaign_input", CAMPAIGN_INPUT)


def classify_campaign_input(path: Path) -> Any:
    """Classify the operator's input once, before anything can have side effects.

    Supported kinds return a classification; unsupported kinds raise the
    terminal refusal. There is deliberately no third outcome — a caller cannot
    receive "unsupported, but here is a partial route" and improvise the rest.
    """
    module = campaign_input_module()
    found = module.classify(Path(path))
    if not found.supported:
        raise module.reject(found)
    return found


def place_campaign_source(source_doc: dict[str, Any], repo_root: Path, campaign_id: str) -> None:
    """Write a supplied campaign-source.v2 to the path the compiler reads.

    This is the direct route's counterpart to `compile_activation`, minus the
    generation step: the operator's source is written verbatim rather than
    rebuilt from a weaker seed, so its tasks, dependencies, validations,
    writable paths, gates, evidence requirements, and authority data survive
    intact. Only the host registry bookkeeping is shared with the activate path.
    """
    module = _load_script("compile_activation_files", ACTIVATE_SCRIPT)
    campaign_dir = repo_root / "environment/program-execution/campaigns" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    source_path = campaign_dir / "CAMPAIGN_SOURCE.yaml"
    dump_yaml(source_path, source_doc)
    module.write_receipt(source_path, campaign_id, stamp=module.utc_now())
    hosts = (
        (
            repo_root / "environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml",
            module.patch_allowlist,
        ),
        (
            repo_root / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml",
            module.patch_execution_policy,
        ),
        (repo_root / "ops/autonomy/surface_profile.yaml", module.patch_surface_profile),
        (
            repo_root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml",
            module.patch_status_ledger,
        ),
    )
    for path, patcher in hosts:
        if not path.is_file() and path.name != "CAMPAIGN_STATUS.yaml":
            raise CampaignError(f"missing host file: {path}")
        patcher(path, campaign_id)


def default_compile_activation(intent: Path, repo_root: Path) -> dict[str, Any]:
    loader = importlib.util.spec_from_file_location("compile_activation_files", ACTIVATE_SCRIPT)
    if loader is None or loader.loader is None:
        raise CampaignError(f"cannot load {ACTIVATE_SCRIPT}")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module.compile_activation(intent, repo_root)


def default_plan_window(
    seed: dict[str, Any], primed_dir: Path, stack_proof_path: Path
) -> dict[str, Any]:
    loader = importlib.util.spec_from_file_location("extract_nuggets", NUGGET_SCRIPT)
    if loader is None or loader.loader is None:
        raise CampaignError(f"cannot load {NUGGET_SCRIPT}")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module.project_plan_window(seed, primed_dir, stack_proof_path)


def dispatch_kernel_change(verification: dict[str, Any]) -> dict[str, Any]:
    kernel = str(verification.get("kernel_verdict") or "").strip()
    gates = verification.get("gates") or {}
    failed = [name for name, value in gates.items() if value == "FAIL"]
    if kernel == "INCOMPLETE":
        return {
            "action": "skip_change",
            "reason": "INCOMPLETE does not enter CHANGE",
            "diagnosed": False,
        }
    if kernel != "FAIL":
        return {"action": "none", "diagnosed": False}
    if not failed:
        return {
            "action": "refuse",
            "reason": "Diagnose First: refuse mutate-before-diagnosis",
            "diagnosed": False,
        }
    return {
        "action": "change",
        "reason": "Diagnose First",
        "diagnosed": True,
        "failed_gates": failed,
        "kernel_profile": "CHANGE",
    }


def failed_gates(verification: dict[str, Any]) -> list[str]:
    gates = verification.get("gates") or {}
    return sorted(name for name, value in gates.items() if value == "FAIL")


def incomplete_gates(verification: dict[str, Any]) -> list[str]:
    gates = verification.get("gates") or {}
    return sorted(name for name, value in gates.items() if value in {"INCOMPLETE", "BLOCKED"})


def apply_fail_change(
    verification: dict[str, Any],
    rewrite: Callable[[], Any],
    reverify: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    decision = dispatch_kernel_change(verification)
    if decision["action"] != "change":
        return decision
    rewrite()
    verified = reverify()
    decision["reverify"] = verified
    return decision


def default_context7_stack(
    seed: dict[str, Any], primed_dir: Path, tool_cache: Any | None = None
) -> dict[str, Any]:
    # Live path never honors a skip env. Tests inject Hooks.context7_stack.
    module = _load_script("context7_stack_proof", PE_ROOT / "scripts/context7_stack_proof.py")
    try:
        return module.prove_stack(seed, primed_dir=primed_dir, tool_cache=tool_cache)
    except module.StackProofError as exc:
        raise CampaignError(str(exc), exit_code=getattr(exc, "exit_code", 2)) from exc


def refuse_hash_campaign_id(campaign_id: str) -> None:
    if HASH_PROGRAM_RE.match(campaign_id):
        raise CampaignError(
            f"{campaign_id} is a program-execution.intent.v1 hash id; "
            "operator campaigns use make campaign INTENT= only"
        )


def default_compile_source(
    source: Path,
    target: Path,
    *,
    allowlist_path: Path | None = None,
    stack_proof: Path | None = None,
) -> None:
    cmd = [
        sys.executable,
        str(COMPILE_SOURCE),
        "--source",
        str(source),
        "--target",
        str(target),
    ]
    if allowlist_path is not None:
        cmd.extend(["--allowlist", str(allowlist_path)])
    if stack_proof is not None:
        cmd.extend(["--stack-proof", str(stack_proof)])
    result = run_cmd(cmd, timeout=COMPILE_TIMEOUT_S, cwd=GOV_ROOT)
    if result.returncode != 0:
        raise CampaignError(
            f"compile_campaign_source failed: {result.stderr.strip() or result.stdout.strip()}"
        )


def default_validate_blueprint(target: Path) -> list[str]:
    result = run_cmd(
        [sys.executable, str(VALIDATE_BLUEPRINT), str(target), "--mode", "template"],
        timeout=PEC_TIMEOUT_S,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        return [detail or "template validate failed"]
    return []


def default_pec_bootstrap(workspace: Path, blueprint: Path) -> dict[str, Any]:
    first = run_cmd(
        [
            sys.executable,
            str(PEC),
            "bootstrap",
            "--workspace",
            str(workspace),
            "--blueprint",
            str(blueprint),
        ],
        timeout=PEC_TIMEOUT_S,
    )
    combined = (first.stderr + "\n" + first.stdout).strip()
    if first.returncode == 0:
        return {"ok": True, "draft": False, "output": combined}
    raise CampaignError(
        "pec bootstrap failed; make campaign must accept the blueprint before lock: " + combined
    )


def _load_script(name: str, path: Path) -> Any:
    cached = sys.modules.get(name)
    if cached is not None and getattr(cached, "__file__", None) == str(path):
        return cached
    loader = importlib.util.spec_from_file_location(name, path)
    if loader is None or loader.loader is None:
        raise CampaignError(f"cannot load {path}")
    module = importlib.util.module_from_spec(loader)
    # Registered before execution so dataclasses in the loaded module can
    # resolve their own annotations, which needs the module in sys.modules.
    sys.modules[name] = module
    try:
        loader.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def quarantine_occupied(path: Path, *, trace: pe_trace.ExecutionTrace | None = None) -> Path | None:
    """Move a leftover runtime dir aside so pec bootstrap can start empty.

    A stopped campaign leaves `$L9_ROOT/programs/<id>` occupied. The next
    `make campaign` for that id must not attach to the draft workspace.
    """
    path = path.resolve()
    if not path.exists():
        return None
    if path.is_dir() and not any(
        item.name != pe_trace.TELEMETRY_DIRNAME for item in path.iterdir()
    ):
        # Only this run's own telemetry lives here, so nothing was left
        # behind to quarantine. Tracing must not invent a workspace recycle.
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = path.parent / "stale" / f"{path.name}-{stamp}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if trace is not None:
        with trace.span(
            "workspace",
            "workspace_quarantine",
            metadata={"path": str(path), "destination": str(dest)},
        ):
            traced_events = trace.path is not None and trace.path.is_relative_to(path)
            path.rename(dest)
            if traced_events:
                # The events file moved with the workspace; follow it so the
                # recycle itself stays inside one continuous trace.
                trace.rehome(dest)
    else:
        path.rename(dest)
    log(f"quarantine occupied {path} → {dest}")
    return dest


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists() or (path / ".git").is_file()


def is_linked_worktree(path: Path) -> bool:
    return (path / ".git").is_file()


def is_shallow_repo(path: Path) -> bool:
    result = run_cmd(
        ["git", "-C", str(path), "rev-parse", "--is-shallow-repository"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    return result.returncode == 0 and (result.stdout or "").strip() == "true"


def may_clone_local(donor: Path) -> bool:
    """`clone --local` from a linked worktree or a shallow repo yields a hollow store."""
    return is_git_repo(donor) and not is_linked_worktree(donor) and not is_shallow_repo(donor)


def history_walkable(path: Path) -> bool:
    """True when HEAD exists and every parent it records is present as an object.

    A genuine root commit records no parent and is walkable. A clone taken from
    a worktree of a shallow repo records a parent SHA whose object it does not
    have, which is what makes the pec verify base_sha gate exit 128.
    """
    head = run_cmd(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    sha = (head.stdout or "").strip()
    if head.returncode != 0 or not sha:
        return False
    shown = run_cmd(
        ["git", "-C", str(path), "cat-file", "-p", sha],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if shown.returncode != 0:
        return False
    parents = [
        line.split()[1] for line in (shown.stdout or "").splitlines() if line.startswith("parent ")
    ]
    for parent in parents:
        typed = run_cmd(
            ["git", "-C", str(path), "cat-file", "-t", parent],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if typed.returncode != 0 or (typed.stdout or "").strip() != "commit":
            return False
    return True


def ensure_target_history(dest: Path, repository_id: str) -> None:
    """Fail closed unless the target can walk its own history before pec verify."""
    dest = dest.resolve()
    if history_walkable(dest) and not is_shallow_repo(dest):
        return
    origin = f"https://github.com/{repository_id}.git"
    run_cmd(
        ["git", "-C", str(dest), "remote", "set-url", "origin", origin],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if is_shallow_repo(dest):
        run_cmd(
            ["git", "-C", str(dest), "fetch", "--unshallow", "origin"],
            timeout=CLONE_TIMEOUT_S,
            env=git_env(),
        )
    if not history_walkable(dest):
        run_cmd(
            ["git", "-C", str(dest), "fetch", "origin", "--deepen=128"],
            timeout=CLONE_TIMEOUT_S,
            env=git_env(),
        )
    if not history_walkable(dest):
        raise CampaignError(f"target checkout {dest} cannot walk its parents; refuse hollow clone")


def default_ensure_target_checkout(
    dest: Path, repository_id: str, *, donor: Path | None = None
) -> Path:
    dest = dest.resolve()
    if dest.exists() and is_git_repo(dest):
        if is_dirty(dest):
            raise CampaignError(
                f"target checkout is dirty: {dest}; make campaign will not attach to a dirty target"
            )
        ensure_target_history(dest, repository_id)
        return dest
    if dest.exists():
        raise CampaignError(f"target path exists and is not a git checkout: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if (
        donor is not None
        and may_clone_local(donor)
        and donor_matches_repository(donor, repository_id)
    ):
        clone = run_cmd(
            ["git", "clone", "--local", str(donor.resolve()), str(dest)],
            timeout=CLONE_TIMEOUT_S,
            env=git_env(),
        )
        if clone.returncode == 0:
            github = f"https://github.com/{repository_id}.git"
            run_cmd(
                ["git", "-C", str(dest), "remote", "set-url", "origin", github],
                timeout=GIT_TIMEOUT_S,
                env=git_env(),
            )
            run_cmd(
                ["git", "-C", str(dest), "remote", "add", "donor", str(donor.resolve())],
                timeout=GIT_TIMEOUT_S,
                env=git_env(),
            )
            if history_walkable(dest):
                return dest
            shutil.rmtree(dest)
    url = f"https://github.com/{repository_id}.git"
    clone = run_cmd(
        ["git", "clone", url, str(dest)],
        timeout=CLONE_TIMEOUT_S,
        env=git_env(),
    )
    if clone.returncode != 0:
        raise CampaignError(
            f"cannot checkout {repository_id} at {dest}: {(clone.stderr or clone.stdout).strip()}"
        )
    return dest


def donor_matches_repository(donor: Path, repository_id: str) -> bool:
    url = run_cmd(
        ["git", "-C", str(donor), "remote", "get-url", "origin"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if url.returncode != 0:
        return False
    text = (url.stdout or "").strip().lower()
    wanted = repository_id.lower()
    return wanted in text


def fetch_stack_refs(dest: Path, campaign_id: str) -> None:
    dest = dest.resolve()
    if not is_git_repo(dest):
        return
    run_cmd(
        ["git", "-C", str(dest), "fetch", "origin", f"campaign/{campaign_id}"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    run_cmd(
        ["git", "-C", str(dest), "fetch", "origin", "refs/heads/pec/*:refs/remotes/origin/pec/*"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )


def default_reconcile(workspace: Path, repository_id: str, target_path: Path) -> dict[str, Any]:
    mapping = f"{repository_id}={target_path}"
    result = run_cmd(
        [
            sys.executable,
            str(PEC),
            "reconcile",
            "--workspace",
            str(workspace),
            "--repository",
            mapping,
        ],
        timeout=PEC_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise CampaignError(f"pec reconcile failed: {(result.stderr or result.stdout).strip()}")
    return {"ok": True, "mapping": mapping, "output": (result.stdout or "").strip()}


def default_admit(blueprint: Path, *, revision: str) -> dict[str, Any]:
    collect = _load_script("collect_evidence", COLLECT_EVIDENCE)
    accept = _load_script("accept_blueprint", ACCEPT_BLUEPRINT)
    collected = collect.collect_evidence(
        blueprint,
        evidence_id="EVID-001",
        revision=revision,
        digest=None,
        notes="make campaign admission bind",
        producer="make-campaign",
        expires_at=None,
    )
    accepted = accept.accept_blueprint(blueprint, actor="make-campaign", evidence_ids=["EVID-001"])
    return {"collected": collected, "accepted": accepted}


def locked_tasks(workspace: Path) -> list[dict[str, Any]]:
    lock_path = workspace / "runtime" / "program-lock.json"
    if not lock_path.is_file():
        raise CampaignError(f"program lock missing: {lock_path}")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    tasks = [
        item for item in (lock.get("tasks") or []) if isinstance(item, dict) and item.get("id")
    ]
    tasks.sort(key=lambda item: str(item["id"]))
    return tasks


def pec_branch(wave_id: str, task_id: str) -> str:
    return f"pec/{wave_id.lower()}/{task_id.lower()}"


def refuse_unstacked_pr_base(pr_base: str) -> None:
    name = pr_base.rsplit("/", 1)[-1]
    if name in {"main", "master"}:
        raise CampaignError(f"PRs must stack; refuse PR_BASE={pr_base}")


def build_pr_stack(campaign_id: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    integration = f"campaign/{campaign_id}"
    stack: list[dict[str, str]] = []
    previous = integration
    for task in tasks:
        task_id = str(task["id"])
        branch = pec_branch(str(task.get("wave_id") or "W0"), task_id)
        stack.append(
            {
                "task_id": task_id,
                "title": str(task.get("title") or task_id),
                "branch": branch,
                "pr_base": previous,
            }
        )
        previous = branch
    return {
        "schema": "l9.program-execution.pr-stack.v1",
        "campaign_id": campaign_id,
        "integration_branch": integration,
        "forbid_pr_base": ["main", "master", "origin/main"],
        "stack": stack,
    }


def write_pr_stack(workspace: Path, stack: dict[str, Any]) -> Path:
    path = workspace / "runtime" / "STACK.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def ensure_integration_branch(target_path: Path, campaign_id: str) -> str:
    branch = f"campaign/{campaign_id}"
    exists = run_cmd(
        ["git", "-C", str(target_path), "rev-parse", "--verify", branch],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if exists.returncode != 0:
        created = run_cmd(
            ["git", "-C", str(target_path), "branch", branch, "HEAD"],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if created.returncode != 0:
            raise CampaignError(
                f"cannot create {branch}: {(created.stderr or created.stdout).strip()}"
            )
    return branch


def register_task_contract(workspace: Path, task_id: str) -> Path:
    contract = workspace / "runtime" / f"{task_id}.source.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    draft = run_cmd(
        [
            sys.executable,
            str(PEC),
            "draft-contract",
            task_id,
            "--workspace",
            str(workspace),
            "--output",
            str(contract),
        ],
        timeout=PEC_TIMEOUT_S,
    )
    if draft.returncode != 0:
        raise CampaignError(
            f"pec draft-contract {task_id} failed: {(draft.stderr or draft.stdout).strip()}"
        )
    register = run_cmd(
        [
            sys.executable,
            str(PEC),
            "register-contract",
            task_id,
            "--workspace",
            str(workspace),
            "--file",
            str(contract),
            "--actor",
            "make-campaign",
        ],
        timeout=PEC_TIMEOUT_S,
    )
    if register.returncode != 0:
        detail = (register.stderr or register.stdout).strip()
        raise CampaignError(f"pec register-contract {task_id} failed: {detail}")
    return contract


def dependency_depth(tasks: list[dict[str, Any]]) -> dict[str, int]:
    """How many dependency hops separate each task from a task that can start now.

    Depth 0 is a task with no unmet dependency inside the program. Depth is used
    instead of `wave_id` because waves are a declared grouping and dependencies
    are the thing that actually decides what can be worked on next.

    The same edge has two spellings: an authored campaign source declares
    `depends_on`, and `pec bootstrap` freezes it into the program lock as
    `dependencies`. Read both, because this runs against the lock but is
    reasoned about against the source.
    """
    parents = {
        str(task["id"]): [
            str(dep) for dep in (task.get("dependencies") or task.get("depends_on") or ())
        ]
        for task in tasks
    }
    depth: dict[str, int] = {}

    def resolve(task_id: str, seen: frozenset[str]) -> int:
        if task_id in depth:
            return depth[task_id]
        if task_id in seen:
            # A dependency cycle is the blueprint validator's failure to report,
            # not this function's: treat it as startable rather than recursing.
            return 0
        known = [dep for dep in parents.get(task_id, ()) if dep in parents]
        value = 1 + max((resolve(dep, seen | {task_id}) for dep in known), default=-1)
        depth[task_id] = value
        return value

    for task_id in parents:
        resolve(task_id, frozenset())
    return depth


def materialization_frontier(
    tasks: list[dict[str, Any]],
    *,
    completed: Iterable[str] = (),
    lookahead: int = 1,
) -> list[str]:
    """The tasks whose contracts are worth rendering now.

    Arming used to render a contract for every locked task, which costs two
    subprocesses each and dominated preparation on a large campaign -- while all
    but the first wave described work that could not be started yet and would be
    re-rendered anyway if the program was replanned before reaching it.

    So render the runnable frontier plus `lookahead` waves beyond it: enough that
    finishing a task never waits on a render, without paying for the tail of the
    program up front. Everything else materializes on demand.
    """
    depth = dependency_depth(tasks)
    done = set(completed)
    pending = [str(task["id"]) for task in tasks if str(task["id"]) not in done]
    if not pending:
        return []
    horizon = min(depth[task_id] for task_id in pending) + lookahead
    return [task_id for task_id in pending if depth[task_id] <= horizon]


def ensure_task_contract(workspace: Path, task_id: str) -> Path:
    """Register `task_id`'s source contract unless it is already registered.

    The on-demand half of lazy materialization. Registration is idempotent for
    identical content, so the cost of calling this on an already-armed task is
    one `pec` invocation rather than a conflict.
    """
    registered = workspace / "contracts" / "source" / f"{task_id}.json"
    if registered.is_file():
        return workspace / "runtime" / f"{task_id}.source.json"
    return register_task_contract(workspace, task_id)


def default_arm(
    workspace: Path,
    campaign_id: str,
    *,
    repository_id: str,
    target_path: Path,
    trace: pe_trace.ExecutionTrace | None = None,
) -> dict[str, Any]:
    refuse_hash_campaign_id(campaign_id)
    ensure_integration_branch(target_path, campaign_id)
    with traced(trace, "reconcile", "reconcile", metadata={"repository": repository_id}):
        reconciled = default_reconcile(workspace, repository_id, target_path)
    tasks = locked_tasks(workspace)
    if not tasks or str(tasks[0]["id"]) != FIRST_TASK_ID:
        raise CampaignError("program lock is missing TASK-001")
    # Only the frontier is rendered now; the rest materializes when it is
    # claimed. The PR stack stays whole -- it is the routing map every later task
    # needs to know its base, and computing it is pure arithmetic over the lock.
    frontier = materialization_frontier(tasks, completed=completed_task_ids(workspace))
    contracts = [str(ensure_task_contract(workspace, task_id)) for task_id in frontier]
    deferred = [str(task["id"]) for task in tasks if str(task["id"]) not in set(frontier)]
    stack = build_pr_stack(campaign_id, tasks)
    write_pr_stack(workspace, stack)
    fetch_stack_refs(target_path, campaign_id)
    claim = run_cmd(
        [
            sys.executable,
            str(PEC),
            "claim",
            FIRST_TASK_ID,
            "--workspace",
            str(workspace),
            "--holder",
            "make-campaign",
            "--ttl-minutes",
            str(TASK_BUDGET_MINUTES),
        ],
        timeout=PEC_TIMEOUT_S,
    )
    return {
        "task_id": FIRST_TASK_ID,
        "armed_task_ids": list(frontier),
        "deferred_task_ids": deferred,
        "contracts": contracts,
        "claim": (claim.stdout or "").strip(),
        "reconcile": reconciled,
        "stack": stack,
    }


def default_make_pr(worktree: Path, campaign_id: str) -> dict[str, Any]:
    refuse_publication("open a host pull request")
    env = os.environ.copy()
    env["PR_BASE"] = f"origin/campaign/{campaign_id}"
    refuse_unstacked_pr_base(env["PR_BASE"])
    env["PR_REMEDIATE"] = "0"
    env["OPEN_PR"] = "1"
    result = run_cmd(["make", "pr"], timeout=MAKE_PR_TIMEOUT_S, cwd=worktree, env=env)
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        raise CampaignError(f"make pr failed: {output}")
    return {"output": output}


def default_pr_status(host_repo: str, number: int | None) -> dict[str, Any]:
    fields = "number,url,mergeable,state,headRefOid"
    cmd = ["gh", "pr", "view", "--repo", host_repo, "--json", fields]
    if number is not None:
        cmd.insert(3, str(number))
    view = run_cmd(cmd, timeout=GH_TIMEOUT_S)
    if view.returncode != 0:
        raise CampaignError(f"gh pr view failed: {view.stderr.strip()}")
    data = json.loads(view.stdout)
    checks = run_cmd(
        ["gh", "pr", "checks", str(data["number"]), "--repo", host_repo],
        timeout=GH_TIMEOUT_S,
    )
    check_text = (checks.stdout + "\n" + checks.stderr).lower()
    green = checks.returncode == 0 and "fail" not in check_text and "pending" not in check_text
    mergeable = str(data.get("mergeable") or "").upper() in {"MERGEABLE", "TRUE"}
    return {
        "number": int(data["number"]),
        "url": str(data.get("url") or ""),
        "green": green,
        "mergeable": mergeable,
        "sha": str(data.get("headRefOid") or ""),
        "output": checks.stdout.strip(),
    }


def default_authorize_and_merge(host_repo: str, number: int) -> dict[str, Any]:
    refuse_publication("authorize and merge a pull request")
    auth = run_cmd(
        [
            sys.executable,
            str(AUTHORIZE_SCRIPT),
            "--repo",
            host_repo,
            "--pr",
            str(number),
            "--reason",
            "l9-pe-campaign-activate remediation complete",
        ],
        timeout=GH_TIMEOUT_S,
    )
    if auth.returncode != 0:
        raise CampaignError(f"authorize_campaign_merge failed: {auth.stderr.strip()}")
    merge = run_cmd(
        ["gh", "pr", "merge", str(number), "--repo", host_repo, "--squash", "--delete-branch"],
        timeout=GH_TIMEOUT_S,
    )
    if merge.returncode != 0:
        raise CampaignError(f"gh pr merge failed: {merge.stderr.strip()}")
    return {"output": merge.stdout.strip()}


def campaign_source_path(worktree: Path, campaign_id: str) -> Path:
    """Where the emitted campaign source lives inside a host worktree."""
    return (
        worktree / "environment/program-execution/campaigns" / campaign_id / "CAMPAIGN_SOURCE.yaml"
    )


def assert_allowed_campaign_dir(worktree: Path, campaign_id: str) -> None:
    campaign_dir = worktree / "environment/program-execution/campaigns" / campaign_id
    if not campaign_dir.is_dir():
        raise CampaignError(f"campaign directory missing: {campaign_dir}")
    names = {path.name for path in campaign_dir.iterdir() if path.is_file()}
    extras = names - ALLOWED_CAMPAIGN_FILES
    if extras:
        raise CampaignError("forbidden extra files: " + ", ".join(sorted(extras)))
    missing = ALLOWED_CAMPAIGN_FILES - names
    if missing:
        raise CampaignError("missing campaign files: " + ", ".join(sorted(missing)))


OPERATOR_ACK_NOTE = (
    "operator_ack.acknowledged_at requires a real acknowledgment from Igor Beylin; "
    "agents must stop and ask, never forge it"
)
ACTIVE_NOTE = "launched by make campaign; pec runtime_status=active; " + OPERATOR_ACK_NOTE


def yaml_scalar(value: str) -> str:
    """Quote only when a plain scalar would change meaning."""
    raw = str(value)
    if not raw:
        return '""'
    if raw.strip() != raw or raw[0] in "'\"[{&*!|>%@`" or ": " in raw or " #" in raw:
        return json.dumps(raw)
    if raw.endswith(":") or ":" in raw and not raw.startswith("http"):
        return json.dumps(raw)
    return raw


def block_bounds(lines: list[str], start: int) -> tuple[int, int]:
    """Return (child_indent, end) for the block opened by lines[start]."""
    opener = lines[start]
    indent = len(opener) - len(opener.lstrip())
    if opener.lstrip().startswith("- "):
        indent += 2
    child_indent = None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        current = len(line) - len(line.lstrip())
        if current < indent or (current == indent and line.lstrip().startswith("- ")):
            end = index
            break
        if child_indent is None:
            child_indent = current
    return (child_indent if child_indent is not None else indent + 2, end)


def set_block_fields(lines: list[str], start: int, updates: dict[str, str]) -> list[str]:
    """Set key: value inside one YAML block, preserving comments and layout."""
    child_indent, end = block_bounds(lines, start)
    pad = " " * child_indent
    for key, value in updates.items():
        rendered = f"{pad}{key}: {yaml_scalar(value)}"
        for index in range(start, end):
            stripped = lines[index].lstrip("- ").lstrip()
            if stripped.startswith(f"{key}:"):
                if index == start:
                    head = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
                    lines[index] = f"{head}- {key}: {yaml_scalar(value)}"
                else:
                    lines[index] = rendered
                break
        else:
            lines.insert(end, rendered)
            end += 1
    return lines


def find_entry(lines: list[str], campaign_id: str) -> int | None:
    """Index of `- id: <campaign_id>` or `<campaign_id>:` in a campaigns block."""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped in {f"- id: {campaign_id}", f"{campaign_id}:"}:
            return index
    return None


def patch_yaml_text(path: Path, mutate: Callable[[list[str]], list[str] | None]) -> None:
    """Rewrite a governance YAML by line, never by load and dump.

    load_yaml then dump_yaml drops every comment in these files, and
    ops/autonomy/surface_profile.yaml tells its consumers not to fork its
    prose. Status edits are single scalars, so edit the lines in place.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = mutate(lines)
    if updated is None:
        return
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def set_top_scalar(lines: list[str], key: str, value: str) -> None:
    rendered = f"{key}: {yaml_scalar(value)}"
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[index] = rendered
            return
    lines.insert(0, rendered)


def mark_host_campaign_active(
    worktree: Path,
    campaign_id: str,
    *,
    pec_workspace: str,
    blueprint: str,
    target_worktree: str,
) -> None:
    """Promote every host status surface agents read from planned/dust to active."""
    now = utc_now()

    status_path = worktree / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
    if status_path.is_file():

        def patch_status(lines: list[str]) -> list[str]:
            set_top_scalar(lines, "updated", now)
            index = find_entry(lines, campaign_id)
            fields = {
                "lifecycle": "in_progress",
                "started_at": now,
                "launched_by": "make campaign",
                "pec_workspace": pec_workspace,
                "blueprint": blueprint,
                "worktree": target_worktree,
                "notes": ACTIVE_NOTE,
            }
            if index is None:
                for position, line in enumerate(lines):
                    if line.startswith("campaigns:"):
                        _, end = block_bounds(lines, position)
                        entry = [f"  - id: {campaign_id}"] + [
                            f"    {key}: {yaml_scalar(value)}" for key, value in fields.items()
                        ]
                        lines[end:end] = entry
                        break
                return lines
            _, end = block_bounds(lines, index)
            for position in range(index, end):
                if lines[position].strip() in {"lifecycle: complete", "lifecycle: cancelled"}:
                    return lines
            fields.pop("started_at")
            return set_block_fields(lines, index, fields)

        patch_yaml_text(status_path, patch_status)

    policy_path = (
        worktree / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml"
    )
    if policy_path.is_file():

        def patch_policy(lines: list[str]) -> list[str]:
            set_top_scalar(lines, "updated", now)
            index = find_entry(lines, campaign_id)
            if index is None:
                return lines
            return set_block_fields(
                lines, index, {"lifecycle": "in_progress", "launched_by": "make campaign"}
            )

        patch_yaml_text(policy_path, patch_policy)

    profile_path = worktree / "ops/autonomy/surface_profile.yaml"
    if profile_path.is_file():

        def patch_profile(lines: list[str]) -> list[str] | None:
            index = find_entry(lines, campaign_id)
            if index is None:
                return None
            return set_block_fields(
                lines, index, {"lifecycle": "in_progress", "launched_by": "make campaign"}
            )

        patch_yaml_text(profile_path, patch_profile)


def annotate_phase0_without_forging_ack(blueprint: Path) -> None:
    """Record that the campaign is launched. Never set operator_ack.acknowledged_at."""
    path = blueprint / "PHASE0_USER_CONFIG.yaml"
    if not path.is_file():
        return
    data = load_yaml(path)
    if not isinstance(data, dict):
        return
    ack = dict(data.get("operator_ack") or {})
    if ack.get("acknowledged_at"):
        raise CampaignError(
            "PHASE0 operator_ack.acknowledged_at is already set; "
            "make campaign will not overwrite a human acknowledgment"
        )
    ack.setdefault("name", "Igor Beylin")
    ack["acknowledged_at"] = None
    data["operator_ack"] = ack
    data["program_deploying"] = False
    completeness = dict(data.get("completeness") or {})
    completeness["phase0_complete"] = False
    data["completeness"] = completeness
    data["notes"] = (
        "Campaign launched by make campaign. " + OPERATOR_ACK_NOTE + ". "
        "program_deploying stays false until that ack."
    )
    dump_yaml(path, data)
    ops = _load_script("blueprint_ops", PE_ROOT / "scripts/blueprint_ops.py")
    compiled_from = "make-campaign"
    manifest = blueprint / "MANIFEST.yaml"
    if manifest.is_file():
        existing = load_yaml(manifest)
        if isinstance(existing, dict) and existing.get("compiled_from"):
            compiled_from = str(existing["compiled_from"])
    ops.write_manifest(blueprint, compiled_from)


def activate_pec_runtime(
    workspace: Path, *, campaign_id: str, actor: str = "make-campaign"
) -> dict[str, Any]:
    """Set pec runtime_status=active so agents do not treat draft intake as idle."""
    workspace = workspace.resolve()
    sqlite = workspace / "runtime" / "state.sqlite"
    if sqlite.is_file():
        scripts_dir = str(PEC.parent)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from pec.controller import ensure_campaign_active, open_runtime

        db, ledger = open_runtime(workspace)
        try:
            return ensure_campaign_active(workspace, actor, db, ledger)
        finally:
            db.close()
    status_path = workspace / "runtime" / "campaign-status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "program-execution-controller.campaign-status.v1",
        "campaign_id": campaign_id,
        "source_status": "operator_intake",
        "runtime_status": "active",
        "activated_at": utc_now(),
        "completed_at": None,
        "verdict": None,
        "evidence": {},
        "actor": actor,
    }
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def write_launch_pointer(
    workspace: Path,
    *,
    campaign_id: str,
    blueprint: str,
    target_worktree: str,
    host_worktree: str,
) -> Path:
    path = workspace / "runtime" / "LAUNCH.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "l9.program-execution.launch-pointer.v1",
        "campaign_id": campaign_id,
        "runtime_status": "active",
        "host_lifecycle": "in_progress",
        "pec_workspace": str(workspace),
        "blueprint": blueprint,
        "target_worktree": target_worktree,
        "host_worktree": host_worktree,
        "operator_ack_required": False,
        "operator_ack_from": "Igor Beylin",
        "forge_operator_ack": False,
        "only_pec_workspace": True,
        "claimed_task": FIRST_TASK_ID,
        "execution_card": str(workspace / "runtime" / f"{FIRST_TASK_ID}.md"),
        "pr_stack": str(workspace / "runtime" / "STACK.json"),
        "forbid_pr_base_main": True,
        "load_operator_brief": False,
        "max_task_minutes": TASK_BUDGET_MINUTES,
        "reconcile_required": True,
        "pec_ready_empty_is_expected": True,
        "write_tree": str(Path(workspace) / "worktrees" / FIRST_TASK_ID),
        "host_tree": host_worktree,
        "target_tree": target_worktree,
        "autonomy_packets_not_required": True,
        "refuse_hash_program": True,
        "next": (
            f"Read {workspace}/runtime/{FIRST_TASK_ID}.md and STACK.json. "
            f"Execute {FIRST_TASK_ID} on {target_worktree} within "
            f"{TASK_BUDGET_MINUTES} minutes. Stack every PR on the previous "
            "task branch. Never PR_BASE=main. Do not open the operator memo. "
            "If blocked, stop and report; do not sit."
        ),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def first_task_title(seed: dict[str, Any]) -> str:
    tasks = seed.get("tasks") or []
    if tasks and isinstance(tasks[0], dict):
        return str(tasks[0].get("title") or tasks[0].get("objective") or FIRST_TASK_ID).strip()
    return FIRST_TASK_ID


def write_execution_card(
    workspace: Path,
    *,
    campaign_id: str,
    target_worktree: str,
    title: str,
    task_id: str = FIRST_TASK_ID,
    pr_base: str = "",
    branch: str = "",
) -> Path:
    path = workspace / "runtime" / f"{task_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    base = pr_base or f"campaign/{campaign_id}"
    refuse_unstacked_pr_base(base)
    head = branch or pec_branch("W0", task_id)
    path.write_text(
        (
            f"# {task_id}\n\n"
            f"Campaign: `{campaign_id}`\n"
            f"Do: {title}\n"
            f"Where: `{target_worktree}`\n"
            f"Branch: `{head}`\n"
            f"PR_BASE: `{base}` — never main\n"
            f"Pec: `{workspace}`\n"
            f"Budget: {TASK_BUDGET_MINUTES} minutes. If blocked, stop and report.\n\n"
            "MUST NOT open the operator memo, attach to pe-<hash>, "
            "write the dirty primary, forge operator_ack, or open a PR onto main.\n"
        ),
        encoding="utf-8",
    )
    return path


def write_stack_cards(
    workspace: Path,
    *,
    campaign_id: str,
    target_worktree: str,
    stack: dict[str, Any],
) -> list[Path]:
    written: list[Path] = []
    for item in stack.get("stack") or []:
        written.append(
            write_execution_card(
                workspace,
                campaign_id=campaign_id,
                target_worktree=target_worktree,
                title=str(item.get("title") or item["task_id"]),
                task_id=str(item["task_id"]),
                pr_base=str(item["pr_base"]),
                branch=str(item["branch"]),
            )
        )
    return written


def default_program_blockers(
    campaign_id: str, *, armed: bool = False, executed: bool = False
) -> list[str]:
    blockers: list[str] = []
    if not armed:
        blockers.append("target work not started")
    if not executed:
        blockers.append(f"do not close {campaign_id} after host-only merge")
    if not armed:
        blockers.append("control-plane binding pending")
    return blockers


def normalize_until(until: str) -> str:
    mapped = UNTIL_ALIASES.get(until, until)
    if mapped not in STAGE_INDEX:
        raise CampaignError(
            "until must be one of " + ", ".join(UNTIL_STAGES + tuple(UNTIL_ALIASES))
        )
    return mapped


def should_run(until: str, stage: str) -> bool:
    return STAGE_INDEX[stage] <= STAGE_INDEX[until]


def pec_cmd(workspace: Path, command: str, *rest: str) -> dict[str, Any]:
    cmd = [sys.executable, str(PEC), command, *rest, "--workspace", str(workspace)]
    result = run_cmd(cmd, timeout=PEC_TIMEOUT_S)
    payload: dict[str, Any] = {}
    text = (result.stdout or "").strip()
    if text:
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = {"output": text}
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or str(payload)
        raise CampaignError(
            f"pec {command} failed: {detail}",
            error_code=f"PEC_{command.upper().replace('-', '_')}_FAILED",
        )
    return payload


def pec_status_tasks(workspace: Path) -> list[dict[str, Any]]:
    payload = pec_cmd(workspace, "status")
    return [item for item in (payload.get("tasks") or []) if isinstance(item, dict)]


def completed_task_ids(workspace: Path) -> list[str]:
    """Task ids the controller already considers COMPLETED.

    Read from the controller rather than the lock: the lock says what the program
    is, only runtime state says how far through it we are.
    """
    if not (workspace / "runtime" / "state.sqlite").is_file():
        return []
    return [
        str(item["id"])
        for item in pec_status_tasks(workspace)
        if str(item.get("runtime_state")) == "COMPLETED" and item.get("id")
    ]


def all_required_tasks_completed(workspace: Path) -> bool:
    locked = locked_tasks(workspace)
    if not locked:
        return False
    by_id = {str(item["id"]): item for item in pec_status_tasks(workspace)}
    return all(
        str(by_id.get(str(task["id"]), {}).get("runtime_state")) == "COMPLETED" for task in locked
    )


def task_output_locations(task: dict[str, Any]) -> list[str]:
    locations: list[str] = []
    for item in (task.get("source") or {}).get("outputs") or []:
        if isinstance(item, dict) and item.get("location"):
            location = str(item["location"]).strip()
            if location and not location.startswith("receipts/") and location not in locations:
                locations.append(location)
    if not locations:
        locations.append(f"docs/program-execution/{task['id']}.md")
    return locations


def task_output_location(task: dict[str, Any]) -> str:
    return task_output_locations(task)[0]


def is_stub_output(path: Path, title: str) -> bool:
    if not path.is_file():
        return True
    existing = path.read_text(encoding="utf-8")
    return existing.strip() == f"{path.stem} complete: {title}" or len(existing.strip()) < 40


def live_lock_missing_seed_paths(seed: dict[str, Any], pec_workspace: Path) -> bool:
    """True when compiled plan files are not in the live rendered contracts.

    Resume must not skip emit/relock when a companion PLAN_DOCUMENT just
    supplied writable paths the stub inspection fallback never had.
    """
    rendered = pec_workspace / "contracts" / "rendered"
    if not rendered.is_dir():
        return False
    for index, item in enumerate(seed.get("tasks") or [], start=1):
        if not isinstance(item, dict):
            continue
        declared = [str(path) for path in (item.get("paths") or []) if path]
        if not declared:
            continue
        raw_id = str(item.get("id") or "").strip()
        candidates = [name for name in (raw_id, f"TASK-{index:03d}") if name]
        found: Path | None = None
        for name in candidates:
            candidate = rendered / f"{name}.json"
            if candidate.is_file():
                found = candidate
                break
        if found is None:
            continue
        try:
            payload = json.loads(found.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True
        writable = {str(path) for path in (payload.get("writable_paths") or [])}
        if any(path not in writable for path in declared):
            return True
    return False


def resumable_workspace(workspace: Path) -> bool:
    """True when $L9_ROOT/programs/<id> is a live pec runtime, not a draft leftover."""
    launch_path = workspace / "runtime" / "LAUNCH.json"
    if not launch_path.is_file() or not (workspace / "runtime" / "program-lock.json").is_file():
        return False
    try:
        launch = json.loads(launch_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        str(launch.get("runtime_status") or "") == "active"
        and str(launch.get("host_lifecycle") or "") == "in_progress"
        and bool(str(launch.get("campaign_id") or "").strip())
    )


def runtime_already_admitted(pec_workspace: Path, blueprint: Path) -> bool:
    """Is this blueprint already frozen into the live runtime's lock?

    Acceptance precedes bootstrap by design, and `accept_blueprint` refuses to
    re-accept a blueprint some workspace has already locked. That refusal is
    correct for a fresh campaign and wrong for a resumed one, where the program
    was admitted on an earlier run and the change since then has been recorded
    per task by the relock.
    """
    lock_path = pec_workspace / "runtime" / "program-lock.json"
    if not lock_path.is_file():
        return False
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    recorded = str(lock.get("blueprint_root") or "")
    return bool(recorded) and Path(recorded).resolve() == blueprint.resolve()


def campaign_source_shape(source: Path) -> dict[str, Any] | None:
    """Digest the authored campaign source as a body plus one digest per task.

    This is the artifact an operator actually edits, so it is the only honest
    place to ask what they changed. The compiled blueprint cannot answer it:
    admission and acceptance annotate several of its files after the lock has
    frozen them, so a rerun that recompiles from an unchanged source still
    produces different digests for `PROGRAM.yaml` and `EVIDENCE_CATALOG.yaml`,
    and a per-file comparison reads one edited task card as a program-wide
    change.
    """
    doc = load_yaml(source)
    if not isinstance(doc, dict):
        return None
    body = {key: value for key, value in doc.items() if key != "tasks"}
    tasks = doc.get("tasks") or []
    if not isinstance(tasks, list):
        return None
    digests: dict[str, str] = {}
    for task in tasks:
        if not isinstance(task, dict) or not task.get("id"):
            return None
        digests[str(task["id"])] = pe_trace.fingerprint(task)
    return {"body": pe_trace.fingerprint(body), "tasks": digests}


def edited_task_ids(current: dict[str, Any], recorded: Any) -> list[str] | None:
    """Which task definitions moved, or None if the change is wider than tasks.

    Wider means anything a live runtime cannot absorb per task: the program body,
    or the set of task ids. Those decide the shape of the program the lock froze,
    so adopting them in place would leave the runtime describing a program that
    no longer exists.
    """
    if not isinstance(recorded, dict) or not isinstance(recorded.get("tasks"), dict):
        return None
    if current["body"] != recorded.get("body"):
        return None
    before: dict[str, Any] = recorded["tasks"]
    if set(before) != set(current["tasks"]):
        return None
    return sorted(
        task_id for task_id, value in current["tasks"].items() if before[task_id] != value
    )


def adopt_changed_definitions(workspace: Path, task_ids: Iterable[str]) -> dict[str, Any] | None:
    """Relock the named task definitions, or None if the runtime refuses.

    The caller decides *which* definitions moved, from the authored source; the
    controller decides whether this runtime can absorb them, by attempting the
    absorption. `pec relock` refuses without mutating, so a refusal is the
    signal to quarantine and rebuild rather than an error.
    """
    named: list[str] = []
    for task_id in task_ids:
        named.extend(["--task", str(task_id)])
    result = run_cmd(
        [
            sys.executable,
            str(PEC),
            "relock",
            "--workspace",
            str(workspace),
            "--actor",
            "make-campaign",
            *named,
        ],
        timeout=PEC_TIMEOUT_S,
    )
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def preparation_is_resumable(
    *,
    pec_workspace: Path,
    blueprint: Path,
    state: Any,
    compile_key: str,
) -> bool:
    """True when the live runtime was prepared from exactly these inputs.

    Resuming is only sound when all three agree: the pec runtime is live rather
    than a draft leftover, its blueprint is still on disk, and the compile inputs
    that produced it are the ones this run computed. A campaign whose source
    moved is a different campaign wearing the same id, and must still be
    quarantined rather than attached to.
    """
    if not resumable_workspace(pec_workspace):
        return False
    if not blueprint.is_dir():
        return False
    recorded = str((state.stages.get("compile") or {}).get("key") or "")
    return bool(recorded) and recorded == compile_key


def committed_changed_files(worktree: Path, base_sha: str, candidate_sha: str) -> list[str]:
    """Claim the diff git actually recorded, not the paths the task declared.

    pec verify compares the receipt against `git diff base..candidate`
    (`changed_files_exact`, `scope`). Claiming every declared writable path is a
    false claim for a task whose deliverables already existed at the base, and
    the honest answer for that task is an empty diff.
    """
    if base_sha == candidate_sha:
        return []
    diff = run_cmd(
        ["git", "-C", str(worktree), "diff", "--name-only", f"{base_sha}..{candidate_sha}"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if diff.returncode != 0:
        raise CampaignError(f"cannot read the committed diff: {(diff.stderr or '').strip()}")
    return [line.strip() for line in diff.stdout.splitlines() if line.strip()]


def observe_first_write(worktree: Path, changed: list[str]) -> list[str]:
    """Paths the repository shows as touched, not paths the worker claimed.

    Prefers the committed diff against the contract base, and falls back to
    the dirty working tree for workers that leave their edits uncommitted.

    Limitation: the runner drives the worker synchronously and has no
    watcher, so the earliest point at which it can observe a write is after
    the worker returns. TASK_FIRST_WRITE therefore times the first write the
    runner can *see*, which is an upper bound on when the write happened.
    Contract PE-TRACE-001 §12 accepts this in place of a watcher daemon.
    """
    if changed:
        return changed
    status = run_cmd(
        ["git", "-C", str(worktree), "status", "--porcelain", "--untracked-files=all"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if status.returncode != 0:
        return []
    return [line[3:].strip() for line in status.stdout.splitlines() if line.strip()]


def traced_verify(
    workspace: Path,
    task_id: str,
    *,
    trace: pe_trace.ExecutionTrace | None = None,
    attempt_number: int | None = None,
) -> dict[str, Any]:
    """Run one controller verification and record the attempt.

    Every call site goes through here, so a task verified three times leaves
    three TASK_VERIFY_STARTED/FINISHED pairs and the repeat is visible
    without a counter of our own.
    """
    emit(
        trace,
        "TASK_VERIFY_STARTED",
        "verification",
        "pec_verify",
        status=pe_trace.STATUS_STARTED,
        task_id=task_id,
        attempt_number=attempt_number,
    )
    with traced(
        trace,
        "verification",
        "pec_verify",
        task_id=task_id,
        attempt_number=attempt_number,
    ) as span:
        verification = pec_cmd(workspace, "verify", task_id)
        span["kernel_verdict"] = verification.get("kernel_verdict")
        span["verdict"] = verification.get("verdict")
        if verification.get("verdict") != "PASSED_LOCAL":
            span["error_code"] = str(
                verification.get("kernel_verdict") or verification.get("verdict") or "UNKNOWN"
            )
    emit(
        trace,
        "TASK_VERIFY_FINISHED",
        "verification",
        "pec_verify_finished",
        task_id=task_id,
        attempt_number=attempt_number,
        metadata={
            "kernel_verdict": verification.get("kernel_verdict"),
            "verdict": verification.get("verdict"),
        },
    )
    return verification


def run_declared_validations(
    worktree: Path,
    commands: list[str],
    *,
    trace: pe_trace.ExecutionTrace | None = None,
    task_id: str | None = None,
    attempt_number: int | None = None,
) -> list[dict[str, Any]]:
    """Run the contract's validation commands and report what actually happened.

    pec verify re-runs these commands itself and compares them against the
    attempt receipt (`worker_validation_claim`). Submitting an empty
    `validation_results` while the contract declares commands is a false claim,
    so the worker runs them first and records the real exit codes.

    Both sides go through `pec.exec_env`, so the interpreter the worker used is
    the interpreter the controller re-runs the command with.
    """
    results: list[dict[str, Any]] = []
    exec_env_mod = load_pec_module("exec_env")
    resolved = exec_env_mod.resolve_exec_env(worktree)
    for index, command in enumerate(commands, start=1):
        with traced(
            trace,
            "validation",
            "validation_command",
            task_id=task_id,
            attempt_number=attempt_number,
            # Position, not text. A contract-declared command line can carry a
            # token in a flag, and the resolved cwd is a machine path; neither
            # belongs in a persisted trace. `count` still says which of the
            # declared commands this span is.
            metadata={"count": index, "validation_count": len(commands)},
        ) as span:
            attempt_result = exec_env_mod.to_attempt_result(
                exec_env_mod.run_validation_command(
                    command, worktree, exec_env=resolved, timeout=VALIDATION_TIMEOUT_S
                )
            )
            span["exit_code"] = attempt_result["exit_code"]
            if attempt_result["exit_code"] != 0:
                # The exit code and the error code go to telemetry; the command
                # output tail stays in the receipt, not the persisted trace.
                span["error_code"] = "VALIDATION_COMMAND_FAILED"
        results.append(attempt_result)
    return results


def render_progress(
    pec_workspace: Path,
    *,
    campaign_id: str,
    timer: Any,
    timing: Any,
    published: str,
) -> str:
    """Report preparation, execution, verification and publish as separate axes.

    A completed preparation checklist is not a completed campaign, and reporting
    one number for both is how "100%" came to mean "zero tasks executed".
    """
    try:
        tasks = pec_status_tasks(pec_workspace)
    except CampaignError:
        tasks = []
    elapsed = timer.by_phase({"preparation": PREPARATION_STAGES, "execution": ("execute",)})
    report = timing.progress(
        tasks,
        campaign_id=campaign_id,
        preparation="COMPLETE",
        published=published,
        timings=elapsed,
    )
    path = pec_workspace / "runtime" / "PROGRESS.json"
    if path.parent.is_dir():
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return timing.format_progress(report)


def check_launchability(
    blueprint: Path,
    repo_root: Path,
    *,
    fast: bool,
    campaign_id: str,
) -> dict[str, Any]:
    """Refuse to bootstrap a campaign that cannot possibly execute.

    Cheap, and deliberately not a correctness proof: it only catches the
    conditions that make execution impossible, so they surface here instead of
    as an INCOMPLETE verdict or a post-bootstrap restart cycle.
    """
    module = _load_script("launchability", PE_ROOT / "scripts/launchability.py")
    tasks = module.blueprint_tasks(blueprint)
    if not tasks:
        return {"launchable": True, "task_count": 0, "findings": [], "skipped": "no_task_cards"}
    report = module.check_tasks(tasks, repo_root, infer=fast)
    # Inference is only true if it lands in the artifact the contract is rendered
    # from. Write it into the Task Cards now, while the blueprint is still ours
    # to change -- after bootstrap freezes the lock it is too late, and the task
    # would reach `pec verify` with nothing to run.
    injected = module.apply_synthesized_validations(
        blueprint, report.get("synthesized_validations") or {}
    )
    if injected:
        report["injected_validations"] = injected
        log(f"validations inferred and written into {len(injected)} task card(s)")
    receipt = blueprint / "launchability-report.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(module.format_report(report))
    if not report["launchable"]:
        detail = "; ".join(
            f"{item['task_id']}: {item['code']} — {item['remedy']}" for item in report["blockers"]
        )
        raise CampaignError(
            f"{campaign_id} is not launchable: {len(report['blockers'])} blocker(s) would make "
            f"execution impossible after bootstrap. {detail}. "
            f"Full report: {receipt}"
        )
    return report


def measure_admission_evidence(target_path: Path) -> dict[str, Any]:
    """Measure the mechanical facts admission needs instead of asking for them.

    Repository SHA, branch, and cleanliness are machine-measurable. Requiring an
    operator to type them is how the evidence ended up missing until after
    bootstrap had already frozen the blueprint and forbidden collecting it.
    """
    measured: dict[str, Any] = {"local_path": str(target_path)}
    if not is_git_repo(target_path):
        measured["available"] = False
        return measured
    for key, args in (
        ("revision", ("rev-parse", "HEAD")),
        ("branch", ("rev-parse", "--abbrev-ref", "HEAD")),
        ("tree", ("rev-parse", "HEAD^{tree}")),
    ):
        result = run_cmd(
            ["git", "-C", str(target_path), *args], timeout=GIT_TIMEOUT_S, env=git_env()
        )
        measured[key] = result.stdout.strip() if result.returncode == 0 else ""
    dirty = run_cmd(
        ["git", "-C", str(target_path), "status", "--porcelain"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    measured["clean"] = dirty.returncode == 0 and not dirty.stdout.strip()
    measured["available"] = bool(measured.get("revision"))
    return measured


def _task_card_command(cards: dict[str, Any], task_id: str) -> str:
    for task in cards.get("tasks") or []:
        if not isinstance(task, dict) or str(task.get("id") or "") != task_id:
            continue
        for entry in task.get("validation") or []:
            if isinstance(entry, dict) and entry.get("method") in {
                "command",
                "command_and_inspection",
            }:
                return str(entry.get("command_or_inspection") or "").strip()
    return ""


def fill_inferred_validation(
    contract_path: Path, contract: dict[str, Any], worktree: Path
) -> dict[str, Any]:
    """Adopt inferred validation through pec relock, never by rewriting digests.

    Hand-editing the rendered contract breaks the contract-digest gate.
    """
    launch = _load_script("launchability", PE_ROOT / "scripts/launchability.py")
    inferred = launch.infer_validation_commands(
        {"writable_paths": contract.get("writable_paths") or []},
        worktree,
    )
    existing = [str(item) for item in (contract.get("validation_commands") or []) if item]
    if not inferred or existing == inferred:
        return contract
    if "-m unittest" not in inferred[0] and "-m pytest" not in inferred[0]:
        return contract
    workspace = contract_path.parents[2]
    task_id = str(contract.get("task_id") or "")
    lock_path = workspace / "runtime" / "program-lock.json"
    if not lock_path.is_file() or not task_id:
        return contract
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    cards_path = Path(str(lock.get("blueprint_root") or "")) / "TASK_CARDS.yaml"
    if not cards_path.is_file():
        return contract
    cards = load_yaml(cards_path)
    if _task_card_command(cards, task_id) == inferred[0]:
        return contract
    changed = False
    for task in cards.get("tasks") or []:
        if not isinstance(task, dict) or str(task.get("id") or "") != task_id:
            continue
        task["validation"] = [
            {
                "id": "VAL-INFERRED-001",
                "method": "command",
                "command_or_inspection": inferred[0],
                "expected_result": "PASS",
            }
        ]
        changed = True
        break
    if not changed:
        return contract
    if yaml is None:
        raise CampaignError("PyYAML required to persist inferred validation")
    cards_path.write_text(yaml.safe_dump(cards, sort_keys=False), encoding="utf-8")
    if adopt_changed_definitions(workspace, [task_id]) is None:
        raise CampaignError(f"pec relock refused inferred validation for {task_id}")
    log(f"inferred validation adopted for {task_id}: {inferred[0]}")
    return contract


def run_worker_handoff(
    workspace: Path,
    task: dict[str, Any],
    contract: dict[str, Any],
    worktree: Path,
    *,
    hooks: Hooks,
) -> dict[str, Any]:
    """Give an implementation task to a worker before anything verifies it.

    An implementation task that reaches verification with an untouched worktree
    is an execution-path defect, not a task failure, so it is refused here with
    the reason rather than certified as complete downstream.
    """
    if hooks.write_task_output is not None:
        # A test or embedding harness owns the write step; no worker is involved.
        return {"invoked": False, "changed": False, "reason": "hook_owns_write"}
    worker = _load_script("pe_worker", PE_ROOT / "scripts/pe_worker.py")
    if worker.is_inspection_only(task):
        return {"invoked": False, "changed": False, "reason": "inspection_only"}
    outcome = worker.invoke_worker(task, contract, worktree, workspace=workspace)
    if not outcome.changed:
        raise CampaignError(worker.unexecuted_task_message(task, outcome, worktree))
    log(
        f"worker {task.get('id')} {outcome.reason} in {outcome.duration_s:.1f}s "
        f"(exit={outcome.exit_code})"
    )
    return outcome.to_dict()


def write_and_commit_output(
    worktree: Path, rel: str, title: str, writable: list[str] | None = None
) -> str:
    """Commit every declared writable file that holds real work, not one stub."""
    declared = list(dict.fromkeys([*(writable or []), rel]))
    to_add = [item for item in declared if item and not is_stub_output(worktree / item, title)]
    if not to_add:
        raise CampaignError(f"refuse stub output for {rel}; implement the task in {worktree} first")
    added = run_cmd(
        ["git", "-C", str(worktree), "add", "--", *to_add],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if added.returncode != 0:
        raise CampaignError(f"git add failed: {(added.stderr or added.stdout).strip()}")
    staged = run_cmd(
        ["git", "-C", str(worktree), "diff", "--cached", "--quiet"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if staged.returncode == 0:
        # Every declared file already holds the work at this base, so there is
        # nothing to commit. That is not an error: the task's own validation
        # command decides whether it is done, not the presence of a new commit.
        head = run_cmd(
            ["git", "-C", str(worktree), "rev-parse", "HEAD"],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if head.returncode != 0:
            raise CampaignError("cannot read candidate SHA for an already-satisfied task")
        return head.stdout.strip()
    commit = run_cmd(
        ["git", "-C", str(worktree), "commit", "-m", f"pec: {Path(rel).stem} output"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if commit.returncode != 0:
        raise CampaignError(f"git commit failed: {(commit.stderr or commit.stdout).strip()}")
    sha = run_cmd(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if sha.returncode != 0:
        raise CampaignError("cannot read candidate SHA after task commit")
    return sha.stdout.strip()


def record_stack_pr(workspace: Path, task_id: str, number: int, url: str) -> None:
    path = workspace / "runtime" / "STACK.json"
    if not path.is_file():
        return
    stack = json.loads(path.read_text(encoding="utf-8"))
    for item in stack.get("stack") or []:
        if str(item.get("task_id")) == task_id:
            item["pr_number"] = number
            item["pr_url"] = url
    path.write_text(json.dumps(stack, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def recorded_stack_pr_numbers(workspace: Path) -> list[int]:
    path = workspace / "runtime" / "STACK.json"
    if not path.is_file():
        return []
    stack = json.loads(path.read_text(encoding="utf-8"))
    numbers: list[int] = []
    for item in stack.get("stack") or []:
        number = item.get("pr_number")
        if isinstance(number, int):
            numbers.append(number)
    return numbers


def maybe_open_task_pr(
    hooks: Hooks,
    worktree: Path,
    campaign_id: str,
    item: dict[str, Any],
) -> dict[str, Any] | None:
    # Opening a task PR is publication by definition — gate it ahead of the
    # hook so an injected opener cannot route around the boundary either.
    refuse_publication("open a task pull request")
    if hooks.open_task_pr is not None:
        return hooks.open_task_pr(worktree, campaign_id, item)
    if hooks.make_pr is not None:
        return None
    refuse_unstacked_pr_base(str(item.get("pr_base") or ""))
    require_remote_campaign_branch(worktree, campaign_id)
    github = f"https://github.com/{HOST_REPO_DEFAULT}.git"
    run_cmd(
        ["git", "-C", str(worktree), "remote", "get-url", "github"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    listed = run_cmd(
        ["git", "-C", str(worktree), "remote"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    remotes = (listed.stdout or "").split()
    if "github" not in remotes:
        run_cmd(
            ["git", "-C", str(worktree), "remote", "add", "github", github],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
    pushed = run_cmd(
        ["git", "-C", str(worktree), "push", "-u", "github", str(item["branch"])],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if pushed.returncode != 0:
        raise CampaignError(
            f"cannot push {item['branch']} to GitHub: {(pushed.stderr or pushed.stdout).strip()}"
        )
    created = run_cmd(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            HOST_REPO_DEFAULT,
            "--base",
            str(item["pr_base"]),
            "--head",
            str(item["branch"]),
            "--title",
            f"[{campaign_id}] {item.get('title') or item['task_id']}",
            "--body",
            f"Stacked task PR for {item['task_id']}. Never based on main.",
        ],
        timeout=GH_TIMEOUT_S,
        cwd=worktree,
        env=git_env(),
    )
    if created.returncode != 0:
        raise CampaignError(f"gh pr create failed: {(created.stderr or created.stdout).strip()}")
    return {"output": created.stdout.strip()}


def default_execute(
    workspace: Path,
    campaign_id: str,
    *,
    hooks: Hooks,
    live_prs: bool,
    trace: pe_trace.ExecutionTrace | None = None,
    timer: Any | None = None,
) -> dict[str, Any]:
    refuse_hash_campaign_id(campaign_id)
    timing = _load_script("pe_timing", PE_ROOT / "scripts/pe_timing.py")
    timer = timer if timer is not None else timing.StageTimer(workspace)
    tasks = locked_tasks(workspace)
    stack_path = workspace / "runtime" / "STACK.json"
    stack_items = []
    if stack_path.is_file():
        stack_items = list(json.loads(stack_path.read_text(encoding="utf-8")).get("stack") or [])
    by_stack = {str(item.get("task_id")): item for item in stack_items if item.get("task_id")}
    completed: list[str] = []
    first_write_seen: set[str] = set()
    for task in tasks:
        task_id = str(task["id"])
        states = {str(item["id"]): item for item in pec_status_tasks(workspace)}
        state = str((states.get(task_id) or {}).get("runtime_state") or "")
        if state == "COMPLETED":
            completed.append(task_id)
            continue
        emit(
            trace,
            "TASK_ELIGIBLE",
            "task",
            "task_eligible",
            task_id=task_id,
            metadata={"runtime_state": state},
        )
        contract_path = workspace / "contracts" / "rendered" / f"{task_id}.json"
        worktree = workspace / "worktrees" / task_id
        already_submitted = state == "SUBMITTED"
        if already_submitted:
            if not contract_path.is_file():
                raise CampaignError(f"{task_id} is SUBMITTED without a Rendered Contract")
            rendered = {"contract": str(contract_path)}
        else:
            if state not in {
                "LEASED",
                "PREPARED",
                "CONTRACTED",
                "EXECUTING",
                "FAILED",
                "VERIFYING",
            }:
                # Arming only rendered the frontier, and a claim is refused
                # without a registered source contract. This is where a deferred
                # task becomes concrete: at the moment it is actually started.
                with traced(trace, "task_prepare", "materialize_contract", task_id=task_id):
                    ensure_task_contract(workspace, task_id)
                with traced(trace, "task_prepare", "pec_claim", task_id=task_id):
                    pec_cmd(
                        workspace,
                        "claim",
                        task_id,
                        "--holder",
                        "make-campaign",
                        "--ttl-minutes",
                        str(TASK_BUDGET_MINUTES),
                    )
                state = "LEASED"
            emit(trace, "TASK_SELECTED", "task", "task_selected", task_id=task_id)
            if state == "LEASED":
                with traced(trace, "task_prepare", "task_worktree_create", task_id=task_id):
                    prepared = pec_cmd(workspace, "prepare", task_id)
                worktree = Path(str(prepared.get("worktree") or worktree))
            if state in {"LEASED", "PREPARED"} or not contract_path.is_file():
                with traced(trace, "task_prepare", "render_contract", task_id=task_id):
                    rendered = pec_cmd(workspace, "render-contract", task_id)
            else:
                rendered = {"contract": str(contract_path)}
            if state in {"LEASED", "PREPARED", "CONTRACTED", "FAILED", "VERIFYING"}:
                pec_cmd(workspace, "start", task_id, "--actor", "make-campaign")
        ensure_workspace_wired(worktree)
        emit(
            trace,
            "TASK_WORKTREE_READY",
            "task",
            "task_worktree_ready",
            task_id=task_id,
            metadata={"worktree": str(worktree)},
        )
        contract = json.loads(Path(str(rendered["contract"])).read_text(encoding="utf-8"))
        contract = fill_inferred_validation(Path(str(rendered["contract"])), contract, worktree)
        writable = [str(path) for path in (contract.get("writable_paths") or []) if path]
        if not writable:
            writable = task_output_locations(task)
        rel = writable[0]
        title = str(task.get("title") or task_id)
        writer = hooks.write_task_output or write_and_commit_output

        def rewrite_output(
            worktree: Path = worktree,
            rel: str = rel,
            title: str = title,
            writable: list[str] = writable,
        ) -> str:
            if hooks.write_task_output is None:
                return write_and_commit_output(worktree, rel, title, writable=writable)
            return writer(worktree, rel, title)

        attempt_number: int | None = None

        def submit_attempt(
            worktree: Path = worktree,
            contract: dict[str, Any] = contract,
            task_id: str = task_id,
            task: dict[str, Any] = task,
        ) -> None:
            nonlocal attempt_number
            emit(trace, "TASK_WORKER_STARTED", "worker", "worker_started", task_id=task_id)
            with traced(trace, "worker", "worker_write", task_id=task_id):
                with timer.stage("task_worker", task_id=task_id):
                    run_worker_handoff(workspace, task, contract, worktree, hooks=hooks)
                candidate = rewrite_output()
            changed = committed_changed_files(worktree, contract["base_sha"], candidate)
            observed = observe_first_write(worktree, changed)
            if observed and task_id not in first_write_seen:
                first_write_seen.add(task_id)
                emit(
                    trace,
                    "TASK_FIRST_WRITE",
                    "filesystem_write",
                    "task_first_write",
                    task_id=task_id,
                    metadata={"path": observed[0], "changed_paths": observed[:50]},
                )
            declared_commands = [
                str(command) for command in (contract.get("validation_commands") or []) if command
            ]
            emit(
                trace,
                "TASK_VALIDATION_STARTED",
                "validation",
                "task_validation",
                status=pe_trace.STATUS_STARTED,
                task_id=task_id,
                metadata={"command_count": len(declared_commands)},
            )
            with timer.stage("task_validation", task_id=task_id):
                validation_results = run_declared_validations(
                    worktree, declared_commands, trace=trace, task_id=task_id
                )
            emit(
                trace,
                "TASK_VALIDATION_FINISHED",
                "validation",
                "task_validation_finished",
                task_id=task_id,
                metadata={
                    "failed": sum(1 for item in validation_results if item["status"] != "PASS"),
                    "total": len(validation_results),
                },
            )
            receipt = {
                "schema": "program-execution-controller.attempt-receipt.v2",
                "task_id": task_id,
                "contract_digest": contract["contract_digest"],
                "program_digest": contract["program_digest"],
                "base_sha": contract["base_sha"],
                "candidate_sha": candidate,
                "changed_files": changed,
                "validation_results": validation_results,
                "produced_evidence": [],
                "residual_unknowns": [],
                "claimed_status": "completed",
            }
            receipt_path = workspace / "runtime" / f"{task_id}.attempt.json"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            with traced(trace, "commit", "record_attempt", task_id=task_id):
                recorded = pec_cmd(
                    workspace, "record-attempt", task_id, "--receipt", str(receipt_path)
                )
            # Attempt identity is PEC state, never a counter of our own.
            if isinstance(recorded.get("attempt"), int):
                attempt_number = int(recorded["attempt"])

        def repair_attempt(task_id: str = task_id) -> None:
            """Take a FAILED verdict back to SUBMITTED as a new attempt.

            A verdict is final for the attempt that earned it. Repair therefore
            re-enters execution and submits fresh work rather than asking the
            controller to verify the same attempt a second time.
            """
            pec_cmd(workspace, "start", task_id, "--actor", "make-campaign")
            submit_attempt()

        if not already_submitted:
            submit_attempt()
        with timer.stage("task_verify", task_id=task_id):
            verification = traced_verify(
                workspace, task_id, trace=trace, attempt_number=attempt_number
            )
        decision = dispatch_kernel_change(verification)
        if decision["action"] == "skip_change":
            raise CampaignError(
                f"pec verify {task_id} INCOMPLETE: skip CHANGE ({decision['reason']}); "
                f"gates={json.dumps(incomplete_gates(verification), sort_keys=True)}. "
                "An INCOMPLETE verdict means the controller could not judge the attempt, "
                "usually because the contract declares no runnable validation command. "
                "Declare validation_commands for the task, or run with --fast to infer them."
            )
        if decision["action"] == "refuse":
            raise CampaignError(f"Diagnose First: {decision['reason']}")
        if decision["action"] == "change":
            emit(
                trace,
                "TASK_CHANGE_STARTED",
                "retry",
                "apply_fail_change",
                status=pe_trace.STATUS_STARTED,
                task_id=task_id,
                attempt_number=attempt_number,
                metadata={"reason": decision["reason"]},
            )
            with traced(
                trace,
                "retry",
                "apply_fail_change",
                task_id=task_id,
                attempt_number=attempt_number,
            ):
                apply_fail_change(
                    verification,
                    rewrite=repair_attempt,
                    reverify=lambda: traced_verify(
                        workspace, task_id, trace=trace, attempt_number=attempt_number
                    ),
                )
            verification = traced_verify(
                workspace, task_id, trace=trace, attempt_number=attempt_number
            )
            if verification.get("kernel_verdict") != "PASS":
                raise CampaignError(
                    f"pec verify {task_id} after CHANGE did not PASS: "
                    f"{verification.get('kernel_verdict') or verification.get('verdict')}; "
                    f"failed gates={decision.get('failed_gates')}"
                )
        if verification.get("verdict") != "PASSED_LOCAL":
            raise CampaignError(
                f"pec verify {task_id} did not PASS: {verification.get('verdict')}; "
                f"failed gates={json.dumps(failed_gates(verification), sort_keys=True)}"
            )
        evidence_id = str(verification["evidence_id"])
        for gate_id in task.get("completion_gates") or task.get("completion_gate_ids") or []:
            with traced(
                trace,
                "gate",
                "evaluate_gate",
                task_id=task_id,
                attempt_number=attempt_number,
                metadata={"gate_id": str(gate_id)},
            ):
                pec_cmd(
                    workspace,
                    "evaluate-gate",
                    str(gate_id),
                    "PASS",
                    "--evidence-id",
                    evidence_id,
                    "--method",
                    "inspection",
                    "--actor",
                    "make-campaign",
                )
        pec_cmd(
            workspace,
            "complete",
            task_id,
            "--actor",
            "make-campaign",
            "--evidence-id",
            evidence_id,
        )
        emit(
            trace,
            "TASK_COMPLETED",
            "task",
            "task_completed",
            task_id=task_id,
            attempt_number=attempt_number,
            metadata={"evidence_id": evidence_id},
        )
        if live_prs:
            item = by_stack.get(task_id) or {
                "task_id": task_id,
                "title": task.get("title") or task_id,
                "branch": pec_branch(str(task.get("wave_id") or "W0"), task_id),
                "pr_base": f"campaign/{campaign_id}",
            }
            with traced(trace, "publish", "open_task_pr", task_id=task_id):
                opened = maybe_open_task_pr(hooks, worktree, campaign_id, item)
            if opened and opened.get("number"):
                record_stack_pr(
                    workspace, task_id, int(opened["number"]), str(opened.get("url") or "")
                )
        completed.append(task_id)
    return {"completed": completed}


def commit_host_emit(worktree: Path, campaign_id: str) -> None:
    if not is_git_repo(worktree):
        return
    campaign_dir = f"environment/program-execution/campaigns/{campaign_id}"
    run_cmd(
        ["git", "-C", str(worktree), "add", "--", campaign_dir],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    dirty = run_cmd(
        ["git", "-C", str(worktree), "status", "--porcelain"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if not (dirty.stdout or "").strip():
        return
    commit = run_cmd(
        ["git", "-C", str(worktree), "commit", "-m", f"campaign: emit {campaign_id}"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if commit.returncode != 0:
        raise CampaignError(f"emit commit failed: {(commit.stderr or commit.stdout).strip()}")


def github_push_remote(worktree: Path, repository_id: str = HOST_REPO_DEFAULT) -> str:
    listed = run_cmd(
        ["git", "-C", str(worktree), "remote"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    remotes = (listed.stdout or "").split()
    origin = run_cmd(
        ["git", "-C", str(worktree), "remote", "get-url", "origin"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    url = (origin.stdout or "").strip()
    if url.startswith("https://github.com/") or url.startswith("git@github.com:"):
        return "origin"
    github = f"https://github.com/{repository_id}.git"
    if "github" not in remotes:
        added = run_cmd(
            ["git", "-C", str(worktree), "remote", "add", "github", github],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if added.returncode != 0:
            raise CampaignError(
                f"cannot add github remote: {(added.stderr or added.stdout).strip()}"
            )
    return "github"


def require_remote_campaign_branch(worktree: Path, campaign_id: str) -> None:
    branch = f"campaign/{campaign_id}"
    for remote in ("github", "origin"):
        check = run_cmd(
            ["git", "-C", str(worktree), "rev-parse", "--verify", f"{remote}/{branch}"],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if check.returncode == 0:
            return
        listed = run_cmd(
            ["git", "-C", str(worktree), "ls-remote", "--heads", remote, branch],
            timeout=GIT_TIMEOUT_S,
            env=git_env(),
        )
        if listed.returncode == 0 and branch in (listed.stdout or ""):
            return
    raise CampaignError(f"remote {branch} missing; push campaign branch before task PRs")


def push_integration_branch(worktree: Path, campaign_id: str) -> None:
    refuse_publication("push the campaign integration branch")
    if not is_git_repo(worktree):
        raise CampaignError("host worktree is not a git checkout; cannot push campaign branch")
    branch = f"campaign/{campaign_id}"
    exists = run_cmd(
        ["git", "-C", str(worktree), "rev-parse", "--verify", branch],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if exists.returncode != 0:
        raise CampaignError(f"local {branch} missing; cannot set PR_BASE=origin/{branch}")
    remote = github_push_remote(worktree)
    pushed = run_cmd(
        ["git", "-C", str(worktree), "push", "-u", remote, branch],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    if pushed.returncode != 0:
        raise CampaignError(f"cannot push {branch}: {(pushed.stderr or pushed.stdout).strip()}")
    require_remote_campaign_branch(worktree, campaign_id)


def default_close(
    workspace: Path,
    campaign_id: str,
    *,
    write_root: Path,
    host_repo: str,
    hooks: Hooks,
    merge_recorded: bool,
) -> dict[str, Any]:
    if merge_recorded:
        refuse_publication("merge recorded stack pull requests")
        for number in recorded_stack_pr_numbers(workspace):
            status_fn = hooks.pr_status or default_pr_status
            status = status_fn(host_repo, number)
            if not status.get("green") or not status.get("mergeable"):
                raise CampaignError(
                    f"recorded PR #{number} is not green and mergeable; merge skipped"
                )
            merge_fn = hooks.authorize_and_merge or default_authorize_and_merge
            merge_fn(host_repo, number)
    pec_cmd(
        workspace,
        "close",
        "--actor",
        "make-campaign",
        "--verdict",
        "CONVERGED",
        "--evidence",
        f"campaign_id={campaign_id}",
    )
    closer = _load_script("close_campaign", PE_ROOT / "campaigns/scripts/close_campaign.py")
    campaigns_root = write_root / "environment/program-execution/campaigns"
    closer.close_campaign(
        campaigns_root,
        campaign_id,
        "CONVERGED",
        {"campaign_id": campaign_id, "pec_workspace": str(workspace)},
        "make-campaign",
    )
    archived = closer.archive_completed(campaigns_root, campaign_id)
    return {"archived": str(archived)}


def target_head_sha(target_path: Path) -> str:
    sha = run_cmd(
        ["git", "-C", str(target_path), "rev-parse", "HEAD"],
        timeout=GIT_TIMEOUT_S,
        env=git_env(),
    )
    value = (sha.stdout or "").strip()
    if sha.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise CampaignError(f"admit requires a reconciled 40-char target HEAD, got {value!r}")
    return value


def resume_live_campaign(
    *,
    campaign_id: str,
    seed: dict[str, Any],
    requested_until: str,
    until: str,
    primary: Path,
    repo_root: Path | None,
    l9_home: Path,
    host_repo: str,
    hooks: Hooks,
    trace: pe_trace.ExecutionTrace | None = None,
) -> CampaignReport:
    """Continue an armed campaign instead of quarantining its live pec workspace.

    Re-running make campaign for an id whose runtime is active used to move
    $L9_ROOT/programs/<id> aside, stranding the leased worktree and every
    recorded attempt. An active LAUNCH.json means execute, not re-arm.
    """
    pec_workspace = l9_home / "programs" / campaign_id
    launch = json.loads((pec_workspace / "runtime" / "LAUNCH.json").read_text(encoding="utf-8"))
    if str(launch.get("campaign_id") or "").strip() != campaign_id:
        raise CampaignError(
            f"LAUNCH.json campaign_id {launch.get('campaign_id')!r} is not {campaign_id}"
        )
    host = str(launch.get("host_worktree") or launch.get("host_tree") or "")
    if repo_root is not None:
        write_root = repo_root.resolve()
    elif host:
        write_root = Path(host).resolve()
    else:
        raise CampaignError(f"resume {campaign_id}: LAUNCH.json has no host worktree")
    refuse_write_to_dirty_primary(primary, write_root)
    target_worktree = str(launch.get("target_worktree") or launch.get("target_tree") or "")
    report = CampaignReport(
        campaign_id=campaign_id,
        until=requested_until,
        worktree=str(write_root),
        primary=str(primary),
        blueprint=str(launch.get("blueprint") or (l9_home / "blueprints" / campaign_id)),
        pec_workspace=str(pec_workspace),
        program_blockers=default_program_blockers(campaign_id, armed=True),
    )
    log(f"resume {campaign_id} (runtime active; workspace kept, not quarantined)")
    report.stages_completed.append("resume")
    repository_id = str((seed.get("target") or {}).get("repository_id") or host_repo)
    target_path = Path(target_worktree) if target_worktree else None
    if target_path is not None and target_path.exists() and is_git_repo(target_path):
        if is_dirty(target_path):
            raise CampaignError(
                f"target checkout is dirty: {target_path}; "
                "make campaign will not attach to a dirty target"
            )
        with traced(trace, "reconcile", "ensure_target_history"):
            ensure_target_history(target_path, repository_id)
    log(f"execute {campaign_id}")
    with traced(trace, "execute", "execute"):
        if hooks.execute is not None:
            hooks.execute(pec_workspace, campaign_id)
        elif (pec_workspace / "runtime" / "program-lock.json").is_file():
            default_execute(
                pec_workspace,
                campaign_id,
                hooks=hooks,
                live_prs=should_run(until, "pr") and hooks.make_pr is None,
                trace=trace,
            )
    executed = False
    if (pec_workspace / "runtime" / "program-lock.json").is_file():
        executed = all_required_tasks_completed(pec_workspace)
    report.program_blockers = default_program_blockers(campaign_id, armed=True, executed=executed)
    report.stages_completed.append("execute")
    with traced(trace, "commit", "commit_host_emit"):
        commit_host_emit(write_root, campaign_id)
    if not should_run(until, "pr"):
        log("campaign complete: local commits only; publication is a release transition")
        return report
    if not executed:
        raise CampaignError("refuse host-only merge before all tasks COMPLETED", exit_code=2)
    refuse_publication("publish the campaign")
    if hooks.make_pr is None:
        pusher = hooks.push_integration or push_integration_branch
        with traced(trace, "publish", "push_integration_branch"):
            pusher(write_root, campaign_id)
    make_pr = hooks.make_pr or default_make_pr
    with traced(trace, "publish", "make_pr"):
        pr_result = make_pr(write_root, campaign_id)
    report.host_pr = str(pr_result.get("url") or pr_result.get("output") or "")
    report.host_pr_number = pr_result.get("number")
    log(f"PR {report.host_pr or report.host_pr_number or 'opened'}")
    report.stages_completed.append("pr")
    if not should_run(until, "close"):
        return report
    with traced(trace, "close", "close"):
        if hooks.close is not None:
            hooks.close(pec_workspace, campaign_id)
        else:
            default_close(
                pec_workspace,
                campaign_id,
                write_root=write_root,
                host_repo=host_repo,
                hooks=hooks,
                merge_recorded=requested_until in {"merge", "close"},
            )
    report.program_blockers = []
    report.stages_completed.append("close")
    return report


def run_campaign(
    intent_path: Path,
    *,
    until: str = AUTONOMOUS_LAST_STAGE,
    primary: Path | None = None,
    worktree: Path | None = None,
    repo_root: Path | None = None,
    l9_root: Path | None = None,
    host_repo: str = HOST_REPO_DEFAULT,
    target_override: str | None = None,
    hooks: Hooks | None = None,
    fast: bool | None = None,
) -> CampaignReport:
    """Run the campaign and leave a forensic execution trace behind it.

    Every invocation gets its own run_id, so a resumed campaign keeps the
    campaign identity and starts a new run. The trace is unbound until the
    seed names a campaign: events emitted before that are buffered and
    flushed into `<pec workspace>/telemetry/events.jsonl` on bind.
    """
    trace = pe_trace.ExecutionTrace()
    try:
        # Category "campaign" is deliberately outside the §21 time buckets:
        # this span is the wall clock, and bucketing it would double-count
        # every stage inside it.
        with traced(
            trace,
            "campaign",
            "campaign_run",
            metadata={"until": until, "host_repo": host_repo},
        ):
            return _run_campaign_stages(
                intent_path,
                until=until,
                primary=primary,
                worktree=worktree,
                repo_root=repo_root,
                l9_root=l9_root,
                host_repo=host_repo,
                target_override=target_override,
                hooks=hooks,
                fast=fast,
                trace=trace,
            )
    finally:
        auto_harvest(trace)


def _run_campaign_stages(
    intent_path: Path,
    *,
    until: str = "merge",
    primary: Path | None = None,
    worktree: Path | None = None,
    repo_root: Path | None = None,
    l9_root: Path | None = None,
    host_repo: str = HOST_REPO_DEFAULT,
    target_override: str | None = None,
    hooks: Hooks | None = None,
    fast: bool | None = None,
    trace: pe_trace.ExecutionTrace | None = None,
) -> CampaignReport:
    requested_until = until
    until = normalize_until(until)
    hooks = hooks or Hooks()
    fast = fast_mode(fast)
    timing = _load_script("pe_timing", PE_ROOT / "scripts/pe_timing.py")
    timer = timing.StageTimer()
    primary = (primary or Path.home() / ".cursor-governance").resolve()
    host_root = (repo_root or primary).resolve()
    l9_home = (l9_root or Path(os.environ.get("L9_ROOT", Path.home() / ".l9"))).resolve()
    with traced(
        trace, "input", "input_classification", metadata={"intent": str(intent_path)}
    ) as classified:
        # Classify once, before any stage can create a worktree, mutate a blueprint,
        # or touch PEC state. An unsupported input fails here in milliseconds.
        kinds = campaign_input_module().CampaignInputKind
        classification = classify_campaign_input(intent_path)
        campaign_source_doc: dict[str, Any] | None = None
        if classification.kind is kinds.CAMPAIGN_SOURCE_V2:
            campaign_source_doc = classification.document
            resolved_intent = classification.path
            seed = campaign_input_module().seed_view(campaign_source_doc or {})
        else:
            resolved_intent = resolve_operator_intent(
                intent_path,
                host_root=host_root,
                target_override=target_override or os.environ.get("TARGET"),
                primed_dir=l9_home / "primed",
            )
            seed = load_activate_seed(resolved_intent)
        campaign_id = str(seed["campaign_id"]).strip()
        if not campaign_id:
            raise CampaignError(f"campaign input has no campaign_id: {intent_path}")
        log(f"PE campaign input: {classification.kind.value}")
        log(f"campaign id: {campaign_id}")
        refuse_hash_campaign_id(campaign_id)
        classified["campaign_id"] = campaign_id
        classified["resolved_intent"] = str(resolved_intent)
    if trace is not None:
        trace.bind(l9_home / "programs" / campaign_id, campaign_id=campaign_id)
    pec_workspace = l9_home / "programs" / campaign_id
    if (
        should_run(until, "execute")
        and resumable_workspace(pec_workspace)
        and not live_lock_missing_seed_paths(seed, pec_workspace)
    ):
        return resume_live_campaign(
            campaign_id=campaign_id,
            seed=seed,
            requested_until=requested_until,
            until=until,
            primary=primary,
            repo_root=repo_root,
            l9_home=l9_home,
            host_repo=host_repo,
            hooks=hooks,
            trace=trace,
        )
    primed_root = l9_home / "primed"
    cache = timing.StageCache(primed_root / campaign_id, enabled=fast)
    # The cache and the prepare-state record live under `primed/`, deliberately
    # outside the pec workspace and the blueprint: those two get stepped aside on
    # rebuild, and evidence of what was already prepared must survive that.
    prepare = _load_script("pe_prepare_state", PE_ROOT / "scripts/pe_prepare_state.py")
    reuse = prepare.PrepareCache(
        cache,
        prepare.PrepareState.load(
            primed_root / campaign_id / "PREPARE_STATE.json", campaign_id=campaign_id
        ),
    )
    stack_fn = hooks.context7_stack or default_context7_stack
    log(f"stack-proof {campaign_id}")
    # Network-backed research is the single most expensive preparation stage and
    # the one most likely to be retried; keyed on the seed, a retry that changed
    # nothing reuses the receipt instead of re-priming.
    stack_key = timing.fingerprint(seed)

    def _stack_receipt_survives(cached: Any) -> bool:
        return Path(str((cached or {}).get("path") or "")).is_file()

    with reuse.stage(timer, "stack_proof", stack_key, verify=_stack_receipt_survives) as staged:
        if staged.reused:
            stack_receipt = dict(staged.value)
        else:
            with traced(trace, "research", "context7_stack_proof"):
                # The receipt is keyed on the whole seed, so any edit misses here
                # and the proof is rebuilt. Rebuilding it is cheap; re-proving
                # each tool over the network is not, so the default proof reuses
                # per-tool evidence that the edit did not invalidate.
                if hooks.context7_stack is not None:
                    stack_receipt = stack_fn(seed, primed_root)
                else:
                    stack_receipt = stack_fn(seed, primed_root, cache)
            staged.value = dict(stack_receipt)
    stack_proof_path = Path(
        str((stack_receipt or {}).get("path") or (primed_root / campaign_id / "stack-proof.json"))
    )
    with timer.stage("isolate"):
        if repo_root is not None:
            write_root = repo_root.resolve()
        else:
            write_root = (worktree or (l9_home / "gov-worktrees" / campaign_id)).resolve()
            with traced(trace, "workspace", "isolate_worktree"):
                write_root = isolate_worktree(
                    primary,
                    campaign_id,
                    write_root,
                    git_fn=hooks.git,
                    trace=trace,
                ).resolve()
    refuse_write_to_dirty_primary(primary, write_root)

    report = CampaignReport(
        campaign_id=campaign_id,
        until=requested_until,
        worktree=str(write_root),
        primary=str(primary),
        blueprint=str(l9_home / "blueprints" / campaign_id),
        pec_workspace=str(l9_home / "programs" / campaign_id),
        program_blockers=default_program_blockers(campaign_id, armed=False),
        mode="fast" if fast else "standard",
    )

    compile_activation = hooks.compile_activation or default_compile_activation
    if campaign_source_doc is not None:
        # A campaign source is already the fully projected artifact the plan
        # window exists to produce, and it declares its own plan_status. Running
        # it through projection and the activation compiler would rebuild it
        # from a weaker representation — the exact loss this route avoids.
        plan_status = str(campaign_source_doc.get("plan_status") or "")
        if plan_status not in {"Ready", "ConditionallyReady"}:
            raise CampaignError(
                f"plan_status {plan_status!r} is not Ready or ConditionallyReady; refuse seal"
            )
        log("compiler: compile_campaign_source (direct, no activation rebuild)")
        log(f"emit {campaign_id} into {write_root}")
        emitted = campaign_source_path(write_root, campaign_id)
        emit_key = timing.fingerprint(campaign_source_doc, str(write_root))
        with reuse.stage(timer, "emit", emit_key, outputs=[emitted]) as staged:
            if not staged.reused:
                with traced(trace, "compile", "place_campaign_source"):
                    place_campaign_source(campaign_source_doc, write_root, campaign_id)
                staged.value = {"path": str(emitted)}
    else:
        plan_fn = hooks.plan_window or default_plan_window
        log(f"plan-window {campaign_id}")
        plan_key = timing.fingerprint(seed, stack_proof_path)

        def _planned_intent_survives(receipt: Any) -> bool:
            # The receipt is only reusable while the intent it projected is still
            # on disk; the next stage reads that file.
            declared = str((receipt or {}).get("intent_path") or "")
            return not declared or Path(declared).is_file()

        with reuse.stage(timer, "plan_window", plan_key, verify=_planned_intent_survives) as staged:
            if staged.reused:
                plan_receipt = staged.value
            else:
                with traced(trace, "planning", "plan_window") as planned:
                    plan_receipt = plan_fn(seed, primed_root / campaign_id, stack_proof_path)
                    planned["plan_status"] = str(plan_receipt.get("plan_status") or "")
                staged.value = plan_receipt
        projected_intent = Path(str(plan_receipt.get("intent_path") or resolved_intent))
        if str(plan_receipt.get("plan_status") or "") not in {"Ready", "ConditionallyReady"}:
            if hooks.compile_activation is None:
                raise CampaignError(
                    f"plan_status {plan_receipt.get('plan_status')!r} is not Ready or "
                    "ConditionallyReady; refuse seal"
                )
        log(f"emit {campaign_id} into {write_root}")
        activation_input = projected_intent if projected_intent.is_file() else resolved_intent
        emitted = campaign_source_path(write_root, campaign_id)
        emit_key = timing.fingerprint(activation_input, str(write_root))
        with reuse.stage(timer, "emit", emit_key, outputs=[emitted]) as staged:
            if not staged.reused:
                with traced(trace, "compile", "compile_activation"):
                    compile_activation(activation_input, write_root)
                staged.value = {"path": str(emitted)}
    assert_allowed_campaign_dir(write_root, campaign_id)
    target_worktree = str(l9_home / "program-worktrees" / campaign_id)
    mark_host_campaign_active(
        write_root,
        campaign_id,
        pec_workspace=report.pec_workspace,
        blueprint=report.blueprint,
        target_worktree=target_worktree,
    )
    log("host status in_progress (active, not planned)")
    report.stages_completed.append("activate")
    if not should_run(until, "blueprint"):
        write_launch_pointer(
            Path(report.pec_workspace),
            campaign_id=campaign_id,
            blueprint=report.blueprint,
            target_worktree=target_worktree,
            host_worktree=str(write_root),
        )
        return report

    source = campaign_source_path(write_root, campaign_id)
    blueprint = Path(report.blueprint)
    allowlist = write_root / "environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml"
    compile_input = pe_trace.fingerprint(source, allowlist, stack_proof_path)
    # Preparing an already-prepared campaign is the operation an operator repeats
    # most often, and stepping the runtime aside to rebuild it unconditionally is
    # what made the second run cost the same as the first. Step aside only when
    # the live runtime did not come from these inputs.
    unchanged = fast and preparation_is_resumable(
        pec_workspace=Path(report.pec_workspace),
        blueprint=blueprint,
        state=reuse.state,
        compile_key=compile_input,
    )
    # A changed source is not necessarily a different campaign. Ask the source
    # itself what moved: editing one task's definition is a change a live runtime
    # can absorb per task, while the program body or the set of tasks changes the
    # shape of the program the lock froze and cannot be absorbed at all.
    shape = campaign_source_shape(source)
    edited: list[str] | None = None
    if (
        fast
        and not unchanged
        and shape is not None
        and resumable_workspace(Path(report.pec_workspace))
    ):
        edited = edited_task_ids(shape, (reuse.recorded_value("compile") or {}).get("source"))
    if unchanged:
        log(f"resume prepared runtime {report.pec_workspace} (compile inputs unchanged)")
    elif edited is None:
        quarantine_occupied(Path(report.pec_workspace), trace=trace)
        quarantine_occupied(Path(report.blueprint), trace=trace)
    log(f"blueprint {blueprint}")
    with reuse.stage(timer, "compile", compile_input, outputs=[blueprint]) as staged:
        if not staged.reused:
            with traced(
                trace, "compile", "compile_campaign_source", input_fingerprint=compile_input
            ):
                if hooks.compile_source is not None:
                    hooks.compile_source(source, blueprint)
                else:
                    default_compile_source(
                        source,
                        blueprint,
                        allowlist_path=allowlist,
                        stack_proof=stack_proof_path,
                    )
            annotate_phase0_without_forging_ack(blueprint)
            # Mint a token for this particular compiled blueprint. Stages that go
            # on to mutate the blueprint key on it rather than on compile's
            # inputs: identical inputs rebuild an identical -- but freshly
            # un-mutated -- blueprint, and keying on inputs alone would let those
            # stages skip work the new blueprint has not had done to it.
            staged.value = {
                "blueprint": str(blueprint),
                "generation": timing.fingerprint(compile_input, datetime.now(UTC).isoformat()),
                # What the program was compiled from, per task. The next run
                # compares its own source against this to decide whether the
                # drift is absorbable.
                "source": shape,
            }
    compile_generation = str((staged.value or {}).get("generation") or compile_input)

    # The edited definitions are adopted after compile, because the relock reads
    # the definitions out of the blueprint it is adopting. The runtime keeps the
    # history of everything already done; only the tasks whose definitions moved
    # lose their contract bindings.
    scoped_resume = False
    if not unchanged and edited is not None:
        with timer.stage("relock") as entry:
            adopted = (
                adopt_changed_definitions(Path(report.pec_workspace), edited) if edited else {}
            )
            entry["detail"] = adopted or {"status": "REFUSED" if edited else "CURRENT"}
        if adopted is None:
            log("runtime cannot absorb the edited definitions; rebuilding from the new blueprint")
            # The blueprint is already the new one, so only the runtime is
            # stepped aside; bootstrap then freezes what compile just produced.
            quarantine_occupied(Path(report.pec_workspace), trace=trace)
        else:
            scoped_resume = True
            relocked = ", ".join(adopted.get("relocked") or edited) or "none"
            log(
                f"resume prepared runtime {report.pec_workspace} (definitions relocked: {relocked})"
            )

    # Validation is a pure function of blueprint content, so the compiled
    # fingerprint is the whole key. A blueprint that validated once does not
    # need re-validating until it changes.
    validate_key = blueprint_fingerprint(blueprint)
    with reuse.stage(timer, "validate_blueprint", validate_key) as staged:
        if staged.reused:
            errors = list(staged.value.get("errors") or [])
        else:
            validate = hooks.validate_blueprint or default_validate_blueprint
            with traced(
                trace,
                "blueprint",
                "blueprint_validation",
                input_fingerprint=validate_key,
            ) as validated:
                errors = validate(blueprint)
                validated["error_count"] = len(errors)
                if errors:
                    validated["error_code"] = "BLUEPRINT_VALIDATION_FAILED"
                    validated["error_message"] = "; ".join(errors)
            staged.value = {"errors": list(errors)}
    if errors:
        raise CampaignError("template validate failed: " + "; ".join(errors))
    log("template validate PASS")

    launch_receipt = blueprint / "launchability-report.json"

    def _launch_receipt_survives(cached: Any) -> bool:
        # A campaign with no task cards never writes a receipt, so only demand
        # the file when the cached verdict says there was something to check.
        if int((cached or {}).get("task_count") or 0) == 0:
            return True
        return launch_receipt.is_file()

    launch_key = timing.fingerprint(validate_key, str(write_root), fast, campaign_id)
    with reuse.stage(timer, "launchability", launch_key, verify=_launch_receipt_survives) as staged:
        if staged.reused:
            report.launchability = dict(staged.value)
        else:
            report.launchability = check_launchability(
                blueprint, write_root, fast=fast, campaign_id=campaign_id
            )
            staged.value = dict(report.launchability)
    if report.launchability.get("injected_validations"):
        # Inference just edited the Task Cards that validation had already read.
        # Re-validate rather than arm a blueprint in a state nothing checked.
        validate = hooks.validate_blueprint or default_validate_blueprint
        with timer.stage("validate_blueprint_reinjected") as entry:
            errors = validate(blueprint)
            entry["detail"] = {"tasks": list(report.launchability["injected_validations"])}
        if errors:
            raise CampaignError("inferred validations broke the blueprint: " + "; ".join(errors))
    report.stages_completed.append("blueprint")
    if not should_run(until, "admit"):
        write_launch_pointer(
            Path(report.pec_workspace),
            campaign_id=campaign_id,
            blueprint=report.blueprint,
            target_worktree=target_worktree,
            host_worktree=str(write_root),
        )
        return report

    repository_id = str((seed.get("target") or {}).get("repository_id") or host_repo)
    target_path = Path(target_worktree)

    def ensure_target_checkout_once() -> None:
        """Provision the target checkout at most once while it stays present.

        Only the provisioning is cached. The revision measured from the checkout
        is admission evidence and is always read fresh: reusing a recorded SHA
        would bind a campaign to a revision the checkout no longer has.
        """
        key = timing.fingerprint(str(target_path), repository_id)
        with reuse.stage(timer, "target_checkout", key, outputs=[target_path]) as checkout:
            if not checkout.reused:
                with traced(trace, "workspace", "ensure_target_checkout"):
                    default_ensure_target_checkout(target_path, repository_id, donor=write_root)
                checkout.value = {"path": str(target_path)}

    with timer.stage("admission_evidence") as entry:
        if hooks.admit is None:
            ensure_target_checkout_once()
            measured = measure_admission_evidence(target_path)
            entry["detail"] = measured
            if not measured.get("available"):
                raise CampaignError(
                    f"cannot measure admission evidence for {campaign_id}: {target_path} is not a "
                    "readable git checkout, so repository revision cannot be bound before "
                    "bootstrap freezes the blueprint. Expected: a target checkout at that path. "
                    "Suggested next action: remove the path and re-run so it is re-cloned. "
                    "Retry is safe."
                )
            host_revision = str(measured["revision"])
        else:
            host_revision = str((seed.get("target") or {}).get("repository_id") or host_repo)
    log(f"admit EVID-001 bind {host_revision}")
    # Keyed on the compiled blueprint instance plus the revision being bound, so
    # a rebuilt blueprint is always admitted again and an unchanged one is not.
    accept_key = timing.fingerprint(compile_generation, host_revision)
    admitted_already = fast and runtime_already_admitted(Path(report.pec_workspace), blueprint)
    with reuse.stage(timer, "accept", accept_key, outputs=[blueprint]) as staged:
        if staged.reused:
            pass
        elif admitted_already:
            # The program was admitted on an earlier run and the live runtime is
            # locked to this blueprint. Re-accepting it is refused, and would add
            # nothing: what changed since is recorded per task by the relock.
            staged.value = {"revision": host_revision, "admitted_by": "existing_lock"}
        else:
            with traced(trace, "acceptance", "acceptance", metadata={"revision": host_revision}):
                if hooks.admit is not None:
                    hooks.admit(blueprint)
                else:
                    default_admit(blueprint, revision=host_revision)
            staged.value = {"revision": host_revision}
    if fast:
        # An acceptance nobody typed still has to be auditable. Record the two
        # facts it rests on, scoped local_only so publish cannot read it as
        # authority for leaving this machine.
        prepare.record_local_acceptance(
            primed_root / campaign_id / "LOCAL_ACCEPTANCE.json",
            campaign_id=campaign_id,
            revision=host_revision,
            compile_key=compile_input,
            launchability=report.launchability,
        )
        log(f"accept {prepare.LOCAL_ACCEPTED} (local_only: compile PASS + launchability PASS)")
    report.stages_completed.append("admit")
    if not should_run(until, "bootstrap"):
        write_launch_pointer(
            Path(report.pec_workspace),
            campaign_id=campaign_id,
            blueprint=report.blueprint,
            target_worktree=target_worktree,
            host_worktree=str(write_root),
        )
        return report

    pec = hooks.pec_bootstrap or default_pec_bootstrap
    pec_workspace_path = Path(report.pec_workspace)
    # Bootstrap requires an empty workspace, so the live runtime is both its
    # output and the proof it already ran. Verifying against that is what makes
    # skipping it safe: a quarantined workspace fails the check and rebuilds.
    bootstrap_key = timing.fingerprint(compile_generation, str(pec_workspace_path))
    with reuse.stage(
        timer,
        "bootstrap",
        bootstrap_key,
        verify=lambda _: resumable_workspace(pec_workspace_path),
    ) as staged:
        if staged.reused:
            pec_result = dict(staged.value or {})
        elif scoped_resume:
            # The compiled blueprint changed, so the key moved, but this runtime
            # was bootstrapped from it and the moved definitions were relocked
            # into it. Bootstrapping again would refuse: it requires an empty
            # workspace, and emptying this one is what discards the history.
            pec_result = {"ok": True, "draft": False, "output": "relocked live runtime"}
            staged.value = dict(pec_result)
        else:
            with traced(
                trace,
                "bootstrap",
                "pec_bootstrap",
                input_fingerprint=blueprint_fingerprint(blueprint),
            ):
                with trace_stepped_aside(trace, pec_workspace_path):
                    pec_result = pec(pec_workspace_path, blueprint)
                if trace is not None:
                    trace.rehome(pec_workspace_path)
            if not pec_result.get("draft"):
                staged.value = dict(pec_result)
    if pec_result.get("draft"):
        raise CampaignError("pec --admission-draft is not a live campaign path")
    # Bootstrap requires an empty workspace, so timings only start persisting
    # once the runtime directory legitimately exists.
    timer.workspace = Path(report.pec_workspace)
    timer.flush()
    report.pec_note = str(pec_result.get("output") or "")
    log("pec bootstrap ok")
    with traced(trace, "bootstrap", "pec_runtime_activate"):
        pec_status = activate_pec_runtime(Path(report.pec_workspace), campaign_id=campaign_id)
    log(f"pec runtime_status={pec_status.get('runtime_status')}")
    mark_host_campaign_active(
        write_root,
        campaign_id,
        pec_workspace=report.pec_workspace,
        blueprint=report.blueprint,
        target_worktree=target_worktree,
    )
    write_launch_pointer(
        Path(report.pec_workspace),
        campaign_id=campaign_id,
        blueprint=report.blueprint,
        target_worktree=target_worktree,
        host_worktree=str(write_root),
    )
    report.stages_completed.append("bootstrap")
    if not should_run(until, "arm"):
        return report

    log(f"arm {FIRST_TASK_ID}")
    with timer.stage("arm"):
        with traced(trace, "arm", "arm"):
            if hooks.arm is not None:
                hooks.arm(Path(report.pec_workspace), campaign_id)
            else:
                ensure_target_checkout_once()
                default_arm(
                    Path(report.pec_workspace),
                    campaign_id,
                    repository_id=repository_id,
                    target_path=target_path,
                    trace=trace,
                )
    report.timings = timer.report()
    log(
        "preparation ready: first task executable after "
        f"{timing.format_duration(sum(timer.by_phase({'prep': PREPARATION_STAGES}).values()))}"
    )
    log(timer.format())
    stack_path = Path(report.pec_workspace) / "runtime" / "STACK.json"
    if stack_path.is_file():
        write_stack_cards(
            Path(report.pec_workspace),
            campaign_id=campaign_id,
            target_worktree=target_worktree,
            stack=json.loads(stack_path.read_text(encoding="utf-8")),
        )
    else:
        write_execution_card(
            Path(report.pec_workspace),
            campaign_id=campaign_id,
            target_worktree=target_worktree,
            title=first_task_title(seed),
        )
    write_launch_pointer(
        Path(report.pec_workspace),
        campaign_id=campaign_id,
        blueprint=report.blueprint,
        target_worktree=target_worktree,
        host_worktree=str(write_root),
    )
    report.program_blockers = default_program_blockers(campaign_id, armed=True)
    report.stages_completed.append("arm")
    # No pre-execution push. Execution is local: the integration branch reaches
    # a remote only through the release transition below, never to set up work.
    if not should_run(until, "execute"):
        return report

    log(f"execute {campaign_id}")
    pec_workspace = Path(report.pec_workspace)
    with timer.stage("execute"):
        with traced(trace, "execute", "execute"):
            if hooks.execute is not None:
                hooks.execute(pec_workspace, campaign_id)
            elif (pec_workspace / "runtime" / "program-lock.json").is_file():
                default_execute(
                    pec_workspace,
                    campaign_id,
                    hooks=hooks,
                    live_prs=should_run(until, "pr") and hooks.make_pr is None,
                    trace=trace,
                    timer=timer,
                )
    executed = False
    if (pec_workspace / "runtime" / "program-lock.json").is_file():
        executed = all_required_tasks_completed(pec_workspace)
    report.timings = timer.report()
    log(
        render_progress(
            pec_workspace,
            campaign_id=campaign_id,
            timer=timer,
            timing=timing,
            published="PENDING" if should_run(until, "pr") else "NOT STARTED",
        )
    )
    report.program_blockers = default_program_blockers(campaign_id, armed=True, executed=executed)
    report.stages_completed.append("execute")
    with traced(trace, "commit", "commit_host_emit"):
        commit_host_emit(write_root, campaign_id)
    if not should_run(until, "pr"):
        log("campaign complete: local commits only; publication is a release transition")
        return report

    if not executed:
        raise CampaignError(
            "refuse host-only merge before all tasks COMPLETED",
            exit_code=2,
        )
    refuse_publication("publish the campaign")
    if hooks.make_pr is None:
        pusher = hooks.push_integration or push_integration_branch
        with traced(trace, "publish", "push_integration_branch"):
            pusher(write_root, campaign_id)
    make_pr = hooks.make_pr or default_make_pr
    with traced(trace, "publish", "make_pr"):
        pr_result = make_pr(write_root, campaign_id)
    report.host_pr = str(pr_result.get("url") or pr_result.get("output") or "")
    report.host_pr_number = pr_result.get("number")
    log(f"PR {report.host_pr or report.host_pr_number or 'opened'}")
    report.stages_completed.append("pr")
    if not should_run(until, "close"):
        return report

    close = hooks.close or default_close
    with traced(trace, "close", "close"):
        if hooks.close is not None:
            close(pec_workspace, campaign_id)
        else:
            default_close(
                pec_workspace,
                campaign_id,
                write_root=write_root,
                host_repo=host_repo,
                hooks=hooks,
                merge_recorded=requested_until in {"merge", "close"},
            )
    report.program_blockers = []
    report.stages_completed.append("close")
    return report


def render_report(report: CampaignReport) -> None:
    log(f"activation blockers: {', '.join(report.activation_blockers) or 'none'}")
    log(f"program blockers: {', '.join(report.program_blockers) or 'none'}")
    print(json.dumps(report.to_dict(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", type=Path, default=None)
    parser.add_argument(
        "--check-input",
        type=Path,
        default=None,
        metavar="PATH",
        help="Classify a campaign input and print its route. Runs no campaign stage.",
    )
    parser.add_argument(
        "--until",
        choices=list(UNTIL_STAGES) + list(UNTIL_ALIASES),
        default=AUTONOMOUS_LAST_STAGE,
        help=(
            "Last stage to run. Autonomous execution ends at "
            f"'{AUTONOMOUS_LAST_STAGE}' with local commits; {PUBLICATION_STAGES} "
            f"require the release transition ({PE_RELEASE_ENV})"
        ),
    )
    parser.add_argument("--primary", type=Path, default=None)
    parser.add_argument("--worktree", type=Path, default=None)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Write into this checkout and skip isolate (tests / already-isolated worktree)",
    )
    parser.add_argument(
        "--l9-root",
        type=Path,
        default=None,
        help="Runtime root for blueprints/programs/worktrees (default $HOME/.l9)",
    )
    parser.add_argument("--host-repo", default=HOST_REPO_DEFAULT)
    parser.add_argument(
        "--target",
        default=None,
        help="Optional owner/repo override when INTENT is a memo",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        default=None,
        help=(
            "Relax preparation ceremony: infer validations, reuse unchanged preparation "
            "artifacts, validate per task during execution. Safety boundaries are unchanged "
            f"(equivalent to {PE_MODE_ENV}=fast)"
        ),
    )
    return parser


def refuse_live_until_shortcut(until: str) -> None:
    resolved = UNTIL_ALIASES.get(until, until)
    if resolved in PUBLICATION_STAGES:
        # Reaching a publication stage at all requires the release transition.
        refuse_publication(f"run the campaign through '{resolved}'")
        return
    if resolved == AUTONOMOUS_LAST_STAGE:
        return
    if os.environ.get("L9_CAMPAIGN_UNTIL_DEBUG") == "1":
        return
    raise CampaignError(
        "CAMPAIGN_UNTIL is not a live campaign path; make campaign runs through "
        f"'{AUTONOMOUS_LAST_STAGE}' and stops at local commits. "
        "Set L9_CAMPAIGN_UNTIL_DEBUG=1 only for runner tests."
    )


def build_trace_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_campaign.py trace",
        description="Harvest the execution trace a campaign run left behind.",
    )
    parser.add_argument(
        "--workspace",
        required=True,
        type=Path,
        help="pec workspace holding telemetry/events.jsonl",
    )
    parser.add_argument("--json", action="store_true", help="print the JSON summary")
    return parser


def trace_command(argv: list[str]) -> int:
    """Harvest telemetry into run-summary.{json,md} and print a digest.

    The caller asked for telemetry here, so unlike campaign execution this
    path reports a harvest failure instead of warning and continuing.
    """
    args = build_trace_parser().parse_args(argv)
    workspace = args.workspace.resolve()
    events = workspace / pe_trace.TELEMETRY_DIRNAME / pe_trace.EVENTS_FILENAME
    if not events.is_file():
        print(f"FAIL: no execution trace at {events}", file=sys.stderr)
        return 2
    summary = pe_trace.harvest_and_write(workspace)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(pe_trace.render_terminal_summary(summary))
        print(f"wrote {workspace / pe_trace.TELEMETRY_DIRNAME / pe_trace.SUMMARY_JSON_FILENAME}")
        print(f"wrote {workspace / pe_trace.TELEMETRY_DIRNAME / pe_trace.SUMMARY_MD_FILENAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "trace":
        return trace_command(raw[1:])
    parser = build_parser()
    args = parser.parse_args(raw)
    if args.check_input is not None:
        return campaign_input_module().main([str(args.check_input)])
    if args.intent is None:
        parser.error("--intent is required (or use --check-input PATH)")
    module = campaign_input_module()
    try:
        refuse_live_until_shortcut(args.until)
        report = run_campaign(
            args.intent.resolve(),
            until=args.until,
            primary=args.primary,
            worktree=args.worktree,
            repo_root=args.repo_root,
            l9_root=args.l9_root,
            host_repo=args.host_repo,
            target_override=args.target,
            fast=args.fast,
        )
    except module.CampaignInputRejected as exc:
        # Printed whole and unadorned: this text is meant to be pasted to an
        # operator, and it already says nothing ran and bypass is forbidden.
        print(exc.render(), file=sys.stderr)
        return exc.exit_code
    except CampaignError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code
    render_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
