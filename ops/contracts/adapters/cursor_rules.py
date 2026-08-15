#!/usr/bin/env python3
"""Cursor rule adapter for the contract-first governance compiler."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from lib.rule_frontmatter import (  # noqa: E402
    activation_class,
    always_apply_is_true,
    normalize_globs,
    parse_rule,
)

BINDING_SCHEMA = "canonical.schema.rule_activation_binding.v1"
BINDING_ID_RE = re.compile(r"^RULE\.CURSOR\.[A-Z0-9_]+\.\d{3}$")
RULE_ID_RE = re.compile(r"^l9\.rule\.[a-z0-9._-]+$")
OUTPUT_RE = re.compile(r"^rules/\d{2}-[a-z0-9][a-z0-9-]*\.mdc$")


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe loader that rejects duplicate YAML mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            line = key_node.start_mark.line + 1
            raise ValueError(f"duplicate YAML key {key!r} at line {line}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class CursorRule:
    path: Path
    relative_path: str
    rule_id: str
    version: str | None
    description: str
    scope: str
    domain: str
    activation: str
    always_apply: bool
    globs: tuple[str, ...]
    authority: str
    context_cost: str
    metadata: dict[str, Any]
    body: str
    text: str
    content_digest: str
    first_heading: str


@dataclass(frozen=True)
class RuleBinding:
    path: Path
    relative_path: str
    data: dict[str, Any]
    binding_id: str
    output_path: str
    migration_state: str
    digest: str


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def stable_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def load_yaml_unique(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=UniqueKeyLoader)


def first_heading(body: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return ""


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", ".", value.casefold()).strip(".")
    return cleaned or "unnamed"


def infer_domain(filename: str, description: str) -> str:
    sample = f"{filename} {description}".casefold()
    groups: tuple[tuple[str, tuple[str, ...]], ...] = (
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
    for domain, needles in groups:
        if any(needle in sample for needle in needles):
            return domain
    return "general"


def normalize_activation(metadata: dict[str, Any], globs: list[str] | None) -> str:
    explicit = str(metadata.get("activation") or "").strip()
    if explicit:
        return explicit
    native = activation_class(metadata, globs)
    if native == "paths":
        return "auto_attached"
    return native


def parse_cursor_rule(root: Path, path: Path) -> CursorRule:
    parsed = parse_rule(path)
    text = path.read_text(encoding="utf-8")
    raw = text.encode("utf-8")
    metadata = dict(parsed.metadata)
    globs = normalize_globs(metadata.get("globs")) or []
    description = str(metadata.get("description") or "").strip()
    rule_id = str(metadata.get("id") or f"l9.rule.{slug(path.stem)}")
    activation = normalize_activation(metadata, globs)
    return CursorRule(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        rule_id=rule_id,
        version=(str(metadata["version"]) if metadata.get("version") is not None else None),
        description=description,
        scope=str(metadata.get("scope") or "global"),
        domain=str(metadata.get("domain") or infer_domain(path.name, description)),
        activation=activation,
        always_apply=always_apply_is_true(metadata),
        globs=tuple(globs),
        authority=str(metadata.get("authority") or "compatibility"),
        context_cost=str(metadata.get("context_cost") or "unknown"),
        metadata=metadata,
        body=parsed.body,
        text=text,
        content_digest=f"sha256:{sha256_bytes(raw)}",
        first_heading=first_heading(parsed.body),
    )


def discover_cursor_rules(root: Path = ROOT) -> list[CursorRule]:
    rules_dir = root / "rules"
    if not rules_dir.is_dir():
        raise ValueError(f"rules directory not found: {rules_dir}")
    return [
        parse_cursor_rule(root, path)
        for path in sorted(rules_dir.glob("*.mdc"), key=lambda item: item.name)
    ]


def _binding_digest(data: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(data))
    integrity = normalized.setdefault("integrity", {})
    if isinstance(integrity, dict):
        integrity["binding_digest"] = None
    return stable_digest(normalized)


def load_rule_binding(root: Path, path: Path) -> RuleBinding:
    loaded = load_yaml_unique(path)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: binding must be a YAML mapping")
    if loaded.get("schema_ref") != BINDING_SCHEMA:
        raise ValueError(f"{path}: schema_ref must equal {BINDING_SCHEMA!r}")
    identity = loaded.get("binding_identity")
    target = loaded.get("target")
    lifecycle = loaded.get("lifecycle")
    if not isinstance(identity, dict):
        raise ValueError(f"{path}: missing binding_identity mapping")
    if not isinstance(target, dict):
        raise ValueError(f"{path}: missing target mapping")
    if not isinstance(lifecycle, dict):
        raise ValueError(f"{path}: missing lifecycle mapping")
    binding_id = str(identity.get("binding_id") or "")
    output_path = str(target.get("output_path") or "")
    migration_state = str(lifecycle.get("migration_state") or "")
    digest = _binding_digest(loaded)
    declared = loaded.get("integrity", {}).get("binding_digest")
    if declared not in {None, "", digest, f"sha256:{digest}"}:
        raise ValueError(
            f"{path}: binding digest mismatch: declared {declared!r}, computed sha256:{digest}"
        )
    return RuleBinding(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        data=loaded,
        binding_id=binding_id,
        output_path=output_path,
        migration_state=migration_state,
        digest=digest,
    )


def discover_rule_bindings(
    root: Path = ROOT,
    binding_dir: Path | None = None,
) -> list[RuleBinding]:
    directory = binding_dir or root / "contracts" / "projections" / "rules"
    if not directory.exists():
        return []
    bindings = [
        load_rule_binding(root, path)
        for path in sorted(directory.glob("*.yaml"), key=lambda item: item.name)
    ]
    return bindings


def binding_contract_refs(binding: RuleBinding) -> list[dict[str, Any]]:
    raw = binding.data.get("contract_bindings")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def binding_activation(binding: RuleBinding) -> dict[str, Any]:
    raw = binding.data.get("activation")
    return dict(raw) if isinstance(raw, dict) else {}


def binding_rule_identity(binding: RuleBinding) -> dict[str, Any]:
    raw = binding.data.get("rule_identity")
    return dict(raw) if isinstance(raw, dict) else {}


def binding_render_config(binding: RuleBinding) -> dict[str, Any]:
    raw = binding.data.get("render")
    return dict(raw) if isinstance(raw, dict) else {}


def binding_guidance(binding: RuleBinding) -> dict[str, Any]:
    raw = binding.data.get("guidance")
    return dict(raw) if isinstance(raw, dict) else {}


def static_glob_prefix(pattern: str) -> str:
    special = set("*?[{")
    position = len(pattern)
    for char in special:
        index = pattern.find(char)
        if index >= 0:
            position = min(position, index)
    return pattern[:position].rstrip("/")


def glob_is_narrower_or_equal(candidate: str, owner: str) -> bool:
    """Conservative approximation of glob subset relation.
    Ambiguous cases intentionally return False.
    """
    candidate = candidate.strip()
    owner = owner.strip()
    if candidate == owner:
        return True
    if owner in {"*", "**", "**/*"}:
        return True
    owner_prefix = static_glob_prefix(owner)
    candidate_prefix = static_glob_prefix(candidate)
    if owner.endswith("/**") and owner_prefix:
        return candidate_prefix.startswith(owner_prefix)
    if owner.startswith("**/*."):
        suffix = owner.removeprefix("**/*")
        return candidate.endswith(suffix)
    if owner.startswith("**/") and candidate.endswith(owner[3:]):
        return True
    if owner_prefix and candidate_prefix.startswith(owner_prefix):
        owner_suffix = owner[len(owner_prefix) :]
        candidate_suffix = candidate[len(candidate_prefix) :]
        if owner_suffix == candidate_suffix:
            return True
    return False


def globs_may_overlap(left: Iterable[str], right: Iterable[str]) -> bool:
    left_items = tuple(left)
    right_items = tuple(right)
    if not left_items or not right_items:
        return True
    for left_pattern in left_items:
        if left_pattern.startswith("!"):
            continue
        for right_pattern in right_items:
            if right_pattern.startswith("!"):
                continue
            if glob_is_narrower_or_equal(left_pattern, right_pattern) or glob_is_narrower_or_equal(
                right_pattern, left_pattern
            ):
                return True
    return False


def activations_may_overlap(
    left: RuleBinding,
    right: RuleBinding,
) -> bool:
    left_activation = binding_activation(left)
    right_activation = binding_activation(right)
    left_mode = str(left_activation.get("mode") or "")
    right_mode = str(right_activation.get("mode") or "")
    if "always" in {left_mode, right_mode}:
        return True
    if left_mode in {"agent_requested", "manual"}:
        return True
    if right_mode in {"agent_requested", "manual"}:
        return True
    left_globs = left_activation.get("globs") or []
    right_globs = right_activation.get("globs") or []
    if not isinstance(left_globs, list) or not isinstance(right_globs, list):
        return True
    return globs_may_overlap(
        (str(item) for item in left_globs),
        (str(item) for item in right_globs),
    )


__all__ = [
    "BINDING_ID_RE",
    "BINDING_SCHEMA",
    "OUTPUT_RE",
    "ROOT",
    "RULE_ID_RE",
    "CursorRule",
    "RuleBinding",
    "activations_may_overlap",
    "binding_activation",
    "binding_contract_refs",
    "binding_guidance",
    "binding_render_config",
    "binding_rule_identity",
    "canonical_json_bytes",
    "discover_cursor_rules",
    "discover_rule_bindings",
    "glob_is_narrower_or_equal",
    "globs_may_overlap",
    "load_rule_binding",
    "load_yaml_unique",
    "parse_cursor_rule",
    "sha256_bytes",
    "stable_digest",
]
