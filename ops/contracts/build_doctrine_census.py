#!/usr/bin/env python3
"""Build the deterministic Skills Doctrine Census.
The census is the migration inventory for the contract-first conversion.
It combines:
1. extraction;
2. duplicate/conflict clustering;
3. explicit ownership detection;
4. legacy-debt accounting;
5. per-skill and per-domain statistics;
6. leverage-ranked migration candidates.
The census is observational. Existing debt does not make this command fail.
Integrity failures do.
Use validate_doctrine_ratchet.py for the policy gate that prevents new debt.
Default generated artifact:
    generated/governance/doctrine-census.yaml
The --check mode performs deterministic regeneration and fails if the tracked
artifact differs from the current repository state.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml
from cluster_doctrine import (
    CLUSTERER_VERSION,
    cluster_records,
)
from detect_hidden_doctrine import (
    DETECTOR_VERSION,
    detect_hidden_doctrine,
)
from extract_doctrine import (
    EXTRACTOR_VERSION,
    ROOT,
    dump_yaml,
    extract_repository,
    stable_digest,
)

CENSUS_VERSION = "1.0.0"
# Provenance fields that describe WHEN/WHERE the census ran, not WHAT it observed.
# They are excluded from ``integrity_digest`` so the digest is a semantic content
# digest: identical corpora yield identical digests, and writing the census
# (which dirties the workspace) cannot change the next run's digest.
# validate_doctrine_ratchet.py still reads them from ``source`` for baseline
# ``created_from`` provenance, so nothing downstream loses information.
VOLATILE_SOURCE_KEYS = ("commit_sha", "commit_timestamp", "workspace_dirty")
DEFAULT_OUTPUT = Path("generated") / "governance" / "doctrine-census.yaml"
RISK_WEIGHT = {
    "critical": 40,
    "high": 26,
    "medium": 13,
    "low": 4,
}
STRENGTH_WEIGHT = {
    "hard_normative": 25,
    "conditional_normative": 19,
    "advisory": 7,
    "descriptive": 1,
    "unknown": 10,
}
SHAREDNESS_WEIGHT = {
    "repository_global": 22,
    "domain_shared": 16,
    "unknown": 11,
    "skill_local": 6,
    "projection_only": 3,
}
KIND_WEIGHT = {
    "invariant": 12,
    "policy": 12,
    "workflow": 9,
    "routing_activation": 9,
    "capability": 8,
    "evidence": 8,
    "unknown": 8,
    "rationale": 0,
    "example": 0,
    "obsolete": 0,
    "conflict": 15,
}


def _source_skill(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return "_skills_root"


def _safe_counter(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _ownership_by_id(
    ownership: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {str(item["extraction_id"]): item for item in ownership["records"]}


def _conflict_membership(
    clustering: dict[str, Any],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for cluster in clustering["conflict_clusters"]:
        cluster_id = str(cluster["cluster_id"])
        for member in cluster["members"]:
            result[str(member["extraction_id"])].append(cluster_id)
    return {extraction_id: sorted(cluster_ids) for extraction_id, cluster_ids in result.items()}


def _duplicate_membership(
    clustering: dict[str, Any],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for cluster in clustering["duplicate_clusters"]:
        cluster_id = str(cluster["cluster_id"])
        for member in cluster["members"]:
            result[str(member["extraction_id"])].append(cluster_id)
    return {extraction_id: sorted(cluster_ids) for extraction_id, cluster_ids in result.items()}


def _priority_score(
    record: dict[str, Any],
    ownership: dict[str, Any],
    *,
    occurrence_count: int,
    conflict_count: int,
    duplicate_count: int,
) -> int:
    classification = record.get("classification", {})
    risk = str(classification.get("risk", "low"))
    strength = str(classification.get("doctrine_strength", "unknown"))
    sharedness = str(classification.get("sharedness", "unknown"))
    kind = str(classification.get("candidate_kind", "unknown"))
    score = (
        RISK_WEIGHT.get(risk, 0)
        + STRENGTH_WEIGHT.get(strength, 0)
        + SHAREDNESS_WEIGHT.get(sharedness, 0)
        + KIND_WEIGHT.get(kind, 0)
    )
    score += min(max(occurrence_count - 1, 0), 10) * 4
    score += min(conflict_count, 5) * 18
    score += min(duplicate_count, 10) * 3
    if ownership.get("debt"):
        score += 15
    if ownership.get("status") == "unresolved_contract_ref":
        score += 20
    return score


def _candidate_index(
    *,
    extraction_records: list[dict[str, Any]],
    ownership: dict[str, Any],
    clustering: dict[str, Any],
) -> list[dict[str, Any]]:
    owner_by_id = _ownership_by_id(ownership)
    conflict_by_id = _conflict_membership(clustering)
    duplicate_by_id = _duplicate_membership(clustering)
    fingerprint_counts = Counter(
        item["doctrine_fingerprint"] for item in ownership["records"] if item["debt"]
    )
    result: list[dict[str, Any]] = []
    for record in extraction_records:
        extraction_id = str(record["extraction_identity"]["extraction_id"])
        owner = owner_by_id[extraction_id]
        source = record["source"]
        classification = record["classification"]
        semantics = record["normalized_semantics"]
        quality = record["extraction_quality"]
        resolution = record["resolution"]
        conflicts = conflict_by_id.get(extraction_id, [])
        duplicates = duplicate_by_id.get(extraction_id, [])
        item = {
            "extraction_id": extraction_id,
            "doctrine_fingerprint": owner["doctrine_fingerprint"],
            "semantic_fingerprint": owner["semantic_fingerprint"],
            "source": {
                "path": source["path"],
                "line_start": source["line_start"],
                "line_end": source["line_end"],
                "section": source.get("section"),
                "skill": _source_skill(str(source["path"])),
            },
            "classification": {
                "candidate_kind": classification["candidate_kind"],
                "doctrine_strength": classification["doctrine_strength"],
                "sharedness": classification["sharedness"],
                "risk": classification["risk"],
                "effect": semantics["effect"],
                "confidence": quality["confidence"],
            },
            "ownership": {
                "status": owner["status"],
                "owned": owner["owned"],
                "debt": owner["debt"],
                "debt_class": owner["debt_class"],
                "owner_ref": owner["owner_ref"],
            },
            "migration": {
                "suggested_disposition": resolution["disposition"],
                "review_status": resolution["review_status"],
                "duplicate_clusters": duplicates,
                "conflict_clusters": conflicts,
            },
            "priority_score": _priority_score(
                record,
                owner,
                occurrence_count=fingerprint_counts.get(
                    owner["doctrine_fingerprint"],
                    0,
                ),
                conflict_count=len(conflicts),
                duplicate_count=len(duplicates),
            ),
        }
        result.append(item)
    result.sort(
        key=lambda item: (
            -int(item["priority_score"]),
            str(item["source"]["path"]).casefold(),
            int(item["source"]["line_start"]),
            str(item["extraction_id"]),
        )
    )
    return result


def _debt_inventory(
    ownership: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in ownership["records"]:
        if not item["debt"]:
            continue
        grouped[str(item["doctrine_fingerprint"])].append(item)
    result: list[dict[str, Any]] = []
    for fingerprint, members in sorted(grouped.items()):
        members.sort(
            key=lambda item: (
                str(item["path"]).casefold(),
                int(item["line_start"]),
                str(item["extraction_id"]),
            )
        )
        representative = members[0]
        result.append(
            {
                "fingerprint": fingerprint,
                "count": len(members),
                "debt_class": representative["debt_class"],
                "risk": representative["risk"],
                "representative": {
                    "extraction_id": representative["extraction_id"],
                    "path": representative["path"],
                    "line_start": representative["line_start"],
                    "skill": representative["skill"],
                },
                "occurrences": [
                    {
                        "extraction_id": member["extraction_id"],
                        "path": member["path"],
                        "line_start": member["line_start"],
                        "skill": member["skill"],
                    }
                    for member in members
                ],
            }
        )
    return result


def _skill_statistics(
    *,
    extraction_records: list[dict[str, Any]],
    ownership: dict[str, Any],
) -> list[dict[str, Any]]:
    owner_by_id = _ownership_by_id(ownership)
    buckets: dict[str, dict[str, Any]] = {}
    for record in extraction_records:
        source = record["source"]
        classification = record["classification"]
        extraction_id = str(record["extraction_identity"]["extraction_id"])
        owner = owner_by_id[extraction_id]
        skill = _source_skill(str(source["path"]))
        bucket = buckets.setdefault(
            skill,
            {
                "skill": skill,
                "candidate_count": 0,
                "normative_candidate_count": 0,
                "unowned_debt_count": 0,
                "owned_count": 0,
                "critical_count": 0,
                "high_count": 0,
                "unknown_count": 0,
            },
        )
        bucket["candidate_count"] += 1
        if owner["normative_candidate"]:
            bucket["normative_candidate_count"] += 1
        if owner["debt"]:
            bucket["unowned_debt_count"] += 1
        elif owner["owned"]:
            bucket["owned_count"] += 1
        risk = classification["risk"]
        if risk == "critical":
            bucket["critical_count"] += 1
        elif risk == "high":
            bucket["high_count"] += 1
        if classification["candidate_kind"] == "unknown":
            bucket["unknown_count"] += 1
    return sorted(
        buckets.values(),
        key=lambda item: (
            -int(item["unowned_debt_count"]),
            -int(item["critical_count"]),
            -int(item["high_count"]),
            str(item["skill"]).casefold(),
        ),
    )


def _migration_queue(
    candidate_index: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for candidate in candidate_index:
        ownership = candidate["ownership"]
        if not ownership["debt"]:
            continue
        queue.append(
            {
                "priority_score": candidate["priority_score"],
                "extraction_id": candidate["extraction_id"],
                "doctrine_fingerprint": candidate["doctrine_fingerprint"],
                "skill": candidate["source"]["skill"],
                "path": candidate["source"]["path"],
                "line_start": candidate["source"]["line_start"],
                "candidate_kind": candidate["classification"]["candidate_kind"],
                "doctrine_strength": (candidate["classification"]["doctrine_strength"]),
                "sharedness": candidate["classification"]["sharedness"],
                "risk": candidate["classification"]["risk"],
                "debt_class": ownership["debt_class"],
                "suggested_disposition": (candidate["migration"]["suggested_disposition"]),
                "duplicate_clusters": candidate["migration"]["duplicate_clusters"],
                "conflict_clusters": candidate["migration"]["conflict_clusters"],
            }
        )
    return queue


def _summary(
    *,
    extraction: dict[str, Any],
    clustering: dict[str, Any],
    ownership: dict[str, Any],
) -> dict[str, Any]:
    records = extraction["records"]
    owner_records = ownership["records"]
    classification_values = [record["classification"] for record in records]
    return {
        "files_scanned": extraction["statistics"]["files_scanned"],
        "candidate_count": len(records),
        "normative_candidate_count": sum(
            1 for item in owner_records if item["normative_candidate"]
        ),
        "unowned_debt_count": sum(1 for item in owner_records if item["debt"]),
        "owned_contract_count": sum(
            1 for item in owner_records if item["status"] == "owned_contract"
        ),
        "owned_skill_local_count": sum(
            1 for item in owner_records if item["status"] == "owned_skill_local"
        ),
        "valid_exception_count": sum(
            1 for item in owner_records if item["status"] == "valid_exception"
        ),
        "unresolved_contract_ref_count": sum(
            1 for item in owner_records if item["status"] == "unresolved_contract_ref"
        ),
        "invalid_exception_count": sum(
            1 for item in owner_records if item["status"] == "invalid_exception"
        ),
        "duplicate_cluster_count": clustering["statistics"]["duplicate_cluster_count"],
        "potential_conflict_cluster_count": clustering["statistics"][
            "potential_conflict_cluster_count"
        ],
        "potential_conflict_pair_count": clustering["statistics"]["potential_conflict_pair_count"],
        "by_kind": _safe_counter([str(value["candidate_kind"]) for value in classification_values]),
        "by_strength": _safe_counter(
            [str(value["doctrine_strength"]) for value in classification_values]
        ),
        "by_sharedness": _safe_counter(
            [str(value["sharedness"]) for value in classification_values]
        ),
        "by_risk": _safe_counter([str(value["risk"]) for value in classification_values]),
        "by_ownership_status": _safe_counter([str(value["status"]) for value in owner_records]),
        "by_debt_class": _safe_counter(
            [str(value["debt_class"]) for value in owner_records if value["debt"]]
        ),
    }


def _semantic_payload(census: dict[str, Any]) -> dict[str, Any]:
    """Census content with the digest itself and volatile provenance removed."""
    payload = {key: value for key, value in census.items() if key != "integrity_digest"}
    source = payload.get("source")
    if isinstance(source, dict):
        payload["source"] = {
            key: value for key, value in source.items() if key not in VOLATILE_SOURCE_KEYS
        }
    return payload


def build_census(
    *,
    root: Path = ROOT,
    surface_mode: str = "governance-text",
    include_archived: bool = False,
    include_code_fences: bool = False,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    """Build the complete deterministic doctrine census."""
    extraction = extract_repository(
        root,
        surface_mode=surface_mode,
        include_archived=include_archived,
        include_code_fences=include_code_fences,
    )
    extraction_errors = [
        finding for finding in extraction["findings"] if finding.get("severity") == "error"
    ]
    if extraction_errors:
        raise RuntimeError("doctrine extraction reported integrity errors; census is unsafe")
    clustering = cluster_records(extraction["records"])
    ownership = detect_hidden_doctrine(
        root=root,
        records=extraction["records"],
        registry_path=registry_path,
    )
    candidate_index = _candidate_index(
        extraction_records=extraction["records"],
        ownership=ownership,
        clustering=clustering,
    )
    debt_inventory = _debt_inventory(ownership)
    conflict_pair_fingerprints = sorted(
        {str(pair["pair_fingerprint"]) for pair in clustering["conflict_pairs"]}
    )
    quality_findings = sorted(
        extraction["findings"] + ownership["findings"],
        key=lambda finding: (
            str(finding.get("path", "")).casefold(),
            int(finding.get("line", 0) or 0),
            str(finding.get("code", "")),
        ),
    )
    source = extraction["source"]
    census = {
        "schema_id": "l9.doctrine_census.v1",
        "version": CENSUS_VERSION,
        "authority": {
            "class": "generated_observational_artifact",
            "creates_contract_authority": False,
            "may_resolve_conflicts": False,
            "may_promote_extractions": False,
        },
        "source": {
            "repository": source["repository"],
            "commit_sha": source["commit_sha"],
            "commit_timestamp": source["commit_timestamp"],
            "workspace_dirty": source["workspace_dirty"],
        },
        "scope": {
            "scan_profile": extraction["scan_profile"],
            "scan_profile_digest": extraction["scan_profile_digest"],
        },
        "algorithms": {
            "extractor": EXTRACTOR_VERSION,
            "clusterer": CLUSTERER_VERSION,
            "ownership_detector": DETECTOR_VERSION,
            "census_builder": CENSUS_VERSION,
        },
        "registry": ownership["registry"],
        "summary": _summary(
            extraction=extraction,
            clustering=clustering,
            ownership=ownership,
        ),
        "per_skill": _skill_statistics(
            extraction_records=extraction["records"],
            ownership=ownership,
        ),
        "debt_inventory": debt_inventory,
        "duplicate_clusters": clustering["duplicate_clusters"],
        "potential_conflict_clusters": clustering["conflict_clusters"],
        "potential_conflict_pair_fingerprints": conflict_pair_fingerprints,
        "migration_queue": _migration_queue(candidate_index),
        "candidate_index": candidate_index,
        "quality": {
            "finding_count": len(quality_findings),
            "error_count": sum(
                1 for finding in quality_findings if finding.get("severity") == "error"
            ),
            "warning_count": sum(
                1 for finding in quality_findings if finding.get("severity") == "warning"
            ),
            "findings": quality_findings,
        },
    }
    census["integrity_digest"] = stable_digest(_semantic_payload(census))
    return census


def render_census(census: dict[str, Any], output_format: str) -> str:
    if output_format == "yaml":
        return dump_yaml(census)
    if output_format == "json":
        return (
            json.dumps(
                census,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    raise ValueError(f"unsupported output format: {output_format}")


def write_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.is_file() else None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic Skills Doctrine Census.")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
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
        "--registry",
        type=Path,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--format",
        choices=("yaml", "json"),
        default="yaml",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated census differs from the requested output file.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print generated census instead of writing it.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        root = args.root.resolve()
        output = args.output if args.output.is_absolute() else root / args.output
        census = build_census(
            root=root,
            surface_mode=args.surface_mode,
            include_archived=args.include_archived,
            include_code_fences=args.include_code_fences,
            registry_path=args.registry,
        )
        rendered = render_census(census, args.format)
        if census["quality"]["error_count"]:
            for finding in census["quality"]["findings"]:
                if finding.get("severity") != "error":
                    continue
                path = finding.get("path", "repository")
                line = finding.get("line")
                location = f"{path}:{line}" if line else str(path)
                print(
                    f"{finding.get('code')}: {location}: {finding.get('message')}",
                    file=sys.stderr,
                )
            return 2
        if args.stdout:
            sys.stdout.write(rendered)
            return 0
        if args.check:
            if not output.is_file():
                print(
                    f"DOCTRINE_CENSUS_STALE: missing {output.relative_to(root)}",
                    file=sys.stderr,
                )
                return 1
            existing = output.read_text(encoding="utf-8")
            if existing != rendered:
                print(
                    "DOCTRINE_CENSUS_STALE: generated census differs from "
                    f"{output.relative_to(root)}",
                    file=sys.stderr,
                )
                return 1
            print(
                "Doctrine census is current: "
                f"{census['summary']['candidate_count']} candidates, "
                f"{census['summary']['unowned_debt_count']} unowned."
            )
            return 0
        changed = write_if_changed(output, rendered)
        action = "updated" if changed else "unchanged"
        print(
            f"Doctrine census {action}: {output.relative_to(root)} "
            f"({census['summary']['candidate_count']} candidates, "
            f"{census['summary']['unowned_debt_count']} unowned, "
            f"{census['summary']['potential_conflict_cluster_count']} "
            "potential conflict clusters)"
        )
    except (
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        print(f"DOCTRINE_CENSUS_ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
