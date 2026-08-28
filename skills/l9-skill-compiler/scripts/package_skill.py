#!/usr/bin/env python3
"""Build a runtime-only skill.zip with SKILL.md at the archive root."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
JUNK_FILES = {".DS_Store"}
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt"}


def runtime_reference_text(root: Path) -> str:
    """Return control-plane text used to distinguish runtime validators from build-only validators."""
    candidates = [root / "SKILL.md"]
    for folder in ("references", "adapters"):
        base = root / folder
        if base.exists():
            candidates.extend(
                p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES
            )
    parts: list[str] = []
    for path in candidates:
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def is_runtime_file(
    path: Path,
    root: Path,
    runtime_text: str,
    *,
    include_tests: bool,
    include_unreferenced_validators: bool,
) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts

    if path.name in JUNK_FILES or path.suffix.lower() == ".pyc":
        return False
    if any(part in CACHE_DIRS for part in parts):
        return False
    if parts and parts[0] == "tests" and not include_tests:
        return False

    if (
        len(parts) >= 2
        and parts[0] == "scripts"
        and path.suffix.lower() == ".py"
        and path.stem.startswith("validate_")
        and not include_unreferenced_validators
    ):
        rel_text = rel.as_posix()
        if rel_text not in runtime_text and path.name not in runtime_text:
            return False

    return True


def selected_files(
    root: Path,
    *,
    include_tests: bool,
    include_unreferenced_validators: bool,
) -> tuple[list[Path], list[Path]]:
    runtime_text = runtime_reference_text(root)
    included: list[Path] = []
    excluded: list[Path] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if is_runtime_file(
            path,
            root,
            runtime_text,
            include_tests=include_tests,
            include_unreferenced_validators=include_unreferenced_validators,
        ):
            included.append(path)
        else:
            excluded.append(path)

    skill = root / "SKILL.md"
    if skill in included:
        included.remove(skill)
    included.insert(0, skill)
    return included, excluded


def validate_staged_runtime(root: Path, files: list[Path]) -> int:
    validator = Path(__file__).with_name("validate_skill_pack.py")
    with tempfile.TemporaryDirectory(prefix="l9-skill-package-") as tmp:
        staged = Path(tmp) / root.name
        staged.mkdir(parents=True)
        for source in files:
            rel = source.relative_to(root)
            target = staged / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        result = subprocess.run([sys.executable, str(validator), str(staged)], text=True)
        return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_folder")
    parser.add_argument("output_directory", nargs="?", default=".")
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include source regression tests in the distributable ZIP. Off by default.",
    )
    parser.add_argument(
        "--include-unreferenced-validators",
        action="store_true",
        help="Include validate_*.py scripts not referenced by SKILL.md/references/adapters. Off by default.",
    )
    args = parser.parse_args()

    root = Path(args.skill_folder).resolve()
    out_dir = Path(args.output_directory).resolve()
    if not root.is_dir() or not (root / "SKILL.md").exists():
        print(f"FAIL: invalid skill folder: {root}", file=sys.stderr)
        return 2

    files, excluded = selected_files(
        root,
        include_tests=args.include_tests,
        include_unreferenced_validators=args.include_unreferenced_validators,
    )
    if validate_staged_runtime(root, files):
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / "skill.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(root).as_posix())

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        skill_entries = [name for name in names if name == "SKILL.md" or name.endswith("/SKILL.md")]
        if not names or names[0] != "SKILL.md":
            print("FAIL: SKILL.md must be the first archive member", file=sys.stderr)
            archive.unlink(missing_ok=True)
            return 1
        if skill_entries != ["SKILL.md"]:
            print(
                f"FAIL: archive must contain exactly one root SKILL.md; found {skill_entries}",
                file=sys.stderr,
            )
            archive.unlink(missing_ok=True)
            return 1
        if any(name.startswith(f"{root.name}/") for name in names):
            print("FAIL: wrapper skill directory detected inside archive", file=sys.stderr)
            archive.unlink(missing_ok=True)
            return 1
        if not args.include_tests and any(name.startswith("tests/") for name in names):
            print("FAIL: tests leaked into runtime distribution", file=sys.stderr)
            archive.unlink(missing_ok=True)
            return 1
        bad = zf.testzip()
        if bad:
            print(f"FAIL: corrupt archive member: {bad}", file=sys.stderr)
            archive.unlink(missing_ok=True)
            return 1

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"PASS: created {archive}")
    print("ARCHIVE_ROOT: SKILL.md")
    print(f"FILES: {len(names)}")
    print(f"EXCLUDED_SOURCE_FILES: {len(excluded)}")
    for path in excluded:
        print(f"EXCLUDED: {path.relative_to(root).as_posix()}")
    print(f"BYTES: {archive.stat().st_size}")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
