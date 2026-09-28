#!/usr/bin/env python3
"""Validate lazy-bootstrap reachability and package classification for L9 Coding Agent."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:
    raise SystemExit(f"PyYAML is required: {exc}")


def flatten_groups(groups: dict) -> set[str]:
    out: set[str] = set()
    for value in groups.values():
        if isinstance(value, list):
            out.update(str(x) for x in value)
    return out


def bootstrap_artifacts(data: dict) -> set[str]:
    out: set[str] = set(data.get("first_read", []))
    for stage in data.get("stages", {}).values():
        out.update(stage.get("artifacts", []))
    for route in data.get("conditional", {}).values():
        out.update(route.get("artifacts", []))
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()
    errors: list[str] = []
    manifest_doc = yaml.safe_load((root / "runtime/MANIFEST.yaml").read_text(encoding="utf-8"))
    bootstrap_doc = yaml.safe_load((root / "runtime/BOOTSTRAP.yaml").read_text(encoding="utf-8"))[
        "bootstrap"
    ]
    skill = (root / "SKILL.md").read_text(encoding="utf-8")

    if "runtime/BOOTSTRAP.yaml" not in skill:
        errors.append("SKILL.md does not route first to runtime/BOOTSTRAP.yaml")
    if "Do not hydrate the whole skill on activation" not in skill:
        errors.append("SKILL.md lacks explicit anti-eager-load guard")

    routed = bootstrap_artifacts(bootstrap_doc)
    routed.add("runtime/MANIFEST.yaml")
    semantic = manifest_doc.get("semantic_owners", {})
    for concern, item in semantic.items():
        owner = item.get("owner")
        if not owner:
            errors.append(f"semantic owner missing path: {concern}")
            continue
        if not (root / owner).is_file():
            errors.append(f"semantic owner missing file: {concern} -> {owner}")
        if owner not in routed:
            errors.append(f"semantic owner unreachable from lazy bootstrap: {concern} -> {owner}")

    inventory: set[str] = set()
    for items in manifest_doc.get("package_inventory", {}).values():
        inventory.update(items)
    actual = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc")
    }
    missing_from_inventory = sorted(actual - inventory)
    missing_files = sorted(inventory - actual)
    for rel in missing_from_inventory:
        errors.append(f"unclassified packaged file: {rel}")
    for rel in missing_files:
        errors.append(f"inventory references missing file: {rel}")

    eager = set(manifest_doc.get("bootstrap_load", []))
    if eager != {"runtime/BOOTSTRAP.yaml"}:
        errors.append(
            f"bootstrap_load must contain only runtime/BOOTSTRAP.yaml, got {sorted(eager)}"
        )

    manifest_runtime = flatten_groups(manifest_doc.get("load_groups", {})) | flatten_groups(
        manifest_doc.get("conditional_load_groups", {})
    )
    declared_routes = routed - {"runtime/BOOTSTRAP.yaml", "runtime/MANIFEST.yaml"}
    if manifest_runtime != declared_routes:
        for rel in sorted(manifest_runtime - declared_routes):
            errors.append(f"manifest route missing from bootstrap router: {rel}")
        for rel in sorted(declared_routes - manifest_runtime):
            errors.append(f"bootstrap route missing from manifest groups: {rel}")

    package_only_prefixes = ("references/", "evals/", "agents/")
    package_only_exact = {
        "README.md",
        "RUNBOOK.md",
        "MANIFEST.md",
        "VALIDATION.md",
        "CHANGELOG.md",
        "expertise_model.yaml",
        "skill_intelligence_report.yaml",
    }
    first_stage = set(bootstrap_doc.get("stages", {}).get("intake", {}).get("artifacts", []))
    if any(x in package_only_exact or x.startswith(package_only_prefixes) for x in first_stage):
        errors.append("package-only intelligence or operator evidence leaked into intake stage")

    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(
        f"PASS: lazy bootstrap closes {len(semantic)} semantic owners and classifies {len(actual)} packaged files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
