#!/usr/bin/env python3
"""Fail-closed validation for environment/contracts/autonomy/MANIFEST.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REQUIRED_ARTIFACT_IDS = frozenset(
    {
        "root-autonomy-control-plane",
        "autonomy-surface-profile",
        "l4-local-autonomy",
        "peer-execution-bounded-autonomy-runtime",
    }
)


LEGACY_CLAUDE_AUTONOMY = "environment/agents/adapters/claude-code/autonomy"
SHARED_PEER_AUTONOMY = "environment/program-execution/peer_execution/autonomy/"


def _exists(root: Path, rel: str) -> bool:
    path = root / rel
    return path.is_dir() if rel.endswith("/") else path.is_file() or path.is_dir()


def _provider_autonomy_residue_errors(root: Path) -> list[str]:
    """Fail closed on any provider adapter autonomy/ tree, including __pycache__ residue."""
    errors: list[str] = []
    hint = f"delete leftover including __pycache__; runtime is {SHARED_PEER_AUTONOMY.rstrip('/')}"
    adapters = root / "environment/agents/adapters"
    if adapters.is_dir():
        for hit in adapters.glob("*/autonomy"):
            if hit.exists():
                errors.append(
                    f"provider-owned autonomy runtime forbidden: {hit.relative_to(root)} ({hint})"
                )
    old = root / LEGACY_CLAUDE_AUTONOMY
    if old.exists():
        errors.append(f"legacy Claude-owned autonomy runtime path still exists ({hint})")
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "environment/contracts/autonomy/MANIFEST.yaml"
    if not manifest_path.is_file():
        return [f"missing {manifest_path.relative_to(root)}"]
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return ["MANIFEST.yaml must be a mapping"]
    if data.get("schema") != "l9.autonomy-contracts.manifest.v1":
        errors.append(f"unexpected schema: {data.get('schema')!r}")
    if data.get("family") != "l9_autonomy_architecture":
        errors.append(f"unexpected family: {data.get('family')!r}")
    law = data.get("law") or {}
    if law.get("subordinate_invariant") != "owns_program_state_false":
        errors.append("law.subordinate_invariant must be owns_program_state_false")
    artifacts = data.get("artifacts") or []
    if not isinstance(artifacts, list) or not artifacts:
        return errors + ["artifacts must be a non-empty list"]
    seen: set[str] = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            errors.append(f"invalid artifact entry: {entry!r}")
            continue
        aid = str(entry.get("artifact_id") or "")
        if not aid:
            errors.append("artifact missing artifact_id")
            continue
        seen.add(aid)
        if entry.get("first_class_artifact") is not True:
            errors.append(f"{aid}: first_class_artifact must be true")
        canon = str(entry.get("canonical_path") or "")
        if not canon:
            errors.append(f"{aid}: missing canonical_path")
        elif not _exists(root, canon):
            errors.append(f"{aid}: canonical_path missing on disk: {canon}")
        meta_rel = str(entry.get("meta") or "")
        if meta_rel:
            meta_path = root / "environment/contracts/autonomy" / meta_rel
            if not meta_path.is_file():
                errors.append(f"{aid}: missing meta sidecar: {meta_rel}")
            elif "first_class_artifact: true" not in meta_path.read_text(encoding="utf-8"):
                errors.append(f"{aid}: meta missing first_class_artifact: true")
        if aid == "root-autonomy-control-plane":
            if entry.get("owns_program_state") is not False:
                errors.append("root-autonomy-control-plane must not own Program state")
            provider = str(entry.get("provider_manifest") or "")
            if not provider or not (root / provider).is_file():
                errors.append(f"{aid}: provider_manifest missing: {provider}")
        if aid == "autonomy-surface-profile" and canon != "ops/autonomy/surface_profile.yaml":
            errors.append(f"{aid}: canonical_path must be ops/autonomy/surface_profile.yaml")
        if aid == "l4-local-autonomy":
            for key in ("gate", "merge_gate", "profile_path"):
                rel = str(entry.get(key) or "")
                if not rel or not (root / rel).is_file():
                    errors.append(f"{aid}: missing {key} path: {rel}")
        if aid == "peer-execution-bounded-autonomy-runtime":
            if canon != SHARED_PEER_AUTONOMY:
                errors.append(f"{aid}: canonical_path must be Peer Execution owned")
            if entry.get("owns_program_state") is not False:
                errors.append(f"{aid}: owns_program_state must be false")
    missing_ids = sorted(REQUIRED_ARTIFACT_IDS - seen)
    if missing_ids:
        errors.append(f"MANIFEST missing required artifact_ids: {missing_ids}")
    for hit in (root / "skills").glob("**/surface_profile.yaml"):
        errors.append(f"forbidden second SSOT: {hit.relative_to(root)}")
    errors.extend(_provider_autonomy_residue_errors(root))
    readme = root / "environment/contracts/autonomy/README.md"
    if not readme.is_file():
        errors.append("missing environment/contracts/autonomy/README.md")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root",
    )
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        print(f"RESULT: FAIL - {len(errors)} issue(s)", file=sys.stderr)
        return 1
    print("RESULT: PASS - autonomy contracts MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
