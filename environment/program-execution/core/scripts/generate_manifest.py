#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import yaml


def generate(root: Path, schema: str, artifact: str) -> Path:
    root = root.resolve()
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
                    "bytes": path.stat().st_size,
                }
            )
    payload = {
        "schema": schema,
        "schema_version": "2.0.0",
        "artifact": artifact,
        "files": files,
        "integrity": {"algorithm": "sha256", "self_excluded": True},
        "summary": {"file_count": len(files), "total_bytes": sum(x["bytes"] for x in files)},
    }
    target = root / "MANIFEST.yaml"
    target.write_text(yaml.safe_dump(payload, sort_keys=False, width=120), encoding="utf-8")
    return target


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--schema", required=True)
    p.add_argument("--artifact", required=True)
    a = p.parse_args()
    print(generate(a.root, a.schema, a.artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
