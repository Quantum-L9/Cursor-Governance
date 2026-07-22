#!/usr/bin/env python3
"""Generate deterministic JSON and YAML indexes for active global MDC rules."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "cursor-global-rules-manifest/1.1"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], bool]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, False
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, False
    data = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data, True


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def rule_record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    metadata, has_frontmatter = parse_frontmatter(text)
    description = metadata.get("description")
    always_apply = metadata.get("alwaysApply")
    globs = metadata.get("globs")
    deprecated = bool(
        isinstance(description, str) and description.lstrip().upper().startswith("DEPRECATED")
    )
    return {
        "file": path.name,
        "description": description,
        "always_apply": always_apply,
        "globs": globs,
        "first_heading": first_heading(text),
        "has_yaml_frontmatter": has_frontmatter,
        "line_count": len(text.splitlines()),
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "source_scope": "global",
        "deprecated": deprecated,
    }


def semantic_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    data = dict(manifest)
    data.pop("generated_utc", None)
    return data


def preserved_or_current_timestamp(json_path: Path, candidate: dict[str, Any]) -> str:
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = None
        if isinstance(existing, dict) and semantic_payload(existing) == semantic_payload(candidate):
            value = existing.get("generated_utc")
            if isinstance(value, str) and value:
                return value
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_manifest(rules_dir: Path, generated_utc: str = "") -> dict[str, Any]:
    records = [rule_record(path) for path in sorted(rules_dir.glob("*.mdc"))]
    true_count = sum(record["always_apply"] is True for record in records)
    false_count = sum(record["always_apply"] is False for record in records)
    other_count = len(records) - true_count - false_count
    total = len(records)
    return {
        "$schema": SCHEMA,
        "generated_utc": generated_utc,
        "rules_directory": "$HOME/.cursor-governance/rules",
        "purpose": "Machine-readable index of active global governance rules for agents and tooling.",
        "summary": {
            "total_mdc_files": total,
            "always_apply_true": true_count,
            "always_apply_false": false_count,
            "no_boolean_always_apply": other_count,
            "fractions": {
                "always_apply_true": f"{true_count}/{total}",
                "always_apply_false": f"{false_count}/{total}",
                "no_boolean_always_apply": f"{other_count}/{total}",
            },
            "identity_holds": true_count + false_count + other_count == total,
        },
        "rules": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-dir", type=Path, default=Path(__file__).resolve().parents[2] / "rules")
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--yaml", dest="yaml_path", type=Path)
    args = parser.parse_args()

    rules_dir = args.rules_dir.resolve()
    json_path = (args.json_path or rules_dir / "RULES-MANIFEST.json").resolve()
    yaml_path = (args.yaml_path or rules_dir / "RULES-MANIFEST.yaml").resolve()

    if not rules_dir.is_dir():
        raise SystemExit(f"rules directory not found: {rules_dir}")

    candidate = build_manifest(rules_dir)
    candidate["generated_utc"] = preserved_or_current_timestamp(json_path, candidate)

    json_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    yaml_path.write_text(yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"generated {json_path}")
    print(f"generated {yaml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
