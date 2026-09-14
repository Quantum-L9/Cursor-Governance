#!/usr/bin/env python3
"""Resolve canonical governance contracts for Cursor rule bindings."""
from __future__ import annotations
import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml
ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = Path(__file__).resolve().parent / "adapters"
if str(ADAPTERS) not in sys.path:
    sys.path.insert(0, str(ADAPTERS))
from cursor_rules import (  # noqa: E402
    RuleBinding,
    binding_contract_refs,
    load_yaml_unique,
    stable_digest,
)
CONTRACT_ID_RE = re.compile(
    r"^[A-Z][A-Z0-9]*(?:\.[A-Z][A-Z0-9_]*)+\.\d{3}$"
)
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REGISTRY_CANDIDATES = (
    Path("contracts") / "registry.yaml",
    Path("generated") / "governance" / "contract-registry.yaml",
)
CONTRACT_SCAN_EXCLUDES = {
    "schemas",
    "projections",
    "extraction",
}
CONFLICTING_EFFECTS = {
    ("permit", "prohibit"),
    ("prohibit", "permit"),
    ("require", "prohibit"),
    ("prohibit", "require"),
    ("require", "stop"),
    ("stop", "require"),
    ("permit", "stop"),
    ("stop", "permit"),
}
@dataclass(frozen=True)
class ContractRecord:
    contract_id: str
    version: str
    status: str
    path: Path
    relative_path: str
    digest: str
    document: dict[str, Any]
    clauses: dict[str, dict[str, Any]]
@dataclass(frozen=True)
class ContractIndex:
    records: dict[str, ContractRecord]
    source: str
def parse_semver(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid semantic version {value!r}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]
def version_matches(version: str, constraint: str) -> bool:
    parsed = parse_semver(version)
    constraint = constraint.strip()
    if constraint in {"", "*"}:
        return True
    if SEMVER_RE.fullmatch(constraint):
        return parsed == parse_semver(constraint)
    if constraint.startswith("^"):
        raw = constraint[1:]
        parts = raw.split(".")
        if not 1 <= len(parts) <= 3:
            raise ValueError(f"unsupported version constraint {constraint!r}")
        expected = tuple(int(part) for part in parts)
        if parsed[0] != expected[0]:
            return False
        if len(expected) >= 2 and parsed[1] < expected[1]:
            return False
        if (
            len(expected) == 3
            and parsed[1] == expected[1]
            and parsed[2] < expected[2]
        ):
            return False
        return True
    raise ValueError(
        f"unsupported version constraint {constraint!r}; "
        "use exact semver, caret major/minor/patch, or '*'"
    )
def canonical_contract_digest(document: dict[str, Any]) -> str:
    normalized = copy.deepcopy(document)
    integrity = normalized.get("integrity")
    if isinstance(integrity, dict):
        integrity["content_digest"] = None
    return stable_digest(normalized)
def _contract_from_document(
    root: Path,
    path: Path,
    document: dict[str, Any],
) -> ContractRecord:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: contract missing metadata mapping")
    contract_id = str(metadata.get("contract_id") or "")
    version = str(metadata.get("version") or "")
    status = str(metadata.get("status") or "")
    if not CONTRACT_ID_RE.fullmatch(contract_id):
        raise ValueError(f"{path}: invalid contract_id {contract_id!r}")
    parse_semver(version)
    raw_clauses = document.get("normative_clauses") or []
    if not isinstance(raw_clauses, list):
        raise ValueError(f"{path}: normative_clauses must be a list")
    clauses: dict[str, dict[str, Any]] = {}
    for index, clause in enumerate(raw_clauses):
        if not isinstance(clause, dict):
            raise ValueError(
                f"{path}: normative_clauses[{index}] must be a mapping"
            )
        clause_id = str(clause.get("clause_id") or "")
        if not clause_id:
            raise ValueError(
                f"{path}: normative_clauses[{index}] missing clause_id"
            )
        if clause_id in clauses:
            raise ValueError(f"{path}: duplicate clause_id {clause_id!r}")
        clauses[clause_id] = clause
    computed = canonical_contract_digest(document)
    declared = (
        document.get("integrity", {}).get("content_digest")
        if isinstance(document.get("integrity"), dict)
        else None
    )
    if declared not in {None, "", computed, f"sha256:{computed}"}:
        raise ValueError(
            f"{path}: contract content digest mismatch: "
            f"declared={declared!r}, computed=sha256:{computed}"
        )
    return ContractRecord(
        contract_id=contract_id,
        version=version,
        status=status,
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        digest=computed,
        document=document,
        clauses=clauses,
    )
def _scan_contracts(root: Path) -> ContractIndex:
    contract_root = root / "contracts"
    records: dict[str, ContractRecord] = {}
    if not contract_root.is_dir():
        raise ValueError(
            "contracts/ is unavailable; the rule compiler requires the "
            "assumed-landed canonical contract plane"
        )
    for path in sorted(contract_root.rglob("*.yaml")):
        relative = path.relative_to(contract_root)
        if relative.parts and relative.parts[0] in CONTRACT_SCAN_EXCLUDES:
            continue
        if path.name == "registry.yaml":
            continue
        loaded = load_yaml_unique(path)
        if not isinstance(loaded, dict):
            continue
        metadata = loaded.get("metadata")
        if not isinstance(metadata, dict) or not metadata.get("contract_id"):
            continue
        record = _contract_from_document(root, path, loaded)
        if record.contract_id in records:
            prior = records[record.contract_id]
            raise ValueError(
                f"duplicate contract identity {record.contract_id}: "
                f"{prior.relative_path}, {record.relative_path}"
            )
        records[record.contract_id] = record
    return ContractIndex(records=records, source="contract_tree_scan")
def _load_registry(root: Path, path: Path) -> ContractIndex:
    loaded = load_yaml_unique(path)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: registry must be a mapping")
    raw_entries = loaded.get("contracts")
    if not isinstance(raw_entries, list):
        raise ValueError(f"{path}: registry contracts must be a list")
    records: dict[str, ContractRecord] = {}
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: contracts[{index}] must be a mapping")
        contract_id = str(entry.get("contract_id") or "")
        relative_path = str(entry.get("path") or "")
        if not relative_path:
            raise ValueError(
                f"{path}: registry entry {contract_id!r} missing path"
            )
        contract_path = root / relative_path
        if not contract_path.is_file():
            raise ValueError(
                f"{path}: registry path does not exist: {relative_path}"
            )
        document = load_yaml_unique(contract_path)
        if not isinstance(document, dict):
            raise ValueError(f"{contract_path}: contract must be a mapping")
        record = _contract_from_document(root, contract_path, document)
        if record.contract_id != contract_id:
            raise ValueError(
                f"{path}: registry identity {contract_id!r} disagrees with "
                f"{record.relative_path} identity {record.contract_id!r}"
            )
        registry_version = str(entry.get("version") or record.version)
        registry_status = str(entry.get("status") or record.status)
        if registry_version != record.version:
            raise ValueError(
                f"{path}: registry version mismatch for {contract_id}"
            )
        if registry_status != record.status:
            raise ValueError(
                f"{path}: registry status mismatch for {contract_id}"
            )
        registry_digest = str(entry.get("digest") or "")
        if registry_digest and registry_digest not in {
            record.digest,
            f"sha256:{record.digest}",
        }:
            raise ValueError(
                f"{path}: registry digest mismatch for {contract_id}"
            )
        if contract_id in records:
            raise ValueError(f"{path}: duplicate registry ID {contract_id}")
        records[contract_id] = record
    return ContractIndex(
        records=records,
        source=path.relative_to(root).as_posix(),
    )
def load_contract_index(
    root: Path = ROOT,
    registry_path: Path | None = None,
) -> ContractIndex:
    if registry_path is not None:
        path = registry_path if registry_path.is_absolute() else root / registry_path
        return _load_registry(root, path)
    for relative in REGISTRY_CANDIDATES:
        candidate = root / relative
        if candidate.is_file():
            return _load_registry(root, candidate)
    return _scan_contracts(root)
def _binding_scope(binding_ref: dict[str, Any]) -> dict[str, Any]:
    raw = binding_ref.get("scope_narrowing")
    return dict(raw) if isinstance(raw, dict) else {}
def _scope_paths(record: ContractRecord) -> list[str]:
    scope = record.document.get("scope")
    if not isinstance(scope, dict):
        return []
    paths = scope.get("paths")
    if not isinstance(paths, list):
        return []
    return [str(item) for item in paths]
def resolve_binding(
    binding: RuleBinding,
    contract_index: ContractIndex,
) -> dict[str, Any]:
    resolved_contracts: list[dict[str, Any]] = []
    directives: list[dict[str, Any]] = []
    refs = binding_contract_refs(binding)
    for ref in refs:
        contract_id = str(ref.get("contract_id") or "")
        constraint = str(ref.get("version_constraint") or "*")
        clause_ids = ref.get("clauses")
        record = contract_index.records.get(contract_id)
        if record is None:
            raise ValueError(
                f"{binding.relative_path}: unresolved contract {contract_id!r}"
            )
        if record.status != "active":
            raise ValueError(
                f"{binding.relative_path}: contract {contract_id} is "
                f"{record.status!r}, expected 'active'"
            )
        if not version_matches(record.version, constraint):
            raise ValueError(
                f"{binding.relative_path}: {contract_id}@{record.version} "
                f"does not satisfy {constraint!r}"
            )
        if not isinstance(clause_ids, list) or not clause_ids:
            raise ValueError(
                f"{binding.relative_path}: {contract_id} requires explicit clauses"
            )
        selected: list[str] = []
        for raw_clause_id in clause_ids:
            clause_id = str(raw_clause_id)
            clause = record.clauses.get(clause_id)
            if clause is None:
                raise ValueError(
                    f"{binding.relative_path}: {contract_id} has no clause "
                    f"{clause_id!r}"
                )
            selected.append(clause_id)
            directive = {
                "contract_id": contract_id,
                "contract_version": record.version,
                "contract_digest": record.digest,
                "clause_id": clause_id,
                "effect": str(clause.get("effect") or ""),
                "subject": str(clause.get("subject") or ""),
                "action": str(clause.get("action") or ""),
                "object": clause.get("object"),
                "conditions": list(clause.get("conditions") or []),
                "exceptions": list(clause.get("exceptions") or []),
                "parameters": dict(clause.get("parameters") or {}),
            }
            directives.append(directive)
        resolved_contracts.append(
            {
                "contract_id": contract_id,
                "version": record.version,
                "digest": record.digest,
                "path": record.relative_path,
                "clauses": selected,
                "contract_scope_paths": _scope_paths(record),
                "scope_narrowing": _binding_scope(ref),
            }
        )
    conflicts = detect_directive_conflicts(directives)
    if conflicts:
        rendered = "; ".join(
            f"{item['left']} <> {item['right']}" for item in conflicts
        )
        raise ValueError(
            f"{binding.relative_path}: conflicting projected clauses: {rendered}"
        )
    bundle_payload = {
        "binding_id": binding.binding_id,
        "binding_digest": binding.digest,
        "contracts": resolved_contracts,
        "directives": directives,
        "activation": binding.data.get("activation"),
    }
    return {
        **bundle_payload,
        "output_path": binding.output_path,
        "rule_identity": dict(binding.data.get("rule_identity") or {}),
        "guidance": dict(binding.data.get("guidance") or {}),
        "render": dict(binding.data.get("render") or {}),
        "migration_state": binding.migration_state,
        "bundle_digest": stable_digest(bundle_payload),
    }
def directive_key(directive: dict[str, Any]) -> tuple[str, str, str]:
    def normalize(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip().casefold())
    return (
        normalize(directive.get("subject")),
        normalize(directive.get("action")),
        normalize(directive.get("object")),
    )
def directives_conflict(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    if (
        left.get("contract_id") == right.get("contract_id")
        and left.get("clause_id") == right.get("clause_id")
    ):
        return False
    if directive_key(left) != directive_key(right):
        return False
    pair = (
        str(left.get("effect") or ""),
        str(right.get("effect") or ""),
    )
    return pair in CONFLICTING_EFFECTS
def detect_directive_conflicts(
    directives: list[dict[str, Any]],
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    for index, left in enumerate(directives):
        for right in directives[index + 1 :]:
            if not directives_conflict(left, right):
                continue
            conflicts.append(
                {
                    "left": (
                        f"{left['contract_id']}:{left['clause_id']}"
                    ),
                    "right": (
                        f"{right['contract_id']}:{right['clause_id']}"
                    ),
                }
            )
    return conflicts
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("binding", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    return parser.parse_args()
def main() -> int:
    args = _parse_args()
    adapters = Path(__file__).resolve().parent / "adapters"
    if str(adapters) not in sys.path:
        sys.path.insert(0, str(adapters))
    from cursor_rules import load_rule_binding
    try:
        root = args.root.resolve()
        path = args.binding if args.binding.is_absolute() else root / args.binding
        binding = load_rule_binding(root, path)
        index = load_contract_index(root, args.registry)
        resolution = resolve_binding(binding, index)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"RULE_RESOLUTION_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(resolution, indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
