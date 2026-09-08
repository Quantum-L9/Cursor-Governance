#!/usr/bin/env python3
"""Fold or compile leftover plan todos. Never write AGENTS.md. Never harvest-write."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
AUDIT_SCRIPTS = SCRIPTS.parents[2] / "l9-pipeline-audit" / "scripts"
if str(AUDIT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(AUDIT_SCRIPTS))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_plans import TEMPLATE_NAME, slug_key  # noqa: E402
from shelf_plans import (  # noqa: E402
    _dump_frontmatter,
    _iter_plan_mds,
    _load_plan,
    apply_status,
)

CONCERN_PREFIXES: list[tuple[str, str]] = [
    ("ceremony", "ceremony_"),
    ("publish", "publish_"),
    ("remediator", "remediator_"),
    ("close_sgd", "close_sgd"),
    ("memory_outbox", "memory_outbox"),
    ("reasoning", "reasoning_"),
    ("ff", "ff_"),
    ("session_end", "session_end_"),
]
OTHER_REPO_PREFIXES = (
    "n8n_",
    "odoo_",
    "website_",
    "constellation_",
    "plastic_",
    "emma_",
    "seo_",
)
LIVE_QUEUE_NUM_RE = re.compile(r"^\d+\.\s+`[^`]+`")
LIVE_QUEUE_HEAD_RE = re.compile(r"^## Live queue")


def concern_for(path: Path, fm: dict[str, Any] | None = None) -> str:
    name = path.name
    for prefix in OTHER_REPO_PREFIXES:
        if name.startswith(prefix):
            return "other-repo"
    ranked = sorted(CONCERN_PREFIXES, key=lambda item: len(item[1]), reverse=True)
    for concern, prefix in ranked:
        if name.startswith(prefix):
            return concern
    return "uncategorized"


def leftover_todos(fm: dict[str, Any]) -> list[dict[str, Any]]:
    todos = fm.get("todos")
    if not isinstance(todos, list):
        return []
    leftover: list[dict[str, Any]] = []
    for item in todos:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "pending").lower()
        if status in {"pending", "in_progress"}:
            leftover.append(dict(item))
    return leftover


def _todo_content(item: dict[str, Any]) -> str:
    return str(item.get("content") or "").strip()


def _append_unique(dest_fm: dict[str, Any], incoming: list[dict[str, Any]]) -> int:
    todos = dest_fm.get("todos")
    if not isinstance(todos, list):
        todos = []
        dest_fm["todos"] = todos
    seen = {_todo_content(item) for item in todos if isinstance(item, dict)}
    ids = {str(item.get("id") or "") for item in todos if isinstance(item, dict)}
    added = 0
    for item in incoming:
        content = _todo_content(item)
        if not content or content in seen:
            continue
        new_id = str(item.get("id") or f"fold-{added + 1}")
        if new_id in ids:
            new_id = f"{new_id}-fold"
        row = dict(item)
        row["id"] = new_id
        todos.append(row)
        seen.add(content)
        ids.add(new_id)
        added += 1
    return added


def _stamp_harvested(path: Path, survivor: Path) -> None:
    loaded = _load_plan(path)
    if loaded is None:
        return
    fm, body = loaded
    if "status" not in fm or not str(fm.get("status") or "").strip():
        parent = path.parent.name
        if parent == "stale":
            fm["status"] = "stale"
        elif parent == "partially-built":
            fm["status"] = "partially-built"
        elif parent in {"built", "BUILT"}:
            fm["status"] = "built"
        elif parent == "superseded":
            fm["status"] = "superseded"
    fm["harvested"] = True
    fm["compiled_into"] = survivor.name
    _dump_frontmatter(path, fm, body)


def _write_plan(path: Path, fm: dict[str, Any], body: str) -> None:
    _dump_frontmatter(path, fm, body)


def _donor_dirs(plans_dir: Path) -> list[Path]:
    return [plans_dir / "stale", plans_dir / "built"]


def _beneficiaries(plans_dir: Path, concern: str) -> list[Path]:
    found: list[Path] = []
    for folder in (plans_dir, plans_dir / "partially-built"):
        for path in _iter_plan_mds(folder):
            if path.name == TEMPLATE_NAME:
                continue
            loaded = _load_plan(path)
            if loaded is None:
                continue
            fm, _body = loaded
            if fm.get("harvested") is True:
                continue
            if concern_for(path, fm) == concern:
                found.append(path)
    found.sort(key=lambda p: (0 if p.parent == plans_dir else 1, p.name))
    return found


def _same_slug_started(plans_dir: Path, donor: Path) -> Path | None:
    key = slug_key(donor)
    if not key:
        return None
    for path in _iter_plan_mds(plans_dir / "partially-built"):
        if slug_key(path) == key:
            return path
    return None


def _compile_path(plans_dir: Path, concern: str) -> Path:
    return plans_dir / f"compiled_{concern}.plan.md"


def rewrite_live_queue(plans_dir: Path, root_now: list[str]) -> bool:
    readme = plans_dir / "README.md"
    if not readme.is_file():
        return False
    names = [name[: -len(".plan.md")] if name.endswith(".plan.md") else name for name in root_now]
    lines = readme.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    in_queue = False
    replaced = False
    changed = False
    for line in lines:
        if LIVE_QUEUE_HEAD_RE.match(line):
            in_queue = True
            out.append(line)
            continue
        if in_queue and line.startswith("## ") and not LIVE_QUEUE_HEAD_RE.match(line):
            if not replaced:
                for idx, name in enumerate(names, start=1):
                    out.append(f"{idx}. `{name}`\n")
                replaced = True
                changed = True
            in_queue = False
            out.append(line)
            continue
        if in_queue and LIVE_QUEUE_NUM_RE.match(line):
            if not replaced:
                for idx, name in enumerate(names, start=1):
                    out.append(f"{idx}. `{name}`\n")
                replaced = True
                changed = True
            continue
        out.append(line)
    if in_queue and not replaced:
        for idx, name in enumerate(names, start=1):
            out.append(f"{idx}. `{name}`\n")
        changed = True
    if changed:
        readme.write_text("".join(out), encoding="utf-8")
    return changed


def refine(plans_dir: Path) -> dict[str, Any]:
    actions: list[str] = []
    compiled_concerns: set[str] = set()
    for folder in _donor_dirs(plans_dir):
        for donor in _iter_plan_mds(folder):
            loaded = _load_plan(donor)
            if loaded is None:
                continue
            fm, body = loaded
            if fm.get("harvested") is True:
                actions.append(f"omit {donor.name}")
                continue
            leftover = leftover_todos(fm)
            if not leftover:
                continue
            concern = concern_for(donor, fm)
            if concern == "other-repo":
                apply_status(donor, "stale")
                actions.append(f"other-repo {donor.name}")
                continue
            started = _same_slug_started(plans_dir, donor)
            if started is not None:
                dest_loaded = _load_plan(started)
                if dest_loaded is None:
                    continue
                dest_fm, dest_body = dest_loaded
                added = _append_unique(dest_fm, leftover)
                if added:
                    _write_plan(started, dest_fm, dest_body)
                actions.append(f"keep-started {donor.name} → {started.name} +{added}")
                continue
            if concern == "uncategorized":
                actions.append(f"uncategorized {donor.name}")
                continue
            beneficiaries = _beneficiaries(plans_dir, concern)
            beneficiaries = [path for path in beneficiaries if path.resolve() != donor.resolve()]
            if beneficiaries:
                survivor = beneficiaries[0]
                dest_loaded = _load_plan(survivor)
                if dest_loaded is None:
                    continue
                dest_fm, dest_body = dest_loaded
                added = _append_unique(dest_fm, leftover)
                if added:
                    _write_plan(survivor, dest_fm, dest_body)
                _stamp_harvested(donor, survivor)
                actions.append(f"fold {donor.name} → {survivor.name} +{added}")
                continue
            packet = _compile_path(plans_dir, concern)
            if packet.is_file() and concern in compiled_concerns:
                dest_loaded = _load_plan(packet)
                if dest_loaded is None:
                    continue
                dest_fm, dest_body = dest_loaded
                added = _append_unique(dest_fm, leftover)
                if added:
                    _write_plan(packet, dest_fm, dest_body)
                _stamp_harvested(donor, packet)
                actions.append(f"compile-append {donor.name} → {packet.name} +{added}")
                continue
            if packet.is_file():
                dest_loaded = _load_plan(packet)
                if dest_loaded is not None:
                    dest_fm, dest_body = dest_loaded
                    added = _append_unique(dest_fm, leftover)
                    if added:
                        _write_plan(packet, dest_fm, dest_body)
                    _stamp_harvested(donor, packet)
                    compiled_concerns.add(concern)
                    actions.append(f"fold {donor.name} → {packet.name} +{added}")
                    continue
            packet_fm: dict[str, Any] = {
                "name": f"Compiled {concern}",
                "overview": f"Compiled leftover todos for {concern}",
                "compiled": True,
                "status": "current",
                "todos": [],
                "isProject": False,
                "kind": "simple",
                "execute_via": "cursor-build",
            }
            added = _append_unique(packet_fm, leftover)
            _write_plan(
                packet,
                packet_fm,
                f"\n# PLAN: Compiled {concern}\n\nFolded leftover todos. Execute via /gmp.\n",
            )
            _stamp_harvested(donor, packet)
            compiled_concerns.add(concern)
            actions.append(f"compile {donor.name} → {packet.name} +{added}")
    root_now = sorted(p.name for p in _iter_plan_mds(plans_dir) if p.name != TEMPLATE_NAME)
    readme = rewrite_live_queue(plans_dir, root_now)
    return {"actions": actions, "root_now": root_now, "readme": readme}


def format_markdown(payload: dict[str, Any]) -> str:
    lines = [f"- refine actions: {len(payload.get('actions') or [])}"]
    for action in payload.get("actions") or []:
        lines.append(f"- {action}")
    if payload.get("readme"):
        lines.append("- README live-queue rewritten")
    root_now = payload.get("root_now") or []
    if not root_now:
        lines.append("- root now: `_TEMPLATE.plan.md` only")
    else:
        for name in root_now:
            lines.append(f"- root now: `{name}`")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plans-dir", required=True)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    plans_dir = Path(args.plans_dir).expanduser().resolve()
    if not plans_dir.is_dir():
        print("plan refine: no plans dir")
        return 0
    payload = refine(plans_dir)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(format_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
