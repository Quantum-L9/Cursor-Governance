#!/usr/bin/env python3
"""Read a file from the organization's ``<owner>/.github`` repository at one exact commit.

This is the only module allowed to read ``<owner>/.github`` (enforced by
``SingleReaderTests`` in ``ops/scripts/tests/test_org_dotgithub.py``). Every caller
gets the same two transports in the same order:

1. REST (``gh api repos/<owner>/.github/...``): default branch -> commit -> contents.
2. git (``git ls-remote`` + a shallow fetch of that commit into a throwaway bare
   repository), when REST fails.

Both read the same bytes at the default branch's head commit, so the second is a
transport swap, not another source. It exists because some session gateways scope
the REST API to the session's own repositories (HTTP 403 for ``<owner>/.github``)
while still serving git for it. Both transports failing is an error: there is no
stale fallback here, and callers decide what an unreachable org file means.

``Quantum-L9/.github`` is private (2026-11-16), so neither transport is anonymous:
REST is ``gh``'s own credential, and git asks ``gh auth git-credential`` after any
helper the user already configured. On a Claude Code cloud session both reach the
repository only when it was selected when the session started; ``add_repo`` cannot
attach a dot-named repository later. The final error says so.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

SHA_RE = re.compile(r"[0-9a-f]{40}")


class OrgFileError(Exception):
    """The org file could not be read at an exact commit over any transport."""


@dataclass(frozen=True)
class OrgFile:
    sha: str
    text: str
    transport: str  # "rest" or "git"


GhApi = Callable[[str], Any]
GitRead = Callable[[str, str], tuple[str, str]]


def gh_api(endpoint: str) -> Any:
    try:
        proc = subprocess.run(
            ["gh", "api", endpoint], capture_output=True, text=True, check=False, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"gh api {endpoint} failed: {exc}"
        raise OrgFileError(msg) from exc
    if proc.returncode != 0:
        msg = f"gh api {endpoint} failed: {proc.stderr.strip() or proc.returncode}"
        raise OrgFileError(msg)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        msg = f"gh api {endpoint} returned non-JSON output"
        raise OrgFileError(msg) from exc


def rest_read(owner: str, path: str, gh: GhApi = gh_api) -> tuple[str, str]:
    """(commit, text) of ``path`` at the default-branch head, over REST."""
    repo = gh(f"repos/{owner}/.github")
    branch = repo.get("default_branch") if isinstance(repo, dict) else None
    if not branch:
        msg = f"{owner}/.github has no default branch in the API response"
        raise OrgFileError(msg)
    commit = gh(f"repos/{owner}/.github/commits/{branch}")
    sha = commit.get("sha", "") if isinstance(commit, dict) else ""
    if not SHA_RE.fullmatch(sha):
        msg = f"{owner}/.github@{branch} did not resolve to a commit"
        raise OrgFileError(msg)
    doc = gh(f"repos/{owner}/.github/contents/{path}?ref={sha}")
    is_file = isinstance(doc, dict) and doc.get("type") == "file"
    if not is_file or doc.get("encoding") != "base64":
        msg = f"{owner}/.github@{sha}:{path} is not a base64 file object"
        raise OrgFileError(msg)
    return sha, base64.b64decode(doc.get("content", "")).decode("utf-8")


#: Appended after any credential helper the user configured, never in place of one:
#: git asks each helper in turn, so a working keychain entry still wins.
GH_CREDENTIAL_HELPER = "!gh auth git-credential"

#: The gateway's refusal for a repository the cloud session was not started with.
SESSION_SCOPE_MARKER = "not enabled for this session"
SESSION_SCOPE_HINT = (
    "this Claude Code cloud session was not started with {owner}/.github; it is private, "
    "and add_repo cannot attach a dot-named repository mid-session: start a new session "
    "with {owner}/.github selected (docs/DEGRADED_MODE_CONTRACT.md, 2026-11-16)"
)


def git_credential_args(which: Callable[[str], str | None] = shutil.which) -> list[str]:
    """``-c`` options that let git authenticate with gh's credential, when gh exists."""
    if which("gh") is None:
        return []
    return ["-c", f"credential.helper={GH_CREDENTIAL_HELPER}"]


def git_read(owner: str, path: str) -> tuple[str, str]:
    """(commit, text) of ``path`` at the default-branch head, over authenticated git."""
    url = f"https://github.com/{owner}/.github"
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    auth = git_credential_args()

    def git(*args: str) -> str:
        try:
            proc = subprocess.run(
                ["git", *auth, *args],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            msg = f"git {args[0]} {url} failed: {exc}"
            raise OrgFileError(msg) from exc
        if proc.returncode != 0:
            msg = f"git {args[0]} {url} failed: {proc.stderr.strip() or proc.returncode}"
            raise OrgFileError(msg)
        return proc.stdout

    heads = [line.split("\t") for line in git("ls-remote", url, "HEAD").splitlines()]
    sha = next((row[0] for row in heads if len(row) == 2 and row[1] == "HEAD"), "")
    if not SHA_RE.fullmatch(sha):
        msg = f"{url} HEAD did not resolve to a commit over git"
        raise OrgFileError(msg)
    with tempfile.TemporaryDirectory() as tmp:
        git("init", "--bare", "-q", tmp)
        git("-C", tmp, "fetch", "-q", "--depth=1", url, sha)
        return sha, git("-C", tmp, "show", f"{sha}:{path}")


def read_org_file(owner: str, path: str, *, gh: GhApi = gh_api, git: GitRead = git_read) -> OrgFile:
    """``path`` from ``<owner>/.github`` at its default-branch head: REST, then git."""
    try:
        sha, text = rest_read(owner, path, gh)
        return OrgFile(sha=sha, text=text, transport="rest")
    except OrgFileError as rest_error:
        try:
            sha, text = git(owner, path)
        except OrgFileError as git_error:
            msg = f"{rest_error}; git transport also failed: {git_error}"
            if SESSION_SCOPE_MARKER in str(rest_error):
                msg = f"{msg}; {SESSION_SCOPE_HINT.format(owner=owner)}"
            raise OrgFileError(msg) from git_error
        return OrgFile(sha=sha, text=text, transport="git")


Runner = Callable[[list[str]], int]


#: Exit statuses the probe CLI shares with gh_auth_probe.sh's _gh_capability:
#: 0 OK, 1 DENIED (the call ran and was refused), 124 timed out and 127 could
#: not run are UNKNOWN, never a refusal GitHub did not make.
PROBE_OK, PROBE_DENIED, PROBE_TIMEOUT, PROBE_UNAVAILABLE = 0, 1, 124, 127


def _run(argv: list[str]) -> int:
    try:
        return subprocess.run(argv, capture_output=True, check=False, timeout=60).returncode
    except subprocess.TimeoutExpired:
        return PROBE_TIMEOUT
    except OSError:
        return PROBE_UNAVAILABLE


def rest_probe(owner: str, path: str, run: Runner = _run) -> int:
    """Exit status for whether the REST transport alone can read ``path``.

    A capability measurement, not a read: it never falls back to git, because its
    caller (``ops/scripts/lib/gh_auth_probe.sh`` ``org_template_read``) reports
    one verdict per transport (``docs/DEGRADED_MODE_CONTRACT.md``). Callers that
    need the file's contents use ``read_org_file``.
    """
    rc = run(["gh", "api", f"repos/{owner}/.github/contents/{path}"])
    if rc in (PROBE_OK, PROBE_TIMEOUT, PROBE_UNAVAILABLE):
        return rc
    return PROBE_DENIED


def main(argv: Sequence[str] | None = None) -> int:
    """``probe-rest OWNER PATH``: exit 0 OK, 1 refused, 124 timed out, 127 could not run."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3 or args[0] != "probe-rest":
        print("usage: org_dotgithub.py probe-rest OWNER PATH", file=sys.stderr)
        return 2
    return rest_probe(args[1], args[2])


if __name__ == "__main__":
    raise SystemExit(main())
