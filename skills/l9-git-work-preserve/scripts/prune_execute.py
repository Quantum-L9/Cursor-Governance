#!/usr/bin/env python3
"""Auth-gated leftover prune: preserve-ref, then worktree, then local branch.

Report-only by default. ``--apply`` requires ``L9_GIT_PRUNE_AUTHORIZED`` and
high-confidence diagnosis receipts. SessionEnd hygiene still owns automatic
spent+clean residue; this script is the missing close for leftovers whose
unique value is already on ``origin/main`` or an open PR by receipt evidence.

Never deletes open-PR heads, ``campaign/*``, dirty porcelain, or
``content_superset`` archive_refs. Remote ``git push --delete`` stays off
unless the auth reason contains ``remote_delete=1`` and
``--confirm-remote-delete`` is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _ops_scripts() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "scripts" / "repo_hygiene.py"
        if candidate.is_file():
            return candidate.parent
    raise SystemExit("cannot locate ops/scripts/repo_hygiene.py")


sys.path.insert(0, str(_ops_scripts()))
import repo_hygiene  # noqa: E402

SCHEMA = "l9.git_work_preserve.receipt/v1"
AUTH_ENV = "L9_GIT_PRUNE_AUTHORIZED"
SSOT = Path.home() / ".cursor-governance"


def load_receipts(paths: list[Path]) -> list[dict]:
    out: list[dict] = []
    for path in paths:
        if path.is_dir():
            for child in sorted(path.glob("*.json")):
                out.extend(load_receipts([child]))
            continue
        if not path.is_file():
            raise SystemExit(f"receipt not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            out.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            out.append(data)
        else:
            raise SystemExit(f"receipt is not JSON object/array: {path}")
    return out


def receipt_authorizes_prune(receipt: dict, *, has_remote: bool) -> tuple[bool, str]:
    klass = str(receipt.get("classification") or "")
    conf = str(receipt.get("confidence") or "")
    basis = str(receipt.get("redundancy_basis") or "")
    if klass == "prune_candidate" and conf == "high":
        return True, "prune_candidate high"
    if klass == "archive_ref" and basis == "content_superset":
        return False, "content_superset never authorizes delete"
    if klass == "archive_ref" and basis == "patch_id" and conf == "high":
        if has_remote and not receipt.get("fetched"):
            return False, "archive_ref patch_id requires fetched:true when origin exists"
        if int(receipt.get("merge_commits_unexamined") or 0) > 0:
            return False, "unexamined merges forbid patch_id delete"
        return True, "archive_ref patch_id"
    return False, f"not authorized ({klass}/{conf}/{basis or '-'})"


def _write_hygiene_receipt(repo: Path, payload: dict) -> Path:
    dest = repo / ".l9" / "hygiene"
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = dest / f"prune-execute-{stamp}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _open_heads(git: repo_hygiene.Git, extra: list[str]) -> tuple[set[str], str | None]:
    heads = {h for h in extra if h}
    url = git.out("remote", "get-url", "origin")
    slug = repo_hygiene.origin_slug(url) if url else ""
    if not slug:
        return heads, None
    prs, err = repo_hygiene.pr_index(slug)
    if err:
        return heads, err
    for name, rec in prs.items():
        if str(rec.get("state") or "") == "OPEN":
            heads.add(name)
    return heads, None


def classify_targets(
    git: repo_hygiene.Git,
    receipts: list[dict],
    *,
    open_heads: set[str],
    has_remote: bool,
) -> list[dict]:
    worktrees = repo_hygiene.worktree_map(git)
    rows: list[dict] = []
    for receipt in receipts:
        ref = str(receipt.get("ref") or "").removeprefix("refs/heads/")
        tip_expected = str(receipt.get("tip_sha") or "")
        row: dict = {
            "ref": ref,
            "receipt_id": receipt.get("receipt_id"),
            "classification": receipt.get("classification"),
            "confidence": receipt.get("confidence"),
            "redundancy_basis": receipt.get("redundancy_basis") or "",
            "action": "keep",
            "detail": "",
            "worktree": "",
            "tip": "",
            "preserve_ref": "",
        }
        if not ref:
            row["detail"] = "receipt missing ref"
            rows.append(row)
            continue
        authorized, why = receipt_authorizes_prune(receipt, has_remote=has_remote)
        if not authorized:
            row["detail"] = why
            rows.append(row)
            continue
        if repo_hygiene.protected(ref) or ref in open_heads:
            row["detail"] = "protected or open_pr head"
            rows.append(row)
            continue
        tip_proc = git("rev-parse", "--verify", ref)
        if tip_proc.returncode != 0:
            row["detail"] = f"ref not present locally: {ref}"
            rows.append(row)
            continue
        tip = tip_proc.stdout.strip()
        row["tip"] = tip
        if tip_expected and tip_expected != tip:
            row["detail"] = f"tip moved (receipt {tip_expected[:12]} vs {tip[:12]})"
            rows.append(row)
            continue
        wt = worktrees.get(ref)
        if wt is not None:
            row["worktree"] = str(wt)
            if wt.resolve() == git.root.resolve():
                row["detail"] = "running in this worktree"
                rows.append(row)
                continue
            if wt.resolve() == SSOT.resolve() if SSOT.exists() else False:
                row["detail"] = "SSOT clone is not leftover residue"
                rows.append(row)
                continue
            if wt.exists():
                dirty = git.out("status", "--porcelain", cwd=wt)
                if dirty:
                    row["detail"] = "porcelain not empty; shipped-copy prune first"
                    rows.append(row)
                    continue
        row["action"] = "delete"
        row["detail"] = why
        rows.append(row)
    return rows


def apply_targets(
    git: repo_hygiene.Git,
    rows: list[dict],
    report: repo_hygiene.Report,
    *,
    remote_delete: bool,
) -> None:
    # Worktrees before branches so a checked-out head can go.
    ordered = sorted(rows, key=lambda r: (not r.get("worktree"), r.get("ref") or ""))
    for row in ordered:
        if row.get("action") != "delete":
            continue
        ref = row["ref"]
        tip = row["tip"]
        if remote_delete:
            remote_ref = f"refs/remotes/origin/{ref}"
            remote_tip = git.out("rev-parse", remote_ref) if git.ok("rev-parse", remote_ref) else ""
            if remote_tip and remote_tip != tip:
                row["action"] = "keep"
                row["detail"] = (
                    f"origin/{ref} moved past receipt tip; refusing delete "
                    f"{tip[:12]} -> {remote_tip[:12]}"
                )
                continue
        if not repo_hygiene.preserve(git, "branch", ref, tip, report):
            row["action"] = "delete-failed"
            row["detail"] = "preserve-ref failed; left in place"
            continue
        row["preserve_ref"] = report.preserved_refs[-1]
        wt = row.get("worktree") or ""
        if wt:
            if not git.ok("worktree", "remove", wt):
                row["action"] = "delete-failed"
                row["detail"] = f"worktree remove failed: {wt}"
                report.errors.append(row["detail"])
                continue
        git("worktree", "prune")
        if not git.ok("branch", "-D", ref):
            row["action"] = "delete-failed"
            row["detail"] = f"branch -D failed: {ref}"
            report.errors.append(row["detail"])
            continue
        if remote_delete:
            pushed = git("push", "origin", "--delete", ref)
            if pushed.returncode != 0:
                row["action"] = "remote-delete-failed"
                row["detail"] = (pushed.stderr or "git push --delete failed").strip()[:200]
                report.errors.append(row["detail"])
                continue
        row["action"] = "deleted"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="git work tree")
    parser.add_argument(
        "--receipt",
        action="append",
        default=[],
        help="diagnosis JSON file or directory (repeatable)",
    )
    parser.add_argument("--json", action="store_true", default=True, help="JSON receipt (default)")
    parser.add_argument("--apply", action="store_true", help="perform authorized deletions")
    parser.add_argument(
        "--open-head",
        action="append",
        default=[],
        help="treat this branch as an open PR head (tests / extra protect)",
    )
    parser.add_argument(
        "--confirm-remote-delete",
        action="store_true",
        help="second confirmation for remote_delete=1 (required with that token)",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="do not fetch (fixtures without a reachable origin)",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    git = repo_hygiene.Git(repo)
    top = git.out("rev-parse", "--show-toplevel")
    if not top:
        print(f"not a git work tree: {repo}", file=sys.stderr)
        return 2
    git.root = Path(top)

    has_remote = git.ok("remote", "get-url", "origin")
    if args.apply and has_remote and not args.skip_fetch:
        if not git.ok("fetch", "--prune", "origin"):
            print("fetch --prune origin failed; refusing --apply", file=sys.stderr)
            return 2

    receipt_paths = [Path(p).expanduser() for p in args.receipt]
    receipts = load_receipts(receipt_paths) if receipt_paths else []
    open_heads, index_err = _open_heads(git, args.open_head)
    if args.apply and index_err:
        print(
            f"open-PR lookup failed ({index_err}); refusing --apply",
            file=sys.stderr,
        )
        return 2
    rows = classify_targets(git, receipts, open_heads=open_heads, has_remote=has_remote)

    auth = (os.environ.get(AUTH_ENV) or "").strip()
    remote_delete = "remote_delete=1" in auth and args.confirm_remote_delete
    if args.apply and "remote_delete=1" in auth and not args.confirm_remote_delete:
        print(
            "remote_delete=1 requires --confirm-remote-delete; refusing remote delete",
            file=sys.stderr,
        )
        return 3

    report = repo_hygiene.Report(repo=str(git.root))
    applied = False
    if args.apply:
        if not auth:
            print(
                f"refusing --apply: set {AUTH_ENV}=<reason> (report-only without it)",
                file=sys.stderr,
            )
            payload = _payload(git, rows, receipts, applied=False, auth="", preserve=[])
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 3
        apply_targets(git, rows, report, remote_delete=remote_delete)
        applied = True

    payload = _payload(
        git,
        rows,
        receipts,
        applied=applied,
        auth=AUTH_ENV if auth else "",
        preserve=report.preserved_refs,
    )
    if applied:
        payload["hygiene_receipt"] = str(_write_hygiene_receipt(git.root, payload))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not any(str(r.get("action") or "").endswith("-failed") for r in rows) else 1


def _payload(
    git: repo_hygiene.Git,
    rows: list[dict],
    receipts: list[dict],
    *,
    applied: bool,
    auth: str,
    preserve: list[str],
) -> dict:
    return {
        "schema": SCHEMA,
        "mode": "prune-execute" if applied else "prune-propose",
        "repo": str(git.root),
        "created_at": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "baseline_ref": "origin/main",
        "applied": applied,
        "auth_env": auth,
        "receipt_count": len(receipts),
        "candidates": rows,
        "preserved_refs": preserve,
        "rollback": "git branch recovered <preserve-ref>  # then git worktree add <path> recovered",
        "counts": {
            "delete": sum(1 for r in rows if r.get("action") in {"delete", "deleted"}),
            "keep": sum(1 for r in rows if r.get("action") == "keep"),
            "deleted": sum(1 for r in rows if r.get("action") == "deleted"),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
