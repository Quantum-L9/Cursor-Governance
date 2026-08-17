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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PE_ROOT = Path(__file__).resolve().parents[1]
GOV_ROOT = PE_ROOT.parents[1]
ACTIVATE_SCRIPT = GOV_ROOT / "skills/l9-pe-campaign-activate/scripts/compile_activation_files.py"
NUGGET_SCRIPT = GOV_ROOT / "skills/l9-pe-campaign-activate/scripts/extract_nuggets.py"
AUTHORIZE_SCRIPT = GOV_ROOT / "skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py"
BRIEF_SCRIPT = GOV_ROOT / "skills/l9-pe-campaign-activate/scripts/compile_brief.py"
COMPILE_SOURCE = PE_ROOT / "scripts/compile_campaign_source.py"
COLLECT_EVIDENCE = PE_ROOT / "scripts/collect_evidence.py"
ACCEPT_BLUEPRINT = PE_ROOT / "scripts/accept_blueprint.py"
VALIDATE_BLUEPRINT = (
    PE_ROOT / "core/program-execution-blueprint-template/scripts/validate_blueprint.py"
)
PEC = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
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
FIRST_TASK_ID = "TASK-001"
GIT_TIMEOUT_S = 45
PEC_TIMEOUT_S = 30
CLONE_TIMEOUT_S = 90
GH_TIMEOUT_S = 45
MAKE_PR_TIMEOUT_S = 180
COMPILE_TIMEOUT_S = 60
TASK_BUDGET_MINUTES = 15


class CampaignError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


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

    def to_dict(self) -> dict[str, Any]:
        return {
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


def dump_yaml(path: Path, value: Any) -> None:
    if yaml is None:
        raise CampaignError("PyYAML required")
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )


def load_activate_seed(path: Path) -> dict[str, Any]:
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
    """Return an activate-seed path. Memos are compiled; YAML seeds pass through."""
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


def isolate_worktree(
    primary: Path,
    campaign_id: str,
    worktree: Path,
    *,
    git_fn: Callable[..., str] | None = None,
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
            return worktree
        log(f"isolate quarantine dirty or unexpected worktree {worktree}")
        quarantine_occupied(worktree)
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
    return worktree


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


def default_context7_stack(seed: dict[str, Any], primed_dir: Path) -> dict[str, Any]:
    # Live path never honors a skip env. Tests inject Hooks.context7_stack.
    module = _load_script("context7_stack_proof", PE_ROOT / "scripts/context7_stack_proof.py")
    try:
        return module.prove_stack(seed, primed_dir=primed_dir)
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
    loader = importlib.util.spec_from_file_location(name, path)
    if loader is None or loader.loader is None:
        raise CampaignError(f"cannot load {path}")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def quarantine_occupied(path: Path) -> Path | None:
    """Move a leftover runtime dir aside so pec bootstrap can start empty.

    A stopped campaign leaves `$L9_ROOT/programs/<id>` occupied. The next
    `make campaign` for that id must not attach to the draft workspace.
    """
    path = path.resolve()
    if not path.exists():
        return None
    if path.is_dir() and not any(path.iterdir()):
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = path.parent / "stale" / f"{path.name}-{stamp}"
    dest.parent.mkdir(parents=True, exist_ok=True)
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


def default_arm(
    workspace: Path,
    campaign_id: str,
    *,
    repository_id: str,
    target_path: Path,
) -> dict[str, Any]:
    refuse_hash_campaign_id(campaign_id)
    ensure_integration_branch(target_path, campaign_id)
    reconciled = default_reconcile(workspace, repository_id, target_path)
    tasks = locked_tasks(workspace)
    if not tasks or str(tasks[0]["id"]) != FIRST_TASK_ID:
        raise CampaignError("program lock is missing TASK-001")
    contracts: list[str] = []
    for task in tasks:
        contracts.append(str(register_task_contract(workspace, str(task["id"]))))
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
        "armed_task_ids": [str(task["id"]) for task in tasks],
        "contracts": contracts,
        "claim": (claim.stdout or "").strip(),
        "reconcile": reconciled,
        "stack": stack,
    }


def default_make_pr(worktree: Path, campaign_id: str) -> dict[str, Any]:
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
    path = worktree / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
    if path.is_file():
        raw = load_yaml(path) or {}
        campaigns = list(raw.get("campaigns") or [])
        found = False
        for item in campaigns:
            if isinstance(item, dict) and str(item.get("id")) == campaign_id:
                if str(item.get("lifecycle") or "") not in {"complete", "cancelled"}:
                    item["lifecycle"] = "in_progress"
                    item["started_at"] = item.get("started_at") or now
                    item["launched_by"] = "make campaign"
                    item["pec_workspace"] = pec_workspace
                    item["blueprint"] = blueprint
                    item["worktree"] = target_worktree
                    item["notes"] = ACTIVE_NOTE
                found = True
        if not found:
            campaigns.append(
                {
                    "id": campaign_id,
                    "lifecycle": "in_progress",
                    "started_at": now,
                    "launched_by": "make campaign",
                    "pec_workspace": pec_workspace,
                    "blueprint": blueprint,
                    "worktree": target_worktree,
                    "notes": ACTIVE_NOTE,
                }
            )
        raw["schema"] = raw.get("schema") or "l9.program-execution.campaign-status-ledger.v1"
        raw["updated"] = now
        raw["campaigns"] = campaigns
        dump_yaml(path, raw)

    policy_path = (
        worktree / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml"
    )
    if policy_path.is_file():
        policy = load_yaml(policy_path) or {}
        for item in list(policy.get("campaigns") or []):
            if isinstance(item, dict) and str(item.get("id")) == campaign_id:
                item["lifecycle"] = "in_progress"
                item["launched_by"] = "make campaign"
        policy["updated"] = now
        dump_yaml(policy_path, policy)

    profile_path = worktree / "ops/autonomy/surface_profile.yaml"
    if profile_path.is_file():
        profile = load_yaml(profile_path) or {}
        block = ((profile.get("campaign_execution") or {}).get("campaigns") or {}).get(campaign_id)
        if isinstance(block, dict):
            block["lifecycle"] = "in_progress"
            block["launched_by"] = "make campaign"
            dump_yaml(profile_path, profile)


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
        raise CampaignError(f"pec {command} failed: {detail}")
    return payload


def pec_status_tasks(workspace: Path) -> list[dict[str, Any]]:
    payload = pec_cmd(workspace, "status")
    return [item for item in (payload.get("tasks") or []) if isinstance(item, dict)]


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
) -> dict[str, Any]:
    refuse_hash_campaign_id(campaign_id)
    tasks = locked_tasks(workspace)
    stack_path = workspace / "runtime" / "STACK.json"
    stack_items = []
    if stack_path.is_file():
        stack_items = list(json.loads(stack_path.read_text(encoding="utf-8")).get("stack") or [])
    by_stack = {str(item.get("task_id")): item for item in stack_items if item.get("task_id")}
    completed: list[str] = []
    for task in tasks:
        task_id = str(task["id"])
        states = {str(item["id"]): item for item in pec_status_tasks(workspace)}
        state = str((states.get(task_id) or {}).get("runtime_state") or "")
        if state == "COMPLETED":
            completed.append(task_id)
            continue
        contract_path = workspace / "contracts" / "rendered" / f"{task_id}.json"
        worktree = workspace / "worktrees" / task_id
        already_submitted = state == "SUBMITTED"
        if already_submitted:
            if not contract_path.is_file():
                raise CampaignError(f"{task_id} is SUBMITTED without a Rendered Contract")
            rendered = {"contract": str(contract_path)}
        else:
            if state not in {"LEASED", "PREPARED", "CONTRACTED", "EXECUTING", "FAILED"}:
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
            if state == "LEASED":
                prepared = pec_cmd(workspace, "prepare", task_id)
                worktree = Path(str(prepared.get("worktree") or worktree))
            if state in {"LEASED", "PREPARED"} or not contract_path.is_file():
                rendered = pec_cmd(workspace, "render-contract", task_id)
            else:
                rendered = {"contract": str(contract_path)}
            if state in {"LEASED", "PREPARED", "CONTRACTED", "FAILED"}:
                pec_cmd(workspace, "start", task_id, "--actor", "make-campaign")
        contract = json.loads(Path(str(rendered["contract"])).read_text(encoding="utf-8"))
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

        if not already_submitted:
            candidate = rewrite_output()
            changed = [item for item in writable if not is_stub_output(worktree / item, title)]
            receipt = {
                "schema": "program-execution-controller.attempt-receipt.v2",
                "task_id": task_id,
                "contract_digest": contract["contract_digest"],
                "program_digest": contract["program_digest"],
                "base_sha": contract["base_sha"],
                "candidate_sha": candidate,
                "changed_files": changed or [rel],
                "validation_results": [],
                "produced_evidence": [],
                "residual_unknowns": [],
                "claimed_status": "completed",
            }
            receipt_path = workspace / "runtime" / f"{task_id}.attempt.json"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            pec_cmd(workspace, "record-attempt", task_id, "--receipt", str(receipt_path))
        verification = pec_cmd(workspace, "verify", task_id)
        decision = dispatch_kernel_change(verification)
        if decision["action"] == "skip_change":
            raise CampaignError(
                f"pec verify {task_id} INCOMPLETE: skip CHANGE ({decision['reason']})"
            )
        if decision["action"] == "refuse":
            raise CampaignError(f"Diagnose First: {decision['reason']}")
        if decision["action"] == "change":
            apply_fail_change(
                verification,
                rewrite=rewrite_output,
                reverify=lambda: pec_cmd(workspace, "verify", task_id),
            )
            verification = pec_cmd(workspace, "verify", task_id)
            if verification.get("kernel_verdict") != "PASS":
                raise CampaignError(
                    f"pec verify {task_id} after CHANGE did not PASS: "
                    f"{verification.get('kernel_verdict') or verification.get('verdict')}"
                )
        if verification.get("verdict") != "PASSED_LOCAL":
            raise CampaignError(f"pec verify {task_id} did not PASS: {verification.get('verdict')}")
        evidence_id = str(verification["evidence_id"])
        for gate_id in task.get("completion_gates") or task.get("completion_gate_ids") or []:
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
        if live_prs:
            item = by_stack.get(task_id) or {
                "task_id": task_id,
                "title": task.get("title") or task_id,
                "branch": pec_branch(str(task.get("wave_id") or "W0"), task_id),
                "pr_base": f"campaign/{campaign_id}",
            }
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
        ensure_target_history(target_path, repository_id)
    log(f"execute {campaign_id}")
    if hooks.execute is not None:
        hooks.execute(pec_workspace, campaign_id)
    elif (pec_workspace / "runtime" / "program-lock.json").is_file():
        default_execute(
            pec_workspace,
            campaign_id,
            hooks=hooks,
            live_prs=should_run(until, "pr") and hooks.make_pr is None,
        )
    executed = False
    if (pec_workspace / "runtime" / "program-lock.json").is_file():
        executed = all_required_tasks_completed(pec_workspace)
    report.program_blockers = default_program_blockers(campaign_id, armed=True, executed=executed)
    report.stages_completed.append("execute")
    if not should_run(until, "pr"):
        return report
    if not executed:
        raise CampaignError("refuse host-only merge before all tasks COMPLETED", exit_code=2)
    commit_host_emit(write_root, campaign_id)
    if hooks.make_pr is None:
        push_integration_branch(write_root, campaign_id)
    make_pr = hooks.make_pr or default_make_pr
    pr_result = make_pr(write_root, campaign_id)
    report.host_pr = str(pr_result.get("url") or pr_result.get("output") or "")
    report.host_pr_number = pr_result.get("number")
    log(f"PR {report.host_pr or report.host_pr_number or 'opened'}")
    report.stages_completed.append("pr")
    if not should_run(until, "close"):
        return report
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
    until: str = "merge",
    primary: Path | None = None,
    worktree: Path | None = None,
    repo_root: Path | None = None,
    l9_root: Path | None = None,
    host_repo: str = HOST_REPO_DEFAULT,
    target_override: str | None = None,
    hooks: Hooks | None = None,
) -> CampaignReport:
    requested_until = until
    until = normalize_until(until)
    hooks = hooks or Hooks()
    primary = (primary or Path.home() / ".cursor-governance").resolve()
    host_root = (repo_root or primary).resolve()
    l9_home = (l9_root or Path(os.environ.get("L9_ROOT", Path.home() / ".l9"))).resolve()
    resolved_intent = resolve_operator_intent(
        intent_path,
        host_root=host_root,
        target_override=target_override or os.environ.get("TARGET"),
        primed_dir=l9_home / "primed",
    )
    seed = load_activate_seed(resolved_intent)
    campaign_id = str(seed["campaign_id"]).strip()
    refuse_hash_campaign_id(campaign_id)
    if should_run(until, "execute") and resumable_workspace(l9_home / "programs" / campaign_id):
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
        )
    primed_root = l9_home / "primed"
    stack_fn = hooks.context7_stack or default_context7_stack
    log(f"stack-proof {campaign_id}")
    stack_receipt = stack_fn(seed, primed_root)
    stack_proof_path = Path(
        str((stack_receipt or {}).get("path") or (primed_root / campaign_id / "stack-proof.json"))
    )
    if repo_root is not None:
        write_root = repo_root.resolve()
    else:
        write_root = (worktree or (l9_home / "gov-worktrees" / campaign_id)).resolve()
        write_root = isolate_worktree(
            primary,
            campaign_id,
            write_root,
            git_fn=hooks.git,
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
    )

    compile_activation = hooks.compile_activation or default_compile_activation
    plan_fn = hooks.plan_window or default_plan_window
    log(f"plan-window {campaign_id}")
    plan_receipt = plan_fn(seed, primed_root / campaign_id, stack_proof_path)
    projected_intent = Path(str(plan_receipt.get("intent_path") or resolved_intent))
    if str(plan_receipt.get("plan_status") or "") not in {"Ready", "ConditionallyReady"}:
        if hooks.compile_activation is None:
            raise CampaignError(
                f"plan_status {plan_receipt.get('plan_status')!r} is not Ready or "
                "ConditionallyReady; refuse seal"
            )
    log(f"emit {campaign_id} into {write_root}")
    compile_activation(
        projected_intent if projected_intent.is_file() else resolved_intent,
        write_root,
    )
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

    quarantine_occupied(Path(report.pec_workspace))
    quarantine_occupied(Path(report.blueprint))
    source = (
        write_root
        / "environment/program-execution/campaigns"
        / campaign_id
        / "CAMPAIGN_SOURCE.yaml"
    )
    blueprint = Path(report.blueprint)
    log(f"blueprint {blueprint}")
    allowlist = write_root / "environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml"
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
    validate = hooks.validate_blueprint or default_validate_blueprint
    errors = validate(blueprint)
    if errors:
        raise CampaignError("template validate failed: " + "; ".join(errors))
    log("template validate PASS")
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
    if hooks.admit is None:
        default_ensure_target_checkout(target_path, repository_id, donor=write_root)
        host_revision = target_head_sha(target_path)
    else:
        host_revision = str((seed.get("target") or {}).get("repository_id") or host_repo)
    log(f"admit EVID-001 bind {host_revision}")
    if hooks.admit is not None:
        hooks.admit(blueprint)
    else:
        default_admit(blueprint, revision=host_revision)
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
    pec_result = pec(Path(report.pec_workspace), blueprint)
    if pec_result.get("draft"):
        raise CampaignError("pec --admission-draft is not a live campaign path")
    report.pec_note = str(pec_result.get("output") or "")
    log("pec bootstrap ok")
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
    if hooks.arm is not None:
        hooks.arm(Path(report.pec_workspace), campaign_id)
    else:
        default_ensure_target_checkout(target_path, repository_id, donor=write_root)
        default_arm(
            Path(report.pec_workspace),
            campaign_id,
            repository_id=repository_id,
            target_path=target_path,
        )
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
    if should_run(until, "execute"):
        pusher = hooks.push_integration
        if pusher is None and hooks.make_pr is None:
            pusher = push_integration_branch
        if pusher is not None:
            log(f"push {campaign_id} integration branch before execute")
            pusher(write_root, campaign_id)
    if not should_run(until, "execute"):
        return report

    log(f"execute {campaign_id}")
    pec_workspace = Path(report.pec_workspace)
    if hooks.execute is not None:
        hooks.execute(pec_workspace, campaign_id)
    elif (pec_workspace / "runtime" / "program-lock.json").is_file():
        default_execute(
            pec_workspace,
            campaign_id,
            hooks=hooks,
            live_prs=should_run(until, "pr") and hooks.make_pr is None,
        )
    executed = False
    if (pec_workspace / "runtime" / "program-lock.json").is_file():
        executed = all_required_tasks_completed(pec_workspace)
    report.program_blockers = default_program_blockers(campaign_id, armed=True, executed=executed)
    report.stages_completed.append("execute")
    if not should_run(until, "pr"):
        return report

    if not executed:
        raise CampaignError(
            "refuse host-only merge before all tasks COMPLETED",
            exit_code=2,
        )
    commit_host_emit(write_root, campaign_id)
    if hooks.make_pr is None:
        push_integration_branch(write_root, campaign_id)
    make_pr = hooks.make_pr or default_make_pr
    pr_result = make_pr(write_root, campaign_id)
    report.host_pr = str(pr_result.get("url") or pr_result.get("output") or "")
    report.host_pr_number = pr_result.get("number")
    log(f"PR {report.host_pr or report.host_pr_number or 'opened'}")
    report.stages_completed.append("pr")
    if not should_run(until, "close"):
        return report

    close = hooks.close or default_close
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
    parser.add_argument("--intent", required=True, type=Path)
    parser.add_argument(
        "--until",
        choices=list(UNTIL_STAGES) + list(UNTIL_ALIASES),
        default="close",
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
    return parser


def refuse_live_until_shortcut(until: str) -> None:
    resolved = UNTIL_ALIASES.get(until, until)
    if resolved == "close":
        return
    if os.environ.get("L9_CAMPAIGN_UNTIL_DEBUG") == "1":
        return
    raise CampaignError(
        "CAMPAIGN_UNTIL is not a live campaign path; make campaign runs "
        "through close. Set L9_CAMPAIGN_UNTIL_DEBUG=1 only for runner tests."
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
        )
    except CampaignError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code
    render_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
