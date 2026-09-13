#!/usr/bin/env python3
"""Probe the live repository factory contract without copying its authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML required: {exc}")

SCHEMA = "l9.idea-foundry.factory-probe/v1"
# A hung git (lock contention, unresponsive filesystem) must fail loudly.
GIT_TIMEOUT_SECONDS = 120
REQUIRED = {
    "architecture": ".l9/architecture.yaml",
    "ownership": "scripts/birth-runner/payload-ownership.yaml",
    "payload_schema": "scripts/birth-runner/schemas/birth-payload.schema.json",
    "compiler": "scripts/birth-runner/compile_birth_payload.py",
    "birth_engine": "scripts/birth-runner/new_repo.py",
    "birth_docs": "docs/ops/REPO_BIRTH.md",
    "birth_readme": "scripts/birth-runner/README.md",
}


class ProbeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(f"git {' '.join(args)} exceeded {GIT_TIMEOUT_SECONDS}s") from exc
    if proc.returncode != 0:
        raise ProbeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def load_json_in_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProbeError(f"expected mapping: {path}")
    return data


def probe(root: Path, *, allow_dirty: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ProbeError(f"factory root is not a directory: {root}")
    paths = {name: root / rel for name, rel in REQUIRED.items()}
    missing = [str(path.relative_to(root)) for path in paths.values() if not path.is_file()]
    if missing:
        raise ProbeError("factory contract incomplete; missing: " + ", ".join(missing))

    revision = git(root, "rev-parse", "HEAD")
    tree = git(root, "rev-parse", "HEAD^{tree}")
    status = [line for line in git(root, "status", "--porcelain").splitlines() if line.strip()]
    if status and not allow_dirty:
        raise ProbeError(
            f"factory checkout is dirty ({len(status)} path(s)); "
            "qualify against a clean exact revision"
        )

    architecture = load_json_in_yaml(paths["architecture"])
    ownership = load_json_in_yaml(paths["ownership"])
    payload_schema = json.loads(paths["payload_schema"].read_text(encoding="utf-8"))

    role = architecture.get("metadata", {}).get("role")
    repository_shape = ownership.get("repository_shape")
    if not isinstance(role, str) or not role:
        raise ProbeError("factory architecture has no metadata.role")
    if (
        not isinstance(repository_shape, list)
        or not repository_shape
        or not all(isinstance(item, str) and item for item in repository_shape)
    ):
        raise ProbeError("factory ownership contract has invalid repository_shape")
    if payload_schema.get("title") != "l9.birth-payload/v1":
        raise ProbeError("factory payload schema title is not l9.birth-payload/v1")
    if payload_schema.get("additionalProperties") is not False:
        raise ProbeError("factory payload schema is not closed")

    files = {
        name: {
            "path": rel,
            "sha256": sha256(paths[name]),
        }
        for name, rel in REQUIRED.items()
    }
    return {
        "schema": SCHEMA,
        "factory": {
            "repository": architecture.get("metadata", {}).get("repository", "Unknown"),
            "revision": revision,
            "tree_sha": tree,
            "clean": not status,
            "role": role,
            "sibling_templates": architecture.get("sibling_templates", {}),
        },
        "birth_contract": {
            "payload_schema": payload_schema.get("title"),
            "payload_schema_id": payload_schema.get("$id"),
            "repository_shape": repository_shape,
            "product_surfaces": ownership.get("product", []),
            "chassis_surfaces": ownership.get("chassis", []),
        },
        "contract_files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe the exact live l9 repository factory contract."
    )
    parser.add_argument("repo_template_root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    try:
        doc = probe(args.repo_template_root, allow_dirty=args.allow_dirty)
    except (ProbeError, OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"FACTORY_PROBE: FAIL: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    print("FACTORY_PROBE: PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
