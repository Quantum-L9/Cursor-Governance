#!/usr/bin/env python3
"""Generate JSON, YAML, and Markdown rule manifests from rules/*.mdc."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "l9.cursor-rules-manifest/v2"


@dataclass(frozen=True)
class ParsedRule:
    path: Path
    metadata: dict[str, Any]
    body: str
    has_frontmatter: bool


def parse_rule(path: Path) -> ParsedRule:
    text = path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    body = text
    has_frontmatter = False
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            raw = yaml.safe_load(parts[1]) or {}
            if not isinstance(raw, dict):
                raise ValueError(f"frontmatter must be a mapping: {path}")
            metadata = raw
            body = parts[2]
            has_frontmatter = True
    return ParsedRule(path=path, metadata=metadata, body=body, has_frontmatter=has_frontmatter)


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")
    return value or "unnamed"


def normalize_globs(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def first_heading(body: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return ""


def infer_domain(filename: str, description: str) -> str:
    sample = f"{filename} {description}".lower()
    ordered = (
        ("git", ("git", "push", "commit")),
        ("testing", ("test", "qa", "playwright", "jest")),
        ("security", ("security", "secret", "protection", "safety")),
        ("deployment", ("deploy", "vps", "infrastructure", "kubernetes")),
        ("memory", ("memory", "graphiti", "redis")),
        ("ci", ("ci-cd", "pipeline", "workflow")),
        ("python", ("python",)),
        ("typescript", ("typescript", "react", "javascript")),
        ("governance", ("governance", "cursor", "gmp", "law")),
        ("execution", ("execution", "tool-efficiency", "recursive")),
        ("output", ("output", "review-ergonomics")),
    )
    for domain, needles in ordered:
        if any(needle in sample for needle in needles):
            return domain
    return "general"


def infer_activation(metadata: dict[str, Any], globs: list[str] | None) -> str:
    explicit = metadata.get("activation")
    if explicit:
        return str(explicit)
    if metadata.get("alwaysApply") is True:
        return "always"
    if globs:
        return "auto_attached"
    return "agent_requested"


def infer_deprecation(metadata: dict[str, Any], description: str, body: str) -> tuple[bool, str | None, str | None]:
    deprecated = bool(metadata.get("deprecated")) or "deprecated" in description.lower()
    replacement = metadata.get("replacement")
    removal_plan = metadata.get("removal_plan")
    if deprecated and not replacement:
        match = re.search(r"superseded by\s+[`\"']?([A-Za-z0-9_.-]+)", f"{description}\n{body}", re.I)
        if match:
            replacement = match.group(1)
    return deprecated, str(replacement) if replacement else None, str(removal_plan) if removal_plan else None


def context_cost(line_count: int, explicit: Any) -> str:
    if explicit:
        return str(explicit)
    if line_count <= 80:
        return "minimal"
    if line_count <= 300:
        return "moderate"
    return "high"


def build_entry(path: Path) -> dict[str, Any]:
    parsed = parse_rule(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    metadata = parsed.metadata
    description = str(metadata.get("description") or "").strip()
    globs = normalize_globs(metadata.get("globs"))
    rule_id = str(metadata.get("id") or f"l9.rule.{slug(path.stem)}")
    id_source = "explicit" if metadata.get("id") else "derived"
    scope = str(metadata.get("scope") or "global")
    authority = str(metadata.get("authority") or ("canonical_global" if id_source == "explicit" else "compatibility"))
    activation = infer_activation(metadata, globs)
    deprecated, replacement, removal_plan = infer_deprecation(metadata, description, parsed.body)
    lines = text.splitlines()
    return {
        "file": path.name,
        "id": rule_id,
        "id_source": id_source,
        "version": str(metadata.get("version")) if metadata.get("version") is not None else None,
        "description": description,
        "scope": scope,
        "domain": str(metadata.get("domain") or infer_domain(path.name, description)),
        "activation": activation,
        "activation_source": "explicit" if metadata.get("activation") else "derived",
        "always_apply": metadata.get("alwaysApply") if isinstance(metadata.get("alwaysApply"), bool) else None,
        "globs": globs,
        "first_heading": first_heading(parsed.body),
        "has_yaml_frontmatter": parsed.has_frontmatter,
        "line_count": len(lines),
        "content_digest": f"sha256:{hashlib.sha256(raw).hexdigest()}",
        "authority": authority,
        "context_cost": context_cost(len(lines), metadata.get("context_cost")),
        "deprecated": deprecated,
        "replacement": replacement,
        "removal_plan": removal_plan,
        "extends": metadata.get("extends"),
        "classification_source": "explicit" if all(metadata.get(k) for k in ("id", "scope", "domain", "activation", "authority")) else "mixed_or_derived",
    }


def build_manifest(root: Path) -> dict[str, Any]:
    rules_dir = root / "rules"
    entries = [build_entry(path) for path in sorted(rules_dir.glob("*.mdc"), key=lambda p: p.name)]
    true_count = sum(entry["always_apply"] is True for entry in entries)
    false_count = sum(entry["always_apply"] is False for entry in entries)
    null_count = len(entries) - true_count - false_count
    explicit_ids = sum(entry["id_source"] == "explicit" for entry in entries)
    manifest = {
        "$schema": SCHEMA,
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": "ops/scripts/generate_rules_manifest.py",
        "rules_directory": "rules",
        "source_tree_digest": "",
        "summary": {
            "total_mdc_files": len(entries),
            "always_apply_true": true_count,
            "always_apply_false": false_count,
            "no_boolean_always_apply": null_count,
            "explicit_rule_ids": explicit_ids,
            "derived_rule_ids": len(entries) - explicit_ids,
            "deprecated_rules": sum(entry["deprecated"] for entry in entries),
        },
        "rules": entries,
    }
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    manifest["source_tree_digest"] = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    return manifest


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# Cursor governance rules manifest",
        "",
        f"Generated: `{manifest['generated_utc']}`. Source: `rules/*.mdc`.",
        "",
        "## Counts",
        "",
        "| Bucket | Count |",
        "|---|---:|",
        f"| Total MDC files | **{summary['total_mdc_files']}** |",
        f"| `alwaysApply: true` | **{summary['always_apply_true']}** |",
        f"| `alwaysApply: false` | **{summary['always_apply_false']}** |",
        f"| No boolean `alwaysApply` | **{summary['no_boolean_always_apply']}** |",
        f"| Explicit stable IDs | **{summary['explicit_rule_ids']}** |",
        f"| Derived compatibility IDs | **{summary['derived_rule_ids']}** |",
        f"| Deprecated rules | **{summary['deprecated_rules']}** |",
        "",
        "## Rule index",
        "",
        "| File | ID | Scope | Domain | Activation | Lines | Digest |",
        "|---|---|---|---|---|---:|---|",
    ]
    for entry in manifest["rules"]:
        digest = entry["content_digest"].split(":", 1)[1][:12]
        lines.append(
            f"| `{entry['file']}` | `{entry['id']}` | {entry['scope']} | {entry['domain']} | "
            f"{entry['activation']} | {entry['line_count']} | `{digest}` |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- IDs marked as derived are compatibility identities. Add explicit immutable `id` metadata when a rule is materially edited.",
            "- The JSON and YAML files are generated from the same in-memory model as this document.",
            "- Never edit manifest counters by hand.",
            "",
        ]
    )
    return "\n".join(lines)


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = build_manifest(root)
    rules_dir = root / "rules"
    json_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    yaml_text = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=1000)
    markdown_text = render_markdown(manifest)
    write_if_changed(rules_dir / "RULES-MANIFEST.json", json_text)
    write_if_changed(rules_dir / "RULES-MANIFEST.yaml", yaml_text)
    write_if_changed(rules_dir / "RULES-MANIFEST.md", markdown_text)
    print(
        "GENERATED: "
        f"{manifest['summary']['total_mdc_files']} rules; "
        f"always={manifest['summary']['always_apply_true']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
