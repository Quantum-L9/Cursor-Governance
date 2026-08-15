#!/usr/bin/env python3
"""Detect normative skill doctrine that lacks an authoritative owner.
Ownership is explicit. This validator never infers ownership because a contract
name happens to appear nearby.
Canonical annotation syntax:
    <!-- l9-doctrine: contract=GIT.PUBLISH.001 -->
    <!-- l9-doctrine: local_contract=SKILL.FORGE.NORMALIZE.001 -->
    <!-- l9-doctrine: exception=quotation; reason="Historical quotation only" -->
Annotations:
- MUST be standalone HTML comments;
- apply only to the next extracted source block;
- may not span headings or unrelated text;
- may not contain unknown fields;
- may not declare multiple ownership mechanisms;
- must resolve active contracts through the generated contract registry;
- cannot use a draft/deprecated/retired contract as active ownership;
- cannot broadly suppress a file or section.
The tool reports existing hidden doctrine. The ratchet validator is responsible
for grandfathering legacy debt while preventing new debt.
Exit codes:
0
    Analysis completed. Hidden doctrine may exist.
1
    Used only with --fail-on-unowned.
2
    Integrity/configuration/annotation failure.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from cluster_doctrine import semantic_fingerprint
from extract_doctrine import (
    CONTRACT_ID_RE,
    ROOT,
    Finding,
    extract_repository,
    load_serialized,
    load_yaml_unique,
    serialize_output,
    stable_digest,
)

DETECTOR_VERSION = "1.0.0"
MARKER_RE = re.compile(
    r"^\s*<!--\s*l9-doctrine:\s*(?P<body>.*?)\s*-->\s*$",
    re.IGNORECASE,
)
MARKER_ANYWHERE_RE = re.compile(
    r"<!--\s*l9-doctrine:",
    re.IGNORECASE,
)
ALLOWED_MARKER_KEYS = {
    "contract",
    "local_contract",
    "exception",
    "reason",
    "scope",
}
OWNERSHIP_KEYS = {
    "contract",
    "local_contract",
    "exception",
}
ALLOWED_EXCEPTION_CLASSES = {
    "explanatory_example",
    "quotation",
    "historical_reference",
    "non_normative_description",
    "test_fixture",
    "local_algorithm_comment",
}
CRITICAL_EXCEPTION_CLASSES = {
    "quotation",
    "historical_reference",
    "test_fixture",
}
REGISTRY_CANDIDATES = (
    Path("contracts") / "registry.yaml",
    Path("generated") / "governance" / "contract-registry.yaml",
    Path("ops") / "generated" / "contract-registry.yaml",
)
HARD_STRENGTHS = {
    "hard_normative",
    "conditional_normative",
}
CONTRACTABLE_KINDS = {
    "invariant",
    "policy",
    "capability",
    "workflow",
    "evidence",
    "routing_activation",
    "unknown",
}


@dataclass(frozen=True)
class Marker:
    path: str
    line: int
    fields: dict[str, str]
    raw: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "fields": dict(self.fields),
            "raw": self.raw,
        }


@dataclass(frozen=True)
class Registry:
    path: str | None
    contracts: dict[str, dict[str, Any]]


def doctrine_fingerprint(record: dict[str, Any]) -> str:
    """Fingerprint debt independently of its line number.
    Repeated copies of the same doctrine intentionally share a fingerprint;
    the ratchet tracks occurrence count separately.
    """
    source = record.get("source", {})
    classification = record.get("classification", {})
    semantics = record.get("normalized_semantics", {})
    normalized_text = re.sub(
        r"\s+",
        " ",
        str(source.get("exact_text", "")).strip().casefold(),
    )
    return stable_digest(
        {
            "text": normalized_text,
            "kind": classification.get("candidate_kind"),
            "strength": classification.get("doctrine_strength"),
            "sharedness": classification.get("sharedness"),
            "effect": semantics.get("effect"),
        }
    )


def _split_semicolon_fields(value: str) -> list[str]:
    """Split marker fields on unquoted semicolons."""
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for character in value:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if character == "\\":
            current.append(character)
            escaped = True
            continue
        if quote is not None:
            current.append(character)
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            current.append(character)
            continue
        if character == ";":
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(character)
    if quote is not None:
        raise ValueError("unterminated quoted annotation value")
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def _decode_marker_value(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0] in {"'", '"'}:
        parsed = shlex.split(value)
        if len(parsed) != 1:
            raise ValueError(f"invalid quoted annotation value: {value!r}")
        return parsed[0]
    return value


def parse_marker_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in _split_semicolon_fields(body):
        if "=" not in part:
            raise ValueError(f"annotation field must use key=value syntax: {part!r}")
        key, raw_value = part.split("=", 1)
        key = key.strip().casefold()
        value = _decode_marker_value(raw_value)
        if key not in ALLOWED_MARKER_KEYS:
            raise ValueError(f"unknown annotation field {key!r}")
        if key in fields:
            raise ValueError(f"duplicate annotation field {key!r}")
        fields[key] = value
    owners = OWNERSHIP_KEYS & set(fields)
    if len(owners) != 1:
        raise ValueError(
            "annotation must contain exactly one of contract, local_contract, or exception"
        )
    scope = fields.get("scope", "next")
    if scope != "next":
        raise ValueError("only scope=next is supported; broad doctrine suppressions are forbidden")
    fields["scope"] = scope
    if "exception" in fields:
        exception = fields["exception"]
        if exception not in ALLOWED_EXCEPTION_CLASSES:
            raise ValueError(
                f"unsupported exception class {exception!r}; expected one of "
                f"{sorted(ALLOWED_EXCEPTION_CLASSES)}"
            )
        reason = fields.get("reason", "").strip()
        if len(reason) < 12:
            raise ValueError(
                "normative exception requires a specific reason of at least 12 characters"
            )
    elif "reason" in fields:
        raise ValueError("reason is valid only for an explicit normative exception")
    for key in ("contract", "local_contract"):
        if key in fields and not CONTRACT_ID_RE.fullmatch(fields[key]):
            raise ValueError(
                f"{key} does not satisfy canonical contract ID grammar: {fields[key]!r}"
            )
    return fields


def parse_markers(
    *,
    root: Path,
    paths: set[str],
) -> tuple[list[Marker], list[Finding]]:
    markers: list[Marker] = []
    findings: list[Finding] = []
    for relative in sorted(paths, key=str.casefold):
        path = root / relative
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(
                Finding(
                    code="ANNOTATION_SOURCE_READ_FAILED",
                    severity="error",
                    path=relative,
                    message=str(exc),
                )
            )
            continue
        for line_number, line in enumerate(lines, start=1):
            if not MARKER_ANYWHERE_RE.search(line):
                continue
            match = MARKER_RE.fullmatch(line)
            if match is None:
                findings.append(
                    Finding(
                        code="ANNOTATION_NOT_STANDALONE",
                        severity="error",
                        path=relative,
                        line=line_number,
                        message=(
                            "l9-doctrine annotation must occupy a standalone HTML-comment line"
                        ),
                    )
                )
                continue
            try:
                fields = parse_marker_fields(match.group("body"))
            except ValueError as exc:
                findings.append(
                    Finding(
                        code="ANNOTATION_INVALID",
                        severity="error",
                        path=relative,
                        line=line_number,
                        message=str(exc),
                    )
                )
                continue
            markers.append(
                Marker(
                    path=relative,
                    line=line_number,
                    fields=fields,
                    raw=line.strip(),
                )
            )
    markers.sort(key=lambda marker: (marker.path.casefold(), marker.line))
    return markers, findings


def _is_binding_barrier(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("<!--") and stripped.endswith("-->"):
        return False
    if re.match(r"^#{1,6}\s+", stripped):
        return True
    return True


def bind_markers(
    *,
    root: Path,
    records: list[dict[str, Any]],
    markers: list[Marker],
) -> tuple[dict[str, Marker], list[Finding]]:
    """Bind each marker to exactly one immediately following extraction record."""
    records_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        path = str(record.get("source", {}).get("path", ""))
        records_by_path[path].append(record)
    for path_records in records_by_path.values():
        path_records.sort(key=lambda record: int(record.get("source", {}).get("line_start", 0)))
    bindings: dict[str, Marker] = {}
    findings: list[Finding] = []
    used_markers: set[tuple[str, int]] = set()
    text_cache: dict[str, list[str]] = {}
    for marker in markers:
        path_records = records_by_path.get(marker.path, [])
        if marker.path not in text_cache:
            try:
                text_cache[marker.path] = (
                    (root / marker.path).read_text(encoding="utf-8").splitlines()
                )
            except (OSError, UnicodeDecodeError) as exc:
                findings.append(
                    Finding(
                        code="ANNOTATION_SOURCE_READ_FAILED",
                        severity="error",
                        path=marker.path,
                        line=marker.line,
                        message=str(exc),
                    )
                )
                continue
        lines = text_cache[marker.path]
        target: dict[str, Any] | None = None
        for record in path_records:
            start = int(record.get("source", {}).get("line_start", 0))
            if start <= marker.line:
                continue
            between = lines[marker.line : start - 1]
            if any(_is_binding_barrier(line) for line in between):
                break
            target = record
            break
        if target is None:
            findings.append(
                Finding(
                    code="ANNOTATION_ORPHANED",
                    severity="error",
                    path=marker.path,
                    line=marker.line,
                    message=(
                        "annotation does not bind to the immediately following doctrine candidate"
                    ),
                )
            )
            continue
        extraction_id = str(target["extraction_identity"]["extraction_id"])
        if extraction_id in bindings:
            previous = bindings[extraction_id]
            findings.append(
                Finding(
                    code="ANNOTATION_MULTIPLE_OWNERS",
                    severity="error",
                    path=marker.path,
                    line=marker.line,
                    message=(
                        f"candidate {extraction_id} already has annotation at line {previous.line}"
                    ),
                )
            )
            continue
        bindings[extraction_id] = marker
        used_markers.add((marker.path, marker.line))
    for marker in markers:
        key = (marker.path, marker.line)
        if key in used_markers:
            continue
        if any(
            finding.path == marker.path
            and finding.line == marker.line
            and finding.code.startswith("ANNOTATION_")
            for finding in findings
        ):
            continue
        findings.append(
            Finding(
                code="ANNOTATION_UNUSED",
                severity="error",
                path=marker.path,
                line=marker.line,
                message="annotation was parsed but did not bind to a candidate",
            )
        )
    return bindings, findings


def _discover_registry_path(
    root: Path,
    explicit: Path | None,
) -> Path | None:
    if explicit is not None:
        path = explicit if explicit.is_absolute() else root / explicit
        return path
    for relative in REGISTRY_CANDIDATES:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def load_contract_registry(
    *,
    root: Path,
    explicit: Path | None = None,
) -> Registry:
    path = _discover_registry_path(root, explicit)
    if path is None:
        return Registry(path=None, contracts={})
    if not path.is_file():
        raise ValueError(f"contract registry does not exist: {path}")
    data = load_yaml_unique(path)
    if not isinstance(data, dict):
        raise ValueError("contract registry must contain a mapping")
    entries = data.get("contracts")
    if not isinstance(entries, list):
        raise ValueError("contract registry must contain a contracts list")
    contracts: dict[str, dict[str, Any]] = {}
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"contract registry entry {index} is not a mapping")
        contract_id = raw_entry.get("contract_id")
        if not isinstance(contract_id, str):
            raise ValueError(f"contract registry entry {index} has no contract_id")
        if not CONTRACT_ID_RE.fullmatch(contract_id):
            raise ValueError(f"contract registry contains invalid contract_id {contract_id!r}")
        if contract_id in contracts:
            raise ValueError(f"contract registry contains duplicate active identity {contract_id}")
        contracts[contract_id] = raw_entry
    return Registry(
        path=path.relative_to(root).as_posix(),
        contracts=contracts,
    )


def _is_normative_candidate(record: dict[str, Any]) -> bool:
    classification = record.get("classification", {})
    signals = record.get("signals", {})
    kind = classification.get("candidate_kind")
    strength = classification.get("doctrine_strength")
    if kind in {"example", "rationale", "obsolete"}:
        return False
    if strength in HARD_STRENGTHS:
        return True
    if kind in {
        "routing_activation",
        "capability",
        "evidence",
    }:
        return True
    if signals.get("authority_tokens"):
        return True
    return False


def _debt_class(record: dict[str, Any]) -> str:
    classification = record.get("classification", {})
    kind = classification.get("candidate_kind")
    sharedness = classification.get("sharedness")
    if kind == "routing_activation":
        return "routing_activation"
    if kind == "capability":
        return "capability_claim"
    if kind == "evidence":
        return "evidence_claim"
    if sharedness == "skill_local":
        return "skill_local_contract"
    if sharedness in {"repository_global", "domain_shared"}:
        return "shared_contract"
    return "unknown_normative"


def _skill_name_from_path(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return "_skills_root"


def _validate_active_contract(
    *,
    marker: Marker,
    key: str,
    registry: Registry,
    skill_name: str,
) -> tuple[bool, str]:
    contract_id = marker.fields[key]
    entry = registry.contracts.get(contract_id)
    if entry is None:
        if registry.path is None:
            return False, (f"{contract_id} cannot resolve because no contract registry exists")
        return False, f"{contract_id} is absent from {registry.path}"
    status = entry.get("status")
    if status != "active":
        return False, (
            f"{contract_id} has status {status!r}; only active contracts own active doctrine"
        )
    if key == "local_contract":
        authority_tier = entry.get("authority_tier")
        if authority_tier != "skill_local":
            return False, (
                f"{contract_id} is referenced as skill-local but has authority "
                f"tier {authority_tier!r}"
            )
        contract_path = str(entry.get("path", ""))
        expected_prefix = f"contracts/skills/{skill_name}/"
        if contract_path and not contract_path.startswith(expected_prefix):
            return False, (
                f"{contract_id} is skill-local but path {contract_path!r} "
                f"is outside {expected_prefix!r}"
            )
    return True, f"resolved active contract {contract_id}"


def analyze_ownership(
    *,
    record: dict[str, Any],
    marker: Marker | None,
    registry: Registry,
) -> dict[str, Any]:
    extraction_id = str(record["extraction_identity"]["extraction_id"])
    source = record.get("source", {})
    classification = record.get("classification", {})
    normative = _is_normative_candidate(record)
    base = {
        "extraction_id": extraction_id,
        "doctrine_fingerprint": doctrine_fingerprint(record),
        "semantic_fingerprint": semantic_fingerprint(record),
        "path": source.get("path"),
        "line_start": source.get("line_start"),
        "skill": _skill_name_from_path(str(source.get("path", ""))),
        "normative_candidate": normative,
        "debt_class": _debt_class(record) if normative else "none",
        "candidate_kind": classification.get("candidate_kind"),
        "doctrine_strength": classification.get("doctrine_strength"),
        "sharedness": classification.get("sharedness"),
        "risk": classification.get("risk"),
        "annotation": marker.as_dict() if marker is not None else None,
    }
    if not normative:
        return {
            **base,
            "status": "not_normative",
            "owned": True,
            "debt": False,
            "owner_ref": None,
            "reason": "candidate is rationale/example/obsolete or non-normative",
        }
    if marker is None:
        return {
            **base,
            "status": "unowned",
            "owned": False,
            "debt": True,
            "owner_ref": None,
            "reason": "normative candidate has no explicit ownership annotation",
        }
    if "exception" in marker.fields:
        exception = marker.fields["exception"]
        if classification.get("risk") == "critical" and exception not in CRITICAL_EXCEPTION_CLASSES:
            return {
                **base,
                "status": "invalid_exception",
                "owned": False,
                "debt": True,
                "owner_ref": None,
                "reason": (
                    "critical-risk doctrine may only use quotation, "
                    "historical_reference, or test_fixture exceptions"
                ),
            }
        return {
            **base,
            "status": "valid_exception",
            "owned": True,
            "debt": False,
            "owner_ref": f"exception:{exception}",
            "reason": marker.fields["reason"],
        }
    key = "local_contract" if "local_contract" in marker.fields else "contract"
    skill_name = _skill_name_from_path(str(source.get("path", "")))
    valid, reason = _validate_active_contract(
        marker=marker,
        key=key,
        registry=registry,
        skill_name=skill_name,
    )
    if not valid:
        return {
            **base,
            "status": "unresolved_contract_ref",
            "owned": False,
            "debt": True,
            "owner_ref": marker.fields[key],
            "reason": reason,
        }
    return {
        **base,
        "status": ("owned_skill_local" if key == "local_contract" else "owned_contract"),
        "owned": True,
        "debt": False,
        "owner_ref": marker.fields[key],
        "reason": reason,
    }


def detect_hidden_doctrine(
    *,
    root: Path,
    records: list[dict[str, Any]],
    registry_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    paths = {
        str(record.get("source", {}).get("path", ""))
        for record in records
        if record.get("source", {}).get("path")
    }
    markers, marker_findings = parse_markers(
        root=root,
        paths=paths,
    )
    bindings, binding_findings = bind_markers(
        root=root,
        records=records,
        markers=markers,
    )
    registry = load_contract_registry(
        root=root,
        explicit=registry_path,
    )
    analyses: list[dict[str, Any]] = []
    findings = marker_findings + binding_findings
    for record in records:
        extraction_id = str(record["extraction_identity"]["extraction_id"])
        analysis = analyze_ownership(
            record=record,
            marker=bindings.get(extraction_id),
            registry=registry,
        )
        analyses.append(analysis)
        if analysis["status"] == "unresolved_contract_ref":
            findings.append(
                Finding(
                    code="DOCTRINE_CONTRACT_REF_UNRESOLVED",
                    severity="error",
                    path=str(analysis["path"]),
                    line=int(analysis["line_start"]),
                    message=str(analysis["reason"]),
                )
            )
        if analysis["status"] == "invalid_exception":
            findings.append(
                Finding(
                    code="DOCTRINE_EXCEPTION_INVALID",
                    severity="error",
                    path=str(analysis["path"]),
                    line=int(analysis["line_start"]),
                    message=str(analysis["reason"]),
                )
            )
    analyses.sort(
        key=lambda item: (
            str(item["path"]).casefold(),
            int(item["line_start"]),
            str(item["extraction_id"]),
        )
    )
    findings.sort(
        key=lambda finding: (
            finding.path.casefold(),
            finding.line or 0,
            finding.code,
        )
    )
    status_counts: dict[str, int] = defaultdict(int)
    debt_class_counts: dict[str, int] = defaultdict(int)
    for analysis in analyses:
        status_counts[str(analysis["status"])] += 1
        if analysis["debt"]:
            debt_class_counts[str(analysis["debt_class"])] += 1
    return {
        "format_version": 1,
        "detector_version": DETECTOR_VERSION,
        "registry": {
            "path": registry.path,
            "available": registry.path is not None,
            "contract_count": len(registry.contracts),
        },
        "annotation_contract": {
            "syntax": "<!-- l9-doctrine: key=value; ... -->",
            "scope": "next_candidate_only",
            "broad_suppression_allowed": False,
            "allowed_exception_classes": sorted(ALLOWED_EXCEPTION_CLASSES),
        },
        "statistics": {
            "candidate_count": len(analyses),
            "normative_candidate_count": sum(
                1 for analysis in analyses if analysis["normative_candidate"]
            ),
            "unowned_debt_count": sum(1 for analysis in analyses if analysis["debt"]),
            "annotation_count": len(markers),
            "finding_count": len(findings),
            "status_counts": dict(sorted(status_counts.items())),
            "debt_class_counts": dict(sorted(debt_class_counts.items())),
        },
        "records": analyses,
        "findings": [finding.as_dict() for finding in findings],
    }


def _records_from_loaded(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        records = value.get("records")
    else:
        records = value
    if not isinstance(records, list):
        raise ValueError("input must contain an extraction records list")
    result: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"records[{index}] must be a mapping")
        result.append(record)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect hidden/unowned doctrine in active skill surfaces."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Existing extraction YAML/JSON/JSONL. Otherwise scan now.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        help="Explicit contract registry path.",
    )
    parser.add_argument(
        "--surface-mode",
        choices=("governance-text", "all-text"),
        default="governance-text",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
    )
    parser.add_argument(
        "--include-code-fences",
        action="store_true",
    )
    parser.add_argument(
        "--fail-on-unowned",
        action="store_true",
        help=(
            "Strict mode for fully migrated scopes. Do not use this for the "
            "legacy-baseline phase; use validate_doctrine_ratchet.py instead."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("yaml", "json"),
        default="yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.input is not None:
            records = _records_from_loaded(load_serialized(args.input))
        else:
            extraction = extract_repository(
                args.root,
                surface_mode=args.surface_mode,
                include_archived=args.include_archived,
                include_code_fences=args.include_code_fences,
            )
            if extraction["statistics"]["error_count"]:
                raise RuntimeError(
                    "extraction produced integrity errors; ownership analysis aborted"
                )
            records = extraction["records"]
        result = detect_hidden_doctrine(
            root=args.root,
            records=records,
            registry_path=args.registry,
        )
        rendered = serialize_output(result, args.format)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        print(f"HIDDEN_DOCTRINE_ERROR: {exc}", file=sys.stderr)
        return 2
    if result["findings"]:
        return 2
    if args.fail_on_unowned and result["statistics"]["unowned_debt_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
