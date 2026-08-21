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

#: Top-level directories under the Program Execution root that the adapter-layer
#: manifest does not describe. ``core/`` carries its own MANIFEST.yaml.
EXCLUDED_TOP_LEVEL = {"core"}


def is_manifest_input(root: Path, path: Path) -> bool:
    """True when ``path`` belongs in the adapter-layer manifest.

    Single source of truth for the manifest's input surface. ``validate_manifest``
    imports this rather than restating it: when the generator skipped a name the
    validator did not, an ordinary ``pytest`` run under
    ``peer_execution/`` (a pytest rootdir) left a ``.pytest_cache/`` the
    validator reported as an inventory mismatch the generator would never fix.
    """
    if not path.is_file():
        return False
    rel_parts = path.relative_to(root).parts
    if not rel_parts:
        return False
    if rel_parts[0] in EXCLUDED_TOP_LEVEL:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return not any(part in EXCLUDED_NAMES for part in rel_parts)


def manifest_inputs(root: Path) -> list[Path]:
    """Every file the manifest must describe, in stable sorted order."""
    return [path for path in sorted(root.rglob("*")) if is_manifest_input(root, path)]


def generate(root: Path) -> dict[str, object]:
    files = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in manifest_inputs(root)
    ]
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
