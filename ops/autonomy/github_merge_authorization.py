#!/usr/bin/env python3
"""Human merge authorization recorded on GitHub, bound to one head.

Ordinary authority for an agent-executed merge is a GitHub identity, not a
local file and not a controlling terminal (CANONICAL_LAW §6.2.13). Two records
count, and only when they name the pull request's current head:

* an ``APPROVED`` review by a human with write access whose ``commit_id`` is
  that head, or
* a review or issue comment by such a human whose body contains the exact line
  ``authorize merge <owner>/<repo>#<pr>@<40-hex>``.

L9-ORG-007 protected paths reject authorization from the pull request's author.
Bots, missing identity, and a head that moved after the record do not authorize.
This module does not merge and does not trust ``L9_MERGE_REVIEW_FILE``: that
file is a hook-test fixture read only by ``merge_gate.py``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

_LINE = re.compile(
    r"^authorize merge (?P<repo>[\w.-]+/[\w.-]+)#(?P<pr>[1-9]\d*)@(?P<sha>[0-9a-f]{40})\s*$",
    re.IGNORECASE,
)
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
WRITE_PERMISSIONS = frozenset({"admin", "maintain", "write"})
_BOT_LOGINS = frozenset(
    {
        "copilot-pull-request-reviewer",
        "chatgpt-codex-connector",
        "dependabot",
        "github-actions",
        "claude",
    }
)
_REVOKED = frozenset({"CHANGES_REQUESTED", "DISMISSED"})
_ORG_INVARIANTS = Path(__file__).resolve().parents[2] / "ORG_INVARIANTS.yaml"
_GH_TIMEOUT_SECONDS = 20


def authorization_line(repo: str, pr: str | int, head_sha: str) -> str:
    """The exact line a human posts on the pull request."""
    return f"authorize merge {repo}#{pr}@{head_sha.strip().lower()}"


def _login(user: Any) -> str:
    if not isinstance(user, dict):
        return ""
    return str(user.get("login") or "").strip()


def _is_human_identity(user: Any) -> bool:
    """A GitHub user who is not a bot. Association is not write permission."""
    login = _login(user)
    kind = str(user.get("type") or "") if isinstance(user, dict) else ""
    if kind != "User" or not login:
        return False
    folded = login.casefold()
    return not folded.endswith("[bot]") and folded not in _BOT_LOGINS


def record_permission(record: dict[str, Any]) -> str:
    """Repository permission on the record, or on its user. Empty when absent."""
    sources: list[Any] = [record]
    user = record.get("user")
    if isinstance(user, dict):
        sources.append(user)
    for source in sources:
        value = str(source.get("permission") or "").strip().lower()
        if value:
            return value
    return ""


def _write_capable(record: dict[str, Any]) -> bool:
    """True only for a repository role that can change the repository."""
    return record_permission(record) in WRITE_PERMISSIONS


@lru_cache(maxsize=1)
def protected_patterns() -> tuple[str, ...]:
    """L9-ORG-007 paths. Unreadable policy fails closed: every path is protected."""
    try:
        import yaml
    except ImportError:
        return ("**",)
    try:
        payload = yaml.safe_load(_ORG_INVARIANTS.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return ("**",)
    items = payload.get("invariants") if isinstance(payload, dict) else None
    for item in items or []:
        if isinstance(item, dict) and item.get("id") == "L9-ORG-007":
            paths = item.get("protected_paths") or []
            if isinstance(paths, list) and paths:
                return tuple(str(path) for path in paths)
            return ("**",)
    return ("**",)


def _path_is_protected(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    for pattern in patterns:
        token = pattern.replace("\\", "/").strip()
        if token in {"**", "**/*"}:
            return True
        if token.endswith("/**"):
            root = token[:-3].rstrip("/")
            if normalized == root or normalized.startswith(root + "/"):
                return True
        elif normalized == token:
            return True
    return False


def _requires_independent_authorizer(files: list[str] | None) -> bool:
    """True when the author must not be the authorizer, or when that is unknown."""
    if files is None:
        return True
    patterns = protected_patterns()
    return any(_path_is_protected(path, patterns) for path in files)


def _line_authorizes(body: str, repo: str, pr: str, head_sha: str) -> bool:
    wanted_repo = repo.casefold()
    wanted_pr = str(pr).strip()
    for raw in body.splitlines():
        match = _LINE.match(raw.strip())
        if not match:
            continue
        if match.group("repo").casefold() != wanted_repo:
            continue
        if match.group("pr") != wanted_pr:
            continue
        if match.group("sha").lower() == head_sha:
            return True
    return False


def evaluate_evidence(
    repo: str,
    pr: str | int,
    head_sha: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Decide whether ``evidence`` authorizes ``repo#pr`` at ``head_sha``.

    ``evidence`` keys: ``author`` (str), ``files`` (list or None), ``reviews``
    (list), ``comments`` (list). Each authorizing record carries ``permission``
    ``admin``, ``maintain`` or ``write``. ``author_association`` is not that
    permission. ``truncated`` fails closed when a list was not read in full.
    """
    sha = head_sha.strip().lower()
    number = str(pr).strip()
    denied: dict[str, Any] = {
        "authorized": False,
        "channel": None,
        "authorizer": None,
        "reason": "no human GitHub merge authorization for this repository, PR and head",
    }
    if not repo or not number.isdigit() or not _FULL_SHA.match(sha):
        denied["reason"] = "merge authorization requires a repository, PR number and full head SHA"
        return denied
    if not isinstance(evidence, dict):
        denied["reason"] = "GitHub merge authorization evidence was unreadable"
        return denied

    author = str(evidence.get("author") or "")
    files = evidence.get("files")
    file_list = [str(item) for item in files] if isinstance(files, list) else None
    independent = _requires_independent_authorizer(file_list)
    reviews = evidence.get("reviews") if isinstance(evidence.get("reviews"), list) else []
    comments = evidence.get("comments") if isinstance(evidence.get("comments"), list) else []
    stale_approval = False
    author_only = False

    latest: dict[str, dict[str, Any] | None] = {}
    ordered = sorted(reviews, key=lambda item: str((item or {}).get("submitted_at") or ""))
    for review in ordered:
        if not isinstance(review, dict):
            continue
        user = review.get("user")
        if not _is_human_identity(user) or not _write_capable(review):
            continue
        login = _login(user)
        state = str(review.get("state") or "")
        if state in _REVOKED:
            latest[login] = None
            continue
        if state != "APPROVED":
            continue
        commit = str(review.get("commit_id") or "").strip().lower()
        if commit == sha:
            latest[login] = review
        else:
            latest[login] = None
            if commit:
                stale_approval = True

    def _accept(login: str, channel: str) -> dict[str, Any] | None:
        nonlocal author_only
        if independent and author and login.casefold() == author.casefold():
            author_only = True
            return None
        return {
            "authorized": True,
            "channel": channel,
            "authorizer": login,
            "reason": f"human GitHub {channel} by {login} matches the live head",
        }

    for login, review in latest.items():
        if review is None:
            continue
        accepted = _accept(login, "approved_review")
        if accepted:
            return accepted

    def _consider_body(record: dict[str, Any], commit_id: str | None) -> dict[str, Any] | None:
        user = record.get("user")
        if not _is_human_identity(user) or not _write_capable(record):
            return None
        if commit_id is not None and commit_id.strip().lower() not in {"", sha}:
            return None
        if not _line_authorizes(str(record.get("body") or ""), repo, number, sha):
            return None
        return _accept(_login(user), "authorization_line")

    for review in reviews:
        if isinstance(review, dict):
            accepted = _consider_body(review, str(review.get("commit_id") or ""))
            if accepted:
                return accepted
    for comment in comments:
        if isinstance(comment, dict):
            accepted = _consider_body(comment, None)
            if accepted:
                return accepted

    if evidence.get("truncated"):
        denied["reason"] = (
            "GitHub authorization page was full and no matching human authorization was visible"
        )
    elif author_only:
        denied["reason"] = (
            "L9-ORG-007: the pull request author cannot authorize this governance-protected change"
        )
    elif stale_approval:
        denied["reason"] = "head changed after authorization"
    return denied


def evidence_from_mapping(payload: Any, repo: str, pr: str | int) -> dict[str, Any] | None:
    """One ``repo#pr`` entry from a review fixture, or None when it is absent."""
    if not isinstance(payload, dict):
        return None
    entry = payload.get(f"{repo}#{pr}")
    return entry if isinstance(entry, dict) else None


def load_review_fixture(path: Path, repo: str, pr: str | int) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return evidence_from_mapping(payload, repo, pr)


def parse_paginated_documents(raw: str) -> Any:
    """Decode one JSON document, or every document ``gh api --paginate`` emitted."""
    text = (raw or "").strip()
    if not text:
        return []
    decoder = json.JSONDecoder()
    values: list[Any] = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gh emitted non-JSON: {exc}") from exc
        values.append(value)
        index = end
    if not values:
        return []
    if len(values) == 1:
        return values[0]
    return values


def flatten_list_pages(payload: Any) -> list[Any]:
    """Flatten a list of pages. A list of records is already one complete page."""
    if not isinstance(payload, list):
        return []
    if payload and all(isinstance(item, list) for item in payload):
        flat: list[Any] = []
        for page in payload:
            flat.extend(page)
        return flat
    return payload


def _gh_capture(args: list[str]) -> str:
    if not _which_gh():
        raise RuntimeError("gh not on PATH")
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["gh", "api", *args],
            capture_output=True,
            text=True,
            timeout=_GH_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"gh failed: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or "gh returned non-zero").strip().splitlines()
        raise RuntimeError(detail[-1][:200] if detail else "gh returned non-zero")
    return proc.stdout or ""


def _gh_json(path: str) -> Any:
    return parse_paginated_documents(_gh_capture([path]))


def _gh_pages(path: str) -> list[Any]:
    """Every page of a list endpoint. ``--slurp`` wraps pages; raw pages still parse."""
    raw = _gh_capture(["--paginate", "--slurp", path])
    return flatten_list_pages(parse_paginated_documents(raw))


def _which_gh() -> bool:
    from shutil import which

    return which("gh") is not None


def _lookup_permission(repo: str, login: str) -> str:
    try:
        payload = _gh_json(f"repos/{repo}/collaborators/{login}/permission")
    except RuntimeError:
        return ""
    if isinstance(payload, dict):
        return str(payload.get("permission") or "").strip().lower()
    return ""


def _attach_permissions(repo: str, records: list[Any]) -> None:
    cache: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict) or record_permission(record):
            continue
        login = _login(record.get("user"))
        if not login or not _is_human_identity(record.get("user")):
            continue
        if login not in cache:
            cache[login] = _lookup_permission(repo, login)
        if cache[login]:
            record["permission"] = cache[login]


def fetch_evidence(repo: str, pr: str | int) -> dict[str, Any]:
    """Live pull request, reviews, comments and files. Raises RuntimeError."""
    number = str(pr).strip()
    view = _gh_json(f"repos/{repo}/pulls/{number}")
    if not isinstance(view, dict):
        raise RuntimeError("pull request payload was not an object")
    reviews = _gh_pages(f"repos/{repo}/pulls/{number}/reviews?per_page=100")
    comments = _gh_pages(f"repos/{repo}/issues/{number}/comments?per_page=100")
    files_payload = _gh_pages(f"repos/{repo}/pulls/{number}/files?per_page=100")
    _attach_permissions(repo, reviews)
    _attach_permissions(repo, comments)
    files = [
        str(item.get("filename"))
        for item in files_payload
        if isinstance(item, dict) and item.get("filename")
    ]
    return {
        "author": _login(view.get("user")),
        "files": files,
        "reviews": reviews,
        "comments": comments,
        "truncated": False,
    }


def authorize_for_merge(repo: str, pr: str | int, head_sha: str) -> dict[str, Any]:
    """Live GitHub verdict. An offline stack probe is not authorization.

    ``L9_STACK_PROBE_FILE`` keeps unit tests off the network and fails closed.
    This function does not read ``L9_MERGE_REVIEW_FILE``: a caller who controls
    this process must not be able to point authorization at a forged fixture.
    """
    if os.environ.get("L9_STACK_PROBE_FILE", "").strip():
        return {
            "authorized": False,
            "channel": None,
            "authorizer": None,
            "reason": "offline probe supplies no GitHub merge authorization",
        }
    try:
        evidence = fetch_evidence(repo, pr)
    except RuntimeError as exc:
        return {
            "authorized": False,
            "channel": None,
            "authorizer": None,
            "reason": f"cannot read GitHub merge authorization ({exc})",
        }
    return evaluate_evidence(repo, pr, head_sha, evidence)


def verdict_for_hook(repo: str, pr: str | int, head_sha: str) -> dict[str, Any]:
    """Hook-process verdict. The review fixture is the test double only.

    The hook's environment is not the tool command's environment. ``stack_safe_merge``
    does not call this function.
    """
    override = os.environ.get("L9_MERGE_REVIEW_FILE", "").strip()
    if override:
        evidence = load_review_fixture(Path(override), repo, pr)
        if evidence is None:
            return {
                "authorized": False,
                "channel": None,
                "authorizer": None,
                "reason": "review fixture has no entry for this repository and PR",
            }
        return evaluate_evidence(repo, pr, head_sha, evidence)
    return authorize_for_merge(repo, pr, head_sha)
