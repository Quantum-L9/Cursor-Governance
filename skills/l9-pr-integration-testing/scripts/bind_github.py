#!/usr/bin/env python3
"""Resolve immutable public/private GitHub PR metadata, without mutating repositories."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HEX = re.compile(r"^[0-9a-f]{40}$")


class BindingError(RuntimeError):
    pass


def github_get(path):
    url = "https://api.github.com" + path
    h = {"Accept": "application/vnd.github+json", "User-Agent": "l9-pr-integration-testing/0.1", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            if urllib.parse.urlsplit(response.geturl()).hostname != "api.github.com":
                raise BindingError("GitHub API response left approved host")
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise BindingError(f"GitHub API HTTP {exc.code} for {path}; check access and PR identity") from None
    except (OSError, ValueError) as exc:
        raise BindingError(f"GitHub API could not read {path}: {type(exc).__name__}") from None


def bind(repo: str, numbers: list[int], base_ref=None):
    if not REPO.fullmatch(repo):
        raise BindingError("repo must be owner/name")
    if not numbers or len(set(numbers)) != len(numbers) or len(numbers) > 8 or any(not isinstance(n, int) or n < 1 for n in numbers):
        raise BindingError("provide 1-8 distinct positive PR numbers")
    owner, name = repo.split("/", 1)
    enc = f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}"
    r = github_get(enc)
    if r.get("full_name", "").lower() != repo.lower():
        raise BindingError("repository does not resolve to requested identity")
    result_prs = []
    branches = set()
    for n in numbers:
        p = github_get(f"{enc}/pulls/{n}")
        if p.get("number") != n or p.get("state") != "open":
            raise BindingError(f"PR #{n} is not an open pull request with matching number")
        base = p.get("base") or {}
        head = p.get("head") or {}
        source_repo = (head.get("repo") or {}).get("full_name")
        src = head.get("sha")
        if not source_repo or not HEX.fullmatch(src or ""):
            raise BindingError(f"PR #{n} has inaccessible source repository or mutable head identity")
        target_repo = (base.get("repo") or {}).get("full_name")
        if (target_repo or "").lower() != repo.lower():
            raise BindingError(f"PR #{n} base repository differs from selected repository")
        base_name = base.get("ref")
        base_sha = base.get("sha")
        if not base_name or not HEX.fullmatch(base_sha or ""):
            raise BindingError(f"PR #{n} lacks resolvable base")
        branches.add(base_name)
        result_prs.append({"number": n, "base_ref": base_name, "pr_base_sha_at_binding": base_sha,
                           "head_sha": src, "source_repo": source_repo,
                           "source_branch": head.get("ref", "UNKNOWN"),
                           "fetch_url": f"https://github.com/{repo}.git", "fetch_ref": f"refs/pull/{n}/head",
                           "html_url": p.get("html_url"), "updated_at": p.get("updated_at")})
    if len(branches) != 1:
        raise BindingError("selected PRs target different branches; resolve stacked base before binding")
    target_ref = next(iter(branches))
    if base_ref is not None and base_ref != target_ref:
        raise BindingError("requested target base differs from actual PR target; explicit alternate-base resolution required")
    branch = github_get(f"{enc}/branches/{urllib.parse.quote(target_ref, safe='')}")
    branch_sha = (branch.get("commit") or {}).get("sha")
    if not HEX.fullmatch(branch_sha or ""):
        raise BindingError("target branch does not resolve to immutable SHA")
    return {"schema": "l9.pr-binding/v1", "binding_state": "BOUND_NOT_EXECUTION_AUTHORIZED",
            "bound_at": datetime.now(timezone.utc).isoformat(),
            "repository": {"full_name": r["full_name"], "url": f"https://github.com/{r['full_name']}.git",
                           "base_ref": target_ref, "base_sha": branch_sha},
            "prs": result_prs,
            "integration_order": numbers,
            "order_basis": "UNRESOLVED" if len(numbers) > 1 else "SINGLE_PR",
            "image": None, "test_procedures": [], "execution_authority": {"scope": "UNRESOLVED", "source": None},
            "negative_probes": [], "required_contracts": {"verified": False, "evidence": []},
            "source_review": {"state": "UNREVIEWED", "exact_revision_evidence": []}, "network": "none"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", action="append", type=int, required=True)
    ap.add_argument("--base-ref")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    try:
        if args.out.exists():
            raise BindingError("refusing to overwrite an existing binding")
        result = bind(args.repo, args.pr, args.base_ref)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    except (BindingError, OSError) as exc:
        print(f"BIND_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(f"BOUND_NOT_AUTHORIZED: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
