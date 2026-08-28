#!/usr/bin/env python3
"""Belt-and-suspenders — apply GitHub branch protection so the merge CALL can't fire early.

REPO-AGNOSTIC. Ships with NO hardcoded repo. Missing repo/branch is never a blocker: owner/repo/branch,
the required status checks, and the review-agent CODEOWNER are all AUTO-DISCOVERED from the local git
context, `.github/workflows/*`, and `.github/CODEOWNERS`. Anything not discoverable degrades to a
WARNING (and a resolvable default), never an error. Dry-run always succeeds and prints a usable payload.

    python apply_branch_protection.py [--config c.yaml] [--owner O --repo R --branch B]
                                      [--checks "ci,lint"] [--apply]

Resolution order for each value: explicit flag > config file > auto-discovery > safe placeholder+warning.
Default config is the bundled branch_protection.example.yaml. `--apply` enacts live via REST when a token
(GITHUB_TOKEN/GH_TOKEN) is set AND a concrete owner/repo/branch was resolved; otherwise it stays dry-run.

Branch protection has no GitHub MCP tool (REST only). Native per-PR auto-merge IS an MCP tool:
mcp__github__enable_pr_auto_merge — call it from the orchestrator merge step once protection is in place.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

API = "https://api.github.com"
HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "branch_protection.example.yaml"


def warn(m):
    print(f"WARN: {m}", file=sys.stderr)


def load(p):
    p = pathlib.Path(p)
    if not p.exists():
        return {}
    text = p.read_text()
    if str(p).endswith((".yaml", ".yml")):
        try:
            import yaml

            return yaml.safe_load(text) or {}
        except Exception as e:
            warn(f"could not parse {p}: {e}")
            return {}
    return json.loads(text)


def _git(*a):
    try:
        r = subprocess.run(["git", *a], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def discover_repo():
    """owner, repo from `git remote get-url origin`; None if not in a git repo."""
    url = _git("remote", "get-url", "origin")
    if not url:
        return None, None
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    return (m.group(1), m.group(2)) if m else (None, None)


def discover_branch():
    return (
        _git("rev-parse", "--abbrev-ref", "HEAD") or _git("symbolic-ref", "--short", "HEAD") or None
    )


def discover_checks():
    """Best-effort required-status-check names from .github/workflows/* (job names)."""
    wf = pathlib.Path(".github/workflows")
    names = set()
    if not wf.is_dir():
        return []
    try:
        import yaml
    except Exception:
        return []
    for f in list(wf.glob("*.yml")) + list(wf.glob("*.yaml")):
        try:
            d = yaml.safe_load(f.read_text()) or {}
        except Exception:
            continue
        for jid, job in (d.get("jobs") or {}).items():
            names.add(job.get("name", jid) if isinstance(job, dict) else jid)
    return sorted(names)


def discover_codeowner():
    """A global (`*`) owner login from CODEOWNERS, if any."""
    for p in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        f = pathlib.Path(p)
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            line = line.strip()
            if line.startswith("*"):
                toks = line.split()
                if len(toks) >= 2:
                    return toks[1].lstrip("@")
    return None


def resolve(args, cfg):
    bp = cfg.get("branch_protection", {})
    owner, repo = discover_repo()
    owner = args.owner or cfg.get("owner") or owner
    repo = args.repo or cfg.get("repo") or repo
    branch = args.branch or cfg.get("branch") or discover_branch()

    concrete = bool(owner and repo and branch)
    if not owner:
        owner = "<owner>"
        warn(
            "owner not detected (not in a git repo?) — using placeholder; pass --owner or run inside the repo"
        )
    if not repo:
        repo = "<repo>"
        warn("repo not detected — using placeholder; pass --repo")
    if not branch:
        branch = "<branch>"
        warn("branch not detected — using placeholder; pass --branch")

    # checks: explicit flag > config (non-empty) > discovered
    rsc = bp.get("required_status_checks") or {}
    checks = (
        [c.strip() for c in args.checks.split(",")]
        if args.checks
        else list(rsc.get("contexts") or [])
    )
    if cfg.get("auto_discover_checks", True):
        disc = discover_checks()
        checks = sorted(set(checks) | set(disc))
    if not checks:
        warn(
            "no required status checks found in .github/workflows and none supplied — contexts will be empty "
            "(protection still enforces reviews + conversation resolution). Add workflows or pass --checks."
        )

    # review-agent CODEOWNER: config > discovery; absent -> disable code-owner requirement (degrade, don't block)
    agent = cfg.get("review_agent_owner")
    if not agent or str(agent).startswith("REPLACE"):
        agent = discover_codeowner()
    rpr = bp.get("required_pull_request_reviews") or {}
    require_code_owner = bool(rpr.get("require_code_owner_reviews", True)) and bool(agent)
    if not agent:
        warn(
            "no CODEOWNERS '*' owner found — require_code_owner_reviews disabled. "
            "Add .github/CODEOWNERS naming your review agent to require its approval (0 human approvals)."
        )

    return owner, repo, branch, concrete, checks, require_code_owner, agent, rpr, bp


def build_payload(checks, require_code_owner, rpr, bp):
    return {
        "required_status_checks": {
            "strict": bool((bp.get("required_status_checks") or {}).get("strict", True)),
            "contexts": checks,
        },
        "enforce_admins": bool(bp.get("enforce_admins", False)),
        "required_pull_request_reviews": {
            "required_approving_review_count": int(rpr.get("required_approving_review_count", 1)),
            "require_code_owner_reviews": require_code_owner,
            "dismiss_stale_reviews": bool(rpr.get("dismiss_stale_reviews", True)),
        },
        "required_conversation_resolution": bool(bp.get("required_conversation_resolution", True)),
        "restrictions": bp.get("restrictions", None),
        "allow_force_pushes": bool(bp.get("allow_force_pushes", False)),
        "allow_deletions": bool(bp.get("allow_deletions", False)),
    }


def token():
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def api_call(method, url, payload):
    import urllib.request

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req) as r:
        return r.status


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--owner")
    ap.add_argument("--repo")
    ap.add_argument("--branch")
    ap.add_argument("--checks")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv[1:])
    cfg = load(a.config)
    owner, repo, branch, concrete, checks, rco, agent, rpr, bp = resolve(a, cfg)
    prot = build_payload(checks, rco, rpr, bp)
    repo_patch = {
        "allow_auto_merge": bool((cfg.get("repository") or {}).get("allow_auto_merge", True))
    }

    print(f"# Target: {owner}/{repo}@{branch}   (auto-discovered where not supplied)")
    print(f"# review agent (CODEOWNER): {agent or 'none — code-owner requirement disabled'}")
    print(f"# required checks ({len(checks)}): {checks or '[] (none discovered)'}\n")
    print("## 1) Repo: enable native auto-merge")
    print(f"gh api --method PATCH repos/{owner}/{repo} -f allow_auto_merge=true\n")
    print("## 2) Branch protection")
    print(f"PUT {API}/repos/{owner}/{repo}/branches/{branch}/protection")
    print(json.dumps(prot, indent=2))
    print(
        f"\ngh api --method PUT repos/{owner}/{repo}/branches/{branch}/protection --input - <<'JSON'\n"
        f"{json.dumps(prot)}\nJSON\n"
    )

    if not a.apply:
        print(
            "## DRY-RUN — repo-agnostic payload emitted; nothing applied. Add --apply (+ token) to enact."
        )
        return 0
    if not concrete:
        warn(
            "--apply requested but owner/repo/branch not fully resolved — cannot apply to a placeholder. "
            "Run inside the target repo or pass --owner/--repo/--branch."
        )
        return 1
    if not token():
        warn("--apply requested but no GITHUB_TOKEN/GH_TOKEN in env — refusing to guess a token.")
        return 1
    try:
        s1 = api_call("PATCH", f"{API}/repos/{owner}/{repo}", repo_patch)
        print(f"repo PATCH -> {s1}")
        s2 = api_call("PUT", f"{API}/repos/{owner}/{repo}/branches/{branch}/protection", prot)
        print(f"protection PUT -> {s2}")
        return 0 if s1 < 300 and s2 < 300 else 1
    except Exception as e:
        warn(f"apply failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
