#!/usr/bin/env python3
"""Diagnose unique value of a ref vs baseline (default origin/main)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from git_fetch import NO_FETCH, fetch_origin

# 59371162 (#334) sliced these to 50 as a display bound. pr-train's
# diagnose_node fail-closes when cherry_novel > len(cherry_novel_commits),
# so a cap below the branch silently blocks the train. 100 is the floor.
RECEIPT_SHA_LIST_CAP = 100
RECEIPT_SUBJECT_LIST_CAP = 100


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _cherry(repo: Path, baseline: str, ref: str) -> tuple[bool, list[str], list[str]]:
    """Split baseline..ref into patches that are novel and patches already upstream.

    ``git cherry -v`` marks a commit ``-`` when an equivalent patch id is already
    reachable from the baseline and ``+`` when it is not. That distinction is the
    whole point of this pack: a squash-merged or superseded branch still reports
    commits ahead, so counting commits alone calls it unique work when none of it
    is. Returns (available, novel_shas, duplicate_shas); available is False when
    git could not answer, which callers must treat as unproven, never as novel.
    """
    proc = _run(repo, "cherry", "-v", baseline, ref)
    if proc.returncode != 0:
        return False, [], []
    novel: list[str] = []
    dup: list[str] = []
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if len(line) < 2 or line[0] not in "+-":
            continue
        fields = line[2:].split(None, 1)
        if not fields:
            continue
        (novel if line[0] == "+" else dup).append(fields[0])
    return True, novel, dup


def _changed_lines(repo: Path, base: str, ref: str, path: str) -> tuple[list[str], list[str], bool]:
    """Lines this ref added and removed for one path, relative to the merge base."""
    diff = _run(repo, "diff", "--unified=0", base, ref, "--", path)
    if diff.returncode != 0:
        return [], [], False
    added: list[str] = []
    removed: list[str] = []
    for line in diff.stdout.splitlines():
        if line.startswith("Binary files"):
            return [], [], False
        if line.startswith(("old mode ", "new mode ")):
            # A permission change carries no lines, so a line comparison would
            # "verify" it by finding nothing to check. Refuse to judge instead.
            # Only true mode flips qualify: "new file mode" and "deleted file
            # mode" head an ordinary diff whose lines are present and checkable.
            return [], [], False
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") and line[1:].strip():
            added.append(line[1:])
        elif line.startswith("-") and line[1:].strip():
            removed.append(line[1:])
    return added, removed, True


def _contained(repo: Path, baseline: str, ref: str, paths: list[str]) -> bool:
    """Has every edit this ref made already been absorbed by the baseline?

    ``git cherry`` compares patch ids, so it cannot see work that reached the
    baseline as a *fuller reimplementation* -- different bytes, same substance.
    That shape is common and it is what leaves dead branches lying around.

    The comparison is against the **merge base**, not against whole files. A ref
    that trails the baseline by hundreds of commits has a stale copy of nearly
    everything, so comparing file contents would report "the baseline is missing
    all this" for text that is merely old. Only the lines this ref actually
    touched are its work, so only those are asked about: every line it added must
    appear in the baseline's copy, and every line it removed must be gone from it.

    Still a heuristic. A rename, a reindent, or a line that coincidentally exists
    elsewhere in the file will all fool it, which is why it may only ever argue
    that a ref is redundant -- never that a ref is unique.
    """
    if not paths:
        return False
    merge_base = _run(repo, "merge-base", baseline, ref)
    if merge_base.returncode != 0:
        return False
    base = merge_base.stdout.strip()

    for path in paths:
        added, removed, readable = _changed_lines(repo, base, ref, path)
        if not readable:
            return False
        if not added and not removed:
            continue
        blob = _run(repo, "show", f"{baseline}:{path}")
        if blob.returncode != 0:
            return False  # the baseline does not have this file at all
        current = set(blob.stdout.splitlines())
        if any(line not in current for line in added):
            return False  # an addition of this ref never landed
        if any(line in current for line in removed):
            return False  # a removal of this ref never landed
    return True


def _unexamined_merges(repo: Path, baseline: str, ref: str) -> int:
    """Count merge commits in baseline..ref, which ``git cherry`` never reports.

    ``git cherry`` compares patch ids of non-merge commits only. A merge whose
    conflict resolution introduced changes of its own therefore leaves no trace
    in either bucket, so a range of otherwise-duplicate commits looks completely
    absorbed and earns the exact ``patch_id`` verdict -- the one basis
    prune-policy lets authorise a delete. Counting them lets `_classify`
    withhold that verdict on evidence it does not actually have.
    """
    proc = _run(repo, "rev-list", "--merges", f"{baseline}..{ref}")
    if proc.returncode != 0:
        return 0
    return len([ln for ln in proc.stdout.splitlines() if ln.strip()])


def _classify(
    baseline_ok: bool,
    unique_commits: int,
    paths: list[str],
    cherry_available: bool,
    cherry_novel: list[str],
    cherry_dup: list[str],
    contained: bool,
    unexamined_merges: int = 0,
) -> tuple[str, str]:
    """Pick a classification, biased toward keeping the ref whenever proof is thin."""
    if not baseline_ok:
        # No baseline means novelty is unprovable. Falling through to the commit
        # counters would read zero commits and zero paths and call the ref a prune
        # candidate -- the exact inversion SKILL.md forbids.
        return "unknown", "unknown"
    if (
        cherry_available
        and unique_commits > 0
        and not cherry_novel
        and cherry_dup
        and not unexamined_merges
    ):
        # Commits ahead, but every one is already upstream by patch id. Exact.
        # Only exact while git cherry saw the whole range: it skips merges, and a
        # merge can carry conflict resolution that landed nowhere else, so any
        # unexamined merge drops through to the weaker signals below rather than
        # granting a basis that authorises deletion.
        return "archive_ref", "high"
    if unique_commits == 0:
        # An empty commit range means the ref is an ancestor of the baseline, so
        # the three-dot diff is empty too: there is no "no commits but new paths"
        # state to distinguish here.
        return "prune_candidate", "high"
    if contained:
        # Every line this ref touched is accounted for upstream, so the work
        # landed reimplemented. Cherry disagrees by construction in this case --
        # the patch ids differ, which is exactly why absorption is consulted --
        # so this is the weaker of the two signals and is graded accordingly.
        # `redundancy_basis` records which signal fired; prune-policy.md only
        # lets `patch_id` authorise a delete.
        return "archive_ref", "medium"
    # Includes the mixed case: one unaccounted patch is enough to keep the ref.
    return "keep_push", "high"


def _basis(
    classification: str, cherry_novel: list[str], cherry_dup: list[str], contained: bool
) -> str:
    """Name the evidence behind an archive_ref so a reader can weigh it.

    The two paths differ in strength and a prune decision should not have to
    re-derive which one fired: ``patch_id`` is exact, ``content_superset`` is a
    heuristic that a rename would fool.
    """
    if classification != "archive_ref":
        return ""
    if cherry_dup and not cherry_novel:
        return "patch_id"
    if contained:
        return "content_superset"
    return ""


def diagnose(repo: Path, ref: str, baseline: str, do_fetch: bool = False) -> dict:
    tip = _run(repo, "rev-parse", ref)
    if tip.returncode != 0:
        raise SystemExit(f"cannot resolve ref {ref}: {tip.stderr.strip()}")
    tip_sha = tip.stdout.strip()

    fetch = fetch_origin(repo, baseline) if do_fetch else dict(NO_FETCH)

    base = _run(repo, "rev-parse", "--verify", "--quiet", baseline)
    baseline_ok = base.returncode == 0
    baseline_tip = base.stdout.strip() if baseline_ok else ""

    log = _run(repo, "log", "--oneline", f"{baseline}..{ref}")
    commits = [ln for ln in log.stdout.splitlines() if ln.strip()] if log.returncode == 0 else []
    diff = _run(repo, "diff", "--name-only", f"{baseline}...{ref}")
    paths = [ln for ln in diff.stdout.splitlines() if ln.strip()] if diff.returncode == 0 else []

    cherry_available, cherry_novel, cherry_dup = (
        _cherry(repo, baseline, ref) if baseline_ok else (False, [], [])
    )

    contained = _contained(repo, baseline, ref, paths) if baseline_ok else False

    unique_commits = len(commits)
    unexamined_merges = _unexamined_merges(repo, baseline, ref) if baseline_ok else 0
    classification, confidence = _classify(
        baseline_ok,
        unique_commits,
        paths,
        cherry_available,
        cherry_novel,
        cherry_dup,
        contained,
        unexamined_merges,
    )

    body = {
        "receipt_id": hashlib.sha256(f"{repo}|{ref}|{tip_sha}".encode()).hexdigest()[:16],
        "mode": "diagnose-value",
        "repo": str(repo.resolve()),
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_ref": baseline,
        "baseline_resolved": baseline_ok,
        "baseline_tip": baseline_tip,
        "fetched": fetch["fetched"],
        "fetch_error": fetch["error"],
        "ref": ref,
        "tip_sha": tip_sha,
        "classification": classification,
        "confidence": confidence,
        "unique_commits": unique_commits,
        "unique_paths": paths,
        "cherry_available": cherry_available,
        "cherry_novel": len(cherry_novel),
        "cherry_dup": len(cherry_dup),
        "cherry_novel_commits": cherry_novel[:RECEIPT_SHA_LIST_CAP],
        "cherry_dup_commits": cherry_dup[:RECEIPT_SHA_LIST_CAP],
        "merge_commits_unexamined": unexamined_merges,
        "content_contained": contained,
        "redundancy_basis": _basis(classification, cherry_novel, cherry_dup, contained),
        "commit_subjects": commits[:RECEIPT_SUBJECT_LIST_CAP],
        "rollback": f"git checkout {tip_sha}  # or reflog",
    }
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git work tree")
    parser.add_argument("--ref", required=True, help="Branch or commit to diagnose")
    parser.add_argument("--baseline", default="origin/main")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Refresh origin first so novelty is judged against current remote state",
    )
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    receipt = diagnose(repo, args.ref, args.baseline, do_fetch=args.fetch)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
