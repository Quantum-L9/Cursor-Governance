#!/usr/bin/env python3
"""Audit Cursor .plan.md files for recent unbuilt / stale plans."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - stdlib fallback for thin envs
    yaml = None  # type: ignore[assignment]

TEMPLATE_NAME = "_TEMPLATE.plan.md"
SLUG_RE = re.compile(r"^(?P<slug>.+)_(?P<hex>[0-9a-fA-F]{8})\.plan\.md$")
EXECUTE_NEEDLE = "Execute via @environment/program-execution"
COMMIT_SHA_RE = re.compile(
    r"(?im)^\s*commit_sha\s*:\s*[`\"']?([0-9a-f]{7,40})[`\"']?\s*$"
)
STATUS_SUPERSEDED_RE = re.compile(r"(?im)^\s*status\s*:\s*superseded\s*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)


@dataclass
class PlanFinding:
    path: str
    name: str
    mtime: float
    age_days: float
    pending: int
    in_progress: int
    total_todos: int
    flags: list[str] = field(default_factory=list)


def resolve_plans_dir(workspace: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    ws_plans = workspace / ".cursor" / "plans"
    if ws_plans.exists():
        return ws_plans.resolve()
    return (Path.home() / ".cursor" / "plans").resolve()


def workspace_head(workspace: Path) -> str | None:
    """Resolve HEAD without spawning git (sessionStart must stay fast/fail-open)."""
    git_dir = workspace / ".git"
    try:
        if git_dir.is_file():
            # worktree / gitfile pointer: gitdir: <path>
            raw = git_dir.read_text(encoding="utf-8", errors="replace").strip()
            if raw.startswith("gitdir:"):
                git_dir = (workspace / raw.split(":", 1)[1].strip()).resolve()
            else:
                return None
        if not git_dir.is_dir():
            return None
        head_path = git_dir / "HEAD"
        head = head_path.read_text(encoding="utf-8", errors="replace").strip()
        if head.startswith("ref:"):
            ref = head.split(":", 1)[1].strip()
            ref_path = git_dir / ref
            if ref_path.is_file():
                return ref_path.read_text(encoding="utf-8", errors="replace").strip() or None
            # packed-refs fallback
            packed = git_dir / "packed-refs"
            if packed.is_file():
                for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("#") or " " not in line:
                        continue
                    sha, name = line.split(" ", 1)
                    if name.strip() == ref:
                        return sha.strip() or None
            return None
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", head):
            return head
    except OSError:
        return None
    return None


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end() :]
    data: dict[str, Any] = {}
    if yaml is not None:
        try:
            loaded = yaml.safe_load(raw)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
    return data, body


def is_unbuilt(todos: Any) -> bool:
    if not isinstance(todos, list) or len(todos) == 0:
        return True
    for item in todos:
        if not isinstance(item, dict):
            return True
        status = str(item.get("status", "pending")).lower()
        if status in {"pending", "in_progress"}:
            return True
    return False


def todo_counts(todos: Any) -> tuple[int, int, int]:
    if not isinstance(todos, list):
        return 0, 0, 0
    pending = in_progress = 0
    for item in todos:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "pending")).lower()
        if status == "pending":
            pending += 1
        elif status == "in_progress":
            in_progress += 1
    return pending, in_progress, len(todos)


def slug_key(path: Path) -> str | None:
    match = SLUG_RE.match(path.name)
    if not match:
        return None
    return match.group("slug")


def collect_newer_slugs(paths: list[Path]) -> set[str]:
    """Return slug keys that have a newer sibling hex suffix in the dir."""
    by_slug: dict[str, list[tuple[float, Path]]] = {}
    for path in paths:
        key = slug_key(path)
        if not key:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        by_slug.setdefault(key, []).append((mtime, path))
    superseded: set[str] = set()
    for key, entries in by_slug.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda t: t[0], reverse=True)
        # every entry except the newest is superseded by a newer slug file
        for _mtime, path in entries[1:]:
            superseded.add(path.name)
    return superseded


def extract_baseline_sha(body: str) -> str | None:
    if "immutable_baseline" not in body and "commit_sha" not in body:
        return None
    match = COMMIT_SHA_RE.search(body)
    if not match:
        return None
    return match.group(1).lower()


def sha_matches(plan_sha: str, head: str) -> bool:
    a, b = plan_sha.lower(), head.lower()
    n = min(len(a), len(b))
    if n < 7:
        return a == b
    return a[:n] == b[:n]


def flags_for(
    *,
    path: Path,
    todos: Any,
    body: str,
    head: str | None,
    superseded_names: set[str],
) -> list[str]:
    flags: list[str] = []
    if not isinstance(todos, list) or len(todos) == 0:
        flags.append("empty_todos")
    pending, in_prog, _total = todo_counts(todos)
    if in_prog:
        flags.append("in_progress")
    plan_sha = extract_baseline_sha(body)
    if plan_sha and head and not sha_matches(plan_sha, head):
        flags.append("baseline_drift")
    if STATUS_SUPERSEDED_RE.search(body) or path.name in superseded_names:
        flags.append("superseded")
    if EXECUTE_NEEDLE not in body:
        flags.append("missing_execute_section")
    # silence unused
    _ = pending
    return flags


def audit(
    *,
    plans_dir: Path,
    workspace: Path,
    window_days: float,
    limit: int,
    deadline: float,
) -> tuple[list[PlanFinding], dict[str, Any]]:
    meta: dict[str, Any] = {
        "plans_dir": str(plans_dir),
        "window_days": window_days,
        "scanned": 0,
        "unbuilt": 0,
        "status": "ok",
    }
    if not plans_dir.is_dir():
        meta["status"] = "no_plans_dir"
        return [], meta

    now = time.time()
    cutoff = now - (window_days * 86400.0)
    head = workspace_head(workspace)

    try:
        candidates = sorted(plans_dir.glob("*.plan.md"))
    except OSError:
        meta["status"] = "unreadable"
        return [], meta

    superseded_names = collect_newer_slugs(candidates)
    findings: list[PlanFinding] = []

    for path in candidates:
        if time.time() > deadline:
            meta["status"] = "deadline"
            break
        if path.name == TEMPLATE_NAME:
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        meta["scanned"] += 1
        if st.st_mtime < cutoff:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, body = parse_frontmatter(text)
        todos = fm.get("todos")
        if not is_unbuilt(todos):
            continue
        meta["unbuilt"] += 1
        pending, in_prog, total = todo_counts(todos)
        name = str(fm.get("name") or path.stem)
        finding = PlanFinding(
            path=str(path),
            name=name,
            mtime=st.st_mtime,
            age_days=round((now - st.st_mtime) / 86400.0, 2),
            pending=pending,
            in_progress=in_prog,
            total_todos=total,
            flags=flags_for(
                path=path,
                todos=todos,
                body=body,
                head=head,
                superseded_names=superseded_names,
            ),
        )
        findings.append(finding)

    findings.sort(key=lambda f: f.mtime, reverse=True)
    return findings[: max(0, limit)], meta


def format_markdown(findings: list[PlanFinding], meta: dict[str, Any], budget: int) -> str:
    status = meta.get("status", "ok")
    if status == "no_plans_dir":
        return "plan audit: no plans dir"
    if status == "unreadable":
        return "plan audit: unreadable plans dir"

    header = (
        f"- window: {meta.get('window_days')}d | scanned: {meta.get('scanned')} | "
        f"unbuilt: {meta.get('unbuilt')}"
    )
    if meta.get("status") == "deadline":
        header += " | truncated: deadline"
    lines = [header]
    if not findings:
        lines.append("- none: no unbuilt plans in window")
        text = "\n".join(lines)
        return text if len(text) <= budget else text[: max(0, budget - 1)] + "…"

    for finding in findings:
        flags = ",".join(finding.flags) if finding.flags else "unbuilt"
        label = "STALE" if finding.flags else "UNBUILT"
        line = (
            f"- {label}: {finding.name} — {flags}; "
            f"age={finding.age_days}d; todos "
            f"pending={finding.pending} in_progress={finding.in_progress}/"
            f"{finding.total_todos}; `{Path(finding.path).name}`"
        )
        candidate = "\n".join([*lines, line])
        if len(candidate) > budget:
            lines.append("- … truncated")
            break
        lines.append(line)
    text = "\n".join(lines)
    if len(text) > budget:
        return text[: max(0, budget - 1)] + "…"
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit recent unbuilt Cursor plans")
    parser.add_argument("--plans-dir", default=None)
    parser.add_argument("--workspace", default=os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--window-days", type=float, default=7.0)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--budget-chars", type=int, default=1200)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--deadline-seconds", type=float, default=2.0)
    args = parser.parse_args(argv)

    deadline = time.time() + max(0.1, float(args.deadline_seconds))
    workspace = Path(args.workspace).expanduser().resolve()
    plans_dir = resolve_plans_dir(workspace, args.plans_dir)

    try:
        findings, meta = audit(
            plans_dir=plans_dir,
            workspace=workspace,
            window_days=float(args.window_days),
            limit=int(args.limit),
            deadline=deadline,
        )
    except Exception as exc:  # fail-open for sessionStart
        print(f"plan audit: unavailable ({type(exc).__name__})")
        return 0

    if args.format == "json":
        payload = {
            "meta": meta,
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(format_markdown(findings, meta, int(args.budget_chars)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
