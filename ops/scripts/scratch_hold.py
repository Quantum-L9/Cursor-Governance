#!/usr/bin/env python3
"""In-repo scratch hold ledger — park/restore non-WIP paths; never park WIP/.

Vault: <workspace>/.l9/scratch-hold/<hold_id>/
Manifest: manifest.json with status open|restored.

Sacred WIP (tracked backlog) must never enter the vault — reject park of WIP/**.
Also imports legacy temp-dir cg-*-hold* / *untracked-hold* trees on restore --all
when those dirs are owned by the current user.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
IMPORTED_SUFFIX = ".imported"
LEGACY_PATTERNS = ("cg-untracked-hold*", "cg-*-hold*", "*untracked-hold*")


def _utc_now() -> str:
    return time.strftime(UTC_FMT, time.gmtime())


def _workspace(path: str | None) -> Path:
    raw = path or os.environ.get("WS") or os.getcwd()
    return Path(raw).expanduser().resolve()


def _hold_root(ws: Path) -> Path:
    return ws / ".l9" / "scratch-hold"


def _is_wip_path(rel: str) -> bool:
    norm = rel.replace("\\", "/").lstrip("./")
    return norm == "WIP" or norm.startswith("WIP/")


def _rel_to_ws(ws: Path, target: Path) -> str:
    resolved = target.expanduser().resolve()
    try:
        return str(resolved.relative_to(ws)).replace("\\", "/")
    except ValueError as exc:
        raise SystemExit(f"ERROR: path outside workspace: {resolved}") from exc


def _load_manifest(hold_dir: Path) -> dict[str, Any]:
    path = hold_dir / MANIFEST_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_manifest(hold_dir: Path, data: dict[str, Any]) -> None:
    hold_dir.mkdir(parents=True, exist_ok=True)
    (hold_dir / MANIFEST_NAME).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _new_manifest(
    hold_id: str, ws: Path, paths: list[dict[str, str]], source: str
) -> dict[str, Any]:
    return {
        "hold_id": hold_id,
        "status": "open",
        "created_at": _utc_now(),
        "workspace": str(ws),
        "paths": paths,
        "source": source,
    }


def cmd_park(ws: Path, paths: list[str]) -> int:
    if not paths:
        print("ERROR: park requires at least one path", file=sys.stderr)
        return 2
    rels: list[str] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = ws / p
        rel = _rel_to_ws(ws, p)
        if _is_wip_path(rel):
            print(
                f"ERROR: refuse to park sacred WIP path: {rel} "
                "(WIP/ is tracked backlog — never relocate for make pr)",
                file=sys.stderr,
            )
            return 2
        if not p.exists():
            print(f"ERROR: path not found: {p}", file=sys.stderr)
            return 2
        rels.append(rel)

    hold_id = f"hold_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    hold_dir = _hold_root(ws) / hold_id
    tree = hold_dir / "tree"
    tree.mkdir(parents=True, exist_ok=False)
    moved: list[dict[str, str]] = []
    for rel in rels:
        src = ws / rel
        dest = tree / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moved.append({"relpath": rel, "held_at": str(dest.relative_to(hold_dir))})
        print(f"parked: {rel} -> {hold_id}")

    _write_manifest(hold_dir, _new_manifest(hold_id, ws, moved, "scratch_hold.park"))
    print(f"OK: hold {hold_id} ({len(moved)} path(s))")
    return 0


def _restore_one_entry(
    ws: Path, hold_dir: Path, entry: dict[str, Any], *, prefer_existing: bool
) -> int:
    """Restore a single manifest path entry. Returns 0 ok, 1 hard error."""
    rel = str(entry.get("relpath") or "")
    if not rel:
        return 0
    held_rel = str(entry.get("held_at") or f"tree/{rel}")
    src = hold_dir / held_rel
    dest = ws / rel
    if not src.exists():
        print(f"WARN: missing held path {src}", file=sys.stderr)
        return 0
    if dest.exists():
        if prefer_existing:
            print(f"skip (exists): {rel}")
            if src.is_dir():
                shutil.rmtree(src)
            else:
                src.unlink(missing_ok=True)
            return 0
        print(f"ERROR: restore target exists: {dest}", file=sys.stderr)
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    print(f"restored: {rel}")
    return 0


def _restore_hold_dir(ws: Path, hold_dir: Path, *, prefer_existing: bool) -> int:
    manifest = _load_manifest(hold_dir)
    if not manifest or manifest.get("status") == "restored":
        return 0
    for entry in manifest.get("paths") or []:
        if not isinstance(entry, dict):
            continue
        if _restore_one_entry(ws, hold_dir, entry, prefer_existing=prefer_existing) != 0:
            return 1
    manifest["status"] = "restored"
    manifest["restored_at"] = _utc_now()
    _write_manifest(hold_dir, manifest)
    return 0


def _legacy_inbox(ws: Path) -> Path | None:
    """Workspace-private inbox for legacy hold import (never public temp dirs)."""
    inbox = (ws / ".l9" / "scratch-hold-inbox").resolve()
    try:
        inbox.relative_to(ws.resolve())
    except ValueError:
        return None
    if not inbox.is_dir():
        return None
    return inbox


def _owned_by_self(path: Path) -> bool:
    try:
        st = path.stat()
    except OSError:
        return False
    if hasattr(os, "getuid"):
        return st.st_uid == os.getuid()
    return True


def _mark_imported(candidate: Path) -> None:
    try:
        candidate.rename(candidate.with_name(candidate.name + IMPORTED_SUFFIX))
    except OSError:
        pass


def _import_wip_layout(ws: Path, candidate: Path) -> bool:
    wip_src = candidate / "WIP"
    if not wip_src.is_dir():
        return False
    hold_id = f"legacy_{candidate.name}_{uuid.uuid4().hex[:6]}"
    hold_dir = _hold_root(ws) / hold_id
    tree = hold_dir / "tree" / "WIP"
    tree.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(wip_src, tree, dirs_exist_ok=True)
    paths = [
        {"relpath": f"WIP/{child.name}", "held_at": f"tree/WIP/{child.name}"}
        for child in sorted(tree.iterdir())
    ]
    _write_manifest(hold_dir, _new_manifest(hold_id, ws, paths, f"legacy_tmp:{candidate}"))
    print(f"imported legacy hold: {candidate} -> {hold_id}")
    _mark_imported(candidate)
    return True


def _collect_legacy_files(candidate: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(candidate.rglob("*")):
        if path.name == MANIFEST_NAME or not path.is_file():
            continue
        try:
            rel = str(path.relative_to(candidate)).replace("\\", "/")
        except ValueError:
            continue
        if not rel.startswith(("WIP/", "reports/", "ops/")):
            continue
        entries.append({"relpath": rel, "src": str(path)})
    return entries


def _import_file_entries(ws: Path, candidate: Path, entries: list[dict[str, str]]) -> bool:
    if not entries:
        return False
    hold_id = f"legacy_{candidate.name}_{uuid.uuid4().hex[:6]}"
    hold_dir = _hold_root(ws) / hold_id
    tree = hold_dir / "tree"
    moved_meta: list[dict[str, str]] = []
    for ent in entries:
        rel = ent["relpath"]
        src = Path(ent["src"])
        dest = tree / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        moved_meta.append({"relpath": rel, "held_at": f"tree/{rel}"})
    _write_manifest(hold_dir, _new_manifest(hold_id, ws, moved_meta, f"legacy_tmp:{candidate}"))
    print(f"imported legacy hold: {candidate} -> {hold_id}")
    _mark_imported(candidate)
    return True


def _import_legacy_tmp(ws: Path) -> int:
    """Import legacy hold layouts from workspace .l9/scratch-hold-inbox into the vault."""
    if os.environ.get("L9_SCRATCH_HOLD_IMPORT_TMP", "1").strip() in {"0", "false", "no"}:
        return 0
    tmp = _legacy_inbox(ws)
    if tmp is None:
        return 0
    imported = 0
    seen: set[Path] = set()
    for pattern in LEGACY_PATTERNS:
        for candidate in tmp.glob(pattern):
            if not candidate.is_dir() or candidate in seen:
                continue
            if candidate.name.endswith(IMPORTED_SUFFIX):
                continue
            if not _owned_by_self(candidate):
                print(f"skip (not owned): {candidate}", file=sys.stderr)
                continue
            seen.add(candidate)
            if _import_wip_layout(ws, candidate):
                imported += 1
                continue
            if _import_file_entries(ws, candidate, _collect_legacy_files(candidate)):
                imported += 1
    return imported


def cmd_restore(ws: Path, hold_id: str | None, *, import_legacy: bool) -> int:
    if import_legacy:
        _import_legacy_tmp(ws)
    root = _hold_root(ws)
    if not root.is_dir():
        print("OK: no scratch holds")
        return 0
    if hold_id:
        targets = [root / hold_id]
        if not targets[0].is_dir():
            print(f"ERROR: unknown hold_id {hold_id}", file=sys.stderr)
            return 2
    else:
        targets = sorted(p for p in root.iterdir() if p.is_dir())
    rc = 0
    for hold_dir in targets:
        if _restore_hold_dir(ws, hold_dir, prefer_existing=True) != 0:
            rc = 1
    if rc == 0:
        print("OK: restore complete")
    return rc


def cmd_status(ws: Path) -> int:
    root = _hold_root(ws)
    open_holds: list[str] = []
    if root.is_dir():
        for hold_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            manifest = _load_manifest(hold_dir)
            if manifest.get("status") == "open":
                open_holds.append(hold_dir.name)
                print(f"OPEN: {hold_dir.name}")
                for ent in manifest.get("paths") or []:
                    if isinstance(ent, dict):
                        print(f"  - {ent.get('relpath')}")
    if open_holds:
        print(
            f"FAIL: {len(open_holds)} open scratch hold(s) — "
            f"run: python3 ops/scripts/scratch_hold.py --workspace {ws} restore --all",
            file=sys.stderr,
        )
        return 1
    print("OK: no open scratch holds")
    return 0


def cmd_gc(ws: Path, *, max_age_days: int) -> int:
    root = _hold_root(ws)
    if not root.is_dir():
        print("OK: nothing to gc")
        return 0
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    errors = 0
    for hold_dir in list(root.iterdir()):
        if not hold_dir.is_dir():
            continue
        manifest = _load_manifest(hold_dir)
        if manifest.get("status") != "restored":
            continue
        if hold_dir.stat().st_mtime > cutoff:
            continue
        try:
            shutil.rmtree(hold_dir)
        except OSError as exc:
            print(f"ERROR: gc failed for {hold_dir.name}: {exc}", file=sys.stderr)
            errors += 1
            continue
        print(f"gc: removed {hold_dir.name}")
        removed += 1
    print(f"OK: gc removed {removed}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--workspace",
        default=None,
        help="repo root (default: WS env or cwd)",
    )
    parser = argparse.ArgumentParser(description=__doc__, parents=[parent])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_park = sub.add_parser("park", help="Park non-WIP paths into the vault", parents=[parent])
    p_park.add_argument("paths", nargs="+")

    p_restore = sub.add_parser("restore", help="Restore open holds", parents=[parent])
    p_restore.add_argument("--all", action="store_true", dest="restore_all")
    p_restore.add_argument("--id", dest="hold_id", default=None)
    p_restore.add_argument(
        "--no-import-legacy",
        action="store_true",
        help="Skip temp-dir legacy hold import",
    )

    sub.add_parser("status", help="Exit 1 if any open hold", parents=[parent])

    p_gc = sub.add_parser("gc", help="Delete old restored holds", parents=[parent])
    p_gc.add_argument("--max-age-days", type=int, default=14)

    args = parser.parse_args(argv)
    ws = _workspace(args.workspace)

    if args.cmd == "park":
        return cmd_park(ws, args.paths)
    if args.cmd == "restore":
        hold_id = None if args.restore_all or not args.hold_id else args.hold_id
        return cmd_restore(ws, hold_id, import_legacy=not args.no_import_legacy)
    if args.cmd == "status":
        return cmd_status(ws)
    if args.cmd == "gc":
        return cmd_gc(ws, max_age_days=args.max_age_days)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
