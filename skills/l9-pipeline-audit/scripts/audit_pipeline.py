#!/usr/bin/env python3
"""Classify plans, WIP, and PE campaigns with the same component verdicts."""

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

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PLAN_AUDIT = Path(__file__).resolve().parents[2] / "l9-plan-audit" / "scripts"
if str(PLAN_AUDIT) not in sys.path:
    sys.path.insert(0, str(PLAN_AUDIT))
from audit_plans import (  # noqa: E402
    STATUS_SUPERSEDED_RE,
    TEMPLATE_NAME,
    audit,
    is_unbuilt,
    parse_frontmatter,
    resolve_plans_dir,
)

SPENT_CAMPAIGN = frozenset({"complete", "completed", "cancelled", "spent", "converged"})
STALE_WIP = frozenset({"possible-landed", "landed", "pruned"})
README_QUEUE_RE = re.compile(r"(?m)^\d+\.\s+`([^`]+)`")
LIVE_QUEUE = (
    "pe_loop_compiled_8-28-26",
    "memory_outbox_drain_7c4a1e93",
    "worktree_parent_clone_8-20-26",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None or not path.is_file():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def resolve_gov_root(workspace: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    home_gov = Path.home() / ".cursor-governance"
    if (workspace / "docs" / "plans").is_dir() and (workspace / "WIP").is_dir():
        return workspace
    if home_gov.is_dir():
        return home_gov
    return workspace


def resolve_tracked_plans_dir(workspace: Path) -> Path:
    """Prefer .cursor/plans → docs/plans (tracked), then ~/.cursor/plans."""
    ws_link = workspace / ".cursor" / "plans"
    if ws_link.exists():
        return ws_link.resolve()
    ws_docs = workspace / "docs" / "plans"
    if ws_docs.is_dir():
        return ws_docs.resolve()
    return resolve_plans_dir(workspace, None)


def _archive_lock_target(plans_dir: Path, wip_root: Path, workspace: Path, gov_root: Path) -> Path:
    """Lock the clone that archive will write, preferring $GC when falling back."""
    gov = gov_root.resolve()
    for path in (plans_dir, wip_root):
        try:
            path.resolve().relative_to(gov)
            return gov
        except ValueError:
            continue
    return workspace.resolve()


def _repo_write_lock_dir(ws: Path) -> Path:
    proc = subprocess.run(
        ["cksum"],
        input=str(ws).encode(),
        capture_output=True,
        check=False,
    )
    ident = proc.stdout.decode().split()[0] if proc.returncode == 0 else "0"
    return Path.home() / ".cursor" / f"l9-repo-write.{ident}.lock.d"


def _try_hold_write_lock(ws: Path) -> Path | None:
    """Acquire the same lock path make pr uses. None means another writer holds it."""
    if os.environ.get("L9_REPO_WRITE_LOCK", "1").lower() in {"0", "false", "no"}:
        return Path()
    lock_dir = _repo_write_lock_dir(ws)
    try:
        lock_dir.mkdir(parents=True)
    except FileExistsError:
        return None
    try:
        (lock_dir / "owner").write_text(
            f"{os.getpid()} {int(time.time())} {ws} audit_pipeline\n",
            encoding="utf-8",
        )
    except OSError:
        shutil.rmtree(lock_dir, ignore_errors=True)
        return None
    os.environ["L9_REPO_WRITE_LOCK_OWNER"] = str(os.getpid())
    return lock_dir


def _release_write_lock(lock_dir: Path | None) -> None:
    if lock_dir is None or str(lock_dir) in {"", "."}:
        return
    if lock_dir.is_dir():
        shutil.rmtree(lock_dir, ignore_errors=True)


def _tracked_store(plans_dir: Path, workspace: Path, gov_root: Path) -> bool:
    """Refuse archive unless the resolved store is workspace or SSOT docs/plans."""
    resolved = plans_dir.resolve()
    allowed = (
        (workspace / "docs" / "plans").resolve(),
        (gov_root / "docs" / "plans").resolve(),
    )
    return any(resolved == item for item in allowed)


def scan_plans(plans_dir: Path, workspace: Path, window_days: float) -> list[dict[str, Any]]:
    if not plans_dir.is_dir():
        return []
    findings, _meta = audit(
        plans_dir=plans_dir,
        workspace=workspace,
        window_days=window_days,
        limit=50,
        deadline=time.time() + 1.2,
    )
    rows: list[dict[str, Any]] = []
    for finding in findings:
        flags = list(finding.flags)
        rows.append(
            {
                "surface": "plans",
                "path": finding.path,
                "name": finding.name,
                "flags": flags,
                "harvestable": "harvestable" in flags,
                "pending": True,
                "compiled": "compiled" in flags or False,
            }
        )
    return rows


def scan_wip(wip_root: Path) -> list[dict[str, Any]]:
    inventory = _load_yaml(wip_root / "INVENTORY.yaml")
    entries = inventory.get("entries") or []
    rows: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path") or "")
        if not rel.startswith("WIP/") or "Legal Defense" in rel:
            continue
        status = str(item.get("status") or "active").lower()
        stale = status in STALE_WIP
        harvestable = status == "possible-landed"
        pending = status == "active"
        flags: list[str] = []
        if pending or harvestable:
            flags.append("live_invariant")
        if stale:
            flags.append("stale_wiring")
        if harvestable:
            flags.append("harvestable")
        rows.append(
            {
                "surface": "wip",
                "path": str(wip_root.parent / rel)
                if wip_root.name == "WIP"
                else str(wip_root / Path(rel).name),
                "name": Path(rel).name,
                "rel": rel,
                "flags": flags,
                "harvestable": harvestable,
                "pending": pending,
                "status": status,
            }
        )
    return rows


def scan_campaigns(campaigns_root: Path) -> list[dict[str, Any]]:
    if not campaigns_root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for source in sorted(campaigns_root.glob("*/CAMPAIGN_SOURCE.yaml")):
        if "environment/program-execution/environment" in source.as_posix():
            continue
        data = _load_yaml(source)
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        name = str(meta.get("campaign_id") or source.parent.name)
        status = str(meta.get("status") or "").lower()
        plan_status = str(data.get("plan_status") or "").lower()
        lifecycle = str(meta.get("lifecycle") or "").lower()
        spent = any(token in SPENT_CAMPAIGN for token in (status, plan_status, lifecycle))
        objective = ""
        directive = data.get("operator_directive")
        if isinstance(directive, dict):
            objective = str(directive.get("objective") or "")
        leftover = bool(objective)
        harvestable = spent and leftover
        pending = not spent
        flags: list[str] = []
        if leftover or not spent:
            flags.append("live_invariant")
        if spent:
            flags.append("superseded_mission")
        if harvestable:
            flags.append("harvestable")
        rows.append(
            {
                "surface": "campaigns",
                "path": str(source),
                "name": name,
                "flags": flags,
                "harvestable": harvestable,
                "pending": pending,
                "status": status or plan_status or lifecycle,
            }
        )
    return rows


def _readme_queue(plans_dir: Path) -> list[str]:
    readme = plans_dir / "README.md"
    if not readme.is_file():
        return list(LIVE_QUEUE)
    names = README_QUEUE_RE.findall(readme.read_text(encoding="utf-8", errors="replace"))
    return names or list(LIVE_QUEUE)


def _is_compiled_plan(path: str) -> bool:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    fm, _body = parse_frontmatter(text)
    return fm.get("compiled") is True


def rank_next(findings: list[dict[str, Any]], plans_dir: Path) -> list[dict[str, Any]]:
    """First-order execute order: compiled, README live queue, campaigns. Not WIP spam."""
    queue = _readme_queue(plans_dir)
    by_key: dict[str, dict[str, Any]] = {}
    for row in findings:
        if not row.get("pending") and not row.get("harvestable"):
            continue
        if row["surface"] == "wip":
            continue
        path_name = Path(str(row.get("path") or "")).name
        stem = path_name[: -len(".plan.md")] if path_name.endswith(".plan.md") else path_name
        for key in (str(row.get("name") or ""), stem):
            if key:
                by_key.setdefault(key, row)
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _take(row: dict[str, Any]) -> None:
        key = str(row.get("name") or "")
        if not key or key in seen:
            return
        seen.add(key)
        item = dict(row)
        if row["surface"] == "plans" and _is_compiled_plan(str(row.get("path"))):
            item["execute"] = "/gmp"
        elif row["surface"] == "campaigns":
            item["execute"] = "/gmp"
        else:
            item["execute"] = "Build or /gmp"
        ranked.append(item)

    for row in findings:
        if row["surface"] == "plans" and _is_compiled_plan(str(row.get("path"))):
            _take(row)
    for name in queue:
        row = by_key.get(name)
        if row is None:
            candidate = plans_dir / f"{name}.plan.md"
            if candidate.is_file():
                try:
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    text = ""
                if text:
                    fm, _body = parse_frontmatter(text)
                    if is_unbuilt(fm.get("todos"), fm):
                        row = {
                            "surface": "plans",
                            "path": str(candidate),
                            "name": str(fm.get("name") or name),
                            "pending": True,
                            "harvestable": False,
                        }
        if row:
            _take(row)
    for row in findings:
        if row["surface"] == "campaigns" and row.get("pending"):
            _take(row)
    for row in findings:
        if row["surface"] == "plans" and row.get("pending"):
            _take(row)
    return ranked[:3]


def archive_landed_wip(wip_root: Path, rows: list[dict[str, Any]], cap: int = 8) -> list[str]:
    """Move inventory-landed WIP only. possible-landed stays for harvest."""
    moved: list[str] = []
    if not wip_root.is_dir():
        return moved
    dest_root = wip_root / "_archived"
    for row in rows:
        if len(moved) >= cap:
            break
        if row.get("surface") != "wip" or str(row.get("status") or "") != "landed":
            continue
        rel = str(row.get("rel") or "")
        if not rel.startswith("WIP/") or "Legal Defense" in rel:
            continue
        src = wip_root.parent / rel
        if not src.is_file():
            continue
        dest = dest_root / Path(rel).relative_to("WIP")
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dest))
            moved.append(f"{src.name} → WIP/_archived/")
        except OSError:
            continue
    return moved


def _built_shelf(plans_dir: Path) -> Path:
    """The shelf for built plans, matching the directory that already exists.

    The canonical tracked shelf is `BUILT/`. This resolved a hard-coded
    lowercase `built`, which is the SAME directory on the case-insensitive
    filesystem this repository is usually developed on and a DIFFERENT one on
    Linux — where the cloud containers run. There it created a stray untracked
    `built/` beside the tracked `BUILT/` and moved committed plan files into
    it, silently un-tracking them: `git status` then showed the originals
    deleted and untracked copies appearing, and the plan gate failed on
    shelved plans that carry no kernel receipt.

    The tracked `BUILT/` wins whenever it exists, so both platforms converge on
    the one shelf that is under version control. A differently-cased directory
    is honoured only where `BUILT/` is absent, which keeps a repository that
    genuinely uses the lowercase spelling working; `BUILT` is created when
    neither exists.
    """
    canonical = plans_dir / "BUILT"
    if canonical.is_dir():
        return canonical
    try:
        for child in plans_dir.iterdir():
            if child.is_dir() and child.name.lower() == "built":
                return child
    except OSError:
        # Directory scan is best-effort. Fall back to canonical BUILT when
        # iterdir cannot run (unreadable parent, vanished path).
        pass
    return canonical


def archive_spent_plans(plans_dir: Path, cap: int = 8) -> list[str]:
    """Move spent root plans. Do not touch harvestable mixed donors."""
    moved: list[str] = []
    if not plans_dir.is_dir():
        return moved
    built = _built_shelf(plans_dir)
    superseded_dir = plans_dir / "archive" / "superseded"
    for path in sorted(plans_dir.glob("*.plan.md")):
        if len(moved) >= cap or path.name == TEMPLATE_NAME:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, body = parse_frontmatter(text)
        if is_unbuilt(fm.get("todos"), fm):
            continue
        dest_dir = superseded_dir if STATUS_SUPERSEDED_RE.search(body) else built
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        if dest.exists():
            continue
        stem = path.name[: -len(".plan.md")]
        companions = [
            path,
            plans_dir / f"{stem}.plan.json",
            plans_dir / f"{stem}.harvest.json",
            plans_dir / f"{stem}.activate.yaml",
        ]
        for src in companions:
            if not src.is_file():
                continue
            target = dest_dir / src.name
            if target.exists():
                continue
            try:
                shutil.move(str(src), str(target))
                moved.append(f"{src.name} → {dest_dir.name}/")
            except OSError:
                continue
    return moved


def run(
    *,
    workspace: Path,
    gov_root: Path,
    window_days: float,
    archive: bool,
) -> dict[str, Any]:
    plans_dir = resolve_tracked_plans_dir(workspace)
    if not plans_dir.is_dir():
        alt = gov_root / "docs" / "plans"
        if alt.is_dir():
            plans_dir = alt
    wip_root = workspace / "WIP"
    if not wip_root.is_dir():
        wip_root = gov_root / "WIP"
    campaigns_root = workspace / "environment" / "program-execution" / "campaigns"
    if not campaigns_root.is_dir():
        campaigns_root = gov_root / "environment" / "program-execution" / "campaigns"
    findings = [
        *scan_plans(plans_dir, workspace, window_days),
        *scan_wip(wip_root),
        *scan_campaigns(campaigns_root),
    ]
    archived: list[str] = []
    if archive and _tracked_store(plans_dir, workspace, gov_root):
        lock_target = _archive_lock_target(plans_dir, wip_root, workspace, gov_root)
        lock_dir = _try_hold_write_lock(lock_target)
        if lock_dir is None:
            archived = []
        else:
            try:
                archived = archive_spent_plans(plans_dir)
                archived.extend(archive_landed_wip(wip_root, findings))
            finally:
                _release_write_lock(lock_dir)
    next_three = rank_next(findings, plans_dir)
    pending = [row for row in findings if row.get("pending")]
    harvestable = [row for row in findings if row.get("harvestable")]
    return {
        "workspace": str(workspace),
        "plans_dir": str(plans_dir),
        "plans_store_ok": "docs/plans" in str(plans_dir).replace("\\", "/"),
        "findings": findings,
        "pending": pending,
        "harvestable": harvestable,
        "next": next_three,
        "archived": archived,
        "counts": {
            "plans": sum(1 for row in findings if row["surface"] == "plans"),
            "wip": sum(1 for row in findings if row["surface"] == "wip"),
            "campaigns": sum(1 for row in findings if row["surface"] == "campaigns"),
            "pending": len(pending),
            "harvestable": len(harvestable),
            "archived": len(archived),
        },
    }


def format_session_start(payload: dict[str, Any], budget: int) -> str:
    counts = payload.get("counts") or {}
    store = str(payload.get("plans_dir") or "")
    ok = "tracked docs/plans" if payload.get("plans_store_ok") else "UNTRACKED store"
    lines = [
        f"- store: {ok}; `{Path(store).as_posix()}`",
        f"- pending: plans={counts.get('plans', 0)} wip={counts.get('wip', 0)} "
        f"campaigns={counts.get('campaigns', 0)} "
        f"harvestable={counts.get('harvestable', 0)}",
    ]
    next_three = payload.get("next") or []
    if not next_three:
        lines.append("- NEXT: none")
    for idx, row in enumerate(next_three, start=1):
        lines.append(
            f"- NEXT {idx}: {row.get('surface')} / {row.get('name')} — "
            f"{row.get('execute')}; `{Path(str(row.get('path'))).name}`"
        )
    archived = payload.get("archived") or []
    if archived:
        lines.append(f"- archived: {len(archived)} spent " + "; ".join(archived[:6]))
    else:
        lines.append("- archived: 0 (mixed harvestable donors kept)")
    text = "\n".join(lines)
    if len(text) > budget:
        return text[: max(0, budget - 1)] + "…"
    return text


def format_markdown(payload: dict[str, Any]) -> str:
    counts = payload.get("counts") or {}
    lines = [
        f"- pipeline audit: plans={counts.get('plans', 0)} "
        f"wip={counts.get('wip', 0)} campaigns={counts.get('campaigns', 0)} "
        f"harvestable={counts.get('harvestable', 0)}"
    ]
    harvestable = payload.get("harvestable") or []
    if not harvestable:
        lines.append("- none: no harvestable components")
        return "\n".join(lines)
    for row in harvestable[:30]:
        flags = ",".join(row.get("flags") or []) or "unbuilt"
        lines.append(
            f"- HARVESTABLE: {row.get('surface')} / {row.get('name')} — {flags}; "
            f"`{Path(str(row.get('path'))).name}`"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--gov-root", default=None)
    parser.add_argument("--window-days", type=float, default=7.0)
    parser.add_argument(
        "--format", choices=("markdown", "json", "session-start"), default="markdown"
    )
    parser.add_argument("--budget-chars", type=int, default=1600)
    parser.add_argument("--archive-spent", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    gov_root = resolve_gov_root(workspace, args.gov_root)
    try:
        payload = run(
            workspace=workspace,
            gov_root=gov_root,
            window_days=float(args.window_days),
            archive=bool(args.archive_spent),
        )
    except Exception as exc:  # fail-open for sessionStart
        print(f"pipeline audit: unavailable ({type(exc).__name__})")
        return 0
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.format == "session-start":
        print(format_session_start(payload, int(args.budget_chars)))
        return 0
    print(format_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
