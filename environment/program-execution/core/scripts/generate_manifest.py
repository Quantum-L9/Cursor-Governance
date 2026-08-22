#!/usr/bin/env python3
"""Regenerate a Program Execution integrity manifest in its own shape.

Three manifests under `core/` are hashed by three different validators, and they
do not agree on shape. `core/MANIFEST.yaml` names its artifact with `artifact:`
and records `bytes:` per file; both template manifests use `template:` and carry
`path`+`sha256` only. Emitting one fixed shape for all of them rewrites two of
the three into a form their own validator rejects — running this script against
the controller template used to turn `template:` into `artifact:` and add a
`bytes:` key to all 60 entries.

So the shape is read from the target, not decided here: an existing manifest
keeps its top-level keys, their order, and its per-file key set, and only the
digests (and `summary`, where the manifest has one) are recomputed. A manifest
that does not exist yet is created from `--schema` and `--artifact`.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import yaml

#: Mirrors the exclusion set every consumer validator applies when it recomputes
#: digests (`validate_controller.py`, `validate_blueprint.py`, `validate_pair.py`).
#: A file this skips is a file they skip; drift here is a permanent gate failure.
DEFAULT_ENTRY_KEYS = ("path", "sha256", "bytes")


def is_manifest_input(root: Path, path: Path) -> bool:
    """True when `path` belongs in `root`'s manifest."""
    return (
        path.is_file()
        and path.name != "MANIFEST.yaml"
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


def manifest_inputs(root: Path) -> list[Path]:
    return [path for path in sorted(root.rglob("*")) if is_manifest_input(root, path)]


def _entry_keys(prior: dict[str, Any] | None) -> tuple[str, ...]:
    """The per-file keys this manifest records, taken from what it already records."""
    files = (prior or {}).get("files") or []
    if files and isinstance(files[0], dict):
        return tuple(files[0])
    return DEFAULT_ENTRY_KEYS


def _load_prior(target: Path) -> dict[str, Any] | None:
    if not target.is_file():
        return None
    doc = yaml.safe_load(target.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def build_payload(
    root: Path,
    *,
    schema: str | None = None,
    artifact: str | None = None,
    prior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The manifest document for `root`, shaped like `prior` when there is one."""
    keys = _entry_keys(prior)
    files: list[dict[str, Any]] = []
    total_bytes = 0
    for path in manifest_inputs(root):
        raw = path.read_bytes()
        total_bytes += len(raw)
        entry = {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
        files.append({key: entry[key] for key in keys if key in entry})

    if prior is not None:
        # dict preserves insertion order, and safe_dump(sort_keys=False) honours
        # it, so the regenerated file keeps the key order it had.
        payload = dict(prior)
        payload["files"] = files
        if "summary" in payload:
            payload["summary"] = {"file_count": len(files), "total_bytes": total_bytes}
        if schema:
            payload["schema"] = schema
        if artifact and "artifact" in payload:
            payload["artifact"] = artifact
        return payload

    if not schema or not artifact:
        raise SystemExit(
            f"{root / 'MANIFEST.yaml'} does not exist yet; --schema and --artifact are "
            "required to create one"
        )
    return {
        "schema": schema,
        "schema_version": "2.0.0",
        "artifact": artifact,
        "files": files,
        "integrity": {"algorithm": "sha256", "self_excluded": True},
        "summary": {"file_count": len(files), "total_bytes": total_bytes},
    }


def generate(root: Path, schema: str | None = None, artifact: str | None = None) -> Path:
    root = root.resolve()
    target = root / "MANIFEST.yaml"
    payload = build_payload(root, schema=schema, artifact=artifact, prior=_load_prior(target))
    target.write_text(yaml.safe_dump(payload, sort_keys=False, width=120), encoding="utf-8")
    return target


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--schema", default=None, help="required only when creating a new manifest")
    p.add_argument("--artifact", default=None, help="required only when creating a new manifest")
    a = p.parse_args()
    print(generate(a.root, a.schema, a.artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
