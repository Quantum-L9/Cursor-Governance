#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _write_under(root: Path, path: Path, text: str) -> None:
    root_r = os.path.realpath(root)
    path_r = os.path.realpath(path)
    if os.path.commonpath([root_r, path_r]) != root_r:
        raise ValueError(f"path escapes root: {path}")
    Path(path_r).write_text(text, encoding="utf-8")


def render_tree(target: Path, replacements: dict[str, str]) -> None:
    if target.exists():
        raise SystemExit(f"target already exists: {target}")
    shutil.copytree(
        ROOT, target, ignore=shutil.ignore_patterns("MANIFEST.yaml", "__pycache__", "*.pyc")
    )
    for path in target.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".md",
            ".yaml",
            ".yml",
            ".json",
            ".py",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for key, value in replacements.items():
            text = text.replace("{{" + key + "}}", value)
        _write_under(target, path, text)
    program_path = target / "PROGRAM.yaml"
    program = yaml.safe_load(program_path.read_text(encoding="utf-8"))
    program["program"]["definition_status"] = "draft"
    _write_under(target, program_path, yaml.safe_dump(program, sort_keys=False, width=110))
    write_manifest(target)


def write_manifest(root: Path) -> None:
    files = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.name != "MANIFEST.yaml"
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ):
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    manifest = {
        "schema": "program-execution-blueprint.manifest.v2",
        "schema_version": "2.0.0",
        "template": "program-execution-blueprint",
        "files": files,
        "integrity": {"algorithm": "sha256", "self_excluded": True},
    }
    _write_under(root, root / "MANIFEST.yaml", yaml.safe_dump(manifest, sort_keys=False, width=110))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--target", required=True, type=Path)
    args = p.parse_args()
    render_tree(
        args.target.resolve(),
        {
            "PROGRAM_NAME": args.name,
            "PROGRAM_ID": args.id,
            "PROGRAM_VERSION": args.version,
            "PROGRAM_OWNER": args.owner,
            "DATE": args.date,
        },
    )
    print(args.target.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
