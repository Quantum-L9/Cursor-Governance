#!/usr/bin/env python3
"""Put every plans-store .plan.md on the binding shelf."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
AUDIT_SCRIPTS = SCRIPTS.parents[1] / "l9-pipeline-audit" / "scripts"
if str(AUDIT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(AUDIT_SCRIPTS))
from audit_plans import (  # noqa: E402
    STATUS_SUPERSEDED_RE,
    TEMPLATE_NAME,
    collect_newer_slugs,
    frontmatter_marks_built,
    parse_frontmatter,
    resolve_plans_dir,
    slug_key,
    todo_counts,
)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

STATUS_FOR_VERDICT = {
    "root": "current",
    "partially-built": "partially-built",
    "built": "built",
    "stale": "stale",
    "archive/superseded": "superseded",
}

LIVE_SHELVES = ("partially-built", "built", "stale", "archive", "archive/superseded")
RETIRED_FOLD = {
    "partial": "partially-built",
    "backlog": "stale",
    "pending": "stale",
}
COMPANION_SUFFIXES = (
    ".plan.json",
    ".activate.yaml",
    ".harvest.json",
    ".section-receipt.json",
)
README_QUEUE_RE = re.compile(r"(?m)^\d+\.\s+`([^`]+)`")
STAMP_RE = re.compile(r"_([0-9]{1,2})-([0-9]{1,2})-([0-9]{2,4})\.plan\.md$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _readme_queue(plans_dir: Path) -> set[str]:
    readme = plans_dir / "README.md"
    if not readme.is_file():
        return set()
    return set(README_QUEUE_RE.findall(readme.read_text(encoding="utf-8", errors="replace")))


def _this_week_stamps(today: date) -> set[str]:
    stamps: set[str] = set()
    start = today - timedelta(days=today.weekday())
    for offset in range(7):
        day = start + timedelta(days=offset)
        yy = day.strftime("%y")
        yyyy = day.strftime("%Y")
        stamps.add(f"{day.month}-{day.day}-{yy}")
        stamps.add(f"{day.month}-{day.day}-{yyyy}")
        stamps.add(f"{day.month:02d}-{day.day:02d}-{yy}")
    return stamps


def _filename_stamp(name: str) -> str | None:
    match = STAMP_RE.search(name)
    if not match:
        return None
    month, day, year = match.group(1), match.group(2), match.group(3)
    return f"{int(month)}-{int(day)}-{year}"


def _is_current(path: Path, fm: dict[str, Any], queue: set[str], week: set[str]) -> bool:
    stem = path.name[: -len(".plan.md")] if path.name.endswith(".plan.md") else path.stem
    if stem in queue or path.name.replace(".plan.md", "") in queue:
        return True
    if fm.get("compiled") is True:
        return True
    stamp = _filename_stamp(path.name)
    if stamp is None:
        return False
    month, day, year = stamp.split("-")
    compact = f"{month}-{day}-{year[-2:] if len(year) == 4 else year}"
    return compact in week or stamp in week


def _load_plan(path: Path) -> tuple[dict[str, Any], str] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return parse_frontmatter(text)


def _progress(path: Path) -> tuple[int, int]:
    loaded = _load_plan(path)
    if loaded is None:
        return (0, 0)
    pending, in_prog, total = todo_counts(loaded[0].get("todos"))
    done = max(0, total - pending - in_prog)
    return (done + in_prog, done)


def _dump_frontmatter(path: Path, fm: dict[str, Any], body: str) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML required to rewrite plan frontmatter")
    dumped = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{dumped}---\n{body}", encoding="utf-8")


def apply_status(path: Path, verdict: str) -> None:
    """Set folder/current status. Never write a parked status onto live root."""
    loaded = _load_plan(path)
    if loaded is None:
        return
    fm, body = loaded
    wanted = STATUS_FOR_VERDICT.get(verdict, "")
    if not wanted:
        return
    current = str(fm.get("status") or "").strip()
    if verdict == "root":
        if current == "current":
            return
        fm["status"] = "current"
        _dump_frontmatter(path, fm, body)
        return
    if current == wanted:
        return
    fm["status"] = wanted
    _dump_frontmatter(path, fm, body)


def shelf_dir(plans_dir: Path, verdict: str) -> Path:
    if verdict == "root":
        return plans_dir
    if verdict == "archive/superseded":
        return plans_dir / "archive" / "superseded"
    if verdict == "built":
        for name in ("built", "BUILT"):
            candidate = plans_dir / name
            if candidate.is_dir():
                return candidate
        return plans_dir / "built"
    return plans_dir / verdict


def slug_collision(dest_dir: Path, src: Path) -> Path:
    """Prefer an existing same-slug file over basename-only dest."""
    named = dest_dir / src.name
    key = slug_key(src)
    if dest_dir.is_dir() and key:
        for existing in dest_dir.glob("*.plan.md"):
            if existing == src:
                continue
            if slug_key(existing) == key:
                return existing
    return named


def _verdict(
    path: Path,
    fm: dict[str, Any],
    body: str,
    *,
    queue: set[str],
    week: set[str],
    superseded_names: set[str],
) -> str:
    if STATUS_SUPERSEDED_RE.search(body) or path.name in superseded_names:
        return "archive/superseded"
    todos = fm.get("todos")
    pending, in_prog, total = todo_counts(todos)
    done = total - pending - in_prog
    if frontmatter_marks_built(fm) or (total > 0 and pending == 0 and in_prog == 0):
        return "built"
    if in_prog or done:
        return "partially-built"
    if _is_current(path, fm, queue, week):
        return "root"
    return "stale"


def _companions(plans_dir: Path, plan: Path) -> list[Path]:
    stem = plan.name[: -len(".plan.md")]
    found: list[Path] = []
    for suffix in COMPANION_SUFFIXES:
        candidate = plan.with_name(stem + suffix)
        if candidate.is_file():
            found.append(candidate)
        root_copy = plans_dir / (stem + suffix)
        if root_copy.is_file() and root_copy not in found:
            found.append(root_copy)
    return found


def _tracked(workspace: Path, path: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(workspace), "ls-files", "--error-unmatch", "--", str(path)],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def _remove_src(src: Path, dest: Path, workspace: Path) -> None:
    if src.resolve() == dest.resolve():
        return
    if _tracked(workspace, src):
        subprocess.run(
            ["git", "-C", str(workspace), "rm", "-q", "--", str(src)],
            check=False,
            capture_output=True,
        )
    else:
        src.unlink(missing_ok=True)


def _place(src: Path, dest: Path, workspace: Path, actions: list[str]) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and src.resolve() != dest.resolve():
        if _sha(src) == _sha(dest):
            _remove_src(src, dest, workspace)
            actions.append(f"drop-ident {src.name}")
            return "dropped"
        dest_prog, dest_done = _progress(dest)
        src_prog, _src_done = _progress(src)
        dest_started = dest_prog > 0
        src_pending_only = src_prog == 0
        dest_wins = dest_started and (src_pending_only or dest_prog >= src_prog)
        if dest_wins:
            _remove_src(src, dest, workspace)
            actions.append(f"keep-started {dest.name}")
            return "kept"
        dest.write_bytes(src.read_bytes())
        if _tracked(workspace, dest):
            subprocess.run(
                ["git", "-C", str(workspace), "add", "--", str(dest)],
                check=False,
                capture_output=True,
            )
        _remove_src(src, dest, workspace)
        actions.append(f"overwrite-unique {src.name} → {dest.parent.name}/")
        return "moved"
    if _tracked(workspace, src):
        proc = subprocess.run(
            ["git", "-C", str(workspace), "mv", "--", str(src), str(dest)],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            shutil.move(str(src), str(dest))
    else:
        shutil.move(str(src), str(dest))
    actions.append(f"mv {src.name} → {dest.parent.name}/")
    return "moved"


def _rmdir_if_empty(path: Path) -> None:
    if not path.is_dir():
        return
    try:
        next(path.iterdir())
    except StopIteration:
        path.rmdir()


def _iter_plan_mds(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.plan.md") if p.is_file())


def fold_retired(plans_dir: Path, workspace: Path, actions: list[str]) -> dict[str, int]:
    counts = {name: 0 for name in RETIRED_FOLD}
    for retired, dest_name in RETIRED_FOLD.items():
        src_dir = plans_dir / retired
        if not src_dir.is_dir():
            continue
        dest_dir = plans_dir / dest_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(p for p in src_dir.iterdir() if p.is_file()):
            dest = (
                slug_collision(dest_dir, src)
                if src.name.endswith(".plan.md")
                else dest_dir / src.name
            )
            _place(src, dest, workspace, actions)
            counts[retired] += 1
        _rmdir_if_empty(src_dir)
        if src_dir.exists() and src_dir.is_dir() and not any(src_dir.iterdir()):
            shutil.rmtree(src_dir, ignore_errors=True)
        if src_dir.exists() and src_dir.is_dir() and not any(src_dir.rglob("*")):
            shutil.rmtree(src_dir, ignore_errors=True)
        if src_dir.is_dir() and not any(src_dir.iterdir()):
            src_dir.rmdir()
    return counts


def shelf(plans_dir: Path, workspace: Path, today: date) -> dict[str, Any]:
    actions: list[str] = []
    folded = fold_retired(plans_dir, workspace, actions)
    queue = _readme_queue(plans_dir)
    week = _this_week_stamps(today)
    candidates = [
        *_iter_plan_mds(plans_dir),
        *_iter_plan_mds(plans_dir / "stale"),
        *_iter_plan_mds(plans_dir / "partially-built"),
    ]
    superseded = collect_newer_slugs(candidates)
    counts = {
        "root": 0,
        "partially-built": 0,
        "built": 0,
        "stale": 0,
        "superseded": 0,
        "dropped": 0,
        "folded_partial": folded.get("partial", 0),
        "folded_backlog": folded.get("backlog", 0),
        "folded_pending": folded.get("pending", 0),
    }
    for path in candidates:
        if path.name == TEMPLATE_NAME:
            counts["root"] += 1
            continue
        loaded = _load_plan(path)
        if loaded is None:
            continue
        fm, body = loaded
        verdict = _verdict(
            path, fm, body, queue=queue, week=week, superseded_names=superseded
        )
        dest_dir = shelf_dir(plans_dir, verdict)
        if verdict == "root":
            counts["root"] += 1
        elif verdict == "archive/superseded":
            counts["superseded"] += 1
        else:
            counts[verdict] += 1
        dest = slug_collision(dest_dir, path)
        if path.resolve() == dest.resolve():
            apply_status(path, verdict)
            continue
        result = _place(path, dest, workspace, actions)
        if result == "dropped":
            counts["dropped"] += 1
            continue
        if dest.exists():
            apply_status(dest, verdict)
        for companion in _companions(plans_dir, path):
            _place(companion, dest_dir / companion.name, workspace, actions)
    for retired in RETIRED_FOLD:
        leftover = plans_dir / retired
        if leftover.is_dir() and not any(leftover.iterdir()):
            leftover.rmdir()
    root_now = sorted(p.name for p in _iter_plan_mds(plans_dir) if p.name != TEMPLATE_NAME)
    return {
        "plans_dir": str(plans_dir),
        "counts": counts,
        "actions": actions,
        "root_now": root_now,
        "retired_present": [name for name in RETIRED_FOLD if (plans_dir / name).exists()],
    }


def format_markdown(payload: dict[str, Any]) -> str:
    counts = payload.get("counts") or {}
    lines = [
        "- plans shelf: "
        f"root={counts.get('root', 0)} "
        f"partially-built={counts.get('partially-built', 0)} "
        f"built={counts.get('built', 0)} "
        f"stale={counts.get('stale', 0)} "
        f"superseded={counts.get('superseded', 0)} "
        f"dropped-dup={counts.get('dropped', 0)}",
        "- folded: "
        f"partial={counts.get('folded_partial', 0)} "
        f"backlog={counts.get('folded_backlog', 0)} "
        f"pending={counts.get('folded_pending', 0)}",
    ]
    retired = payload.get("retired_present") or []
    if retired:
        lines.append("- leftover retired dirs: " + ", ".join(retired))
    else:
        lines.append("- leftover retired dirs: none")
    root_now = payload.get("root_now") or []
    if not root_now:
        lines.append("- root now: `_TEMPLATE.plan.md` only")
    else:
        for name in root_now:
            lines.append(f"- root now: `{name}`")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--plans-dir", default=None)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--today", default=None, help="YYYY-MM-DD override for tests")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    plans_dir = resolve_plans_dir(workspace, args.plans_dir)
    if args.plans_dir:
        plans_dir = Path(args.plans_dir).expanduser().resolve()
    today = date.fromisoformat(args.today) if args.today else datetime.now().date()
    if not plans_dir.is_dir():
        print("plan shelf: no plans dir")
        return 0
    payload = shelf(plans_dir, workspace, today)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(format_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
