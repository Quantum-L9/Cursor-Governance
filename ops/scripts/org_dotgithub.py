#!/usr/bin/env python3
"""Read a file from the organization's ``<owner>/.github`` repository at one exact commit.

This is the only module allowed to read ``<owner>/.github`` (enforced by
``tests/ops/scripts/test_org_dotgithub_single_reader.py``). Every caller gets the
same two transports in the same order:

1. REST (``gh api repos/<owner>/.github/...``): default branch -> commit -> contents.
2. git (``git ls-remote`` + a shallow fetch of that commit into a throwaway bare
   repository), when REST fails.

Both read the same bytes at the default branch's head commit, so the second is a
transport swap, not another source. It exists because some session gateways scope
the REST API to the session's own repositories (HTTP 403 for ``<owner>/.github``)
while still serving git for it. Both transports failing is an error: there is no
stale fallback here, and callers decide what an unreachable org file means.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
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


def git_read(owner: str, path: str) -> tuple[str, str]:
    """(commit, text) of ``path`` at the default-branch head, over git."""
    url = f"https://github.com/{owner}/.github"
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    def git(*args: str) -> str:
        try:
            proc = subprocess.run(
                ["git", *args], capture_output=True, text=True, check=False, timeout=60, env=env
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
            raise OrgFileError(msg) from git_error
        return OrgFile(sha=sha, text=text, transport="git")
