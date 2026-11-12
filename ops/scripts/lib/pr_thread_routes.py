"""REST review routes keyed on comment id, plus the own-PR gate.

Claude Code's permission list matches a command prefix, not a URL. The
allowlisted command is ``ops/scripts/pr_threads.py`` inside the governance
clone and ``~/.cursor-governance/ops/scripts/pr_threads.py`` from any other
checkout. These functions are the
only place that command, and the remediator batch script, build a review
write. Paths are the three author-review routes. Merge, approve, unresolve,
and GraphQL are not constructed here.

``ccr/review_threads`` emits no GraphQL node id, so resolve is addressed by
the REST comment id.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

GH_TIMEOUT_SEC = 30
SUMMARY_REL = Path(".l9/pr/pr-summary.json")
SUMMARY_SCHEMA = "l9.pr_summary.v1"
FOOTER_MARK = "_Posted by the PR author via ops/scripts/pr_threads.py._"
FOOTER = f"\n\n---\n{FOOTER_MARK}\n"

RunGh = Callable[..., str]


def fail(msg: str) -> NoReturn:
    print(f"FAIL: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def replies_path(repo: str, number: int, comment_id: int) -> str:
    return f"repos/{repo}/pulls/{number}/comments/{comment_id}/replies"


def resolve_path(repo: str, number: int, comment_id: int) -> str:
    return f"repos/{repo}/pulls/{number}/ccr/comments/{comment_id}/resolve"


def issue_comment_path(repo: str, number: int) -> str:
    return f"repos/{repo}/issues/{number}/comments"


def with_footer(body: str) -> str:
    text = body.strip()
    if not text:
        fail("review body is empty")
    if text.endswith(FOOTER_MARK):
        return text + "\n"
    return text + FOOTER


def run_gh(argv: list[str], *, input_text: str | None = None) -> str:
    try:
        proc = subprocess.run(  # noqa: S603
            argv,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        fail(f"gh timed out after {GH_TIMEOUT_SEC}s: {' '.join(argv[:6])}: {exc}")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[-800:]
        fail(f"gh exit {proc.returncode}: {' '.join(argv[:6])}: {err}")
    return proc.stdout


def post(path: str, payload: dict[str, Any] | None, *, run: RunGh) -> str:
    argv = ["gh", "api", "--method", "POST", path]
    if payload is None:
        return run(argv)
    return run([*argv, "--input", "-"], input_text=json.dumps(payload))


def reply(repo: str, number: int, comment_id: int, body: str, *, run: RunGh = run_gh) -> str:
    return post(
        replies_path(repo, number, comment_id),
        {"body": with_footer(body)},
        run=run,
    )


def resolve(repo: str, number: int, comment_id: int, *, run: RunGh = run_gh) -> str:
    raw = post(resolve_path(repo, number, comment_id), None, run=run)
    try:
        resolved = json.loads(raw).get("resolved")
    except json.JSONDecodeError:
        fail(f"comment {comment_id}: resolve returned non-JSON: {raw[:200]}")
    if resolved is not True:
        fail(f"comment {comment_id}: resolve returned resolved!=true: {raw[:200]}")
    return raw


def comment(repo: str, number: int, body: str, *, run: RunGh = run_gh) -> str:
    return post(issue_comment_path(repo, number), {"body": with_footer(body)}, run=run)


def parse_origin_repo(url: str | None) -> str | None:
    """``owner/name`` (lowercase) from an origin URL, or None."""
    if not url:
        return None
    text = url.strip()
    scheme = False
    for prefix in ("ssh://", "git://", "https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            scheme = True
            break
    if scheme:
        _authority, _, path = text.partition("/")
        text = path
    else:
        text = text.rsplit("@", 1)[-1]
        _host, sep, path = text.partition(":")
        text = path if sep else text
    if text.endswith(".git"):
        text = text[: -len(".git")]
    parts = [part for part in text.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    return f"{parts[-2]}/{parts[-1]}".lower()


def origin_repo(workspace: Path) -> str | None:
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "-C", str(workspace), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return parse_origin_repo(proc.stdout)


def load_summary(workspace: Path) -> dict[str, Any]:
    path = workspace / SUMMARY_REL
    if not path.is_file():
        fail(f"missing {SUMMARY_REL} — this checkout has not published a PR")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"unreadable {SUMMARY_REL}: {exc}")
    if not isinstance(data, dict) or data.get("schema") != SUMMARY_SCHEMA:
        fail(f"{SUMMARY_REL} schema is not {SUMMARY_SCHEMA}")
    return data


def git_out(workspace: Path, *args: str) -> str | None:
    """Stdout of a read-only git command in ``workspace``, or None on any failure."""
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "-C", str(workspace), *args],
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


def require_live_own_pr(
    workspace: Path, number: int, origin: str, *, run: RunGh = run_gh
) -> dict[str, Any]:
    """Ownership without a receipt: the open PR whose head is this checkout's branch.

    Used when no ``pr-summary.json`` exists, as on a native publish route whose
    own ``make pr`` writes none. Every fact is read, never assumed: the PR is
    open, its head repository is origin, its head ref is the checked-out
    branch, and its head commit is HEAD or an ancestor of HEAD (a local fix not
    yet pushed). Any unreadable fact refuses. Nothing is fetched to make the
    proof pass.
    """
    branch = git_out(workspace, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch or branch == "HEAD":
        fail(
            f"no {SUMMARY_REL} and no checked-out branch in {workspace} — "
            f"cannot prove PR #{number} is this checkout's"
        )
    raw = run(["gh", "api", "--method", "GET", f"repos/{origin}/pulls/{number}"])
    try:
        pr = json.loads(raw)
    except json.JSONDecodeError:
        fail(f"PR #{number}: GET returned non-JSON: {raw[:200]}")
    if not isinstance(pr, dict):
        fail(f"PR #{number}: GET returned no object")
    state = str(pr.get("state") or "").strip().lower()
    if state != "open":
        fail(f"PR #{number} is {state or 'unknown'}, not open")
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    head_repo = head.get("repo") if isinstance(head.get("repo"), dict) else {}
    head_full = str(head_repo.get("full_name") or "").strip().lower()
    if head_full != origin.strip().lower():
        fail(f"PR #{number} head repository {head_full or '<none>'} is not origin {origin}")
    head_ref = str(head.get("ref") or "").strip()
    if head_ref != branch:
        fail(
            f"PR #{number} head branch {head_ref or '<none>'} "
            f"is not the checked-out branch {branch}"
        )
    head_sha = str(head.get("sha") or "").strip()
    if not head_sha or git_out(workspace, "merge-base", "--is-ancestor", head_sha, "HEAD") is None:
        fail(
            f"PR #{number} head {head_sha[:12] or '<none>'} "
            f"is not HEAD or an ancestor of HEAD in {workspace}"
        )
    return {
        "repo": origin.strip().lower(),
        "number": number,
        "state": "open",
        "source": "live_head_branch",
    }


def require_own_pr(
    workspace: Path, number: int, origin: str, *, run: RunGh = run_gh
) -> dict[str, Any]:
    """The standing grant is the open PR this checkout published.

    The ``pr-summary.json`` receipt decides when it exists. Without one, the
    live head-branch proof in ``require_live_own_pr`` decides.
    """
    if not (workspace / SUMMARY_REL).is_file():
        return require_live_own_pr(workspace, number, origin, run=run)
    summary = load_summary(workspace)
    recorded = str(summary.get("repo") or "").strip().lower()
    if recorded != origin.strip().lower():
        fail(f"pr-summary repo {recorded or '<empty>'} does not match origin {origin}")
    try:
        recorded_number = int(summary.get("number"))
    except (TypeError, ValueError):
        fail("pr-summary number is missing")
    if recorded_number != number:
        fail(f"PR #{number} is not the published PR #{recorded_number}")
    state = str(summary.get("state") or "").strip().lower()
    if state != "open":
        fail(f"published PR #{recorded_number} is {state or 'unknown'}, not open")
    return summary
