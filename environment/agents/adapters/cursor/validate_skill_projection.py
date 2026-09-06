#!/usr/bin/env python3
"""Cursor skill-projection validator (Virtual Skill Plane, repository-pure).

Proves, from repository content alone, that Cursor native discovery
cardinality is decoupled from canonical L9 skill cardinality:

  * .cursor-plugin/plugin.json points Cursor at the adapter projection
  * the projection contains exactly one skill: l9-skill-gateway
  * the gateway is in neither the canonical registry nor AUTONOMY_MANIFEST
  * no canonical skill is mirrored, copied, or symlinked into the projection
  * the projection cannot escape into the canonical corpus (and vice versa)
  * the gateway's discovery metadata fits the configured Cursor budget
  * the gateway never enumerates the canonical corpus
  * AUTONOMY_MANIFEST models cursor discovery as virtual_gateway
  * the registry names exactly the live canonical corpus

Exit 0 on PASS, 1 on any failure. `--json` prints the findings.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

GATEWAY = "l9-skill-gateway"
PROJECTION_REL = Path("environment/agents/adapters/cursor/skills")
PLUGIN_REL = Path(".cursor-plugin/plugin.json")
REGISTRY_REL = Path("ops/generated/skill-registry.json")
MANIFEST_REL = Path("skills/AUTONOMY_MANIFEST.yaml")
CANONICAL_REL = Path("skills")
PLUGIN_SKILLS_VALUE = "./environment/agents/adapters/cursor/skills"
BUDGET = int(os.environ.get("CURSOR_NATIVE_DISCOVERY_BUDGET", "1024"))
DESC_MIN, DESC_MAX = 150, 500


def load_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{path}: unterminated frontmatter")
    if yaml is None:
        raise RuntimeError("PyYAML is required")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    return data, text[end + 5 :]


def live_canonical_names(root: Path) -> list[str]:
    skills = root / CANONICAL_REL
    return sorted(
        path.name
        for path in skills.iterdir()
        if path.is_dir() and not path.name.startswith("_") and (path / "SKILL.md").is_file()
    )


def validate(root: Path, *, allow_legacy_manifest: bool = False) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    facts: dict[str, Any] = {}

    # --- plugin manifest -------------------------------------------------
    plugin_path = root / PLUGIN_REL
    try:
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"plugin manifest unreadable: {exc}")
        plugin = {}
    facts["plugin_skills"] = plugin.get("skills")
    if plugin.get("skills") != PLUGIN_SKILLS_VALUE:
        msg = f"plugin.skills must be {PLUGIN_SKILLS_VALUE!r}, got {plugin.get('skills')!r}"
        if allow_legacy_manifest and plugin.get("skills") == "skills":
            facts["plugin_legacy"] = True
        else:
            errors.append(msg)
    l9_meta = plugin.get("l9", {}) if isinstance(plugin.get("l9"), dict) else {}
    if l9_meta.get("canonical_skills_directory") != "skills":
        errors.append("plugin.l9.canonical_skills_directory must be 'skills'")

    # --- projection contents --------------------------------------------
    projection = root / PROJECTION_REL
    canonical = (root / CANONICAL_REL).resolve()
    if not projection.is_dir():
        errors.append(f"projection missing: {PROJECTION_REL}")
        native: list[str] = []
    else:
        proj_resolved = projection.resolve()
        if proj_resolved.is_relative_to(canonical) or canonical.is_relative_to(proj_resolved):
            errors.append("projection and canonical skill root must not nest")
        native = []
        for entry in sorted(projection.iterdir()):
            if entry.is_symlink():
                errors.append(f"projection entry is a symlink: {entry.name}")
            if entry.is_dir():
                native.append(entry.name)
                skill_md = entry / "SKILL.md"
                if skill_md.is_symlink():
                    errors.append(f"projection SKILL.md is a symlink: {entry.name}")
                try:
                    if skill_md.exists() and skill_md.resolve().is_relative_to(canonical):
                        errors.append(f"projection resolves into canonical corpus: {entry.name}")
                except OSError:
                    errors.append(f"projection entry unresolvable: {entry.name}")
    facts["native_skills"] = native
    facts["native_skill_count"] = len(native)
    if native != [GATEWAY]:
        errors.append(f"native projection must be exactly [{GATEWAY}], got {native}")

    # --- registry + manifest membership ---------------------------------
    registry_names: list[str] = []
    registry: dict[str, Any] = {}
    try:
        registry = json.loads((root / REGISTRY_REL).read_text(encoding="utf-8"))
        registry_names = sorted(str(item.get("name")) for item in registry.get("skills", []))
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"registry unreadable: {exc}")
    if registry.get("schema_version") != 2:
        errors.append("registry schema_version must be 2")
    if GATEWAY in registry_names:
        errors.append(f"{GATEWAY} must not be in the canonical registry")
    canonical_names = live_canonical_names(root) if canonical.is_dir() else []
    facts["canonical_skill_count"] = len(canonical_names)
    facts["registry_skill_count"] = len(registry_names)
    if registry_names != canonical_names:
        missing = sorted(set(canonical_names) - set(registry_names))
        extra = sorted(set(registry_names) - set(canonical_names))
        errors.append(f"registry != canonical corpus (missing={missing}, extra={extra})")
    if GATEWAY in canonical_names:
        errors.append(f"{GATEWAY} must not live under the canonical corpus")
    mirrored = sorted(set(native) & set(canonical_names))
    if mirrored:
        errors.append(f"canonical skills mirrored into projection: {mirrored}")

    manifest: dict[str, Any] = {}
    try:
        if yaml is None:
            raise RuntimeError("PyYAML is required")
        manifest = yaml.safe_load((root / MANIFEST_REL).read_text(encoding="utf-8")) or {}
    except (OSError, RuntimeError, yaml.YAMLError if yaml else RuntimeError) as exc:  # type: ignore[misc]
        errors.append(f"manifest unreadable: {exc}")
    tiers = manifest.get("tiers", {}) if isinstance(manifest, dict) else {}
    tier_names = {
        str(entry.get("skill"))
        for tier in ("auto_invoke", "explicit_only")
        for entry in (tiers.get(tier, []) or [])
        if isinstance(entry, dict)
    }
    if GATEWAY in tier_names:
        errors.append(f"{GATEWAY} must not be a manifest tier entry")
    discovery = manifest.get("cursor_discovery", {}) if isinstance(manifest, dict) else {}
    if not isinstance(discovery, dict) or discovery.get("mode") != "virtual_gateway":
        errors.append("AUTONOMY_MANIFEST cursor_discovery.mode must be virtual_gateway")
    else:
        projection_model = discovery.get("native_projection", {}) or {}
        if projection_model.get("path") != PROJECTION_REL.as_posix():
            errors.append("cursor_discovery.native_projection.path mismatch")
        if projection_model.get("gateway") != GATEWAY:
            errors.append("cursor_discovery.native_projection.gateway mismatch")
        if projection_model.get("expected_skill_count") != 1:
            errors.append("cursor_discovery.native_projection.expected_skill_count must be 1")
        if discovery.get("canonical_root") != "skills":
            errors.append("cursor_discovery.canonical_root must be 'skills'")
        if (discovery.get("registry", {}) or {}).get("path") != REGISTRY_REL.as_posix():
            errors.append("cursor_discovery.registry.path mismatch")
        invariants = discovery.get("invariants", {}) or {}
        for key in (
            "canonical_cardinality_independent_of_native_cardinality",
            "native_canonical_mirroring_forbidden",
        ):
            if invariants.get(key) is not True:
                errors.append(f"cursor_discovery.invariants.{key} must be true")

    # --- gateway contract --------------------------------------------------
    gateway_md = projection / GATEWAY / "SKILL.md"
    if gateway_md.is_file():
        try:
            fm, body = load_frontmatter(gateway_md)
        except (ValueError, RuntimeError) as exc:
            errors.append(str(exc))
            fm, body = {}, ""
        name = str(fm.get("name") or "")
        desc = str(fm.get("description") or "")
        if name != GATEWAY:
            errors.append(f"gateway frontmatter name must be {GATEWAY}")
        if not (DESC_MIN <= len(desc) <= DESC_MAX):
            errors.append(f"gateway description {len(desc)} chars outside {DESC_MIN}-{DESC_MAX}")
        if "use when" not in desc.lower():
            errors.append("gateway description lacks a `use when` trigger clause")
        if fm.get("disable-model-invocation") is True:
            errors.append("gateway must stay model-invocable")
        footprint = len(name.encode()) + len(desc.encode())
        facts["gateway_discovery_bytes"] = footprint
        if footprint > BUDGET:
            errors.append(f"gateway discovery footprint {footprint} exceeds budget {BUDGET}")
        leaked = sorted(
            n
            for n in registry_names
            if re.search(rf"(?<![a-z0-9-]){re.escape(n)}(?![a-z0-9-])", body)
        )
        if leaked:
            errors.append(f"gateway enumerates canonical skills: {leaked[:5]}")
        for phrase in ("skill-route.json",):
            if phrase in body:
                errors.append(f"gateway references retired global state: {phrase}")
    else:
        errors.append(f"gateway SKILL.md missing: {gateway_md.relative_to(root)}")

    # --- hook registration --------------------------------------------------
    template = root / "ops" / "hooks" / "hooks.json.template"
    try:
        hooks = json.loads(template.read_text(encoding="utf-8")).get("hooks", {})
        commands = [item.get("command", "") for item in hooks.get("beforeSubmitPrompt", [])]
        if not any("before-submit-skill-router.py" in cmd for cmd in commands):
            errors.append("hooks.json.template does not register before-submit-skill-router.py")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"hooks.json.template unreadable: {exc}")

    facts["cardinality_decoupled"] = facts.get("native_skill_count") == 1 and not any(
        "mirrored" in err or "projection" in err for err in errors
    )
    return {"ok": not errors, "errors": errors, "facts": facts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--allow-legacy-manifest",
        action="store_true",
        help="pre-cutover mode: tolerate plugin.skills == 'skills' (never in CI)",
    )
    args = parser.parse_args(argv)
    result = validate(args.root, allow_legacy_manifest=args.allow_legacy_manifest)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        facts = result["facts"]
        print(
            "cursor projection: native="
            f"{facts.get('native_skill_count')} canonical={facts.get('canonical_skill_count')} "
            f"registry={facts.get('registry_skill_count')} "
            f"gateway_bytes={facts.get('gateway_discovery_bytes')} budget={BUDGET}"
        )
        for err in result["errors"]:
            print(f"  - {err}")
        print("PASS" if result["ok"] else f"FAIL ({len(result['errors'])})")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
