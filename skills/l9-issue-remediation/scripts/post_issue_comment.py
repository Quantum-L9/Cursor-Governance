#!/usr/bin/env python3
"""Post a canonical l9-issue-remediation unblock comment via GitHub API.

Stdlib-only, secret-safe. Token from GITHUB_TOKEN / GH_TOKEN (never printed).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_OPS_LIB = Path(__file__).resolve().parents[3] / "ops" / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))

from safe_https import https_exchange  # noqa: E402

_SECRETISH = re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[=:]\s*\S+")
_ISSUE_RE = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)$")
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./#: +\-]+$")
_REPO_SEGMENT = re.compile(r"^[A-Za-z0-9_.-]+$")
API_HOST = "api.github.com"
API_ORIGIN = f"https://{API_HOST}"
API_VERSION = "2022-11-28"


def _clean(text: str) -> str:
    text = _SECRETISH.sub(r"\1=[REDACTED]", text or "")
    return text.strip()


def _parse_issue(value: str) -> tuple[str, str, int]:
    match = _ISSUE_RE.match(value.strip())
    if not match:
        raise SystemExit("BLOCKED: --issue must be owner/repo#number")
    owner_repo = match.group(1)
    owner, _, repo = owner_repo.partition("/")
    if not owner or not repo:
        raise SystemExit("BLOCKED: --issue must be owner/repo#number")
    return owner, repo, int(match.group(2))


def _require_safe(label: str, value: str) -> str:
    cleaned = _clean(value)
    if not cleaned or not _SAFE_TOKEN.match(cleaned):
        raise SystemExit(f"BLOCKED: unsafe characters in {label}")
    return cleaned


def _comments_url(owner: str, repo: str, number: int) -> str:
    """Build a fail-closed GitHub comments URL (https://api.github.com only).

    Owner/repo are restricted to safe path segments and the final URL is re-parsed
    so urllib cannot be pointed at file:// or a non-GitHub host.
    """
    if not _REPO_SEGMENT.match(owner) or not _REPO_SEGMENT.match(repo):
        raise SystemExit("BLOCKED: owner/repo must be alphanumeric path segments")
    if number < 1:
        raise SystemExit("BLOCKED: issue number must be positive")
    path = (
        f"/repos/{urllib.parse.quote(owner, safe='')}/"
        f"{urllib.parse.quote(repo, safe='')}/issues/{number}/comments"
    )
    url = urllib.parse.urljoin(API_ORIGIN + "/", path.lstrip("/"))
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != API_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise SystemExit("BLOCKED: refusing non-https api.github.com comment URL")
    return url


def _post_comment(owner: str, repo: str, number: int, body: str, token: str) -> None:
    url = _comments_url(owner, repo, number)
    payload = json.dumps({"body": body}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", API_VERSION)
    request.add_header("User-Agent", "Quantum-L9-l9-issue-remediation")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Content-Type", "application/json")
    try:
        # URL is allow-listed to https://api.github.com by _comments_url.
        with https_exchange(
            request,
            timeout=45,
            allowed_hosts=frozenset({API_HOST}),
            label="GitHub comment URL",
        ) as response:
            if response.status not in (200, 201):
                raise SystemExit(f"BLOCKED: GitHub comment HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"BLOCKED: GitHub comment HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise SystemExit(f"BLOCKED: GitHub comment request failed: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, help="owner/repo#number")
    parser.add_argument("--cluster-id", required=True)
    parser.add_argument("--ownership", required=True)
    parser.add_argument("--owning-repo", required=True)
    parser.add_argument("--change", required=True, help="commit SHA, PR URL, or none note")
    parser.add_argument("--resume", required=True, help="next agent action one-liner")
    parser.add_argument("--remaining", default="none")
    parser.add_argument("--cycle", type=int, default=1)
    parser.add_argument("--status", choices=["fixed", "partial", "blocked"], default="partial")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    owner, repo, number = _parse_issue(args.issue)
    cluster_id = _require_safe("cluster-id", args.cluster_id)
    ownership = _require_safe("ownership", args.ownership)
    owning_repo = _require_safe("owning-repo", args.owning_repo)
    change = _require_safe("change", args.change)
    resume = _require_safe("resume", args.resume)
    remaining = _require_safe("remaining", args.remaining)

    marker = (
        f"<!-- l9-issue-remediation: cluster={cluster_id}; "
        f"cycle={args.cycle}; status={args.status} -->"
    )
    body = f"""## l9-issue-remediation unblock

**Cluster:** {cluster_id}
**Ownership:** {ownership}
**Owning repo:** {owning_repo}
**Change:** {change}
**Unblocked for resume:** {resume}
**Remaining:** {remaining}

{marker}
"""
    if args.dry_run:
        print(body)
        return 0

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("BLOCKED: GITHUB_TOKEN or GH_TOKEN required to post comments")

    _post_comment(owner, repo, number, body, token)
    print(json.dumps({"ok": True, "issue": f"{owner}/{repo}#{number}"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
