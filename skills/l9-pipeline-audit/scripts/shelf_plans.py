#!/usr/bin/env python3
"""Shelf plans by todo state, including when frontmatter was never updated.

Dry-run is the default. ``--apply`` moves files. This is the /plan-audit
shelf. Do not draft a replacement script.

Root plans:
  all todos finished, or frontmatter built/completed/cancelled -> built/
  superseded -> archive/superseded
  some todos started -> partially-built/
  never started, not on the README live queue, not compiled, older than
  7 days -> stale/

README live-queue names, compiled packets, and never-started plans edited
in the last 7 days stay at the root. A todo-complete plan outside ``built/``
still moves to ``built/`` when it is not marked superseded. ``--apply``
writes ``status`` to match the destination and sets ``built: true`` on the
built shelf. An identical file already at the destination is a duplicate:
the source is removed and the destination keeps the status.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_pipeline import (  # noqa: E402
    _archive_lock_target,
    _built_shelf,
    _release_write_lock,
    _try_hold_write_lock,
    resolve_tracked_plans_dir,
)
from audit_plans import (  # noqa: E402
    STATUS_SUPERSEDED_RE,
    TEMPLATE_NAME,
    frontmatter_marks_built,
    is_unbuilt,
    parse_frontmatter,
    todo_counts,
)

RECENT_DAYS = 7
PLAN_SUFFIX = ".plan.md"
README_RE = re.compile(r"(?m)^\d+\.\s+`([^`]+)`")
STATUS_LINE = re.compile(r"(?m)^status:\s*.*$")
BUILT_LINE = re.compile(r"(?m)^built:\s*.*$")
COMPANION_SUFFIXES = (
    ".plan.json",
    ".harvest.json",
    ".activate.yaml",
    ".section-receipt.json",
    ".gar-run.json",
    ".gar-decision.json",
)
STATUS_FOR_DEST = {
    "built": "built",
    "partially-built": "partially-built",
    "stale": "stale",
    "archive/superseded": "superseded",
}


def readme_queue(plans_dir: Path) -> set[str]:
    readme = plans_dir / "README.md"
    if not readme.is_file():
        return set()
    return set(README_RE.findall(readme.read_text(encoding="utf-8", errors="replace")))


def shelf_dir(plans_dir: Path, name: str) -> Path:
    if name == "built":
        return _built_shelf(plans_dir)
    target = name.lower()
    try:
        for child in plans_dir.iterdir():
            if child.is_dir() and child.name.lower() == target:
                return child
    except OSError:
        pass
    return plans_dir / name


def _inside_built(path: Path, plans_dir: Path) -> bool:
    try:
        parts = path.resolve().relative_to(plans_dir.resolve()).parts[:-1]
    except ValueError:
        return False
    return any(part.lower() == "built" for part in parts)


def classify(path: Path, plans_dir: Path, queue: set[str], now: float) -> tuple[str | None, str]:
    """Return ``(destination folder, reason)``. Destination None keeps the file."""
    if path.name == TEMPLATE_NAME or _inside_built(path, plans_dir):
        return None, ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, ""
    fm, body = parse_frontmatter(text)
    todos = fm.get("todos")
    pending, in_progress, total = todo_counts(todos)
    status = str(fm.get("status", "")).strip().lower()
    superseded = status == "superseded" or bool(STATUS_SUPERSEDED_RE.search(body))
    at_root = path.parent.resolve() == plans_dir.resolve()
    stem = path.name[: -len(PLAN_SUFFIX)] if path.name.endswith(PLAN_SUFFIX) else path.stem
    if superseded:
        return ("archive/superseded", "superseded") if at_root else (None, "")
    if not is_unbuilt(todos, fm):
        reason = "frontmatter_built" if frontmatter_marks_built(fm) else "todos_terminal"
        return "built", reason
    if not at_root:
        return None, ""
    if total > pending + in_progress or in_progress:
        return "partially-built", "partial"
    if stem in queue or fm.get("compiled") is True:
        why = "compiled" if fm.get("compiled") is True else "live_queue"
        return None, why
    age_days = (now - path.stat().st_mtime) / 86400
    if age_days <= RECENT_DAYS:
        return None, "recent"
    return "stale", "stale"


def set_frontmatter(text: str, status: str, *, mark_built: bool) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    front = text[4:end]
    if STATUS_LINE.search(front):
        front = STATUS_LINE.sub(f"status: {status}", front, count=1)
    else:
        front = front.rstrip("\n") + f"\nstatus: {status}\n"
    if mark_built:
        if BUILT_LINE.search(front):
            front = BUILT_LINE.sub("built: true", front, count=1)
        else:
            front = front.rstrip("\n") + "\nbuilt: true\n"
    return "---\n" + front.rstrip("\n") + text[end:]


def _git(workspace: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def _tracked(workspace: Path, path: Path) -> bool:
    rel = path.resolve().relative_to(workspace.resolve())
    proc = _git(workspace, ["ls-files", "--error-unmatch", "--", rel.as_posix()])
    return proc.returncode == 0


def _rel(workspace: Path, path: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def plan_actions(plans_dir: Path, queue: set[str], now: float) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    try:
        candidates = sorted(plans_dir.rglob(f"*{PLAN_SUFFIX}"))
    except OSError:
        return actions
    for path in candidates:
        if not path.is_file():
            continue
        dest_name, reason = classify(path, plans_dir, queue, now)
        rel = path.name
        if dest_name is None:
            if path.parent.resolve() == plans_dir.resolve() and reason:
                actions.append({"action": "keep", "name": rel, "reason": reason})
            continue
        dest = shelf_dir(plans_dir, dest_name) / path.name
        if dest.exists():
            same = dest.is_file() and dest.read_bytes() == path.read_bytes()
            actions.append(
                {
                    "action": "drop" if same else "skip",
                    "name": rel,
                    "dest": dest_name,
                    "reason": "duplicate" if same else "differ",
                    "src": str(path),
                }
            )
            continue
        actions.append(
            {
                "action": "move",
                "name": rel,
                "dest": dest_name,
                "reason": reason,
                "src": str(path),
            }
        )
    return actions


def _stamp(path: Path, status: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    updated = set_frontmatter(text, status, mark_built=status == "built")
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def _move_file(workspace: Path, src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if _tracked(workspace, src):
        proc = _git(workspace, ["mv", "--", _rel(workspace, src), _rel(workspace, dest)])
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "git mv failed")
        return "git"
    shutil.move(str(src), str(dest))
    return "file"


def _remove_file(workspace: Path, path: Path) -> str:
    if _tracked(workspace, path):
        proc = _git(workspace, ["rm", "-f", "--", _rel(workspace, path)])
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.strip() or "git rm failed")
        return "git"
    path.unlink()
    return "file"


def _companions(path: Path) -> list[Path]:
    stem = path.name[: -len(PLAN_SUFFIX)]
    found: list[Path] = []
    for suffix in COMPANION_SUFFIXES:
        companion = path.parent / f"{stem}{suffix}"
        if companion.is_file():
            found.append(companion)
    return found


def _place_companions(workspace: Path, companions: list[Path], dest_dir: Path) -> None:
    for companion in companions:
        if not companion.is_file():
            continue
        target = dest_dir / companion.name
        if target.exists():
            if target.is_file() and target.read_bytes() == companion.read_bytes():
                _remove_file(workspace, companion)
            continue
        _move_file(workspace, companion, target)


def apply_actions(workspace: Path, plans_dir: Path, actions: list[dict[str, Any]]) -> list[Path]:
    staged: list[Path] = []
    for row in actions:
        if row["action"] not in {"move", "drop"}:
            continue
        src = Path(row["src"])
        dest_dir = shelf_dir(plans_dir, str(row["dest"]))
        dest = dest_dir / src.name
        status = STATUS_FOR_DEST[str(row["dest"])]
        companions = _companions(src)
        if row["action"] == "drop":
            if dest.is_file():
                _stamp(dest, status)
                if _tracked(workspace, dest):
                    staged.append(dest)
            if src.exists():
                _remove_file(workspace, src)
            _place_companions(workspace, companions, dest_dir)
            continue
        how = _move_file(workspace, src, dest)
        _stamp(dest, status)
        if how == "git":
            staged.append(dest)
        _place_companions(workspace, companions, dest_dir)
    if staged:
        add = subprocess.run(
            ["git", "add", "--pathspec-from-file=-"],
            cwd=workspace,
            input="".join(f"{_rel(workspace, path)}\n" for path in staged),
            capture_output=True,
            text=True,
            check=False,
        )
        if add.returncode != 0:
            raise SystemExit(add.stderr.strip() or "git add failed")
    return staged


def _counts(actions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"move": 0, "drop": 0, "skip": 0, "keep": 0}
    for row in actions:
        action = str(row["action"])
        if action in counts:
            counts[action] += 1
    return counts


def format_text(payload: dict[str, Any]) -> str:
    counts = payload["counts"]
    lines = [
        f"shelf: move={counts['move']} drop={counts['drop']} "
        f"skip={counts['skip']} keep={counts['keep']} apply={payload['apply']}"
    ]
    for row in payload["actions"]:
        action = row["action"]
        if action == "keep":
            lines.append(f"KEEP {row['reason']}: {row['name']}")
        elif action == "move":
            lines.append(f"MOVE {row['dest']} ({row['reason']}): {row['name']}")
        elif action == "drop":
            lines.append(f"DROP duplicate -> {row['dest']}: {row['name']}")
        else:
            lines.append(f"SKIP {row['reason']} -> {row['dest']}: {row['name']}")
    return "\n".join(lines)


def run(workspace: Path, plans_dir: Path, *, apply: bool) -> dict[str, Any]:
    now = time.time()
    queue = readme_queue(plans_dir)
    actions = plan_actions(plans_dir, queue, now)
    if apply:
        lock_target = _archive_lock_target(plans_dir, workspace, workspace)
        lock = _try_hold_write_lock(lock_target)
        if lock is None:
            return {
                "plans_dir": str(plans_dir),
                "apply": False,
                "locked": True,
                "counts": _counts(actions),
                "actions": actions,
            }
        try:
            apply_actions(workspace, plans_dir, actions)
        finally:
            _release_write_lock(lock)
    return {
        "plans_dir": str(plans_dir),
        "apply": apply,
        "locked": False,
        "counts": _counts(actions),
        "actions": actions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--gov-root", default=None)
    parser.add_argument("--plans-dir", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    if args.plans_dir:
        plans = Path(args.plans_dir).expanduser().resolve()
    else:
        plans = resolve_tracked_plans_dir(workspace)
    if not plans.is_dir():
        print(f"shelf: no plans dir at {plans}")
        return 1
    if os.environ.get("L9_REPO_WRITE_LOCK", "1").lower() in {"0", "false", "no"}:
        os.environ["L9_REPO_WRITE_LOCK"] = "0"
    payload = run(workspace, plans, apply=bool(args.apply))
    if payload.get("locked"):
        print("LOCK_HELD")
        return 2
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
