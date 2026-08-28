#!/usr/bin/env python3
"""Triage the refs `/ff` parked, using the same evidence as ref diagnosis.

`/ff` belongs to `l9-repo-sync`. It parks unique work rather than deleting it,
which is the right default and also means the preserve refs accumulate: nothing
in that command ever revisits them, so a clone slowly fills with refs nobody can
tell apart. Some hold work that has since landed; some are the only surviving
copy of work that never did.

This is the handoff. It reads what `/ff` parked and classifies each ref through
`diagnose_ref_value.diagnose`, so the answer comes from patch-id and absorption
evidence rather than from a date or a commit count. It is read-only by
construction -- there is no delete path here at all. See `triage-handoff.md`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from diagnose_ref_value import _run, diagnose
from git_fetch import NO_FETCH, fetch_origin

# Written by skills/l9-repo-sync/scripts/ff.sh. Unique commits are parked at
# both a ref and a branch pointing at the same commit; the dirty tree is parked
# as a `git stash create` object, which is a commit too and diagnoses the same way.
#
# These are globs on purpose. A literal `for-each-ref` pattern only matches a
# whole ref or a prefix ending at a slash, so `refs/heads/l9/ff-preserve-` --
# a partial path component -- silently matches nothing at all.
PRESERVE_PATTERNS = (
    "refs/l9/preserved/ff/*",
    "refs/l9/preserved/ff-dirty/*",
    "refs/heads/l9/ff-preserve-*",
)

# classification (+ redundancy_basis) -> bucket. The split between `superseded`
# and `review` is the whole point: only patch-id evidence may ever authorise a
# removal, and even then not from here. See value-diagnosis.md.
BUCKETS = ("novel", "superseded", "review", "merged", "unproven")


def preserved_refs(repo: Path) -> list[str]:
    """Every ref `/ff` parks, in a stable order."""
    proc = _run(repo, "for-each-ref", "--format=%(refname)", *PRESERVE_PATTERNS)
    if proc.returncode != 0:
        return []
    return sorted(ln.strip() for ln in proc.stdout.splitlines() if ln.strip())


def _bucket(receipt: dict) -> str:
    classification = receipt.get("classification")
    if classification == "keep_push":
        return "novel"
    if classification == "prune_candidate":
        return "merged"
    if classification == "archive_ref":
        # A heuristic must never land in the bucket that reads as removable.
        return "superseded" if receipt.get("redundancy_basis") == "patch_id" else "review"
    return "unproven"


def triage(repo: Path, baseline: str, do_fetch: bool = False) -> dict:
    # Fetch once for the whole run, not once per ref: the refs are judged against
    # a single baseline and re-fetching would only add round trips.
    fetch = fetch_origin(repo, baseline) if do_fetch else dict(NO_FETCH)

    buckets: dict[str, list[str]] = {name: [] for name in BUCKETS}
    refs: list[dict] = []

    for ref in preserved_refs(repo):
        receipt = diagnose(repo, ref, baseline, do_fetch=False)
        bucket = _bucket(receipt)
        buckets[bucket].append(ref)
        refs.append(
            {
                "ref": ref,
                "bucket": bucket,
                "tip_sha": receipt["tip_sha"],
                "classification": receipt["classification"],
                "confidence": receipt["confidence"],
                "redundancy_basis": receipt["redundancy_basis"],
                "unique_commits": receipt["unique_commits"],
                "cherry_available": receipt["cherry_available"],
                "cherry_novel": receipt["cherry_novel"],
                "cherry_dup": receipt["cherry_dup"],
                "content_contained": receipt["content_contained"],
                "restore": f"git branch <name> {receipt['tip_sha']}",
            }
        )

    return {
        "receipt_id": hashlib.sha256(f"{repo}|triage|{len(refs)}".encode()).hexdigest()[:16],
        "schema": "l9.git_work_preserve.triage/v1",
        "mode": "triage-preserved",
        "repo": str(repo.resolve()),
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_ref": baseline,
        "baseline_tip": fetch["baseline_tip"],
        "fetched": fetch["fetched"],
        "fetch_error": fetch["error"],
        "preserved_total": len(refs),
        "buckets": buckets,
        "refs": refs,
        # Stated in the receipt so a consumer cannot mistake triage for prune.
        "deletes_performed": 0,
        "removal_path": "prune-policy.md (prune-execute; patch_id basis only)",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage refs parked by /ff (read-only)")
    parser.add_argument("--repo", default=".", help="Git work tree")
    parser.add_argument("--baseline", default="origin/main")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Refresh origin first so novelty is judged against current remote state",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON (default)")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    print(json.dumps(triage(repo, args.baseline, do_fetch=args.fetch), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
