from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def validate(root: Path) -> list[str]:
    manifest_path = root / "MANIFEST.json"
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    expected = {item["path"]: item["sha256"] for item in value["files"]}
    for relative, digest in expected.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing manifest file: {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            errors.append(f"manifest digest mismatch: {relative}")
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name != "MANIFEST.json"
        and path.suffix not in {".pyc", ".pyo", ".sqlite", ".sqlite3"}
        and path.relative_to(root).parts[0] != "core"
        and "__pycache__" not in path.parts
    }
    if set(expected) != actual_paths:
        errors.append(
            "manifest inventory mismatch: "
            f"missing={sorted(actual_paths - set(expected))}, "
            f"stale={sorted(set(expected) - actual_paths)}"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    errors = validate(root)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
