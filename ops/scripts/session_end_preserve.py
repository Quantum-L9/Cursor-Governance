"""Park this session's authored bytes. Never porcelain. Never other sessions.

Copies ledger paths from the payload workspace onto
refs/l9/preserved/session/<session_id> using an isolated git index.
Does not git add the real index, does not push, does not delete worktree files.
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


def _git(
    root: Path,
    *args: str,
    env: dict[str, str] | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=check,
        env=merged,
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
    return commit.startswith(
        ("add-failed", "write-tree-failed", "commit-tree-failed", "update-ref-failed")
    )


def existing_ledger_rels(workspace: Path, rels: list[str]) -> list[str]:
    kept: list[str] = []
    for rel in rels:
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            continue
        path = workspace / rel
        if path.is_file() or path.is_symlink():
            kept.append(rel)
    return kept


def park(
    workspace: Path,
    session_id: str,
    rels: list[str],
) -> tuple[str, str]:
    """Return (ref, commit_sha or skip/fail token)."""
    ref = f"{PRESERVE_NS}/{safe_session_id(session_id)}"
    if not rels:
        return ref, "empty"
    with tempfile.TemporaryDirectory(prefix="l9-session-preserve-") as tmp:
        index = Path(tmp) / "index"
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(index)
        env.setdefault("GIT_AUTHOR_NAME", "l9-session-preserve")
        env.setdefault("GIT_AUTHOR_EMAIL", "l9-session-preserve@local")
        env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
        env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
        list_path = Path(tmp) / "paths.txt"
        list_path.write_text("\n".join(rels) + "\n", encoding="utf-8")
        added = _git(
            workspace,
            "add",
            "--pathspec-from-file",
            str(list_path),
            env=env,
        )
        if added.returncode != 0:
            return ref, f"add-failed:{added.stderr.strip()[:160]}"
        tree = _git(workspace, "write-tree", env=env)
        if tree.returncode != 0 or not tree.stdout.strip():
            return ref, f"write-tree-failed:{tree.stderr.strip()[:160]}"
        tree_sha = tree.stdout.strip()
        existing = _git(workspace, "rev-parse", "-q", "--verify", ref)
        parents: list[str] = []
        if existing.returncode == 0 and existing.stdout.strip():
            parents = ["-p", existing.stdout.strip()]
        msg = f"session-preserve {safe_session_id(session_id)}"
        commit = _git(
            workspace,
            "commit-tree",
            tree_sha,
            *parents,
            "-m",
            msg,
            env=env,
        )
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
    rels = existing_ledger_rels(workspace, list(ledger.get("paths") or []))
    receipt["paths"] = rels
    if not rels:
        receipt["skipped"] = "ledger_paths_absent"
        return receipt
    ref, commit = park(workspace, session_id, rels)
    receipt["ref"] = ref
    receipt["commit"] = commit
    if _park_failed(commit):
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
