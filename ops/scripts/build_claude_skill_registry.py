#!/usr/bin/env python3
"""Build the deterministic Claude Code skill registry from L9 governance SSOT.

The registry is generated from:
  * skills/AUTONOMY_MANIFEST.yaml (invocation tier + routing policy)
  * skills/*/SKILL.md frontmatter (name, description, when_to_use, controls)

It is committed because Claude Code Web/Mobile setup and prompt hooks must run
without importing PyYAML in an arbitrary consumer repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

DEFAULT_OUT = Path("environment/claude-code/generated/skill-registry.json")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {path}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"unterminated YAML frontmatter: {path}")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise ValueError(f"frontmatter must be a mapping: {path}")
    return data


def tier_entries(manifest: dict[str, Any], tier: str) -> list[dict[str, Any]]:
    entries = manifest.get("tiers", {}).get(tier, [])
    if not isinstance(entries, list):
        raise ValueError(f"tiers.{tier} must be a list")
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("skill"):
            raise ValueError(f"invalid {tier} entry: {entry!r}")
        normalized.append(entry)
    return normalized


def build_registry(root: Path) -> dict[str, Any]:
    manifest_path = root / "skills" / "AUTONOMY_MANIFEST.yaml"
    manifest_bytes = manifest_path.read_bytes()
    manifest = yaml.safe_load(manifest_bytes) or {}
    if not isinstance(manifest, dict):
        raise ValueError("AUTONOMY_MANIFEST.yaml must be a mapping")

    auto = tier_entries(manifest, "auto_invoke")
    explicit = tier_entries(manifest, "explicit_only")
    names = [entry["skill"] for entry in auto + explicit]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"skills appear in multiple tiers: {duplicates}")

    routing = manifest.get("claude_routing", {})
    if not isinstance(routing, dict):
        raise ValueError("claude_routing must be a mapping")
    primary = set(routing.get("primary_skills", []))
    supporting = set(routing.get("supporting_skills", []))

    records: list[dict[str, Any]] = []
    corpus_hash = hashlib.sha256()
    for mode, entries in (("model_allowed", auto), ("explicit_only", explicit)):
        for entry in entries:
            name = str(entry["skill"])
            skill_path = root / "skills" / name / "SKILL.md"
            if not skill_path.is_file():
                raise FileNotFoundError(f"manifest skill is missing: {skill_path}")
            fm = load_frontmatter(skill_path)
            fm_name = str(fm.get("name") or name)
            if fm_name != name:
                raise ValueError(f"skill name mismatch: folder={name!r}, frontmatter={fm_name!r}")
            description = str(fm.get("description") or "").strip()
            when_to_use = str(fm.get("when_to_use") or entry.get("use_when") or "").strip()
            disabled = bool(fm.get("disable-model-invocation", False))
            if mode == "model_allowed" and disabled:
                raise ValueError(f"auto-invoke skill disables model invocation: {name}")
            if mode == "explicit_only" and not disabled:
                raise ValueError(
                    f"explicit-only skill must set disable-model-invocation: true: {name}"
                )
            if not description:
                raise ValueError(f"skill has no description: {name}")

            if name in primary:
                composition_role = "primary"
            elif name in supporting:
                composition_role = "supporting"
            else:
                composition_role = "general"

            skill_bytes = skill_path.read_bytes()
            corpus_hash.update(name.encode("utf-8") + b"\0" + skill_bytes)
            records.append(
                {
                    "name": name,
                    "path": f"skills/{name}",
                    "invocation": mode,
                    "composition_role": composition_role,
                    "description": description,
                    "when_to_use": when_to_use,
                    "reason": str(entry.get("reason") or ""),
                    "disable_model_invocation": disabled,
                    "user_invocable": bool(fm.get("user-invocable", True)),
                }
            )

    routes = routing.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError("claude_routing.routes must be a list")
    known = {record["name"] for record in records}
    for route in routes:
        if not isinstance(route, dict):
            raise ValueError(f"invalid route: {route!r}")
        route_primary = route.get("primary")
        if route_primary not in known:
            raise ValueError(f"route references unknown primary skill: {route_primary!r}")
        for support in route.get("supporting", []):
            if support not in known:
                raise ValueError(f"route references unknown supporting skill: {support!r}")

    return {
        "schema_version": 1,
        "source": "skills/AUTONOMY_MANIFEST.yaml",
        "source_manifest_sha256": sha256_bytes(manifest_bytes),
        "source_skill_corpus_sha256": corpus_hash.hexdigest(),
        "routing": routing,
        "skills": sorted(records, key=lambda item: item["name"]),
    }


def serialized(registry: dict[str, Any]) -> str:
    return json.dumps(registry, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    out = (args.out or (root / DEFAULT_OUT)).resolve()
    # Validate the constructed path before any filesystem access so faulty
    # --root/--out arguments cannot escape the repository root (path traversal).
    if not out.is_relative_to(root):
        raise SystemExit(f"refusing to access path outside repository root: {out}")
    registry_text = serialized(build_registry(root))
    if args.check:
        if not out.is_file() or out.read_text(encoding="utf-8") != registry_text:
            print(f"STALE: {out}")
            return 1
        print(f"CURRENT: {out}")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.is_file() and out.read_text(encoding="utf-8") == registry_text:
        print(f"CURRENT: {out}")
        return 0
    out.write_text(registry_text, encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
