#!/usr/bin/env python3
"""Operator front door for PE campaign activation.

Sealed stages: isolate → emit → blueprint → collect → accept →
pec bootstrap (no draft) → pec reconcile → contract/claim TASK-001 →
host PR → merge-if-green.

program-execution.intent.v1 and pe-<hash> workspaces are not this path.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
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
UNTIL_STAGES = ("activate", "blueprint", "admit", "bootstrap", "arm", "pr", "merge")
STAGE_INDEX = {name: index for index, name in enumerate(UNTIL_STAGES)}
HOST_REPO_DEFAULT = "Quantum-L9/Cursor-Governance"
HASH_PROGRAM_RE = re.compile(r"^pe-[0-9a-f]{8,}$")
FIRST_TASK_ID = "TASK-001"


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
    make_pr: Callable[[Path, str], dict[str, Any]] | None = None
    pr_status: Callable[[str, int | None], dict[str, Any]] | None = None
    authorize_and_merge: Callable[[str, int], dict[str, Any]] | None = None
    git: Callable[..., str] | None = None


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
            if life not in {"complete", "cancelled"}:
                ids.add(str(item["id"]))
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
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
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
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
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
    if worktree.exists():
        log(f"isolate reuse worktree {worktree}")
        return worktree
    branch = f"feat/{campaign_id}"
    existing = subprocess.run(
        ["git", "-C", str(primary), "rev-parse", "--verify", branch],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.returncode == 0:
        git("worktree", "add", str(worktree), branch)
    else:
        git("worktree", "add", "-b", branch, str(worktree), "origin/main")
    campaign_branch = f"campaign/{campaign_id}"
    has_campaign = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "--verify", f"origin/{campaign_branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if has_campaign.returncode != 0:
        local = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "--verify", campaign_branch],
            capture_output=True,
            text=True,
            check=False,
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


def refuse_hash_campaign_id(campaign_id: str) -> None:
    if HASH_PROGRAM_RE.match(campaign_id):
        raise CampaignError(
            f"{campaign_id} is a program-execution.intent.v1 hash id; "
            "operator campaigns use make campaign INTENT= only"
        )


def default_compile_source(
    source: Path, target: Path, *, allowlist_path: Path | None = None
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
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(GOV_ROOT),
    )
    if result.returncode != 0:
        raise CampaignError(
            f"compile_campaign_source failed: {result.stderr.strip() or result.stdout.strip()}"
        )


def default_validate_blueprint(target: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_BLUEPRINT), str(target), "--mode", "template"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        return [detail or "template validate failed"]
    return []


def default_pec_bootstrap(workspace: Path, blueprint: Path) -> dict[str, Any]:
    def _run(*, admission_draft: bool) -> subprocess.CompletedProcess[str]:
        cmd = [
            sys.executable,
            str(PEC),
            "bootstrap",
            "--workspace",
            str(workspace),
            "--blueprint",
            str(blueprint),
        ]
        if admission_draft:
            cmd.append("--admission-draft")
        return subprocess.run(cmd, check=False, capture_output=True, text=True)

    first = _run(admission_draft=False)
    combined = (first.stderr + "\n" + first.stdout).strip()
    if first.returncode == 0:
        return {"ok": True, "draft": False, "output": combined}
    raise CampaignError(
        "pec bootstrap failed without --admission-draft; "
        "collect_evidence + accept_blueprint must precede lock: " + combined
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


def default_ensure_target_checkout(
    dest: Path, repository_id: str, *, donor: Path | None = None
) -> Path:
    dest = dest.resolve()
    if dest.exists() and is_git_repo(dest):
        if is_dirty(dest):
            raise CampaignError(
                f"target checkout is dirty: {dest}; make campaign will not attach to a dirty target"
            )
        return dest
    if dest.exists():
        raise CampaignError(f"target path exists and is not a git checkout: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if donor is not None and is_git_repo(donor):
        clone = subprocess.run(
            ["git", "clone", "--local", str(donor.resolve()), str(dest)],
            check=False,
            capture_output=True,
            text=True,
        )
        if clone.returncode == 0:
            return dest
    url = f"https://github.com/{repository_id}.git"
    clone = subprocess.run(
        ["git", "clone", "--branch", "main", url, str(dest)],
        check=False,
        capture_output=True,
        text=True,
    )
    if clone.returncode != 0:
        raise CampaignError(
            f"cannot checkout {repository_id} at {dest}: {(clone.stderr or clone.stdout).strip()}"
        )
    return dest


def default_reconcile(workspace: Path, repository_id: str, target_path: Path) -> dict[str, Any]:
    mapping = f"{repository_id}={target_path}"
    result = subprocess.run(
        [
            sys.executable,
            str(PEC),
            "reconcile",
            "--workspace",
            str(workspace),
            "--repository",
            mapping,
        ],
        check=False,
        capture_output=True,
        text=True,
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


def default_arm(
    workspace: Path,
    campaign_id: str,
    *,
    repository_id: str,
    target_path: Path,
) -> dict[str, Any]:
    refuse_hash_campaign_id(campaign_id)
    reconciled = default_reconcile(workspace, repository_id, target_path)
    contract = workspace / "runtime" / f"{FIRST_TASK_ID}.source.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    draft = subprocess.run(
        [
            sys.executable,
            str(PEC),
            "draft-contract",
            FIRST_TASK_ID,
            "--workspace",
            str(workspace),
            "--output",
            str(contract),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if draft.returncode != 0:
        raise CampaignError(f"pec draft-contract failed: {(draft.stderr or draft.stdout).strip()}")
    register = subprocess.run(
        [
            sys.executable,
            str(PEC),
            "register-contract",
            FIRST_TASK_ID,
            "--workspace",
            str(workspace),
            "--file",
            str(contract),
            "--actor",
            "make-campaign",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if register.returncode != 0:
        raise CampaignError(
            f"pec register-contract failed: {(register.stderr or register.stdout).strip()}"
        )
    claim = subprocess.run(
        [
            sys.executable,
            str(PEC),
            "claim",
            FIRST_TASK_ID,
            "--workspace",
            str(workspace),
            "--holder",
            "make-campaign",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if claim.returncode != 0:
        raise CampaignError(f"pec claim failed: {(claim.stderr or claim.stdout).strip()}")
    return {
        "task_id": FIRST_TASK_ID,
        "contract": str(contract),
        "claim": (claim.stdout or "").strip(),
        "reconcile": reconciled,
    }


def default_make_pr(worktree: Path, campaign_id: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["PR_BASE"] = f"origin/campaign/{campaign_id}"
    env["PR_REMEDIATE"] = "0"
    env["OPEN_PR"] = "1"
    result = subprocess.run(
        ["make", "pr"],
        cwd=str(worktree),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        raise CampaignError(f"make pr failed: {output}")
    return {"output": output}


def default_pr_status(host_repo: str, number: int | None) -> dict[str, Any]:
    fields = "number,url,mergeable,state,headRefOid"
    cmd = ["gh", "pr", "view", "--repo", host_repo, "--json", fields]
    if number is not None:
        cmd.insert(3, str(number))
    view = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if view.returncode != 0:
        raise CampaignError(f"gh pr view failed: {view.stderr.strip()}")
    data = json.loads(view.stdout)
    checks = subprocess.run(
        ["gh", "pr", "checks", str(data["number"]), "--repo", host_repo],
        check=False,
        capture_output=True,
        text=True,
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
    auth = subprocess.run(
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
        check=False,
        capture_output=True,
        text=True,
    )
    if auth.returncode != 0:
        raise CampaignError(f"authorize_campaign_merge failed: {auth.stderr.strip()}")
    merge = subprocess.run(
        ["gh", "pr", "merge", str(number), "--repo", host_repo, "--squash", "--delete-branch"],
        check=False,
        capture_output=True,
        text=True,
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
        "operator_ack_required": True,
        "operator_ack_from": "Igor Beylin",
        "forge_operator_ack": False,
        "only_pec_workspace": True,
        "claimed_task": FIRST_TASK_ID,
        "reconcile_required": True,
        "pec_ready_empty_is_expected": False,
        "autonomy_packets_not_required": True,
        "refuse_hash_program": True,
        "next": (
            f"Only path: pec workspace {workspace} campaign_id={campaign_id}. "
            f"Execute {FIRST_TASK_ID} on {target_worktree}. "
            "Do not attach to pe-<hash>. Do not write the dirty primary. "
            "Stop and ask Igor for PHASE0 operator_ack; do not forge acknowledged_at."
        ),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def default_program_blockers(campaign_id: str) -> list[str]:
    return [
        "target work not started",
        "control-plane binding pending",
        f"do not close {campaign_id} after host-only merge",
    ]


def should_run(until: str, stage: str) -> bool:
    return STAGE_INDEX[stage] <= STAGE_INDEX[until]


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
    if until not in STAGE_INDEX:
        raise CampaignError(f"until must be one of {', '.join(UNTIL_STAGES)}")
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
        until=until,
        worktree=str(write_root),
        primary=str(primary),
        blueprint=str(l9_home / "blueprints" / campaign_id),
        pec_workspace=str(l9_home / "programs" / campaign_id),
        program_blockers=default_program_blockers(campaign_id),
    )

    compile_activation = hooks.compile_activation or default_compile_activation
    log(f"emit {campaign_id} into {write_root}")
    compile_activation(resolved_intent, write_root)
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
        default_compile_source(source, blueprint, allowlist_path=allowlist)
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

    quarantine_occupied(Path(report.pec_workspace))
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
    repository_id = str((seed.get("target") or {}).get("repository_id") or host_repo)
    target_path = Path(target_worktree)
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
    write_launch_pointer(
        Path(report.pec_workspace),
        campaign_id=campaign_id,
        blueprint=report.blueprint,
        target_worktree=target_worktree,
        host_worktree=str(write_root),
    )
    report.stages_completed.append("arm")
    if not should_run(until, "pr"):
        return report

    make_pr = hooks.make_pr or default_make_pr
    pr_result = make_pr(write_root, campaign_id)
    report.host_pr = str(pr_result.get("url") or pr_result.get("output") or "")
    report.host_pr_number = pr_result.get("number")
    log(f"PR {report.host_pr or report.host_pr_number or 'opened'}")
    report.stages_completed.append("pr")
    if not should_run(until, "merge"):
        return report

    status_fn = hooks.pr_status or default_pr_status
    status = status_fn(host_repo, report.host_pr_number)
    report.host_pr = str(status.get("url") or report.host_pr)
    report.host_pr_number = int(status.get("number") or report.host_pr_number or 0) or None
    if not status.get("green") or not status.get("mergeable"):
        report.activation_blockers.append(
            "host PR checks are red, pending, or not mergeable; merge skipped"
        )
        raise CampaignError(
            "host PR is not green and mergeable; merge skipped",
            exit_code=2,
        )
    merge_fn = hooks.authorize_and_merge or default_authorize_and_merge
    if report.host_pr_number is None:
        raise CampaignError("host PR number unknown; merge skipped")
    merged = merge_fn(host_repo, report.host_pr_number)
    report.merge_sha = str(status.get("sha") or merged.get("output") or "")
    log(f"checks green; merged squash {report.merge_sha}")
    report.stages_completed.append("merge")
    return report


def render_report(report: CampaignReport) -> None:
    log(f"activation blockers: {', '.join(report.activation_blockers) or 'none'}")
    log(f"program blockers: {', '.join(report.program_blockers) or 'none'}")
    print(json.dumps(report.to_dict(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", required=True, type=Path)
    parser.add_argument("--until", choices=UNTIL_STAGES, default="merge")
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
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
