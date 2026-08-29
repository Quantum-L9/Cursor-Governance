"""PR-train LangGraph — open stacked PRs, halt for remediator, then /ff.

LANGGRAPH_RUNTIME (not a SessionDAG). Never call register_session_dag.

Stops (one slash, graph + remediator skill):

1. OPEN_TRAIN — inventory unique commits on the **current branch** (opt-in
   ``--all-refs``), drop already-landed patches, consolidate colliding work
   into one slice (shared path, generated-prefix clobber, or ``git merge-tree``
   conflict; unknown probe fail-closes into the same PR), cherry-pick onto
   the unique stack tip, publish with ``PR_STACK=auto make pr``.
2. REMEDIATE — this graph does **not** run MERGE_TRAIN and does **not** write
   merge authorization. It dispatches skill ``l9-pr-remediation`` Converge
   and HALTS. Do not run ``make pr`` here.
3. FF — ``--ff-only`` after ``open_pr_count == 0``, run
   ``skills/l9-repo-sync/scripts/ff.sh``.

Rebase and conflict resolution stay forbidden. Cherry-pick conflict stops.
Campaign branches halt unless ``campaign_override``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PRESERVE_SCRIPTS = _REPO_ROOT / "skills" / "l9-git-work-preserve" / "scripts"
_FF_SH = _REPO_ROOT / "skills" / "l9-repo-sync" / "scripts" / "ff.sh"
_RESOLVE_STACK = _REPO_ROOT / "ops" / "scripts" / "resolve_stack_tip.py"
_AUTHORIZE_MERGE = _REPO_ROOT / "ops" / "autonomy" / "authorize_merge.py"
_L4_LOCAL = _REPO_ROOT / "ops" / "autonomy" / "l4_local.py"
GRAPH_ID = "pr-train-v1"
MAX_SLICES = 32
REMEDIATOR_SKILL = "l9-pr-remediation"
_SCRIPTS = _REPO_ROOT / "ops" / "scripts"


def _load_generated_prefixes() -> tuple[str, ...]:
    path = _SCRIPTS / "sync_generated_artifacts.py"
    if not path.is_file():
        return ()
    spec = importlib.util.spec_from_file_location("_l9_sync_generated_artifacts", path)
    if spec is None or spec.loader is None:
        return ()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prefixes = getattr(module, "GENERATED_PATH_PREFIXES", ())
    return tuple(prefixes) if prefixes else ()


GENERATED_PATH_PREFIXES = _load_generated_prefixes()


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without git)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NovelCommit:
    sha: str
    paths: tuple[str, ...]
    ref: str


def campaign_halt(branch: str | None, override: bool) -> str | None:
    name = (branch or "").strip()
    if name.startswith("campaign/") and not override:
        return f"campaign branch {name!r} refuses pr-train (pass campaign_override)"
    return None


def generated_prefix(path: str) -> str | None:
    rel = path.lstrip("./")
    for prefix in GENERATED_PATH_PREFIXES:
        if rel.startswith(prefix) or rel == prefix.rstrip("."):
            return prefix
    return None


def shares_generated_clobber(left: NovelCommit, right: NovelCommit) -> bool:
    """Whole-file generated corpora clobber on MERGE_TRAIN if split across PRs."""
    left_p = {generated_prefix(p) for p in left.paths} - {None}
    right_p = {generated_prefix(p) for p in right.paths} - {None}
    return bool(left_p & right_p)


def parse_merge_tree_name_only(stdout: str, returncode: int) -> list[str] | None:
    """Same contract as ``pr_overlap_check.probe_ref_conflicts``: [] / paths / None."""
    if returncode == 0:
        return []
    if returncode != 1:
        return None
    conflicts: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or " " in line or line.isdigit():
            continue
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            continue
        conflicts.append(line)
    return conflicts


def is_git_repo(repo: Path) -> bool:
    return _git(repo, "rev-parse", "--is-inside-work-tree").returncode == 0


def sha_is_commit(repo: Path, sha: str) -> bool:
    return _git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def probe_sha_conflicts(repo: Path, left: str, right: str) -> list[str] | None:
    """Textual conflicts if ``left`` and ``right`` were merged. None = unknown.

    Exit 1 with no parseable paths still counts as a conflict (fail-closed).
    """
    result = _git(repo, "merge-tree", "--write-tree", "--name-only", left, right)
    if result.returncode == 0:
        return []
    if result.returncode != 1:
        return None
    parsed = parse_merge_tree_name_only(result.stdout, 1)
    return parsed if parsed else ["__merge_tree_conflict__"]


def commit_unix(repo: Path, sha: str) -> int:
    proc = _git(repo, "log", "-1", "--format=%ct", sha)
    if proc.returncode != 0:
        return 0
    try:
        return int((proc.stdout or "0").strip() or "0")
    except ValueError:
        return 0


def commits_must_colocate(repo: Path, left: NovelCommit, right: NovelCommit) -> bool:
    """True → same stacked PR. Unknown merge-tree is fail-closed (colocate)."""
    if shares_generated_clobber(left, right):
        return True
    if not is_git_repo(repo):
        return False
    if not sha_is_commit(repo, left.sha) or not sha_is_commit(repo, right.sha):
        return False
    conflicts = probe_sha_conflicts(repo, left.sha, right.sha)
    if conflicts is None:
        return True
    return bool(conflicts)


def order_slice(repo: Path, group: list[NovelCommit]) -> list[NovelCommit]:
    """Oldest commit first so cherry-pick onto the stack tip is linear."""
    if len(group) < 2 or not is_git_repo(repo):
        return group
    return sorted(group, key=lambda c: (commit_unix(repo, c.sha), c.sha))


def group_slices(
    commits: list[NovelCommit],
    must_colocate: Callable[[NovelCommit, NovelCommit], bool] | None = None,
) -> list[list[NovelCommit]]:
    """One PR per conflict component.

    Always union commits that share a path. Then union any pair for which
    ``must_colocate`` is true (merge-tree conflict, unknown probe, or
    generated-prefix clobber). Unknown is fail-closed: one PR, not a stacked
    pair that will stall MERGE_TRAIN.
    """
    if not commits:
        return []
    parent = list(range(len(commits)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    first_for_path: dict[str, int] = {}
    for i, commit in enumerate(commits):
        for path in commit.paths:
            seen = first_for_path.get(path)
            if seen is None:
                first_for_path[path] = i
            else:
                union(i, seen)

    if must_colocate is not None:
        for i, left in enumerate(commits):
            for j in range(i + 1, len(commits)):
                if find(i) == find(j):
                    continue
                if must_colocate(left, commits[j]):
                    union(i, j)

    grouped: dict[int, list[NovelCommit]] = {}
    order: list[int] = []
    for i, commit in enumerate(commits):
        root = find(i)
        if root not in grouped:
            grouped[root] = []
            order.append(root)
        grouped[root].append(commit)
    return [grouped[root] for root in order]


def resolve_ff_clone(repo: Path, branch: str | None) -> Path:
    """ff.sh only runs on main. Feature worktrees catch up the SSOT clone."""
    name = (branch or "").removeprefix("origin/")
    if name in {"main", "master"}:
        return repo
    ssot = Path.home() / ".cursor-governance"
    return ssot if ssot.exists() else repo


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class PrTrainState(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    repo: str = Field(default="")
    baseline: str = Field(default="origin/main")
    execute: bool = Field(default=False)
    campaign_override: bool = Field(default=False)
    fetch: bool = Field(default=True)
    all_refs: bool = Field(default=False)
    refs: list[str] = Field(default_factory=list)
    ff_only: bool = Field(default=False)

    branch: str | None = Field(default=None)
    inventory: dict[str, Any] = Field(default_factory=dict)
    unpushed_refs: list[str] = Field(default_factory=list)
    diagnoses: list[dict[str, Any]] = Field(default_factory=list)
    novel: list[dict[str, Any]] = Field(default_factory=list)
    skipped_dup: list[str] = Field(default_factory=list)
    slices: list[list[dict[str, Any]]] = Field(default_factory=list)
    current_slice: int = Field(default=0)

    stack_tip: str = Field(default="")
    stack_tip_sha: str = Field(default="")
    stack_reason: str = Field(default="")

    extract_worktree: str = Field(default="")
    extract_branch: str = Field(default="")
    opened_prs: list[dict[str, Any]] = Field(default_factory=list)

    open_pr_count: int | None = Field(default=None)
    skill_dispatch: str = Field(default="")
    merge_authorized: bool = Field(default=False)
    ff_ran: bool = Field(default=False)
    ff_clone: str = Field(default="")
    ff_skipped: str = Field(default="")
    extract_fn: Any = Field(default=None)
    publish_fn: Any = Field(default=None)
    remediate_fn: Any = Field(default=None)
    ff_fn: Any = Field(default=None)
    colocate_fn: Any = Field(default=None)

    status: Literal["running", "blocked", "complete", "failed"] = Field(default="running")
    halt_reason: str = Field(default="")
    stop: Literal["open_train", "remediate", "ff", "report"] = Field(default="open_train")
    report: str = Field(default="")
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# IO seams (monkeypatched in tests)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _python() -> str:
    venv = _REPO_ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def load_inventory(repo: Path, baseline: str, fetch: bool) -> dict[str, Any]:
    cmd = [_python(), str(_PRESERVE_SCRIPTS / "inventory_git_work.py"), "--repo", str(repo)]
    if fetch:
        cmd.append("--fetch")
    if baseline:
        cmd.extend(["--baseline", baseline])
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "inventory_git_work.py failed")
    return json.loads(proc.stdout)


def load_diagnosis(repo: Path, ref: str, baseline: str, fetch: bool) -> dict[str, Any]:
    cmd = [
        _python(),
        str(_PRESERVE_SCRIPTS / "diagnose_ref_value.py"),
        "--repo",
        str(repo),
        "--ref",
        ref,
        "--baseline",
        baseline,
    ]
    if fetch:
        cmd.append("--fetch")
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"diagnose_ref_value.py failed for {ref}")
    return json.loads(proc.stdout)


def load_commit_paths(repo: Path, sha: str) -> tuple[str, ...] | None:
    proc = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha)
    if proc.returncode != 0:
        return None
    return tuple(line for line in proc.stdout.splitlines() if line.strip())


def github_repo_slug(repo: Path) -> str:
    remote = _git(repo, "remote", "get-url", "origin")
    if remote.returncode != 0:
        raise RuntimeError("cannot resolve origin for GitHub slug")
    url = remote.stdout.strip().removesuffix(".git")
    if "github.com" not in url:
        raise RuntimeError("origin is not GitHub; refuse slug")
    tail = url.split("github.com", 1)[1].lstrip(":/")
    parts = [p for p in tail.split("/") if p]
    if len(parts) < 2:
        raise RuntimeError("origin is not owner/repo; refuse slug")
    return f"{parts[0]}/{parts[1]}"


def load_stack_tip(repo: Path, default_ref: str) -> tuple[str, str, str]:
    proc = subprocess.run(
        [_python(), str(_RESOLVE_STACK), "--workspace", str(repo), "--default-ref", default_ref],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "resolve_stack_tip.py failed")
    tip = sha = reason = ""
    for line in proc.stdout.splitlines():
        if line.startswith("STACK_TIP="):
            tip = line.split("=", 1)[1]
        elif line.startswith("STACK_TIP_SHA="):
            sha = line.split("=", 1)[1]
        elif line.startswith("REASON="):
            reason = line.split("=", 1)[1]
    if not tip:
        raise RuntimeError("resolve_stack_tip.py returned no STACK_TIP")
    return tip, sha, reason


def count_open_prs(repo: Path) -> int:
    slug = github_repo_slug(repo)
    proc = subprocess.run(
        ["gh", "pr", "list", "--repo", slug, "--state", "open", "--json", "number"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "gh pr list failed")
    rows = json.loads(proc.stdout or "[]")
    return len(rows)


def authorize_merge(repo_slug: str, reason: str) -> None:
    proc = subprocess.run(
        [
            _python(),
            str(_AUTHORIZE_MERGE),
            "--repo",
            repo_slug,
            "--all-open",
            "--reason",
            reason,
        ],
        text=True,
        capture_output=True,
        check=False,
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "authorize_merge.py failed")


def run_ff(clone: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CURSOR_GOVERNANCE_DIR"] = str(clone)
    env["GOVERNANCE_SYNC_PUSH"] = "0"
    env["GOVERNANCE_SYNC_HARD_RESET"] = "0"
    return subprocess.run(
        ["bash", str(_FF_SH)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def default_extract(
    repo: Path,
    slice_commits: list[dict[str, Any]],
    stack_tip: str,
    index: int,
) -> tuple[str, str]:
    short = (slice_commits[0]["sha"] if slice_commits else "empty")[:8]
    branch = f"feat/pr-train-{index}-{short}"
    stamp = os.getpid()
    worktree = Path.home() / ".l9" / "gov-worktrees" / f"pr-train-{index}-{stamp}"
    if worktree.exists():
        raise RuntimeError(f"extract worktree already exists: {worktree}")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    add = _git(repo, "worktree", "add", "-b", branch, str(worktree), stack_tip)
    if add.returncode != 0:
        raise RuntimeError(add.stderr.strip() or "git worktree add failed")
    for item in slice_commits:
        pick = subprocess.run(
            ["git", "-C", str(worktree), "cherry-pick", item["sha"]],
            text=True,
            capture_output=True,
            check=False,
        )
        if pick.returncode != 0:
            subprocess.run(
                ["git", "-C", str(worktree), "cherry-pick", "--abort"],
                text=True,
                capture_output=True,
                check=False,
            )
            raise RuntimeError(f"cherry-pick conflict on {item['sha']}: {pick.stderr.strip()}")
    return str(worktree), branch


def _l4_authorize_worktree(worktree: str) -> None:
    """Fresh extract worktrees have no L4 receipt; make pr fail-closes without one."""
    for args in (
        ["begin", "--workspace", worktree, "--contract-id", GRAPH_ID],
        ["record-kernels", "--workspace", worktree],
        ["authorize-release", "--workspace", worktree],
    ):
        proc = subprocess.run(
            [_python(), str(_L4_LOCAL), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                proc.stderr.strip() or proc.stdout.strip() or f"l4_local.py {args[0]} failed"
            )


def default_publish(worktree: str) -> dict[str, Any]:
    _l4_authorize_worktree(worktree)
    gov = Path.home() / ".cursor-governance"
    makefile = gov if (gov / "Makefile").is_file() else _REPO_ROOT
    env = os.environ.copy()
    env["PR_STACK"] = "auto"
    env["PR_REMEDIATE"] = "0"
    env["WS"] = worktree
    proc = subprocess.run(
        ["make", "-C", str(makefile), "pr", f"WS={worktree}"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "make pr failed")
    return {"worktree": worktree, "ok": True}


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def inventory_node(state: PrTrainState) -> dict[str, Any]:
    repo = Path(state.repo or ".").resolve()
    try:
        data = load_inventory(repo, state.baseline, state.fetch)
    except Exception as exc:
        return {"status": "failed", "halt_reason": str(exc), "errors": [str(exc)]}
    branch = data.get("branch")
    halt = campaign_halt(branch, state.campaign_override)
    if halt:
        return {
            "inventory": data,
            "branch": branch,
            "status": "blocked",
            "halt_reason": halt,
            "stop": "report",
        }
    if state.refs:
        refs = [name for name in state.refs if name]
    elif state.all_refs:
        refs = [row["name"] for row in data.get("unpushed_or_diverged") or [] if row.get("name")]
        if branch and branch not in refs and data.get("head"):
            refs = [branch, *refs]
    elif branch:
        refs = [branch]
    else:
        return {
            "inventory": data,
            "branch": branch,
            "status": "blocked",
            "halt_reason": "no current branch; refuse all-ref inventory",
            "stop": "report",
        }
    return {
        "inventory": data,
        "branch": branch,
        "unpushed_refs": refs,
        "stop": "open_train",
        "status": "running",
    }


def diagnose_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"}:
        return {}
    repo = Path(state.repo).resolve()
    diagnoses: list[dict[str, Any]] = []
    novel: list[dict[str, Any]] = []
    skipped: list[str] = []
    seen: set[str] = set()
    try:
        for ref in state.unpushed_refs:
            receipt = load_diagnosis(repo, ref, state.baseline, fetch=False)
            diagnoses.append(receipt)
            if not receipt.get("cherry_available") or not receipt.get("baseline_resolved"):
                return {
                    "diagnoses": diagnoses,
                    "status": "blocked",
                    "halt_reason": f"novelty unproven for {ref}",
                    "stop": "report",
                }
            for sha in receipt.get("cherry_dup_commits") or []:
                skipped.append(sha)
            for sha in receipt.get("cherry_novel_commits") or []:
                if sha in seen:
                    continue
                seen.add(sha)
                paths = load_commit_paths(repo, sha)
                if paths is None:
                    return {
                        "diagnoses": diagnoses,
                        "status": "blocked",
                        "halt_reason": f"paths unproven for {sha}; refuse slice split",
                        "stop": "report",
                    }
                novel.append({"sha": sha, "paths": list(paths), "ref": ref})
    except Exception as exc:
        return {"status": "failed", "halt_reason": str(exc), "errors": [str(exc)]}
    return {"diagnoses": diagnoses, "novel": novel, "skipped_dup": skipped}


def slice_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"}:
        return {}
    repo = Path(state.repo or ".").resolve()
    commits = [
        NovelCommit(sha=row["sha"], paths=tuple(row.get("paths") or ()), ref=row.get("ref") or "")
        for row in state.novel
    ]
    must = state.colocate_fn
    if must is None:

        def must(left: NovelCommit, right: NovelCommit) -> bool:
            return commits_must_colocate(repo, left, right)

    slices = [
        [{"sha": c.sha, "paths": list(c.paths), "ref": c.ref} for c in order_slice(repo, group)]
        for group in group_slices(commits, must_colocate=must)
    ]
    if len(slices) > MAX_SLICES:
        return {
            "slices": slices[:MAX_SLICES],
            "status": "blocked",
            "halt_reason": f"slice cap {MAX_SLICES} exceeded",
            "stop": "report",
        }
    probe: dict[str, Any] = {"slices": slices, "current_slice": 0}
    try:
        tip, sha, reason = load_stack_tip(repo, state.baseline)
        probe["stack_tip"] = tip
        probe["stack_tip_sha"] = sha
        probe["stack_reason"] = reason
    except Exception as exc:
        probe["stack_reason"] = str(exc)
        probe["errors"] = [str(exc)]
    return probe


def stack_base_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"}:
        return {}
    if not state.slices or not state.execute:
        return {}
    repo = Path(state.repo).resolve()
    try:
        tip, sha, reason = load_stack_tip(repo, state.baseline)
    except Exception as exc:
        msg = str(exc)
        if "sibling open-PR" in msg:
            return {
                "status": "blocked",
                "halt_reason": f"{msg}; collapse via {REMEDIATOR_SKILL} Converge before OPEN_TRAIN",
                "skill_dispatch": REMEDIATOR_SKILL,
                "stop": "remediate",
            }
        return {"status": "blocked", "halt_reason": msg, "stop": "report"}
    return {"stack_tip": tip, "stack_tip_sha": sha, "stack_reason": reason}


def extract_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"} or not state.execute or not state.slices:
        return {}
    if state.current_slice >= len(state.slices):
        return {}
    repo = Path(state.repo).resolve()
    extract_fn: Callable[..., tuple[str, str]] = state.extract_fn or default_extract
    try:
        worktree, branch = extract_fn(
            repo, state.slices[state.current_slice], state.stack_tip, state.current_slice
        )
    except Exception as exc:
        return {"status": "blocked", "halt_reason": str(exc), "stop": "report"}
    return {"extract_worktree": worktree, "extract_branch": branch}


def publish_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"} or not state.execute or not state.slices:
        return {}
    if state.current_slice >= len(state.slices):
        return {}
    publish_fn: Callable[[str], dict[str, Any]] = state.publish_fn or default_publish
    try:
        result = publish_fn(state.extract_worktree)
    except Exception as exc:
        return {"status": "blocked", "halt_reason": str(exc), "stop": "report"}
    opened = list(state.opened_prs)
    opened.append(result)
    return {"opened_prs": opened, "current_slice": state.current_slice + 1}


def remediate_node(state: PrTrainState) -> dict[str, Any]:
    if state.status == "failed":
        return {}
    if state.status == "blocked" and state.skill_dispatch == REMEDIATOR_SKILL:
        return {"stop": "remediate"}
    if not state.execute:
        return {"stop": "remediate", "skill_dispatch": REMEDIATOR_SKILL}
    remediator: Callable[[PrTrainState], dict[str, Any]] | None = state.remediate_fn
    updates: dict[str, Any] = {
        "stop": "remediate",
        "skill_dispatch": REMEDIATOR_SKILL,
        "merge_authorized": False,
    }
    if remediator is None:
        return {
            **updates,
            "status": "blocked",
            "halt_reason": "awaiting l9-pr-remediation Converge",
        }
    extra = remediator(state)
    updates.update(extra)
    return updates


def ff_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"}:
        return {}
    if not state.execute:
        return {"stop": "ff", "ff_skipped": "plan-only"}
    repo = Path(state.repo).resolve()
    open_count = state.open_pr_count
    if open_count is None:
        try:
            open_count = count_open_prs(repo)
        except Exception as exc:
            return {"status": "blocked", "halt_reason": str(exc), "stop": "ff"}
    if open_count != 0:
        return {
            "open_pr_count": open_count,
            "ff_ran": False,
            "ff_skipped": f"open_pr={open_count}",
            "stop": "ff",
        }
    clone = resolve_ff_clone(repo, state.branch)
    ff_fn: Callable[[Path], subprocess.CompletedProcess[str]] = state.ff_fn or run_ff
    proc = ff_fn(clone)
    if proc.returncode != 0:
        return {
            "ff_clone": str(clone),
            "ff_ran": False,
            "status": "failed",
            "halt_reason": proc.stderr.strip() or proc.stdout.strip() or "ff.sh failed",
            "stop": "ff",
        }
    return {"ff_clone": str(clone), "ff_ran": True, "open_pr_count": open_count, "stop": "ff"}


def report_node(state: PrTrainState) -> dict[str, Any]:
    status = state.status if state.status != "running" else "complete"
    lines = [
        f"# PR train ({GRAPH_ID})",
        f"status: {status}",
        f"branch: {state.branch or '?'}",
        f"novel commits: {len(state.novel)} (skipped landed: {len(state.skipped_dup)})",
        f"slices: {len(state.slices)} (path ∪ generated-prefix ∪ merge-tree; unknown=colocate)",
        f"stack: {state.stack_reason or '(unprobed)'}",
        f"opened: {len(state.opened_prs)}",
        f"stop 2 skill: {state.skill_dispatch or '(not dispatched)'}"
        + (" — graph does not MERGE_TRAIN" if state.skill_dispatch else ""),
        f"open_pr_count: {state.open_pr_count}",
        f"stop 3 /ff: {'ran' if state.ff_ran else state.ff_skipped or 'not run'}",
    ]
    if state.halt_reason:
        lines.append(f"halt: {state.halt_reason}")
    if not state.execute:
        lines.append("execute=false — plan only; no extract/publish/merge/ff")
    return {"report": "\n".join(lines), "status": status, "stop": "report"}


def _repo_slug(repo: Path) -> str:
    return github_repo_slug(repo)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_start(state: PrTrainState) -> Literal["inventory", "ff"]:
    if state.ff_only:
        return "ff"
    return "inventory"


def route_after_slice(state: PrTrainState) -> Literal["stack_base", "remediate", "report"]:
    if state.status in {"blocked", "failed"}:
        return "report"
    if state.execute and state.slices:
        return "stack_base"
    if state.execute:
        return "report"
    return "remediate"


def route_after_stack(state: PrTrainState) -> Literal["extract", "remediate", "report"]:
    if state.status == "blocked" and state.skill_dispatch == REMEDIATOR_SKILL:
        return "remediate"
    if state.status in {"blocked", "failed"}:
        return "report"
    return "extract"


def route_after_extract(state: PrTrainState) -> Literal["publish", "report"]:
    if state.status in {"blocked", "failed"}:
        return "report"
    return "publish"


def route_after_publish(state: PrTrainState) -> Literal["stack_base", "remediate", "report"]:
    if state.status in {"blocked", "failed"}:
        return "report"
    if state.current_slice < len(state.slices):
        return "stack_base"
    return "remediate"


def route_after_remediate(state: PrTrainState) -> Literal["ff", "report"]:
    if state.status in {"blocked", "failed"}:
        return "report"
    return "ff"


def build_pr_train_graph():
    graph = StateGraph(PrTrainState)
    graph.add_node("inventory", inventory_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("slice", slice_node)
    graph.add_node("stack_base", stack_base_node)
    graph.add_node("extract", extract_node)
    graph.add_node("publish", publish_node)
    graph.add_node("remediate", remediate_node)
    graph.add_node("ff", ff_node)
    graph.add_node("report", report_node)

    graph.add_conditional_edges(
        START,
        route_start,
        {"inventory": "inventory", "ff": "ff"},
    )
    graph.add_edge("inventory", "diagnose")
    graph.add_edge("diagnose", "slice")
    graph.add_conditional_edges(
        "slice",
        route_after_slice,
        {"stack_base": "stack_base", "remediate": "remediate", "report": "report"},
    )
    graph.add_conditional_edges(
        "stack_base",
        route_after_stack,
        {"extract": "extract", "remediate": "remediate", "report": "report"},
    )
    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {"publish": "publish", "report": "report"},
    )
    graph.add_conditional_edges(
        "publish",
        route_after_publish,
        {"stack_base": "stack_base", "remediate": "remediate", "report": "report"},
    )
    graph.add_conditional_edges(
        "remediate",
        route_after_remediate,
        {"ff": "ff", "report": "report"},
    )
    graph.add_edge("ff", "report")
    graph.add_edge("report", END)
    return graph.compile()


PR_TRAIN_DAG = build_pr_train_graph()


def run_pr_train(
    repo: str | Path | None = None,
    *,
    execute: bool = False,
    campaign_override: bool = False,
    fetch: bool = True,
    all_refs: bool = False,
    refs: list[str] | None = None,
    ff_only: bool = False,
    **hooks: Any,
) -> PrTrainState:
    initial = PrTrainState(
        repo=str(Path(repo or Path.cwd()).resolve()),
        execute=execute or ff_only,
        campaign_override=campaign_override,
        fetch=fetch,
        all_refs=all_refs,
        refs=list(refs or []),
        ff_only=ff_only,
        **hooks,
    )
    result = PR_TRAIN_DAG.invoke(initial)
    return PrTrainState.model_validate(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--campaign-override", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--all-refs", action="store_true")
    parser.add_argument("--ref", action="append", dest="refs", default=[])
    parser.add_argument("--ff-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    state = run_pr_train(
        args.repo,
        execute=args.execute,
        campaign_override=args.campaign_override,
        fetch=not args.no_fetch,
        all_refs=args.all_refs,
        refs=args.refs,
        ff_only=args.ff_only,
    )
    if args.json:
        print(state.model_dump_json(indent=2))
    else:
        print(state.report)
    return 0 if state.status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
