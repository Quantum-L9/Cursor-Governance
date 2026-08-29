#!/usr/bin/env python3
"""Automatic, evidence-based cleanup of local git residue.

The friction this removes: stale local branches, per-PR worktrees left behind
after their PR lands, stashes nobody pops, and having to ask an agent whether
there are untracked files. All of it is decidable from git plus the PR state,
so none of it should require a human prompt.

Safety contract
---------------
Nothing is deleted unless its content is provably recoverable afterwards:

1. Every deletion is preceded by a preserve ref under refs/l9/preserved/, so
   the tip stays reachable indefinitely (reflog expiry cannot reap it).
2. A branch is only deletable with positive evidence that its work landed --
   a MERGED pull request for that head, or no commits unique to it versus
   origin/main. Squash merges break ancestry, which is why the PR state is
   consulted first rather than `git branch --merged`.
3. Worktrees are only removed when `git status --porcelain` is empty, so no
   modified or untracked file is ever discarded.
4. Stashes are never dropped without first writing a preserve ref.
5. Untracked files are reported, never deleted.

A branch whose PR was CLOSED while still holding unique commits is reported as
`closed_unlanded` and kept. That is the shape that loses work silently when a
stacked parent is squash-merged, so surfacing it is the point.

Usage
-----
    repo_hygiene.py                     # report, exit 0
    repo_hygiene.py --apply             # perform the safe deletions
    repo_hygiene.py --json              # machine-readable receipt
    repo_hygiene.py --assert-origin Quantum-L9/Cursor-Governance
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

PRESERVE_NS = "refs/l9/preserved"
L4_RECEIPT_DIR = ".l9/autonomy"
L4_RECEIPT_NAMES = ("l4-local-phase.json", "l4-release-receipt.json")
DEFAULT_L4_RECEIPT_AGE_HOURS = 12.0
PROTECTED_BRANCHES = {"main", "master", "HEAD"}
PROTECTED_PREFIXES = ("campaign/",)
DEFAULT_STASH_AGE_HOURS = 24.0
GH_LIMIT = 200
GH_TIMEOUT = 30

SAFE_TO_DELETE = {"merged", "absorbed"}


@dataclass
class BranchFinding:
    name: str
    tip: str
    status: str
    detail: str
    unique_commits: int = 0
    worktree: str = ""
    action: str = "keep"


@dataclass
class WorktreeFinding:
    path: str
    branch: str
    status: str
    detail: str
    action: str = "keep"


@dataclass
class StashFinding:
    ref: str
    tip: str
    age_hours: float
    subject: str
    action: str = "keep"


@dataclass
class ReceiptFinding:
    path: str
    branch: str
    contract_id: str
    age_hours: float
    status: str
    detail: str
    action: str = "keep"


@dataclass
class Report:
    repo: str = ""
    origin: str = ""
    applied: bool = False
    branches: list[BranchFinding] = field(default_factory=list)
    worktrees: list[WorktreeFinding] = field(default_factory=list)
    stashes: list[StashFinding] = field(default_factory=list)
    receipts: list[ReceiptFinding] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    preserved_refs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Git:
    def __init__(self, root: Path) -> None:
        self.root = root

    def __call__(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(cwd or self.root), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def out(self, *args: str, cwd: Path | None = None) -> str:
        return self(*args, cwd=cwd).stdout.strip()

    def ok(self, *args: str, cwd: Path | None = None) -> bool:
        return self(*args, cwd=cwd).returncode == 0


def origin_slug(url: str) -> str:
    """owner/name from an ssh or https remote URL."""
    match = re.search(r"[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", url)
    return match.group(1) if match else ""


def pr_index(slug: str) -> tuple[dict[str, dict], str]:
    """Map head branch -> most recent PR record. Empty map when gh cannot answer."""
    if not slug or not shutil.which("gh"):
        return {}, "gh unavailable"
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [
                "gh",
                "pr",
                "list",
                "--repo",
                slug,
                "--state",
                "all",
                "--limit",
                str(GH_LIMIT),
                "--json",
                "number,headRefName,state,mergedAt",
            ],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {}, f"gh failed: {exc}"
    if proc.returncode != 0:
        return {}, (proc.stderr or "gh returned non-zero").strip().splitlines()[-1][:200]
    try:
        records = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        return {}, f"gh emitted non-JSON: {exc}"

    index: dict[str, dict] = {}
    for record in records:
        head = str(record.get("headRefName") or "")
        if not head:
            continue
        prior = index.get(head)
        # MERGED beats any other state; otherwise the highest PR number wins.
        if prior is None:
            index[head] = record
        elif record.get("state") == "MERGED":
            index[head] = record
        elif prior.get("state") != "MERGED" and record.get("number", 0) > prior.get("number", 0):
            index[head] = record
    return index, ""


def worktree_map(git: Git) -> dict[str, Path]:
    """branch name -> worktree path, for every linked worktree."""
    mapping: dict[str, Path] = {}
    current: Path | None = None
    for line in git.out("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            current = Path(line[len("worktree ") :])
        elif line.startswith("branch ") and current is not None:
            mapping[line[len("branch refs/heads/") :]] = current
    return mapping


def protected(branch: str) -> bool:
    return branch in PROTECTED_BRANCHES or branch.startswith(PROTECTED_PREFIXES)


MAX_DIFF_PATHS = 500


def content_in_main(git: Git, name: str) -> bool:
    """True when every path this branch touched already matches origin/main.

    Ancestry cannot answer this: a squash merge lands the content while leaving
    the branch's commits unreachable from main. Comparing the branch's own
    changed paths against main answers it for squash, rebase, and merge alike.
    """
    changed = git.out("diff", "--name-only", f"origin/main...{name}").splitlines()
    if not changed:
        return True
    if len(changed) > MAX_DIFF_PATHS:
        return False  # too wide to verify cheaply; treat as unlanded
    return git.ok("diff", "--quiet", "origin/main", name, "--", *changed)


def classify_branch(
    git: Git, name: str, prs: dict[str, dict], worktrees: dict[str, Path]
) -> BranchFinding:
    tip = git.out("rev-parse", name)
    unique = git.out("rev-list", "--count", f"origin/main..{name}")
    unique_n = int(unique) if unique.isdigit() else 0
    wt = str(worktrees.get(name, ""))
    finding = BranchFinding(
        name=name, tip=tip, status="", detail="", unique_commits=unique_n, worktree=wt
    )

    if protected(name):
        finding.status, finding.detail = "protected", "protected branch"
        return finding

    record = prs.get(name)
    pr_state = str(record.get("state")) if record else ""
    pr_ref = f"PR #{record['number']}" if record else "no pull request"
    landed = content_in_main(git, name)

    if unique_n == 0:
        finding.status, finding.detail = "absorbed", "no commits unique to origin/main"
    elif landed:
        finding.status = "merged" if pr_state == "MERGED" else "absorbed"
        finding.detail = f"content already in origin/main ({pr_ref})"
    elif pr_state == "MERGED":
        # Branch name reused after its PR merged: the merge is real but these
        # commits are not it. Deleting on the PR state alone would lose them.
        finding.status = "reused_after_merge"
        finding.detail = (
            f"{pr_ref} merged, but {unique_n} later commit(s) on this branch are NOT in main"
        )
    elif pr_state == "CLOSED":
        finding.status = "closed_unlanded"
        finding.detail = f"{pr_ref} closed with {unique_n} unique commit(s) NOT in main"
    elif pr_state == "OPEN":
        finding.status, finding.detail = "open_pr", f"{pr_ref} open"
    else:
        finding.status = "unmerged_no_pr"
        finding.detail = f"{unique_n} unique commit(s), no pull request"
    return finding


def classify_worktree(
    git: Git, path: Path, branch: str, branch_status: dict[str, str]
) -> WorktreeFinding:
    finding = WorktreeFinding(path=str(path), branch=branch, status="", detail="")
    if not path.exists():
        finding.status, finding.detail = "missing", "path gone; prune only"
        return finding
    dirty = git.out("status", "--porcelain", cwd=path)
    if dirty:
        lines = dirty.splitlines()
        finding.status = "dirty"
        finding.detail = f"{len(lines)} uncommitted/untracked path(s)"
        return finding
    if not branch:
        finding.status, finding.detail = "detached", "detached HEAD, clean"
        return finding
    if branch_status.get(branch) in SAFE_TO_DELETE:
        finding.status = "spent"
        finding.detail = f"clean, branch {branch_status[branch]}"
        return finding
    finding.status, finding.detail = "active", f"clean, branch {branch_status.get(branch, '?')}"
    return finding


def classify_stashes(git: Git, max_age_hours: float) -> list[StashFinding]:
    findings: list[StashFinding] = []
    raw = git.out("stash", "list", "--format=%gd%x1f%H%x1f%ct%x1f%gs")
    now = time.time()
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 4:
            continue
        ref, tip, ts, subject = parts
        age = (now - float(ts)) / 3600.0 if ts.isdigit() else 0.0
        findings.append(StashFinding(ref=ref, tip=tip, age_hours=round(age, 1), subject=subject))
    for finding in findings:
        finding.action = "preserve+drop" if finding.age_hours >= max_age_hours else "keep"
    return findings


def _receipt_age_hours(payload: dict) -> float:
    for key in ("authorized_at", "recorded_at", "started_at"):
        raw = payload.get(key)
        if not raw:
            continue
        try:
            stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        return round((datetime.now(UTC) - stamp).total_seconds() / 3600.0, 1)
    return 0.0


def classify_receipts(git: Git, max_age_hours: float) -> list[ReceiptFinding]:
    """L4 phase/release receipts that no longer describe this checkout.

    A receipt naming a branch the checkout is not on still reads as
    authoritative to `ops/autonomy/local_execution_gate.py`, which then refuses
    an unrelated publish with a branch name nobody recognises. Expiring them is
    what keeps that gate's message truthful.
    """
    findings: list[ReceiptFinding] = []
    current = git.out("rev-parse", "--abbrev-ref", "HEAD")
    for name in L4_RECEIPT_NAMES:
        path = git.root / L4_RECEIPT_DIR / name
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            findings.append(
                ReceiptFinding(str(path), "", "", 0.0, "unreadable", "not valid JSON", "archive")
            )
            continue
        branch = str(payload.get("stacked_branch") or payload.get("branch") or "")
        age = _receipt_age_hours(payload)
        finding = ReceiptFinding(
            path=str(path),
            branch=branch,
            contract_id=str(payload.get("contract_id") or ""),
            age_hours=age,
            status="",
            detail="",
        )
        if branch and branch != current:
            finding.status = "foreign-branch"
            finding.detail = f"receipt names '{branch}', checkout is on '{current}'"
            finding.action = "archive"
        elif age >= max_age_hours:
            finding.status = "expired"
            finding.detail = f"{age}h old (limit {max_age_hours}h)"
            finding.action = "archive"
        else:
            finding.status = "current"
            finding.detail = f"matches '{current}', {age}h old"
        findings.append(finding)
    return findings


def preserve(git: Git, kind: str, label: str, sha: str, report: Report) -> bool:
    """Write an immortal ref at sha. Returns False if it could not be created."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or "unnamed"
    ref = f"{PRESERVE_NS}/{kind}/{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{safe}"
    if not git.ok("update-ref", ref, sha):
        report.errors.append(f"could not preserve {label} at {sha[:12]}; kept as-is")
        return False
    report.preserved_refs.append(ref)
    return True


def sync_remote_refs(git: Git) -> str | None:
    """Prune stale remote-tracking refs AND ensure origin/HEAD resolves.

    These two are one operation, not two, and #325 established why: pruning
    alone converts an OVERCOUNT into SILENCE. A branch deleted upstream leaves
    refs/remotes/origin/<branch> behind, so a checker resolving it counts every
    commit main gained since the merge as unpushed work (measured: 16 reported
    where 2 were real). Prune that ref and the fallback becomes origin/HEAD --
    which a fetch-built checkout never sets -- so rev-list fails and the count
    reads 0 with real unpushed commits present. A false negative on a real
    condition is worse than an inflated one.

    ops/scripts/bootstrap_agent_environment.sh ships both halves at session
    start. This function is the same contract for the tool that DELETES
    branches on that evidence, which previously pruned without ever ensuring
    the fallback it creates a dependence on.

    Both halves are fail-soft: they need the remote, and a session with no
    network is not a reason to abort hygiene. Returns a warning, or None.
    """
    if not git.ok("remote", "get-url", "origin"):
        return None
    if not git.ok("fetch", "--prune", "origin"):
        return (
            "could not fetch/prune stale remote-tracking refs (remote unreachable); "
            "unpushed counts may overcount and branch judgements may be stale"
        )
    if git.ok("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"):
        return None
    if git.ok("remote", "set-head", "origin", "-a"):
        return None
    return (
        "origin/HEAD unset and could not be resolved — with stale refs pruned, "
        "a deleted branch leaves unpushed counts unreportable rather than merely wrong"
    )


def build_report(
    git: Git, *, max_stash_age: float, max_receipt_age: float = DEFAULT_L4_RECEIPT_AGE_HOURS
) -> Report:
    report = Report(repo=str(git.root))
    report.origin = git.out("remote", "get-url", "origin")
    slug = origin_slug(report.origin)
    ref_warning = sync_remote_refs(git)
    if ref_warning:
        report.errors.append(ref_warning)

    prs, pr_error = pr_index(slug)
    if pr_error:
        report.errors.append(
            f"PR state unavailable ({pr_error}); branches judged by ancestry only, "
            "so squash-merged branches will be kept rather than deleted"
        )

    worktrees = worktree_map(git)
    branches = [
        b for b in git.out("for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
    ]
    report.branches = [classify_branch(git, b, prs, worktrees) for b in branches]
    status_by_branch = {b.name: b.status for b in report.branches}

    for branch, path in sorted(worktrees.items(), key=lambda kv: str(kv[1])):
        if path.resolve() == git.root.resolve():
            continue
        report.worktrees.append(classify_worktree(git, path, branch, status_by_branch))

    report.stashes = classify_stashes(git, max_stash_age)
    report.receipts = classify_receipts(git, max_receipt_age)
    report.untracked = git.out("status", "--porcelain", "--untracked-files=normal").splitlines()

    # A branch checked out in a worktree can only go once that worktree does.
    removable = {w.branch for w in report.worktrees if w.status in {"spent", "missing"}}
    for finding in report.branches:
        if finding.status not in SAFE_TO_DELETE:
            continue
        if finding.worktree and finding.name not in removable:
            finding.action = "blocked-by-worktree"
        else:
            finding.action = "delete"
    for worktree in report.worktrees:
        if worktree.status in {"spent", "missing"}:
            worktree.action = "remove"
    return report


def apply_report(git: Git, report: Report) -> None:
    for worktree in report.worktrees:
        if worktree.action != "remove":
            continue
        if not git.ok("worktree", "remove", worktree.path):
            worktree.action = "remove-failed"
            report.errors.append(f"could not remove worktree {worktree.path}")
    git("worktree", "prune")

    for branch in report.branches:
        if branch.action != "delete":
            continue
        if not preserve(git, "branch", branch.name, branch.tip, report):
            branch.action = "delete-failed"
            continue
        # -D not -d: a squash-merged branch is not an ancestor of main, so the
        # ancestry check git uses for -d cannot see that the work landed. The
        # preserve ref above is what makes this recoverable.
        if not git.ok("branch", "-D", branch.name):
            branch.action = "delete-failed"
            report.errors.append(f"could not delete branch {branch.name}")

    for stash in reversed(report.stashes):  # reverse: dropping renumbers the rest
        if stash.action != "preserve+drop":
            continue
        if not preserve(git, "stash", stash.subject, stash.tip, report):
            stash.action = "preserve-failed"
            continue
        if not git.ok("stash", "drop", stash.ref):
            stash.action = "drop-failed"
            report.errors.append(f"could not drop {stash.ref}")

    for receipt in report.receipts:
        if receipt.action != "archive":
            continue
        source = Path(receipt.path)
        target = (
            source.parent
            / "expired"
            / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{source.name}"
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
        except OSError as exc:
            receipt.action = "archive-failed"
            report.errors.append(f"could not archive {source}: {exc}")

    report.applied = True


def render(report: Report) -> str:
    lines = [f"repo hygiene: {report.repo}", f"origin: {report.origin}", ""]

    def section(title: str, rows: list[str]) -> None:
        lines.append(title)
        lines.extend(rows or ["  (none)"])
        lines.append("")

    section(
        "branches",
        [
            f"  {b.action:<20} {b.name:<44} {b.status:<16} {b.detail}"
            for b in sorted(report.branches, key=lambda b: (b.action != "delete", b.name))
        ],
    )
    section(
        "worktrees",
        [f"  {w.action:<20} {w.path:<44} {w.status:<16} {w.detail}" for w in report.worktrees],
    )
    section(
        "stashes",
        [f"  {s.action:<20} {s.ref:<44} {s.age_hours:>6.1f}h  {s.subject}" for s in report.stashes],
    )

    section(
        "L4 receipts",
        [
            f"  {r.action:<20} {Path(r.path).name:<44} {r.status:<16} {r.detail}"
            for r in report.receipts
        ],
    )

    attention = [
        b for b in report.branches if b.status in {"closed_unlanded", "reused_after_merge"}
    ]
    if attention:
        section(
            "UNLANDED WORK — commits that exist nowhere in main",
            [f"  {b.name} — {b.detail} — recover from {b.tip[:12]}" for b in attention],
        )
    if report.untracked:
        section(
            f"untracked/modified in {report.repo} ({len(report.untracked)})",
            [f"  {entry}" for entry in report.untracked[:20]]
            + (["  ..."] if len(report.untracked) > 20 else []),
        )
    if report.preserved_refs:
        section(
            "preserved refs (recover with git branch <name> <ref>)",
            [f"  {ref}" for ref in report.preserved_refs],
        )
    if report.errors:
        section("errors", [f"  {err}" for err in report.errors])
    if not report.applied:
        lines.append("report only — re-run with --apply to perform the actions above")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="repo root (default: cwd)")
    parser.add_argument("--apply", action="store_true", help="perform the safe deletions")
    parser.add_argument(
        "--report", action="store_true", help="report only (default; overrides --apply)"
    )
    parser.add_argument("--json", action="store_true", help="emit the receipt as JSON")
    parser.add_argument(
        "--assert-origin",
        default="",
        metavar="OWNER/NAME",
        help="fail closed unless origin resolves to this slug",
    )
    parser.add_argument(
        "--stash-age-hours",
        type=float,
        default=DEFAULT_STASH_AGE_HOURS,
        help=f"preserve+drop stashes at least this old (default {DEFAULT_STASH_AGE_HOURS})",
    )
    parser.add_argument(
        "--l4-receipt-age-hours",
        type=float,
        default=DEFAULT_L4_RECEIPT_AGE_HOURS,
        help=f"archive L4 receipts at least this old (default {DEFAULT_L4_RECEIPT_AGE_HOURS})",
    )
    args = parser.parse_args(argv)

    root = Path(args.workspace).expanduser().resolve()
    git = Git(root)
    top = git.out("rev-parse", "--show-toplevel")
    if not top:
        print(f"not a git work tree: {root}", file=sys.stderr)
        return 2
    git.root = Path(top)

    if args.assert_origin:
        actual = origin_slug(git.out("remote", "get-url", "origin"))
        if actual != args.assert_origin:
            print(
                f"origin mismatch: expected {args.assert_origin}, found {actual or '<none>'}",
                file=sys.stderr,
            )
            return 3

    report = build_report(
        git, max_stash_age=args.stash_age_hours, max_receipt_age=args.l4_receipt_age_hours
    )
    if args.apply and not args.report:
        apply_report(git, report)
    print(json.dumps(asdict(report), indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
