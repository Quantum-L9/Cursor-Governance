from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Loaded as a bare script by `make program-execution-conformance` and by tests
# that import it by path, so neither entry can rely on the package being on
# sys.path. Bind the sibling module explicitly instead of restating its rules.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_manifest import is_manifest_input  # noqa: E402


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
        if is_manifest_input(root, path)
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
