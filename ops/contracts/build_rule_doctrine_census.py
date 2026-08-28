#!/usr/bin/env python3
"""Build rules/** doctrine census and enforce its monotonic debt baseline."""

from __future__ import annotations

import argparse
import copy
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = Path(__file__).resolve().parent / "adapters"
CONTRACTS = Path(__file__).resolve().parent
for directory in (ADAPTERS, CONTRACTS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from cluster_doctrine import cluster_records  # noqa: E402
from cursor_rules import discover_cursor_rules, stable_digest  # noqa: E402
from detect_hidden_doctrine import (  # noqa: E402
    detect_hidden_doctrine,
    doctrine_fingerprint,
)
from extract_doctrine import (  # noqa: E402
    SourceBlock,
    analyze_block,
    git_commit_timestamp,
    git_head_sha,
    git_workspace_dirty,
    iter_markdown_blocks,
    repository_identity,
    serialize_output,
)

CENSUS_SCHEMA = "l9.rule-doctrine-census/v1"
# Provenance fields that describe WHEN/WHERE the census ran, not WHAT it observed.
# They are excluded from ``integrity_digest`` so the digest is a semantic content
# digest: identical rule corpora yield identical digests, and writing the census
# (which dirties the workspace) cannot change the next run's digest.
VOLATILE_SOURCE_KEYS = ("commit_sha", "commit_timestamp", "workspace_dirty")
BASELINE_SCHEMA = "l9.rule-doctrine-ratchet-baseline/v1"
DEFAULT_CENSUS = Path("generated/governance/rule-doctrine-census.yaml")
DEFAULT_BASELINE = Path("ops/config/doctrine-baseline.rules.yaml")
RISK_WEIGHT = {
    "critical": 40,
    "high": 25,
    "medium": 12,
    "low": 3,
}
ACTIVATION_WEIGHT = {
    "always": 30,
    "auto_attached": 15,
    "agent_requested": 8,
    "manual": 4,
}


def _frontmatter_line_count(text: str) -> int:
    if not text.startswith("---\n"):
        return 0
    lines = text.splitlines()
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index + 1
    return 0


def extract_rule_doctrine(root: Path) -> dict[str, Any]:
    commit_sha = git_head_sha(root)
    timestamp = git_commit_timestamp(root, commit_sha)
    repository = repository_identity(root)
    records: list[dict[str, Any]] = []
    rule_context: dict[str, dict[str, Any]] = {}
    for rule in discover_cursor_rules(root):
        offset = _frontmatter_line_count(rule.text)
        source_sha = rule.content_digest.split(":", 1)[1]
        for block in iter_markdown_blocks(
            path=rule.relative_path,
            skill_name=rule.rule_id,
            text=rule.body,
            scan_frontmatter_description=False,
            include_code_fences=False,
        ):
            adjusted = SourceBlock(
                path=block.path,
                skill_name=rule.rule_id,
                line_start=block.line_start + offset,
                line_end=block.line_end + offset,
                section=block.section,
                exact_text=block.exact_text,
            )
            record = analyze_block(
                block=adjusted,
                repository=repository,
                commit_sha=commit_sha,
                commit_timestamp=timestamp,
                source_sha256=source_sha,
            )
            if record is None:
                continue
            record["source"]["source_kind"] = "rule"
            extraction_id = record["extraction_identity"]["extraction_id"]
            rule_context[extraction_id] = {
                "rule_id": rule.rule_id,
                "file": rule.relative_path,
                "activation": rule.activation,
                "always_apply": rule.always_apply,
                "globs": list(rule.globs),
                "domain": rule.domain,
                "scope": rule.scope,
            }
            records.append(record)
    records.sort(
        key=lambda item: (
            str(item["source"]["path"]).casefold(),
            int(item["source"]["line_start"]),
            str(item["extraction_identity"]["extraction_id"]),
        )
    )
    return {
        "records": records,
        "rule_context": rule_context,
        "source": {
            "repository": repository,
            "commit_sha": commit_sha,
            "commit_timestamp": timestamp,
            "workspace_dirty": git_workspace_dirty(root),
        },
    }


def _priority(
    record: dict[str, Any],
    context: dict[str, Any],
    *,
    duplicate_count: int,
    conflict_count: int,
) -> int:
    classification = record["classification"]
    score = RISK_WEIGHT.get(str(classification["risk"]), 0)
    score += ACTIVATION_WEIGHT.get(str(context["activation"]), 0)
    score += min(duplicate_count, 10) * 4
    score += min(conflict_count, 5) * 20
    if classification["doctrine_strength"] == "hard_normative":
        score += 25
    elif classification["doctrine_strength"] == "conditional_normative":
        score += 18
    if classification["sharedness"] == "repository_global":
        score += 20
    elif classification["sharedness"] == "domain_shared":
        score += 12
    return score


def build_rule_census(
    root: Path = ROOT,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    extraction = extract_rule_doctrine(root)
    records = extraction["records"]
    contexts = extraction["rule_context"]
    clustering = cluster_records(records)
    ownership = detect_hidden_doctrine(
        root=root,
        records=records,
        registry_path=registry_path,
    )
    ownership_by_id = {item["extraction_id"]: item for item in ownership["records"]}
    duplicates: dict[str, list[str]] = defaultdict(list)
    for cluster in clustering["duplicate_clusters"]:
        for member in cluster["members"]:
            duplicates[member["extraction_id"]].append(cluster["cluster_id"])
    conflicts: dict[str, list[str]] = defaultdict(list)
    for cluster in clustering["conflict_clusters"]:
        for member in cluster["members"]:
            conflicts[member["extraction_id"]].append(cluster["cluster_id"])
    candidate_index: list[dict[str, Any]] = []
    debt_counts: Counter[str] = Counter()
    for record in records:
        extraction_id = record["extraction_identity"]["extraction_id"]
        owner = ownership_by_id[extraction_id]
        context = contexts[extraction_id]
        if owner["debt"]:
            debt_counts[doctrine_fingerprint(record)] += 1
        candidate_index.append(
            {
                "extraction_id": extraction_id,
                "fingerprint": doctrine_fingerprint(record),
                "source": {
                    "path": record["source"]["path"],
                    "line_start": record["source"]["line_start"],
                    "section": record["source"].get("section"),
                },
                "rule": context,
                "classification": record["classification"],
                "ownership": {
                    "status": owner["status"],
                    "debt": owner["debt"],
                    "owner_ref": owner["owner_ref"],
                },
                "duplicate_clusters": sorted(duplicates.get(extraction_id, [])),
                "conflict_clusters": sorted(conflicts.get(extraction_id, [])),
                "priority_score": _priority(
                    record,
                    context,
                    duplicate_count=len(duplicates.get(extraction_id, [])),
                    conflict_count=len(conflicts.get(extraction_id, [])),
                ),
            }
        )
    candidate_index.sort(
        key=lambda item: (
            -int(item["priority_score"]),
            str(item["source"]["path"]).casefold(),
            int(item["source"]["line_start"]),
        )
    )
    conflict_fingerprints = sorted(
        {pair["pair_fingerprint"] for pair in clustering["conflict_pairs"]}
    )
    result = {
        "$schema": CENSUS_SCHEMA,
        "source": extraction["source"],
        "summary": {
            "rule_count": len(discover_cursor_rules(root)),
            "candidate_count": len(records),
            "normative_candidate_count": sum(
                1 for item in ownership["records"] if item["normative_candidate"]
            ),
            "unowned_debt_count": sum(1 for item in ownership["records"] if item["debt"]),
            "duplicate_cluster_count": len(clustering["duplicate_clusters"]),
            "potential_conflict_cluster_count": len(clustering["conflict_clusters"]),
            "always_rule_candidate_count": sum(
                1 for item in candidate_index if item["rule"]["always_apply"]
            ),
        },
        "debt_allowance_candidate": [
            {
                "fingerprint": fingerprint,
                "count": count,
            }
            for fingerprint, count in sorted(debt_counts.items())
        ],
        "potential_conflict_pair_fingerprints": conflict_fingerprints,
        "candidate_index": candidate_index,
        "duplicate_clusters": clustering["duplicate_clusters"],
        "potential_conflict_clusters": clustering["conflict_clusters"],
        "quality_findings": ownership["findings"],
    }
    result["integrity_digest"] = stable_digest(_semantic_payload(result))
    return result


def _semantic_payload(census: dict[str, Any]) -> dict[str, Any]:
    """Census content with the digest itself and volatile provenance removed."""
    payload = {key: value for key, value in census.items() if key != "integrity_digest"}
    source = payload.get("source")
    if isinstance(source, dict):
        payload["source"] = {
            key: value for key, value in source.items() if key not in VOLATILE_SOURCE_KEYS
        }
    return payload


def _baseline_digest(baseline: dict[str, Any]) -> str:
    copied = copy.deepcopy(baseline)
    copied.pop("integrity_digest", None)
    return stable_digest(copied)


def _load_baseline(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("rules doctrine baseline must be a mapping")
    digest = loaded.get("integrity_digest")
    if digest not in {None, "", _baseline_digest(loaded)}:
        raise ValueError("rules doctrine baseline integrity digest mismatch")
    return loaded


def bootstrap_baseline(
    census: dict[str, Any],
    baseline_path: Path,
    reason: str,
) -> None:
    if census["source"]["workspace_dirty"]:
        raise ValueError("refusing to bootstrap rules baseline from dirty workspace")
    if len(reason.strip()) < 20:
        raise ValueError("bootstrap reason must be at least 20 characters")
    existing = _load_baseline(baseline_path) if baseline_path.exists() else None
    if existing and existing.get("status") != "bootstrap_required":
        raise ValueError("active rules doctrine baseline already exists")
    baseline = {
        "$schema": BASELINE_SCHEMA,
        "status": "active",
        "policy": {
            "legacy_debt_may_increase": False,
            "legacy_debt_may_decrease": True,
            "new_conflicts_allowed": False,
            "automatic_upward_rebaseline_allowed": False,
        },
        "created_from": census["source"],
        "bootstrap_reason": reason.strip(),
        "allowances": {
            "unowned_doctrine": census["debt_allowance_candidate"],
            "potential_conflict_pairs": census["potential_conflict_pair_fingerprints"],
        },
    }
    baseline["integrity_digest"] = _baseline_digest(baseline)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        yaml.safe_dump(
            baseline,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        ),
        encoding="utf-8",
    )


def check_baseline(
    census: dict[str, Any],
    baseline: dict[str, Any],
) -> list[str]:
    if baseline.get("status") != "active":
        return ["rules doctrine baseline is not active; bootstrap required"]
    allowed = {
        item["fingerprint"]: int(item["count"])
        for item in baseline["allowances"]["unowned_doctrine"]
    }
    current = {
        item["fingerprint"]: int(item["count"]) for item in census["debt_allowance_candidate"]
    }
    failures: list[str] = []
    for fingerprint in sorted(set(allowed) | set(current)):
        current_count = current.get(fingerprint, 0)
        allowed_count = allowed.get(fingerprint, 0)
        if current_count > allowed_count:
            failures.append(
                f"new/unexpanded doctrine debt {fingerprint}: "
                f"current={current_count}, allowed={allowed_count}"
            )
    allowed_conflicts = set(baseline["allowances"]["potential_conflict_pairs"])
    current_conflicts = set(census["potential_conflict_pair_fingerprints"])
    for fingerprint in sorted(current_conflicts - allowed_conflicts):
        failures.append(f"new potential doctrine conflict {fingerprint}")
    return failures


def tighten_baseline(
    census: dict[str, Any],
    baseline_path: Path,
) -> None:
    baseline = _load_baseline(baseline_path)
    failures = check_baseline(census, baseline)
    if failures:
        raise ValueError("cannot tighten a failing baseline: " + "; ".join(failures))
    current = {
        item["fingerprint"]: int(item["count"]) for item in census["debt_allowance_candidate"]
    }
    old = {
        item["fingerprint"]: int(item["count"])
        for item in baseline["allowances"]["unowned_doctrine"]
    }
    baseline["allowances"]["unowned_doctrine"] = [
        {
            "fingerprint": fingerprint,
            "count": min(current.get(fingerprint, 0), old_count),
        }
        for fingerprint, old_count in sorted(old.items())
        if current.get(fingerprint, 0) > 0
    ]
    baseline["allowances"]["potential_conflict_pairs"] = sorted(
        set(baseline["allowances"]["potential_conflict_pairs"])
        & set(census["potential_conflict_pair_fingerprints"])
    )
    baseline["integrity_digest"] = _baseline_digest(baseline)
    baseline_path.write_text(
        yaml.safe_dump(
            baseline,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_CENSUS)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--check-baseline", action="store_true")
    parser.add_argument("--bootstrap-baseline", action="store_true")
    parser.add_argument("--tighten-baseline", action="store_true")
    parser.add_argument("--reason")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        census = build_rule_census(root, args.registry)
        output = args.output if args.output.is_absolute() else root / args.output
        baseline_path = args.baseline if args.baseline.is_absolute() else root / args.baseline
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            serialize_output(census, "yaml"),
            encoding="utf-8",
        )
        if args.bootstrap_baseline:
            if not args.reason:
                raise ValueError("--bootstrap-baseline requires --reason")
            bootstrap_baseline(census, baseline_path, args.reason)
        elif args.tighten_baseline:
            tighten_baseline(census, baseline_path)
        elif args.check_baseline:
            baseline = _load_baseline(baseline_path)
            failures = check_baseline(census, baseline)
            if failures:
                print(f"FAIL ({len(failures)})")
                for failure in failures:
                    print(f"  - {failure}")
                return 1
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"RULE_DOCTRINE_CENSUS_ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        "RULE DOCTRINE CENSUS: "
        f"{census['summary']['candidate_count']} candidates; "
        f"{census['summary']['unowned_debt_count']} unowned; "
        f"{census['summary']['potential_conflict_cluster_count']} "
        "potential conflict clusters"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
