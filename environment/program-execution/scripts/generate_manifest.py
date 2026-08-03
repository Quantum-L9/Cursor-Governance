from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EXCLUDED_NAMES = {
    "MANIFEST.json",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3"}


def generate(root: Path) -> dict[str, object]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if "core" in path.relative_to(root).parts[:1]:
            continue
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return {
        "schema": "program-execution-adapter-layer.manifest.v1",
        "artifact": "program-execution-adapter-layer-v1.0.0",
        "integrity": {"algorithm": "sha256", "self_excluded": True},
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    output = root / "MANIFEST.json"
    output.write_text(
        json.dumps(generate(root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
