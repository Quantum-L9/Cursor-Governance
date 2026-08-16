#!/usr/bin/env python3
"""Generate v3 JSON, YAML, and Markdown rule manifests from rules/*.mdc."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import yaml
_SCRIPTS = Path(__file__).resolve().parent
_ROOT = Path(__file__).resolve().parents[2]
_CONTRACTS = _ROOT / "ops" / "contracts"
for directory in (_SCRIPTS, _CONTRACTS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from lib.rule_frontmatter import (  # noqa: E402
    ParsedRule,
    normalize_globs,
    parse_rule,
)
SCHEMA = "l9.cursor-rules-manifest/v3"
__all__ = [
    "SCHEMA",
    "ParsedRule",
    "build_entry",
    "build_manifest",
    "normalize_globs",
    "parse_rule",
    "render_markdown",
    "serialize_manifest",
]
def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", ".", value.casefold()).strip(".")
    return value or "unnamed"
def first_heading(body: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return ""
def infer_domain(filename: str, description: str) -> str:
    sample = f"{filename} {description}".casefold()
    ordered = (
        ("git", ("git", "push", "commit")),
        ("testing", ("test", "qa", "playwright", "jest")),
        ("security", ("security", "secret", "protection", "safety")),
        ("deployment", ("deploy", "vps", "infrastructure", "kubernetes")),
        ("memory", ("memory", "graphiti", "redis")),
        ("ci", ("ci-cd", "pipeline", "workflow")),
        ("python", ("python",)),
        ("typescript", ("typescript", "react", "javascript")),
        ("governance", ("governance", "cursor", "gmp", "law", "contract")),
        ("execution", ("execution", "tool-efficiency", "recursive")),
        ("output", ("output", "review-ergonomics")),
    )
    for domain, needles in ordered:
        if any(needle in sample for needle in needles):
            return domain
    return "general"
def infer_activation(
    metadata: dict[str, Any],
    globs: list[str] | None,
) -> str:
    explicit = metadata.get("activation")
    if explicit:
        return str(explicit)
    if metadata.get("alwaysApply") is True:
        return "always"
    if globs:
        return "auto_attached"
    return "agent_requested"
def infer_deprecation(
    metadata: dict[str, Any],
    description: str,
    body: str,
) -> tuple[bool, str | None, str | None]:
    deprecated = bool(metadata.get("deprecated")) or (
        "deprecated" in description.casefold()
    )
    replacement = metadata.get("replacement")
    removal_plan = metadata.get("removal_plan")
    if deprecated and not replacement:
        match = re.search(
            r"superseded by\s+[`\"']?([A-Za-z0-9_.-]+)",
            f"{description}\n{body}",
            re.I,
        )
        if match:
            replacement = match.group(1)
    return (
        deprecated,
        str(replacement) if replacement else None,
        str(removal_plan) if removal_plan else None,
    )
def context_cost(line_count: int, explicit: Any) -> str:
    if explicit:
        return str(explicit)
    if line_count <= 80:
        return "minimal"
    if line_count <= 300:
        return "moderate"
    return "high"
def _default_projection() -> dict[str, Any]:
    return {
        "migration_state": "legacy",
        "binding": None,
        "contracts": [],
        "projection": None,
        "context": {},
        "semantic_authority": {
            "owner": "legacy_rule_pending_migration",
            "rule_may_redefine": True,
        },
    }
def build_entry(
    path: Path,
    projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = parse_rule(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    metadata = parsed.metadata
    description = str(metadata.get("description") or "").strip()
    globs = normalize_globs(metadata.get("globs"))
    rule_id = str(metadata.get("id") or f"l9.rule.{slug(path.stem)}")
    id_source = "explicit" if metadata.get("id") else "derived"
    scope = str(metadata.get("scope") or "global")
    authority = str(
        metadata.get("authority")
        or ("canonical_global" if id_source == "explicit" else "compatibility")
    )
    activation = infer_activation(metadata, globs)
    deprecated, replacement, removal_plan = infer_deprecation(
        metadata,
        description,
        parsed.body,
    )
    lines = text.splitlines()
    bytes_count = len(raw)
    contract_state = _default_projection()
    if projection:
        contract_state.update(projection)
    context = dict(contract_state.get("context") or {})
    context.setdefault("measured_bytes", bytes_count)
    context.setdefault("token_estimate", (bytes_count + 3) // 4)
    context.setdefault("budget_bytes", None)
    context.setdefault("budget_status", "legacy_unbudgeted")
    return {
        "file": path.name,
        "id": rule_id,
        "id_source": id_source,
        "version": (
            str(metadata.get("version"))
            if metadata.get("version") is not None
            else None
        ),
        "description": description,
        "scope": scope,
        "domain": str(
            metadata.get("domain")
            or infer_domain(path.name, description)
        ),
        "activation": activation,
        "activation_source": (
            "explicit" if metadata.get("activation") else "derived"
        ),
        "always_apply": (
            metadata.get("alwaysApply")
            if isinstance(metadata.get("alwaysApply"), bool)
            else None
        ),
        "globs": globs,
        "first_heading": first_heading(parsed.body),
        "has_yaml_frontmatter": parsed.has_frontmatter,
        "line_count": len(lines),
        "content_digest": (
            f"sha256:{hashlib.sha256(raw).hexdigest()}"
        ),
        "authority": authority,
        "context_cost": context_cost(
            len(lines),
            metadata.get("context_cost"),
        ),
        "deprecated": deprecated,
        "replacement": replacement,
        "removal_plan": removal_plan,
        "extends": metadata.get("extends"),
        "classification_source": (
            "explicit"
            if all(
                metadata.get(key)
                for key in (
                    "id",
                    "scope",
                    "domain",
                    "activation",
                    "authority",
                )
            )
            else "mixed_or_derived"
        ),
        "migration_state": contract_state["migration_state"],
        "binding": contract_state.get("binding"),
        "contracts": contract_state.get("contracts") or [],
        "projection": contract_state.get("projection"),
        "context": context,
        "semantic_authority": contract_state["semantic_authority"],
        "lifecycle": {
            "deprecated": deprecated,
            "replacement": replacement,
            "removal_plan": removal_plan,
        },
    }
def _load_projection_index(root: Path) -> dict[str, dict[str, Any]]:
    """Resolve projection metadata when contract tooling is available."""
    try:
        from build_rules import build_projection_index
    except ImportError:
        return {}
    try:
        projection_index, _ = build_projection_index(root)
    except (OSError, ValueError):
        return {}
    return projection_index
def _existing_generated_utc(root: Path) -> str | None:
    path = root / "rules" / "RULES-MANIFEST.json"
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(loaded, dict):
        value = loaded.get("generated_utc")
        if isinstance(value, str):
            return value
    return None
def _semantic_manifest_payload(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    copied = dict(manifest)
    copied.pop("generated_utc", None)
    return copied
def build_manifest(
    root: Path,
    projection_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rules_dir = root / "rules"
    if projection_index is None:
        projection_index = _load_projection_index(root)
    entries = [
        build_entry(
            path,
            projection_index.get(
                path.relative_to(root).as_posix()
            ),
        )
        for path in sorted(
            rules_dir.glob("*.mdc"),
            key=lambda item: item.name,
        )
    ]
    true_count = sum(
        entry["always_apply"] is True
        for entry in entries
    )
    false_count = sum(
        entry["always_apply"] is False
        for entry in entries
    )
    null_count = len(entries) - true_count - false_count
    explicit_ids = sum(
        entry["id_source"] == "explicit"
        for entry in entries
    )
    state_counts = {
        state: sum(
            entry["migration_state"] == state
            for entry in entries
        )
        for state in (
            "legacy",
            "extracted",
            "hybrid",
            "contract_bound",
            "generated",
            "retired",
        )
    }
    always_bytes = sum(
        int(entry["context"]["measured_bytes"])
        for entry in entries
        if entry["always_apply"] is True
    )
    manifest = {
        "$schema": SCHEMA,
        "generated_utc": (
            _existing_generated_utc(root)
            or datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
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
            "deprecated_rules": sum(
                bool(entry["deprecated"])
                for entry in entries
            ),
            "legacy_rules": state_counts["legacy"],
            "extracted_rules": state_counts["extracted"],
            "hybrid_rules": state_counts["hybrid"],
            "contract_bound_rules": state_counts["contract_bound"],
            "generated_rules": state_counts["generated"],
            "retired_rules": state_counts["retired"],
            "always_apply_bytes": always_bytes,
            "always_apply_token_estimate": (always_bytes + 3) // 4,
            "unowned_normative_statements": None,
            "unresolved_contract_refs": 0,
            "unresolved_conflicts": 0,
            "projection_drift_count": 0,
            "context_budget_violations": sum(
                entry["context"].get("budget_status")
                == "exceeded"
                for entry in entries
            ),
        },
        "rules": entries,
    }
    canonical = json.dumps(
        entries,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    manifest["source_tree_digest"] = (
        f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    )
    existing_json = root / "rules" / "RULES-MANIFEST.json"
    if existing_json.is_file():
        try:
            existing = json.loads(
                existing_json.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError:
            existing = None
        if isinstance(existing, dict):
            if (
                _semantic_manifest_payload(existing)
                == _semantic_manifest_payload(manifest)
            ):
                existing_time = existing.get("generated_utc")
                if isinstance(existing_time, str):
                    manifest["generated_utc"] = existing_time
    return manifest
def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# Cursor governance rules manifest",
        "",
        f"Generated: `{manifest['generated_utc']}`.",
        "",
        "## Counts",
        "",
        "| Bucket | Count |",
        "|---|---:|",
        f"| Total MDC files | **{summary['total_mdc_files']}** |",
        f"| `alwaysApply: true` | **{summary['always_apply_true']}** |",
        f"| `alwaysApply: false` | **{summary['always_apply_false']}** |",
        f"| Legacy | **{summary['legacy_rules']}** |",
        f"| Extracted | **{summary['extracted_rules']}** |",
        f"| Hybrid | **{summary['hybrid_rules']}** |",
        f"| Contract-bound | **{summary['contract_bound_rules']}** |",
        f"| Generated | **{summary['generated_rules']}** |",
        f"| Retired | **{summary['retired_rules']}** |",
        f"| Always-on bytes | **{summary['always_apply_bytes']}** |",
        "",
        "## Rule index",
        "",
        "| File | ID | Domain | Activation | Migration | Owner | Binding | Bytes |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for entry in manifest["rules"]:
        binding = entry.get("binding")
        binding_id = (
            binding.get("id")
            if isinstance(binding, dict)
            else "—"
        )
        owner = entry["semantic_authority"]["owner"]
        lines.append(
            f"| `{entry['file']}` | `{entry['id']}` | "
            f"{entry['domain']} | {entry['activation']} | "
            f"{entry['migration_state']} | {owner} | "
            f"`{binding_id}` | "
            f"{entry['context']['measured_bytes']} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This manifest is generated and does not own governance semantics.",
            "- Generated rules project canonical contract clauses.",
            "- Legacy rule authority remains explicit migration debt.",
            "- Never edit manifest counters or projection metadata by hand.",
            "",
        ]
    )
    return "\n".join(lines)
def serialize_manifest(
    manifest: dict[str, Any],
) -> dict[str, str]:
    return {
        "json": json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        "yaml": yaml.safe_dump(
            manifest,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        ),
    }
def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        manifest = build_manifest(root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"RULE_MANIFEST_ERROR: {exc}", file=sys.stderr)
        return 2
    serialized = serialize_manifest(manifest)
    rules_dir = root / "rules"
    wrote = any(
        [
            write_if_changed(
                rules_dir / "RULES-MANIFEST.json",
                serialized["json"],
            ),
            write_if_changed(
                rules_dir / "RULES-MANIFEST.yaml",
                serialized["yaml"],
            ),
            write_if_changed(
                rules_dir / "RULES-MANIFEST.md",
                render_markdown(manifest),
            ),
        ]
    )
    label = "GENERATED" if wrote else "CURRENT"
    print(
        f"{label}: {manifest['summary']['total_mdc_files']} rules; "
        f"always={manifest['summary']['always_apply_true']}; "
        f"generated={manifest['summary']['generated_rules']}; "
        f"legacy={manifest['summary']['legacy_rules']}"
    )
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
