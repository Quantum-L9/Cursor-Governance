#!/usr/bin/env python3
"""Create a deterministic, safety-aware inventory for an idea pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sql",
    ".csv",
    ".xml",
    ".html",
    ".css",
    ".sh",
    ".ps1",
    ".svg",
    ".graphql",
    ".proto",
}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz"}
METADATA_NAMES = {".DS_Store", "Thumbs.db"}
METADATA_PARTS = {"__MACOSX", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def path_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.name in METADATA_NAMES or any(part in METADATA_PARTS for part in path.parts):
        return "metadata"
    suffix = path.suffix.lower()
    if suffix in ARCHIVE_EXTENSIONS or path.name.lower().endswith(".tar.gz"):
        return "archive"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    return "binary"


def record_path(records: list[dict], root: Path, path: Path, prefix: str = "") -> None:
    rel = path.relative_to(root).as_posix()
    kind = path_kind(path)
    if path.is_symlink():
        target = path.readlink().as_posix().encode("utf-8")
        records.append(
            {
                "path": f"{prefix}{rel}",
                "size": len(target),
                "sha256": sha256_bytes(target),
                "kind": kind,
                "symlink_target": target.decode("utf-8"),
            }
        )
        return

    data = path.read_bytes()
    records.append(
        {
            "path": f"{prefix}{rel}",
            "size": len(data),
            "sha256": sha256_bytes(data),
            "kind": kind,
        }
    )


def _safe_target(dest: Path, member_name: str) -> Path:
    member = Path(member_name)
    if member.is_absolute():
        raise ValueError(f"absolute archive member: {member_name}")
    target = (dest / member).resolve()
    resolved_dest = dest.resolve()
    if target != resolved_dest and resolved_dest not in target.parents:
        raise ValueError(f"archive traversal member: {member_name}")
    return target


def safe_extract_zip(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        for member in zf.infolist():
            target = _safe_target(dest, member.filename)
            mode = (member.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise ValueError(f"zip symlink member rejected: {member.filename}")
            if member.is_dir() or member.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src_fh, target.open("wb") as out_fh:
                out_fh.write(src_fh.read())


def safe_extract_tar(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(src) as tf:
        for member in tf.getmembers():
            target = _safe_target(dest, member.name)
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"unsafe tar member type rejected: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValueError(f"unsafe tar member type rejected: {member.name}")
            extracted = tf.extractfile(member)
            if extracted is None:
                raise ValueError(f"tar member unreadable: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with extracted, target.open("wb") as out_fh:
                out_fh.write(extracted.read())


def extract_archive(src: Path, dest: Path) -> None:
    if zipfile.is_zipfile(src):
        safe_extract_zip(src, dest)
        return
    if tarfile.is_tarfile(src):
        safe_extract_tar(src, dest)
        return
    raise ValueError("unsupported archive format")


def inventory_tree(
    root: Path,
    expand_archives: bool,
    max_depth: int,
    depth: int = 0,
    prefix: str = "",
) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    issues: list[dict] = []

    paths = sorted(root.rglob("*"), key=lambda p: p.as_posix())
    for path in paths:
        if path.is_symlink():
            record_path(records, root, path, prefix)
            continue
        if not path.is_file():
            continue

        record_path(records, root, path, prefix)
        if not expand_archives or depth >= max_depth or path_kind(path) != "archive":
            continue

        nested_name = f"{prefix}{path.relative_to(root).as_posix()}"
        try:
            with tempfile.TemporaryDirectory(prefix="idea-pack-nested-") as td:
                dest = Path(td)
                extract_archive(path, dest)
                nested_prefix = nested_name + "!/"
                child_records, child_issues = inventory_tree(
                    dest, True, max_depth, depth + 1, nested_prefix
                )
                records.extend(child_records)
                issues.extend(child_issues)
        except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
            issues.append(
                {
                    "path": nested_name,
                    "code": "NESTED_ARCHIVE_UNREADABLE",
                    "detail": str(exc),
                }
            )

    return records, issues


def canonical_digest(records: list[dict], issues: list[dict]) -> str:
    material = json.dumps(
        {"files": records, "issues": issues},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256_bytes(material)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--no-expand-archives", action="store_true")
    parser.add_argument("--max-archive-depth", type=int, default=3)
    args = parser.parse_args()

    if args.max_archive_depth < 0:
        raise SystemExit("--max-archive-depth must be >= 0")

    source = args.source.resolve()
    if not source.exists():
        raise SystemExit(f"source not found: {source}")

    issues: list[dict] = []
    if source.is_dir():
        records, issues = inventory_tree(
            source, not args.no_expand_archives, args.max_archive_depth
        )
        source_kind = "directory"
    elif zipfile.is_zipfile(source) or tarfile.is_tarfile(source):
        source_kind = "archive"
        try:
            with tempfile.TemporaryDirectory(prefix="idea-pack-") as td:
                root = Path(td)
                extract_archive(source, root)
                records, issues = inventory_tree(
                    root, not args.no_expand_archives, args.max_archive_depth
                )
        except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
            raise SystemExit(f"unsafe or unreadable source archive: {exc}") from exc
    else:
        source_kind = "file"
        if source.is_symlink():
            target = source.readlink().as_posix().encode("utf-8")
            records = [
                {
                    "path": source.name,
                    "size": len(target),
                    "sha256": sha256_bytes(target),
                    "kind": "symlink",
                    "symlink_target": target.decode("utf-8"),
                }
            ]
        else:
            data = source.read_bytes()
            records = [
                {
                    "path": source.name,
                    "size": len(data),
                    "sha256": sha256_bytes(data),
                    "kind": path_kind(source),
                }
            ]

    records = sorted(records, key=lambda r: r["path"])
    issues = sorted(issues, key=lambda r: (r["path"], r["code"], r["detail"]))
    payload = {
        "schema": "l9.idea-pack-inventory/v1",
        "source_name": source.name,
        "source_kind": source_kind,
        "file_count": len(records),
        "archive_count": sum(1 for r in records if r["kind"] == "archive"),
        "issue_count": len(issues),
        "inventory_digest": canonical_digest(records, issues),
        "issues": issues,
        "files": records,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
