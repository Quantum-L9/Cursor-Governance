"""Park this session's authored bytes. Never porcelain. Never other sessions.

Records ledger paths from the payload workspace onto
refs/l9/preserved/session/<session_id> using an isolated git index. The
preserved commit's tree is the workspace HEAD tree with this session's
ledger paths applied on top: present paths carry their current bytes and
ledger paths that no longer exist on disk are removed from the tree, so a
deletion is preserved as a real deletion against a defined parent
(``git diff <ref>^ <ref>`` is exactly this session's authored delta).

Does not git add the real index, does not push, does not delete or restore
worktree files, and does not read porcelain. The delta against the parent
names only paths the ledger recorded.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from session_authored_ledger import (  # noqa: E402
    load_ledger,
    safe_session_id,
    session_id_from_event,
    workspace_from_event,
)

PRESERVE_NS = "refs/l9/preserved/session"
SCHEMA = "l9.session-end-preserve.v1"
DEFAULT_GIT_TIMEOUT_S = 60
_PARK_FAILURES = (
    "read-tree-failed",
    "update-index-failed",
    "add-failed",
    "write-tree-failed",
    "commit-tree-failed",
    "update-ref-failed",
)


def git_timeout_s() -> int:
    """Per-command git timeout; sessionEnd must never hang on a blocked git."""
    raw = os.environ.get("L9_SESSION_PRESERVE_GIT_TIMEOUT", "").strip()
    try:
        value = int(raw) if raw else DEFAULT_GIT_TIMEOUT_S
    except ValueError:
        value = DEFAULT_GIT_TIMEOUT_S
    return value if value > 0 else DEFAULT_GIT_TIMEOUT_S


def _git(
    root: Path,
    *args: str,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git under a timeout. A timeout is a non-zero result, never a hang."""
    merged = os.environ.copy()
    if env:
        merged.update(env)
    argv = ["git", "-C", str(root), *args]
    limit = git_timeout_s()
    try:
        return subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            text=True,
            check=False,
            env=merged,
            input=input_text,
            timeout=limit,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            argv,
            124,
            stdout="",
            stderr=f"git timed out after {limit}s: {' '.join(args[:3])}",
        )


def parse_payload(raw: str) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def skip_reason(event: dict[str, Any]) -> str:
    if os.environ.get("L9_SESSION_PRESERVE", "1") in {"0", "false", "no"}:
        return "L9_SESSION_PRESERVE=0"
    if os.environ.get("GOVERNANCE_BACKUP_SKIP", "0") == "1":
        return "GOVERNANCE_BACKUP_SKIP=1"
    if event.get("is_background_agent") is True or event.get("isBackgroundAgent") is True:
        return "background agent session"
    if not session_id_from_event(event):
        return "no session_id"
    workspace = workspace_from_event(event)
    if workspace is None:
        return "no payload workspace"
    git_dir = workspace / ".git"
    inside = _git(workspace, "rev-parse", "--is-inside-work-tree")
    if not git_dir.exists() and inside.returncode != 0:
        return "workspace_not_git"
    return ""


def _park_failed(commit: str) -> bool:
    return commit.startswith(_PARK_FAILURES)


def _safe_rel(rel: str) -> bool:
    if not rel or "\0" in rel or rel.startswith("/"):
        return False
    return ".." not in Path(rel).parts


def partition_ledger_rels(workspace: Path, rels: list[str]) -> tuple[list[str], list[str]]:
    """Split ledger paths into (present on disk, absent from disk)."""
    present: list[str] = []
    absent: list[str] = []
    for rel in rels:
        if not _safe_rel(rel):
            continue
        path = workspace / rel
        if path.is_file() or path.is_symlink():
            present.append(rel)
        elif not path.is_dir():
            absent.append(rel)
    return present, absent


def existing_ledger_rels(workspace: Path, rels: list[str]) -> list[str]:
    return partition_ledger_rels(workspace, rels)[0]


def _nul_joined(rels: list[str]) -> str:
    return "".join(f"{rel}\0" for rel in rels)


def ignored_rels(workspace: Path, rels: list[str]) -> set[str]:
    """Ledger paths git would refuse to add (ignored). Tracked paths never match."""
    if not rels:
        return set()
    proc = _git(workspace, "check-ignore", "-z", "--stdin", input_text=_nul_joined(rels))
    if proc.returncode not in (0, 1):
        return set()
    return {rel for rel in proc.stdout.split("\0") if rel}


def parent_commit(workspace: Path) -> str:
    """The defined parent for deletion semantics: the workspace HEAD commit."""
    proc = _git(workspace, "rev-parse", "-q", "--verify", "HEAD^{commit}")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def tombstone_rels(workspace: Path, parent: str, absent: list[str]) -> list[str]:
    """Absent ledger paths that exist in the parent tree — real deletions.

    A ledger path that was a directory in the parent (the ``Delete`` tool on a
    folder) expands to every blob beneath it, since the index holds blobs only.
    """
    if not parent:
        return []
    deleted: list[str] = []
    seen: set[str] = set()
    for rel in absent:
        kind = _git(workspace, "cat-file", "-t", f"{parent}:{rel}")
        if kind.returncode != 0:
            continue
        if kind.stdout.strip() == "tree":
            listing = _git(workspace, "ls-tree", "-r", "-z", "--name-only", f"{parent}:{rel}")
            if listing.returncode != 0:
                continue
            entries = [f"{rel}/{name}" for name in listing.stdout.split("\0") if name]
        else:
            entries = [rel]
        for entry in entries:
            if entry not in seen:
                seen.add(entry)
                deleted.append(entry)
    return deleted


def park(
    workspace: Path,
    session_id: str,
    present: list[str],
    deleted: list[str],
    parent: str,
) -> tuple[str, str]:
    """Return (ref, commit_sha or skip/fail token).

    Builds an isolated index from ``parent`` (empty when the repository is
    unborn), removes ``deleted`` entries, adds ``present`` bytes with literal
    NUL-delimited pathspecs, and commits the tree with ``parent`` as first
    parent (deletion semantics) and the previous preserve tip, if any, as
    second parent (rolling history). The real index and worktree are untouched.
    """
    ref = f"{PRESERVE_NS}/{safe_session_id(session_id)}"
    if not present and not deleted:
        return ref, "empty"
    with tempfile.TemporaryDirectory(prefix="l9-session-preserve-") as tmp:
        author = os.environ.get("GIT_AUTHOR_NAME", "l9-session-preserve")
        email = os.environ.get("GIT_AUTHOR_EMAIL", "l9-session-preserve@local")
        env = {
            "GIT_INDEX_FILE": str(Path(tmp) / "index"),
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": os.environ.get("GIT_COMMITTER_NAME", author),
            "GIT_COMMITTER_EMAIL": os.environ.get("GIT_COMMITTER_EMAIL", email),
        }
        seeded = _git(workspace, "read-tree", parent if parent else "--empty", env=env)
        if seeded.returncode != 0:
            return ref, f"read-tree-failed:{seeded.stderr.strip()[:160]}"
        if deleted:
            removed = _git(
                workspace,
                "update-index",
                "--force-remove",
                "-z",
                "--stdin",
                env=env,
                input_text=_nul_joined(deleted),
            )
            if removed.returncode != 0:
                return ref, f"update-index-failed:{removed.stderr.strip()[:160]}"
        if present:
            list_path = Path(tmp) / "paths.nul"
            list_path.write_bytes(_nul_joined(present).encode("utf-8"))
            added = _git(
                workspace,
                "--literal-pathspecs",
                "add",
                f"--pathspec-from-file={list_path}",
                "--pathspec-file-nul",
                env=env,
            )
            if added.returncode != 0:
                return ref, f"add-failed:{added.stderr.strip()[:160]}"
        tree = _git(workspace, "write-tree", env=env)
        if tree.returncode != 0 or not tree.stdout.strip():
            return ref, f"write-tree-failed:{tree.stderr.strip()[:160]}"
        tree_sha = tree.stdout.strip()
        if parent:
            parent_tree = _git(workspace, "rev-parse", "-q", "--verify", f"{parent}^{{tree}}")
            if parent_tree.returncode == 0 and parent_tree.stdout.strip() == tree_sha:
                return ref, "no_authored_delta"
        parents: list[str] = []
        if parent:
            parents += ["-p", parent]
        existing = _git(workspace, "rev-parse", "-q", "--verify", ref)
        previous = existing.stdout.strip() if existing.returncode == 0 else ""
        if previous and previous != parent:
            parents += ["-p", previous]
        msg = f"session-preserve {safe_session_id(session_id)}"
        commit = _git(workspace, "commit-tree", tree_sha, *parents, "-m", msg, env=env)
        if commit.returncode != 0 or not commit.stdout.strip():
            return ref, f"commit-tree-failed:{commit.stderr.strip()[:160]}"
        sha = commit.stdout.strip()
        upd = _git(workspace, "update-ref", ref, sha)
        if upd.returncode != 0:
            return ref, f"update-ref-failed:{upd.stderr.strip()[:160]}"
        return ref, sha


def run(
    event: dict[str, Any],
    *,
    ledger_home: Path | None = None,
) -> dict[str, Any]:
    skipped = skip_reason(event)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at": datetime.now(UTC).strftime("%Y%m%dT%H:%M:%SZ"),
        "skipped": skipped,
        "applied": False,
        "paths": [],
        "deleted": [],
        "ignored": [],
        "parent": "",
        "ref": "",
        "commit": "",
    }
    if skipped:
        return receipt
    session_id = session_id_from_event(event)
    workspace = workspace_from_event(event)
    assert workspace is not None
    receipt["session_id"] = session_id
    receipt["workspace"] = str(workspace)
    ledger = load_ledger(session_id, home=ledger_home)
    bound = str(ledger.get("workspace") or "")
    if not bound:
        receipt["skipped"] = "empty_ledger"
        return receipt
    if Path(bound).resolve() != workspace:
        receipt["skipped"] = "workspace_mismatch"
        return receipt
    present, absent = partition_ledger_rels(workspace, list(ledger.get("paths") or []))
    ignored = ignored_rels(workspace, present)
    present = [rel for rel in present if rel not in ignored]
    parent = parent_commit(workspace)
    deleted = tombstone_rels(workspace, parent, absent)
    receipt["paths"] = present
    receipt["deleted"] = deleted
    receipt["ignored"] = sorted(ignored)
    receipt["parent"] = parent
    if not present and not deleted:
        receipt["skipped"] = "ledger_paths_absent"
        return receipt
    ref, commit = park(workspace, session_id, present, deleted, parent)
    receipt["ref"] = ref
    receipt["commit"] = commit
    if _park_failed(commit) or commit == "no_authored_delta":
        receipt["skipped"] = commit
        return receipt
    receipt["applied"] = True
    receipt["skipped"] = ""
    dest = (
        (ledger_home if ledger_home is not None else Path.home() / ".cursor" / "l9" / "sessions")
        / safe_session_id(session_id)
        / "preserve.json"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt["receipt"] = str(dest)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Session-scoped sessionEnd preserve")
    parser.add_argument("--payload", default="", help="sessionEnd JSON (or read stdin)")
    parser.add_argument("--ledger-home", default="", help="override ledger root (tests)")
    args = parser.parse_args(argv)
    raw = args.payload
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    event = parse_payload(raw)
    home = Path(args.ledger_home).expanduser() if args.ledger_home else None
    receipt = run(event, ledger_home=home)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
