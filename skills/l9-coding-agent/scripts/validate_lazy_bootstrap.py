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


# Procedure-only keys; anything else risks a local restatement of upstream law.
CANONICAL_BINDING_KEYS = {
    "purpose",
    "applies_in_modes",
    "mode_independence",
    "upstream",
    "accepted_input",
    "not_accepted",
    "verifier",
    "selection",
    "binds_into",
    "outcomes",
    "invalidation",
    "unknown_handling",
    "enforcement_scope",
}


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return {str(k) for k in node} | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def check_canonical_binding(root: Path, bootstrap_doc: dict, inventory: set[str]) -> list[str]:
    """Intake must bind canonical invariants by reference before mutation."""
    errors: list[str] = []
    intake = bootstrap_doc.get("stages", {}).get("intake", {})
    bind = intake.get("bind_before_exit") or {}
    owner, _, section = str(bind.get("owner", "")).partition("#")
    if owner not in intake.get("artifacts", []) or section != "canonical_invariant_binding":
        errors.append(
            "intake does not bind canonical_invariant_binding from a routed owner section"
        )
        return errors
    script = str(bind.get("invoke", ""))
    if script not in inventory or not (root / script).is_file():
        errors.append(f"canonical binding verifier is not a packaged file: {script}")
    try:
        owner_doc = yaml.safe_load((root / owner).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [f"canonical binding owner unreadable: {owner}: {exc}"]
    binding = owner_doc.get(section) if isinstance(owner_doc, dict) else None
    if not isinstance(binding, dict):
        return [f"canonical binding section missing: {owner}#{section}"]
    unexpected = sorted(set(binding) - CANONICAL_BINDING_KEYS)
    if unexpected:
        errors.append("canonical binding has undeclared top-level keys: " + ", ".join(unexpected))
    reasons = yaml.safe_load((root / "catalogs/REASON_CODES.yaml").read_text(encoding="utf-8"))
    if "BLOCKED_UPSTREAM_PROJECTION_PRODUCER" not in ((reasons or {}).get("reasons") or {}):
        errors.append("BLOCKED_UPSTREAM_PROJECTION_PRODUCER is not a registered reason code")
    upstream = binding.get("upstream") or {}
    if upstream.get("semantic_owner") != "Quantum-L9/.github" or not upstream.get("profile_ref"):
        errors.append("canonical binding lacks upstream owner/profile identity")
    if (binding.get("verifier") or {}).get("script") != script:
        errors.append("canonical binding verifier differs from the intake route")
    if not (binding.get("unknown_handling") or {}).get("no_fallback"):
        errors.append("canonical binding lacks an explicit no-fallback rule for Unknown")
    if "Instructional" not in str(binding.get("enforcement_scope", "")):
        errors.append("canonical binding must state that its enforcement is instructional")
    if {"statement", "statements"} & _keys(binding):
        errors.append("canonical binding restates upstream law text instead of referencing it")
    return errors


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

    errors.extend(check_canonical_binding(root, bootstrap_doc, inventory))

    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(
        "PASS: lazy bootstrap closes "
        + f"{len(semantic)} semantic owners and classifies {len(actual)} packaged files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
