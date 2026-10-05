#!/usr/bin/env python3
"""Answer one question about GitHub: is there an OPEN pull request for a branch?

Two governance planes need the answer and neither may guess it:

* ``l4_local`` — a stale release receipt is still honoured for a push that
  advances an already-open PR (the remediation path).
* ``first_publication_gate`` — a raw ``git push`` is a *first publication*
  (denied outside ``make pr``) unless the branch already has an open PR.

The answer is tri-state. ``True`` / ``False`` are observations; ``None`` means
the probe could not observe (no ``gh``, no network, unresolvable remote), and
every caller treats ``None`` as "not shown to be open" — fail closed.

Transport (rule 62): REST first, because ``gh pr view --json`` is a GraphQL
call and the session gateway of a model-controlled surface refuses GraphQL
while ``gh api repos/...`` works. GraphQL stays as the fallback so the probe is
unchanged wherever it does work.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

#: Seconds allowed for one GitHub round-trip inside a PreToolUse hook.
PROBE_TIMEOUT_S = 15

_SSH_REMOTE = re.compile(r"^(?:ssh://)?git@[^:/]+[:/](?P<slug>[^/]+/[^/]+?)(?:\.git)?/?$")
_HTTP_REMOTE = re.compile(r"^https?://[^/]+/(?P<slug>[^/]+/[^/]+?)(?:\.git)?/?$")


def _git_out(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def repo_slug(root: Path, remote: str = "origin") -> str | None:
    """``owner/name`` of ``remote``, or None when it is not a GitHub-shaped URL."""
    url = _git_out(root, "remote", "get-url", remote)
    if not url:
        return None
    for pattern in (_SSH_REMOTE, _HTTP_REMOTE):
        match = pattern.match(url.strip())
        if match:
            slug = match.group("slug")
            return slug if slug.count("/") == 1 else None
    return None


def _gh(args: list[str], cwd: Path) -> str | None:
    if shutil.which("gh") is None:
        return None
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["gh", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _rest_open_pr(root: Path, slug: str, branch: str) -> bool | None:
    owner = slug.split("/", 1)[0]
    out = _gh(
        ["api", f"repos/{slug}/pulls?head={owner}:{branch}&state=open&per_page=1"],
        cwd=root,
    )
    if out is None:
        return None
    try:
        data = json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    return any(
        isinstance(item, dict) and str(item.get("state") or "").lower() == "open" for item in data
    )


def _graphql_open_pr(root: Path, branch: str) -> bool | None:
    out = _gh(["pr", "view", branch, "--json", "state", "-q", ".state"], cwd=root)
    if out is None:
        return None
    return out.strip().upper() == "OPEN"


def open_pr_for_branch(root: Path, branch: str, *, remote: str = "origin") -> bool | None:
    """True/False when GitHub answered; None when the state is undeterminable."""
    if not branch or branch == "HEAD":
        return None
    slug = repo_slug(root, remote)
    if slug is not None:
        answer = _rest_open_pr(root, slug, branch)
        if answer is not None:
            return answer
    return _graphql_open_pr(root, branch)


__all__ = ["PROBE_TIMEOUT_S", "open_pr_for_branch", "repo_slug"]
