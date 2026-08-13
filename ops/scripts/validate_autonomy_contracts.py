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
        "claude-code-bounded-autonomy-scheduler",
    }
)


def _exists(root: Path, rel: str) -> bool:
    path = root / rel
    if rel.endswith("/"):
        return path.is_dir()
    return path.is_file() or path.is_dir()


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
        errors.append("artifacts must be a non-empty list")
        return errors

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
            else:
                meta_text = meta_path.read_text(encoding="utf-8")
                if "first_class_artifact: true" not in meta_text:
                    errors.append(f"{aid}: meta missing first_class_artifact: true")
        if aid == "root-autonomy-control-plane":
            if entry.get("owns_program_state") is not False:
                errors.append("root-autonomy-control-plane must set owns_program_state: false")
            provider = str(entry.get("provider_manifest") or "")
            if not provider or not (root / provider).is_file():
                errors.append(f"{aid}: provider_manifest missing: {provider}")
            else:
                provider_data = yaml.safe_load((root / provider).read_text(encoding="utf-8")) or {}
                if provider_data.get("owns_program_state") is not False:
                    errors.append(
                        f"{provider}: owns_program_state must be false "
                        "(PE Controller owns program state)"
                    )
                if provider_data.get("canonical_path") not in {canon, canon.rstrip("/")}:
                    # allow trailing-slash variance
                    pcanon = str(provider_data.get("canonical_path") or "").rstrip("/")
                    if pcanon != canon.rstrip("/"):
                        errors.append(
                            f"{aid}: PROVIDER canonical_path {pcanon!r} != MANIFEST {canon!r}"
                        )
        if aid == "autonomy-surface-profile":
            if canon != "ops/autonomy/surface_profile.yaml":
                errors.append(f"{aid}: canonical_path must be ops/autonomy/surface_profile.yaml")
        if aid == "l4-local-autonomy":
            for key in ("gate", "merge_gate", "profile_path"):
                rel = str(entry.get(key) or "")
                if not rel or not (root / rel).is_file():
                    errors.append(f"{aid}: missing {key} path: {rel}")
        if aid == "claude-code-bounded-autonomy-scheduler":
            if entry.get("e14_exemption") is not True:
                errors.append(f"{aid}: e14_exemption must be true")

    missing_ids = sorted(REQUIRED_ARTIFACT_IDS - seen)
    if missing_ids:
        errors.append(f"MANIFEST missing required artifact_ids: {missing_ids}")

    # Forbidden second SSOT: skill-local surface_profile fork
    for hit in (root / "skills").glob("**/surface_profile.yaml"):
        errors.append(f"forbidden second SSOT: {hit.relative_to(root)}")

    # Extinguished transitional Claude autonomy path must not be a live tree
    extinct = root / "environment/claude-code/autonomy"
    if extinct.exists() and not extinct.is_symlink():
        # directory present as real tree is a regression; symlink alone is transitional residue
        if extinct.is_dir() and any(extinct.iterdir()):
            errors.append(
                "forbidden live path environment/claude-code/autonomy/ "
                "(use environment/agents/adapters/claude-code/autonomy/)"
            )

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
    root = args.root.resolve()
    errors = validate(root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        print(f"RESULT: FAIL - {len(errors)} issue(s)", file=sys.stderr)
        return 1
    print("RESULT: PASS - autonomy contracts MANIFEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
