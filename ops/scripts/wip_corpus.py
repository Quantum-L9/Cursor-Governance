#!/usr/bin/env python3
"""WIP dated corpus: inventory, file loose drops, high-evidence prune.

WIP/ is tracked on main. Hygiene never deletes unique or unmatched bytes.
Legal Defense and credential-shaped globs are never walked or staged.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

INVENTORY_SCHEMA = "l9.wip.inventory.v1"
RECEIPT_SCHEMA = "l9.wip.prune_receipt.v1"
INVENTORY_REL = "WIP/INVENTORY.yaml"
RECEIPTS_REL = "WIP/_receipts"
LEGAL_DEFENSE = "Legal Defense"
SECRET_GLOBS = ("*oauth*.json", "*credentials*.json", "*client_secret*.json")
DATE_BUCKET_RE = re.compile(r"^\d{1,2}-\d{1,2}-\d{2}$")
SKIP_DIR_NAMES = frozenset({LEGAL_DEFENSE})
INDEX_NAMES = frozenset({"INVENTORY.yaml"})


def today_bucket(now: datetime | None = None) -> str:
    """Return M-D-YY with no leading zeros (8-16-26)."""
    stamp = now or datetime.now()
    return f"{stamp.month}-{stamp.day}-{stamp.strftime('%y')}"


def is_date_bucket(name: str) -> bool:
    return bool(DATE_BUCKET_RE.fullmatch(name))


def posix_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wip_parts(rel: str) -> list[str]:
    norm = rel.replace("\\", "/").lstrip("./")
    return [part for part in norm.split("/") if part]


def is_legal_defense(rel: str) -> bool:
    parts = _wip_parts(rel)
    return len(parts) >= 2 and parts[0] == "WIP" and parts[1] == LEGAL_DEFENSE


def is_secret_glob(rel: str) -> bool:
    name = Path(rel).name
    return any(fnmatch.fnmatch(name, pattern) for pattern in SECRET_GLOBS)


def should_skip(rel: str) -> bool:
    return is_legal_defense(rel) or is_secret_glob(rel)


def entry_kind(rel: str) -> str:
    parts = _wip_parts(rel)
    if len(parts) >= 2 and parts[1] == "_receipts":
        return "receipt"
    if len(parts) >= 2 and is_date_bucket(parts[1]):
        return "dated"
    return "series"


def date_bucket_of(rel: str) -> str | None:
    parts = _wip_parts(rel)
    if len(parts) >= 2 and is_date_bucket(parts[1]):
        return parts[1]
    return None


def load_prior_inventory(root: Path) -> dict[str, dict[str, Any]]:
    path = root / INVENTORY_REL
    if yaml is None or not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in data.get("entries") or []:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            out[item["path"]] = item
    return out


def walk_wip_files(root: Path) -> list[Path]:
    wip = root / "WIP"
    if not wip.is_dir():
        return []
    found: list[Path] = []
    for path in sorted(wip.rglob("*")):
        if not path.is_file():
            continue
        rel = posix_rel(path, root)
        if should_skip(rel):
            continue
        if path.name in INDEX_NAMES and path.parent == wip:
            continue
        found.append(path)
    return found


def file_loose(root: Path, now: datetime | None = None) -> list[str]:
    """Move WIP/* files (not dirs, not INVENTORY) into WIP/<today>/."""
    wip = root / "WIP"
    if not wip.is_dir():
        return []
    dest_dir = wip / today_bucket(now)
    moved: list[str] = []
    for path in sorted(wip.iterdir()):
        if not path.is_file():
            continue
        if path.name in INDEX_NAMES:
            continue
        rel = posix_rel(path, root)
        if should_skip(rel):
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        if dest.exists():
            if dest.is_file() and sha256_file(dest) == sha256_file(path):
                path.unlink()
                moved.append(posix_rel(dest, root))
            continue
        path.rename(dest)
        moved.append(posix_rel(dest, root))
    return moved


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def tracked_non_wip_hashes(root: Path) -> dict[str, str]:
    """sha256 -> first tracked non-WIP path."""
    proc = _git(root, "ls-files", "-z")
    if proc.returncode != 0:
        return {}
    index: dict[str, str] = {}
    for rel in proc.stdout.split("\0"):
        if not rel or rel == "WIP" or rel.startswith("WIP/"):
            continue
        path = root / rel
        if not path.is_file():
            continue
        index.setdefault(sha256_file(path), rel)
    return index


def tracked_non_wip_basenames(hashes: dict[str, str]) -> dict[str, str]:
    return {Path(path).name: path for path in hashes.values()}


def _is_tracked(root: Path, rel: str) -> bool:
    proc = _git(root, "ls-files", "--error-unmatch", "--", rel)
    return proc.returncode == 0


def _remove_wip_file(root: Path, rel: str) -> None:
    if _is_tracked(root, rel):
        proc = _git(root, "rm", "-f", "--", rel)
        if proc.returncode == 0:
            return
    path = root / rel
    if path.is_file():
        path.unlink()


def _landed_marker(prior: dict[str, Any] | None) -> dict[str, Any] | None:
    if not prior:
        return None
    landed = prior.get("landed")
    if not isinstance(landed, dict):
        return None
    path = landed.get("path")
    if isinstance(path, str) and path.strip() and not path.startswith("WIP/"):
        return landed
    return None


def prune(root: Path, now: datetime | None = None) -> Path | None:
    """Remove high-evidence landed WIP files and write a receipt."""
    prior = load_prior_inventory(root)
    hashes = tracked_non_wip_hashes(root)
    removed: list[dict[str, str]] = []
    for path in walk_wip_files(root):
        rel = posix_rel(path, root)
        if entry_kind(rel) == "receipt":
            continue
        if path.stat().st_size == 0:
            continue
        digest = sha256_file(path)
        landed_path = hashes.get(digest)
        marker = _landed_marker(prior.get(rel))
        if landed_path is None and marker is not None:
            landed_path = str(marker.get("path") or "")
        if not landed_path:
            continue
        _remove_wip_file(root, rel)
        removed.append(
            {
                "wip_path": rel,
                "landed_path": landed_path,
                "sha256": digest,
                "action": "removed",
            }
        )
    if not removed:
        return None
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    receipts = root / RECEIPTS_REL
    receipts.mkdir(parents=True, exist_ok=True)
    dest = receipts / f"prune-{stamp}.json"
    payload = {
        "schema": RECEIPT_SCHEMA,
        "created_at": (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "removed": removed,
    }
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def build_inventory(root: Path, now: datetime | None = None) -> dict[str, Any]:
    prior = load_prior_inventory(root)
    hashes = tracked_non_wip_hashes(root)
    names = tracked_non_wip_basenames(hashes)
    entries: list[dict[str, Any]] = []
    for path in walk_wip_files(root):
        rel = posix_rel(path, root)
        digest = sha256_file(path)
        kind = entry_kind(rel)
        status = "active"
        note = None
        if digest not in hashes and Path(rel).name in names and kind != "receipt":
            status = "possible-landed"
            note = "possible-landed"
        item: dict[str, Any] = {
            "path": rel,
            "kind": kind,
            "date_bucket": date_bucket_of(rel),
            "sha256": digest,
            "status": status,
        }
        if note:
            item["note"] = note
        prev = prior.get(rel)
        if prev and isinstance(prev.get("landed"), dict):
            item["landed"] = prev["landed"]
        entries.append(item)
    entries.sort(key=lambda row: str(row["path"]))
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"schema": INVENTORY_SCHEMA, "updated": stamp, "entries": entries}


def render_inventory(data: dict[str, Any]) -> str:
    if yaml is None:
        raise SystemExit("ERROR: PyYAML is required for WIP inventory")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def write_inventory(root: Path, data: dict[str, Any]) -> Path:
    dest = root / INVENTORY_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_inventory(data), encoding="utf-8")
    return dest


def inventory_check(root: Path, data: dict[str, Any]) -> int:
    path = root / INVENTORY_REL
    if not path.is_file():
        print(f"WIP inventory drift: missing {INVENTORY_REL}", file=sys.stderr)
        return 1
    if yaml is None:
        raise SystemExit("ERROR: PyYAML is required for WIP inventory")
    on_disk = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = dict(data)
    actual = dict(on_disk) if isinstance(on_disk, dict) else {}
    expected.pop("updated", None)
    actual.pop("updated", None)
    if expected != actual:
        print(f"WIP inventory drift: {INVENTORY_REL} is stale", file=sys.stderr)
        return 1
    return 0


def cmd_inventory(root: Path, check: bool, now: datetime | None) -> int:
    data = build_inventory(root, now=now)
    if check:
        return inventory_check(root, data)
    write_inventory(root, data)
    print(f"wrote {INVENTORY_REL} ({len(data['entries'])} entries)")
    return 0


def cmd_file_loose(root: Path, now: datetime | None) -> int:
    moved = file_loose(root, now=now)
    print(f"filed {len(moved)} loose WIP file(s)")
    return 0


def cmd_prune(root: Path, now: datetime | None) -> int:
    receipt = prune(root, now=now)
    if receipt is None:
        print("prune: nothing removed")
        return 0
    print(f"wrote {posix_rel(receipt, root)}")
    return 0


def cmd_hygiene(root: Path, now: datetime | None) -> int:
    file_loose(root, now=now)
    prune(root, now=now)
    return cmd_inventory(root, check=False, now=now)


def _parse_now(raw: str | None) -> datetime | None:
    if not raw:
        return None
    if raw.endswith("Z"):
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=UTC)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WIP dated corpus hygiene")
    parser.add_argument(
        "mode",
        choices=("inventory", "file-loose", "prune", "hygiene"),
    )
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument(
        "--check",
        action="store_true",
        help="inventory only: fail on INVENTORY.yaml drift (no write)",
    )
    parser.add_argument("--now", help="override clock (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    now = _parse_now(args.now)
    if args.mode == "inventory":
        return cmd_inventory(root, check=args.check, now=now)
    if args.check:
        print("ERROR: --check is only valid with inventory", file=sys.stderr)
        return 2
    if args.mode == "file-loose":
        return cmd_file_loose(root, now=now)
    if args.mode == "prune":
        return cmd_prune(root, now=now)
    return cmd_hygiene(root, now=now)


if __name__ == "__main__":
    raise SystemExit(main())
