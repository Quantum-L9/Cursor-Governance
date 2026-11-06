#!/usr/bin/env python3
"""Open one integration PR for a retested exported candidate.

The Docker runner never calls this module. This module never updates a source
PR branch and never merges. First publication is ``make pr`` in the governance
checkout. A failed release stops here.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from integrate import HEX40, SafetyError, git  # noqa: E402


class PublishRefusal(SafetyError):
    """The candidate is not allowed to become a remote branch."""


def branch_name(numbers: list[int]) -> str:
    ordered = sorted({int(n) for n in numbers})
    if not ordered or any(n < 1 for n in ordered):
        raise PublishRefusal("integration branch needs at least one PR number")
    return "integration/l9-prs-" + "-".join(str(n) for n in ordered)


def head_descends_from(candidate: Path, manifest_sha: str) -> bool:
    """True when HEAD is the exported candidate or a commit that descends from it."""
    if not HEX40.fullmatch(manifest_sha):
        return False
    probe = git(
        ["merge-base", "--is-ancestor", manifest_sha, "HEAD"],
        cwd=candidate,
        check=False,
    )
    return probe.returncode == 0


def decide(
    *,
    head_sha: str,
    retest_sha: str,
    manifest_sha: str,
    descends_from_manifest: bool,
    branch: str,
    source_branches: set[str],
    remote_branches: set[str],
    worse: bool,
    dirty: bool,
) -> None:
    if not HEX40.fullmatch(manifest_sha):
        raise PublishRefusal("integration manifest has no candidate SHA")
    if not descends_from_manifest:
        raise PublishRefusal(
            "candidate HEAD does not descend from the integration manifest candidate"
        )
    if not HEX40.fullmatch(head_sha) or head_sha != retest_sha:
        raise PublishRefusal("candidate HEAD is not the retested SHA")
    if branch in source_branches:
        raise PublishRefusal("refusing to publish onto a source PR branch")
    if branch in remote_branches:
        raise PublishRefusal("remote already has the integration branch")
    if worse:
        raise PublishRefusal("retest is worse than baseline")
    if dirty:
        raise PublishRefusal("candidate is dirty or conflicted")


def remote_has_branch(url: str, branch: str) -> bool:
    probe = subprocess.run(
        ["git", "ls-remote", "--heads", url, f"refs/heads/{branch}"],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if probe.returncode != 0:
        raise PublishRefusal("could not read remote branches")
    return bool(probe.stdout.strip())


def prepare_local_branch(candidate: Path, branch: str, origin_url: str) -> None:
    """Point the export at the target repository and name the integration branch.

    Other local branches are left where they are.
    """
    existing = git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=candidate,
        check=False,
    )
    if existing.returncode == 0:
        raise PublishRefusal("local integration branch already exists")
    git(["switch", "-c", branch], cwd=candidate)
    origin = git(["remote"], cwd=candidate, check=False)
    names = origin.stdout.split()
    if "origin" in names:
        git(["remote", "set-url", "origin", origin_url], cwd=candidate)
    else:
        git(["remote", "add", "origin", origin_url], cwd=candidate)


def _load_json(path: Path) -> dict:
    body = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise PublishRefusal(f"{path.name} is not an object")
    return body


def assess_evidence(evidence: Path, candidate: Path, retest_dir: Path) -> dict:
    manifest = _load_json(evidence / "integration_manifest.json")
    retest = _load_json(retest_dir / "retest.json")
    repository = manifest.get("repository") or {}
    prs = manifest.get("prs") or []
    numbers = [int(pr["number"]) for pr in prs]
    source_branches = {str(pr.get("source_branch") or "") for pr in prs}
    source_branches.discard("")
    branch = branch_name(numbers)
    head = git(["rev-parse", "HEAD"], cwd=candidate).stdout.strip()
    dirty = git(["status", "--porcelain"], cwd=candidate, check=False)
    origin_url = str(repository.get("url") or "")
    if not origin_url:
        raise PublishRefusal("evidence has no repository url")
    manifest_sha = str(manifest.get("candidate_sha") or "")
    decide(
        head_sha=head,
        retest_sha=str(retest.get("candidate_sha") or ""),
        manifest_sha=manifest_sha,
        descends_from_manifest=head_descends_from(candidate, manifest_sha),
        branch=branch,
        source_branches=source_branches,
        remote_branches={branch} if remote_has_branch(origin_url, branch) else set(),
        worse=bool(retest.get("worse_than_baseline")),
        dirty=dirty.returncode != 0 or bool(dirty.stdout.strip()),
    )
    base_ref = str(repository.get("base_ref") or "")
    if not base_ref:
        raise PublishRefusal("evidence has no base ref")
    return {
        "branch": branch,
        "head_sha": head,
        "origin_url": origin_url,
        "base_ref": base_ref,
        "pr_numbers": numbers,
        "source_head_shas": {str(pr["number"]): pr.get("head_sha") for pr in prs},
    }


def open_via_make_pr(candidate: Path, base_ref: str) -> int:
    gov = Path(os.environ.get("L9_GOVERNANCE_DIR", Path.home() / ".cursor-governance"))
    py = gov / ".venv" / "bin" / "python"
    l4 = gov / "ops" / "autonomy" / "l4_local.py"
    env = os.environ.copy()
    env["PR_REMEDIATE"] = "0"
    env["PR_STACK"] = ""
    env["PR_BASE"] = base_ref if base_ref.startswith("origin/") else f"origin/{base_ref}"
    env["WS"] = str(candidate)
    for args in (
        [str(py), str(l4), "--workspace", str(candidate), "begin"],
        [str(py), str(l4), "--workspace", str(candidate), "authorize-release"],
    ):
        started = subprocess.run(args, cwd=candidate, env=env, check=False)
        if started.returncode != 0:
            return started.returncode
    released = subprocess.run(
        ["make", "-C", str(gov), "pr"],
        cwd=candidate,
        env=env,
        check=False,
    )
    return released.returncode


def write_receipt(evidence: Path, plan: dict, pr_url: str) -> Path:
    receipt = {
        "schema": "l9.integration.publication/v1",
        "branch": plan["branch"],
        "sha": plan["head_sha"],
        "pr_url": pr_url,
        "source_pr_numbers": plan["pr_numbers"],
        "source_head_shas": plan["source_head_shas"],
        "source_branches_updated": False,
    }
    path = evidence / "publication-receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--retest", required=True, type=Path)
    ap.add_argument(
        "--prepare-only",
        action="store_true",
        help="create the local branch and receipt stub, and do not run make pr",
    )
    args = ap.parse_args()
    try:
        plan = assess_evidence(args.evidence, args.candidate, args.retest)
        prepare_local_branch(args.candidate, plan["branch"], plan["origin_url"])
        pr_url = ""
        if not args.prepare_only:
            code = open_via_make_pr(args.candidate, plan["base_ref"])
            if code != 0:
                print("PUBLISH_BLOCKED: release command failed", file=sys.stderr)
                return code
        write_receipt(args.evidence, plan, pr_url)
    except (PublishRefusal, SafetyError, OSError, ValueError) as exc:
        print(f"PUBLISH_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(plan["branch"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
