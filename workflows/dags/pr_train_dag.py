"""PR-train LangGraph — open stacked PRs, converge, then /ff.

LANGGRAPH_RUNTIME (not a SessionDAG). Never call register_session_dag.

Stops (one slash, one graph):

1. OPEN_TRAIN — inventory unique local commits, drop already-landed patches,
   keep colliding paths in one slice, cherry-pick onto the unique stack tip,
   publish with ``PR_STACK=auto make pr``.
2. REMEDIATE — dispatch skill ``l9-pr-remediation`` Converge (merge
   authorization for all open PRs). Do not run ``make pr`` here.
3. FF — only when ``open_pr_count == 0``, run ``skills/l9-repo-sync/scripts/ff.sh``.

Rebase and conflict resolution stay forbidden. Cherry-pick conflict stops.
Campaign branches halt unless ``campaign_override``.
"""

from __future__ import annotations

import argparse
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
GRAPH_ID = "pr-train-v1"
MAX_SLICES = 32
REMEDIATOR_SKILL = "l9-pr-remediation"


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


def group_slices(commits: list[NovelCommit]) -> list[list[NovelCommit]]:
    """Union-find by shared paths. Overlapping hunk owners stay one PR."""
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


def load_commit_paths(repo: Path, sha: str) -> tuple[str, ...]:
    proc = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha)
    if proc.returncode != 0:
        return ()
    return tuple(line for line in proc.stdout.splitlines() if line.strip())


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
    remote = _git(repo, "remote", "get-url", "origin")
    if remote.returncode != 0:
        raise RuntimeError("cannot resolve origin for open-PR count")
    url = remote.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    if "github.com" not in url:
        raise RuntimeError("origin is not GitHub; refuse open-PR count")
    tail = url.split("github.com", 1)[1].lstrip(":/")
    parts = [p for p in tail.split("/") if p]
    slug = f"{parts[0]}/{parts[1]}"
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


def default_publish(worktree: str) -> dict[str, Any]:
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
    refs = [row["name"] for row in data.get("unpushed_or_diverged") or [] if row.get("name")]
    if branch and branch not in refs and data.get("head"):
        refs = [branch, *refs]
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
                novel.append({"sha": sha, "paths": list(paths), "ref": ref})
    except Exception as exc:
        return {"status": "failed", "halt_reason": str(exc), "errors": [str(exc)]}
    return {"diagnoses": diagnoses, "novel": novel, "skipped_dup": skipped}


def slice_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"}:
        return {}
    commits = [
        NovelCommit(sha=row["sha"], paths=tuple(row.get("paths") or ()), ref=row.get("ref") or "")
        for row in state.novel
    ]
    slices = [
        [{"sha": c.sha, "paths": list(c.paths), "ref": c.ref} for c in group]
        for group in group_slices(commits)
    ]
    if len(slices) > MAX_SLICES:
        return {
            "slices": slices[:MAX_SLICES],
            "status": "blocked",
            "halt_reason": f"slice cap {MAX_SLICES} exceeded",
            "stop": "report",
        }
    return {"slices": slices, "current_slice": 0}


def stack_base_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"}:
        return {}
    if not state.slices or not state.execute:
        return {}
    repo = Path(state.repo).resolve()
    try:
        tip, sha, reason = load_stack_tip(repo, state.baseline)
    except Exception as exc:
        return {"status": "blocked", "halt_reason": str(exc), "stop": "report"}
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
    if state.status in {"blocked", "failed"}:
        return {}
    if not state.execute:
        return {"stop": "remediate", "skill_dispatch": REMEDIATOR_SKILL}
    repo = Path(state.repo).resolve()
    remediator: Callable[[PrTrainState], dict[str, Any]] | None = state.remediate_fn
    updates: dict[str, Any] = {
        "stop": "remediate",
        "skill_dispatch": REMEDIATOR_SKILL,
        "merge_authorized": True,
    }
    if remediator is None:
        try:
            authorize_merge(
                _repo_slug(repo),
                "pr-train-v1 stop 2: l9-pr-remediation Converge",
            )
        except Exception as exc:
            return {
                "stop": "remediate",
                "skill_dispatch": REMEDIATOR_SKILL,
                "status": "blocked",
                "halt_reason": str(exc),
            }
        try:
            updates["open_pr_count"] = count_open_prs(repo)
        except Exception as exc:
            return {**updates, "status": "blocked", "halt_reason": str(exc)}
        return updates
    extra = remediator(state)
    updates.update(extra)
    return updates


def ff_node(state: PrTrainState) -> dict[str, Any]:
    if state.status in {"blocked", "failed"}:
        return {}
    if not state.execute:
        return {"stop": "ff", "ff_skipped": "plan-only"}
    if state.open_pr_count is None:
        return {"status": "blocked", "halt_reason": "open_pr_count unknown; refuse /ff"}
    if state.open_pr_count != 0:
        return {
            "ff_ran": False,
            "ff_skipped": f"open_pr={state.open_pr_count}",
            "stop": "ff",
        }
    if not state.execute:
        return {"stop": "ff", "ff_skipped": "plan-only"}
    repo = Path(state.repo).resolve()
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
    return {"ff_clone": str(clone), "ff_ran": True, "stop": "ff"}


def report_node(state: PrTrainState) -> dict[str, Any]:
    status = state.status if state.status != "running" else "complete"
    lines = [
        f"# PR train ({GRAPH_ID})",
        f"status: {status}",
        f"branch: {state.branch or '?'}",
        f"novel commits: {len(state.novel)} (skipped landed: {len(state.skipped_dup)})",
        f"slices: {len(state.slices)}",
        f"opened: {len(state.opened_prs)}",
        f"stop 2 skill: {state.skill_dispatch or '(not dispatched)'}",
        f"open_pr_count: {state.open_pr_count}",
        f"stop 3 /ff: {'ran' if state.ff_ran else state.ff_skipped or 'not run'}",
    ]
    if state.halt_reason:
        lines.append(f"halt: {state.halt_reason}")
    if not state.execute:
        lines.append("execute=false — plan only; no extract/publish/merge/ff")
    return {"report": "\n".join(lines), "status": status, "stop": "report"}


def _repo_slug(repo: Path) -> str:
    remote = _git(repo, "remote", "get-url", "origin")
    url = remote.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    tail = url.split("github.com", 1)[1].lstrip(":/")
    parts = [p for p in tail.split("/") if p]
    return f"{parts[0]}/{parts[1]}"


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_after_slice(state: PrTrainState) -> Literal["stack_base", "remediate", "report"]:
    if state.status in {"blocked", "failed"}:
        return "report"
    if state.slices and state.execute:
        return "stack_base"
    return "remediate"


def route_after_stack(state: PrTrainState) -> Literal["extract", "report"]:
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

    graph.add_edge(START, "inventory")
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
        {"extract": "extract", "report": "report"},
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
    **hooks: Any,
) -> PrTrainState:
    initial = PrTrainState(
        repo=str(Path(repo or Path.cwd()).resolve()),
        execute=execute,
        campaign_override=campaign_override,
        fetch=fetch,
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    state = run_pr_train(
        args.repo,
        execute=args.execute,
        campaign_override=args.campaign_override,
        fetch=not args.no_fetch,
    )
    if args.json:
        print(state.model_dump_json(indent=2))
    else:
        print(state.report)
    return 0 if state.status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
