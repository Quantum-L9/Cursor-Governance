#!/usr/bin/env python3
"""Enforce the no-new-hidden-doctrine migration ratchet.
Policy:
    Legacy doctrine debt may remain temporarily.
    Legacy doctrine debt may decrease.
    Legacy doctrine debt may NEVER increase silently.
The baseline records occurrence allowances by semantic doctrine fingerprint.
This gives line-number stability while still detecting additional copies of an
existing unowned rule.
Potential conflict pairs are independently baselined so moving/rewording debt
cannot silently introduce a new contradiction while total debt count remains
flat.
Absolute failures are never grandfathered:
- malformed doctrine annotations;
- unresolved contract references;
- invalid normative exceptions;
- extraction integrity failures;
- scan-profile drift;
- algorithm-version drift;
- malformed baseline data.
Supported baseline mutations:
--bootstrap
    Creates the initial baseline only when one does not already exist.
    Requires a clean Git workspace and an explicit reason.
--tighten
    Monotonically lowers existing allowances to current values and removes
    resolved debt/conflicts. It refuses to run if current state already violates
    the existing baseline.
There is intentionally NO automatic "rebaseline upward" operation. Expanding
the baseline changes governance policy and must be a separately reviewed manual
policy change.
Exit codes:
0
    Ratchet passes, or requested monotonic baseline operation succeeded.
1
    Doctrine-policy violation: new debt or new potential conflict.
2
    Configuration, baseline-integrity, scan-integrity, or annotation failure.
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
import yaml
from build_doctrine_census import (
    CENSUS_VERSION,
    build_census,
)
from extract_doctrine import (
    ROOT,
    dump_yaml,
    load_yaml_unique,
    stable_digest,
)
RATCHET_VERSION = "1.0.0"
BASELINE_SCHEMA_ID = "l9.doctrine_ratchet.baseline.v1"
DEFAULT_BASELINE = (
    Path("ops")
    / "config"
    / "doctrine-baseline.yaml"
)
ALLOWED_BASELINE_TOP_LEVEL = {
    "schema_id",
    "version",
    "policy",
    "scope",
    "algorithms",
    "created_from",
    "bootstrap_reason",
    "last_tightened_from",
    "allowances",
    "integrity_digest",
}
REQUIRED_BASELINE_TOP_LEVEL = {
    "schema_id",
    "version",
    "policy",
    "scope",
    "algorithms",
    "created_from",
    "bootstrap_reason",
    "allowances",
    "integrity_digest",
}
def _current_debt_counts(census: dict[str, Any]) -> Counter[str]:
    return Counter(
        {
            str(item["fingerprint"]): int(item["count"])
            for item in census["debt_inventory"]
        }
    )
def _current_conflict_pairs(census: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for value in census["potential_conflict_pair_fingerprints"]
    }
def _algorithms_for_baseline(census: dict[str, Any]) -> dict[str, str]:
    algorithms = census["algorithms"]
    return {
        "extractor": str(algorithms["extractor"]),
        "clusterer": str(algorithms["clusterer"]),
        "ownership_detector": str(algorithms["ownership_detector"]),
        "census_builder": str(algorithms["census_builder"]),
        "ratchet": RATCHET_VERSION,
    }
def _representatives_by_fingerprint(
    census: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(item["fingerprint"]): dict(item["representative"])
        for item in census["debt_inventory"]
    }
def _baseline_payload_without_digest(
    baseline: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in baseline.items()
        if key != "integrity_digest"
    }
def _baseline_digest(baseline: dict[str, Any]) -> str:
    return stable_digest(_baseline_payload_without_digest(baseline))
def build_baseline(
    *,
    census: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    reason = reason.strip()
    if len(reason) < 20:
        raise ValueError(
            "bootstrap reason must contain at least 20 meaningful characters"
        )
    debt_counts = _current_debt_counts(census)
    representatives = _representatives_by_fingerprint(census)
    debt_allowances = [
        {
            "fingerprint": fingerprint,
            "max_count": count,
            "representative": representatives.get(fingerprint),
        }
        for fingerprint, count in sorted(debt_counts.items())
    ]
    baseline = {
        "schema_id": BASELINE_SCHEMA_ID,
        "version": 1,
        "policy": {
            "name": "no_new_hidden_doctrine",
            "legacy_debt_may_increase": False,
            "legacy_debt_may_decrease": True,
            "new_potential_conflicts_allowed": False,
            "unresolved_contract_refs_allowed": False,
            "invalid_annotations_allowed": False,
            "automatic_upward_rebaseline_allowed": False,
        },
        "scope": {
            "scan_profile": census["scope"]["scan_profile"],
            "scan_profile_digest": census["scope"]["scan_profile_digest"],
        },
        "algorithms": _algorithms_for_baseline(census),
        "created_from": {
            "repository": census["source"]["repository"],
            "commit_sha": census["source"]["commit_sha"],
            "commit_timestamp": census["source"]["commit_timestamp"],
        },
        "bootstrap_reason": reason,
        "last_tightened_from": None,
        "allowances": {
            "unowned_debt": debt_allowances,
            "potential_conflict_pairs": sorted(
                _current_conflict_pairs(census)
            ),
        },
    }
    baseline["integrity_digest"] = _baseline_digest(baseline)
    return baseline
def validate_baseline_structure(
    baseline: Any,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(baseline, dict):
        return ["baseline must contain a YAML mapping"]
    unknown = set(baseline) - ALLOWED_BASELINE_TOP_LEVEL
    if unknown:
        errors.append(
            f"baseline contains unknown top-level fields: {sorted(unknown)}"
        )
    missing = REQUIRED_BASELINE_TOP_LEVEL - set(baseline)
    if missing:
        errors.append(
            f"baseline is missing required top-level fields: {sorted(missing)}"
        )
    if baseline.get("schema_id") != BASELINE_SCHEMA_ID:
        errors.append(
            f"schema_id must equal {BASELINE_SCHEMA_ID!r}"
        )
    if baseline.get("version") != 1:
        errors.append("baseline version must equal 1")
    policy = baseline.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be a mapping")
    else:
        required_policy = {
            "legacy_debt_may_increase": False,
            "legacy_debt_may_decrease": True,
            "new_potential_conflicts_allowed": False,
            "unresolved_contract_refs_allowed": False,
            "invalid_annotations_allowed": False,
            "automatic_upward_rebaseline_allowed": False,
        }
        for key, expected in required_policy.items():
            if policy.get(key) is not expected:
                errors.append(
                    f"policy.{key} must remain {expected!r}"
                )
    scope = baseline.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be a mapping")
    elif not isinstance(scope.get("scan_profile_digest"), str):
        errors.append("scope.scan_profile_digest must be a string")
    algorithms = baseline.get("algorithms")
    if not isinstance(algorithms, dict):
        errors.append("algorithms must be a mapping")
    allowances = baseline.get("allowances")
    if not isinstance(allowances, dict):
        errors.append("allowances must be a mapping")
    else:
        debt = allowances.get("unowned_debt")
        conflicts = allowances.get("potential_conflict_pairs")
        if not isinstance(debt, list):
            errors.append("allowances.unowned_debt must be a list")
        else:
            seen: set[str] = set()
            for index, item in enumerate(debt):
                if not isinstance(item, dict):
                    errors.append(
                        f"allowances.unowned_debt[{index}] must be a mapping"
                    )
                    continue
                fingerprint = item.get("fingerprint")
                max_count = item.get("max_count")
                if not isinstance(fingerprint, str) or len(fingerprint) != 64:
                    errors.append(
                        f"allowances.unowned_debt[{index}].fingerprint "
                        "must be a SHA-256 string"
                    )
                    continue
                if fingerprint in seen:
                    errors.append(
                        f"duplicate debt fingerprint {fingerprint}"
                    )
                seen.add(fingerprint)
                if (
                    not isinstance(max_count, int)
                    or isinstance(max_count, bool)
                    or max_count < 1
                ):
                    errors.append(
                        f"allowances.unowned_debt[{index}].max_count "
                        "must be a positive integer"
                    )
        if not isinstance(conflicts, list):
            errors.append(
                "allowances.potential_conflict_pairs must be a list"
            )
        elif len(conflicts) != len(set(conflicts)):
            errors.append(
                "allowances.potential_conflict_pairs contains duplicates"
            )
    expected_digest = baseline.get("integrity_digest")
    if not isinstance(expected_digest, str):
        errors.append("integrity_digest must be a string")
    elif expected_digest != _baseline_digest(baseline):
        errors.append(
            "baseline integrity_digest does not match canonical content"
        )
    return errors
def _allowed_debt_counts(
    baseline: dict[str, Any],
) -> dict[str, int]:
    return {
        str(item["fingerprint"]): int(item["max_count"])
        for item in baseline["allowances"]["unowned_debt"]
    }
def _absolute_integrity_violations(
    census: dict[str, Any],
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    quality = census["quality"]
    for finding in quality["findings"]:
        code = str(finding.get("code", ""))
        if code in {
            "DOCTRINE_CONTRACT_REF_UNRESOLVED",
            "DOCTRINE_EXCEPTION_INVALID",
            "ANNOTATION_INVALID",
            "ANNOTATION_NOT_STANDALONE",
            "ANNOTATION_MULTIPLE_OWNERS",
            "ANNOTATION_ORPHANED",
            "ANNOTATION_UNUSED",
            "ANNOTATION_SOURCE_READ_FAILED",
        }:
            violations.append(
                {
                    "code": code,
                    "path": finding.get("path"),
                    "line": finding.get("line"),
                    "message": finding.get("message"),
                }
            )
    return violations
def compare_to_baseline(
    *,
    census: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Compare current repository state to immutable ratchet allowances."""
    integrity_errors = validate_baseline_structure(baseline)
    if integrity_errors:
        return {
            "status": "configuration_error",
            "configuration_errors": integrity_errors,
            "violations": [],
            "improvements": [],
        }
    expected_scope_digest = baseline["scope"]["scan_profile_digest"]
    current_scope_digest = census["scope"]["scan_profile_digest"]
    if current_scope_digest != expected_scope_digest:
        return {
            "status": "configuration_error",
            "configuration_errors": [
                "scan-profile digest changed; baseline and current census "
                "are not comparable"
            ],
            "violations": [],
            "improvements": [],
        }
    current_algorithms = _algorithms_for_baseline(census)
    if current_algorithms != baseline["algorithms"]:
        return {
            "status": "configuration_error",
            "configuration_errors": [
                "doctrine algorithm versions changed; perform a reviewed "
                "baseline migration rather than silently comparing "
                "incompatible fingerprints"
            ],
            "violations": [],
            "improvements": [],
        }
    absolute = _absolute_integrity_violations(census)
    if absolute:
        return {
            "status": "integrity_error",
            "configuration_errors": [],
            "violations": absolute,
            "improvements": [],
        }
    current_counts = _current_debt_counts(census)
    allowed_counts = _allowed_debt_counts(baseline)
    representatives = _representatives_by_fingerprint(census)
    violations: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    all_fingerprints = sorted(
        set(current_counts) | set(allowed_counts)
    )
    for fingerprint in all_fingerprints:
        current = current_counts.get(fingerprint, 0)
        allowed = allowed_counts.get(fingerprint, 0)
        if current > allowed:
            representative = representatives.get(fingerprint, {})
            violations.append(
                {
                    "code": "NEW_UNOWNED_DOCTRINE",
                    "fingerprint": fingerprint,
                    "baseline_max_count": allowed,
                    "current_count": current,
                    "increase": current - allowed,
                    "representative": representative,
                    "message": (
                        "unowned doctrine occurrence count exceeds "
                        "grandfathered baseline"
                    ),
                }
            )
        elif current < allowed:
            improvements.append(
                {
                    "code": "DOCTRINE_DEBT_REDUCED",
                    "fingerprint": fingerprint,
                    "baseline_max_count": allowed,
                    "current_count": current,
                    "reduction": allowed - current,
                }
            )
    current_conflicts = _current_conflict_pairs(census)
    allowed_conflicts = set(
        baseline["allowances"]["potential_conflict_pairs"]
    )
    for fingerprint in sorted(current_conflicts - allowed_conflicts):
        violations.append(
            {
                "code": "NEW_POTENTIAL_DOCTRINE_CONFLICT",
                "pair_fingerprint": fingerprint,
                "message": (
                    "new potential contradiction is absent from the "
                    "grandfathered conflict baseline"
                ),
            }
        )
    for fingerprint in sorted(allowed_conflicts - current_conflicts):
        improvements.append(
            {
                "code": "POTENTIAL_DOCTRINE_CONFLICT_REMOVED",
                "pair_fingerprint": fingerprint,
            }
        )
    return {
        "status": "fail" if violations else "pass",
        "configuration_errors": [],
        "violations": violations,
        "improvements": improvements,
        "metrics": {
            "baseline_unowned_occurrences": sum(allowed_counts.values()),
            "current_unowned_occurrences": sum(current_counts.values()),
            "baseline_unique_debt_fingerprints": len(allowed_counts),
            "current_unique_debt_fingerprints": len(current_counts),
            "baseline_potential_conflict_pairs": len(allowed_conflicts),
            "current_potential_conflict_pairs": len(current_conflicts),
        },
    }
def tighten_baseline(
    *,
    census: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Return a baseline that can only become stricter."""
    comparison = compare_to_baseline(
        census=census,
        baseline=baseline,
    )
    if comparison["status"] != "pass":
        raise ValueError(
            "baseline cannot be tightened while current repository state "
            f"does not pass the existing ratchet ({comparison['status']})"
        )
    current_counts = _current_debt_counts(census)
    old_allowed = _allowed_debt_counts(baseline)
    representatives = _representatives_by_fingerprint(census)
    tightened_debt: list[dict[str, Any]] = []
    for fingerprint in sorted(old_allowed):
        current = current_counts.get(fingerprint, 0)
        allowed = old_allowed[fingerprint]
        tightened = min(current, allowed)
        if tightened <= 0:
            continue
        tightened_debt.append(
            {
                "fingerprint": fingerprint,
                "max_count": tightened,
                "representative": representatives.get(fingerprint),
            }
        )
    old_conflicts = set(
        baseline["allowances"]["potential_conflict_pairs"]
    )
    current_conflicts = _current_conflict_pairs(census)
    tightened = dict(baseline)
    tightened["allowances"] = {
        "unowned_debt": tightened_debt,
        "potential_conflict_pairs": sorted(
            old_conflicts & current_conflicts
        ),
    }
    tightened["last_tightened_from"] = {
        "repository": census["source"]["repository"],
        "commit_sha": census["source"]["commit_sha"],
        "commit_timestamp": census["source"]["commit_timestamp"],
    }
    tightened["integrity_digest"] = _baseline_digest(tightened)
    old_total = sum(old_allowed.values())
    new_total = sum(
        int(item["max_count"])
        for item in tightened_debt
    )
    if new_total > old_total:
        raise AssertionError("ratchet attempted to increase debt allowance")
    if not set(
        tightened["allowances"]["potential_conflict_pairs"]
    ).issubset(old_conflicts):
        raise AssertionError(
            "ratchet attempted to increase potential conflict allowance"
        )
    return tightened
def _write_atomic(path: Path, content: str) -> None:
    """Write through a sibling temporary file to avoid partial baseline state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
def _load_baseline(path: Path) -> dict[str, Any]:
    data = load_yaml_unique(path)
    if not isinstance(data, dict):
        raise ValueError("baseline must contain a mapping")
    return data
def _print_text_result(
    *,
    comparison: dict[str, Any],
    census: dict[str, Any],
) -> None:
    status = comparison["status"].upper()
    summary = census["summary"]
    print(f"Doctrine ratchet: {status}")
    print(
        "  candidates: "
        f"{summary['candidate_count']}"
    )
    print(
        "  normative candidates: "
        f"{summary['normative_candidate_count']}"
    )
    print(
        "  current unowned debt: "
        f"{summary['unowned_debt_count']}"
    )
    print(
        "  potential conflict pairs: "
        f"{summary['potential_conflict_pair_count']}"
    )
    metrics = comparison.get("metrics")
    if metrics:
        print(
            "  baseline/current unowned occurrences: "
            f"{metrics['baseline_unowned_occurrences']}/"
            f"{metrics['current_unowned_occurrences']}"
        )
        print(
            "  baseline/current potential conflicts: "
            f"{metrics['baseline_potential_conflict_pairs']}/"
            f"{metrics['current_potential_conflict_pairs']}"
        )
    for error in comparison.get("configuration_errors", []):
        print(f"CONFIGURATION_ERROR: {error}", file=sys.stderr)
    for violation in comparison.get("violations", []):
        code = violation.get("code", "DOCTRINE_VIOLATION")
        representative = violation.get("representative", {})
        location = ""
        if representative:
            path = representative.get("path")
            line = representative.get("line_start")
            if path and line:
                location = f"{path}:{line}: "
        print(
            f"{code}: {location}{violation.get('message', '')}",
            file=sys.stderr,
        )
    if comparison.get("improvements"):
        print(
            f"  improvements detected: "
            f"{len(comparison['improvements'])}"
        )
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enforce the no-new-hidden-doctrine ratchet."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
    )
    parser.add_argument(
        "--registry",
        type=Path,
    )
    parser.add_argument(
        "--surface-mode",
        choices=("governance-text", "all-text"),
        default="governance-text",
    )
    parser.add_argument(
        "--include-code-fences",
        action="store_true",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "Create the initial baseline. Refuses to overwrite an existing "
            "baseline or bootstrap from a dirty workspace."
        ),
    )
    operation.add_argument(
        "--tighten",
        action="store_true",
        help=(
            "Monotonically reduce baseline allowances to current passing state."
        ),
    )
    parser.add_argument(
        "--reason",
        help="Required human-readable reason for --bootstrap.",
    )
    return parser.parse_args()
def main() -> int:
    args = _parse_args()
    try:
        root = args.root.resolve()
        baseline_path = (
            args.baseline
            if args.baseline.is_absolute()
            else root / args.baseline
        )
        census = build_census(
            root=root,
            surface_mode=args.surface_mode,
            include_archived=False,
            include_code_fences=args.include_code_fences,
            registry_path=args.registry,
        )
        if census["quality"]["error_count"]:
            result = {
                "status": "integrity_error",
                "configuration_errors": [],
                "violations": census["quality"]["findings"],
                "improvements": [],
            }
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "result": result,
                            "census_summary": census["summary"],
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
            else:
                _print_text_result(
                    comparison=result,
                    census=census,
                )
            return 2
        if args.bootstrap:
            if baseline_path.exists():
                raise ValueError(
                    f"baseline already exists at "
                    f"{baseline_path.relative_to(root)}; upward rebaselining "
                    "is intentionally unsupported"
                )
            if census["source"]["workspace_dirty"]:
                raise ValueError(
                    "refusing to bootstrap doctrine baseline from a dirty "
                    "workspace; baseline must bind a reviewable repository state"
                )
            if not args.reason:
                raise ValueError("--bootstrap requires --reason")
            baseline = build_baseline(
                census=census,
                reason=args.reason,
            )
            _write_atomic(
                baseline_path,
                dump_yaml(baseline),
            )
            print(
                "Doctrine baseline bootstrapped: "
                f"{baseline_path.relative_to(root)} "
                f"({census['summary']['unowned_debt_count']} "
                "legacy unowned occurrences)"
            )
            return 0
        if not baseline_path.is_file():
            raise ValueError(
                f"doctrine baseline missing at "
                f"{baseline_path.relative_to(root)}; perform one reviewed "
                "--bootstrap before enabling the ratchet gate"
            )
        baseline = _load_baseline(baseline_path)
        if args.tighten:
            tightened = tighten_baseline(
                census=census,
                baseline=baseline,
            )
            if dump_yaml(tightened) == dump_yaml(baseline):
                print("Doctrine baseline already matches current minimum debt.")
                return 0
            _write_atomic(
                baseline_path,
                dump_yaml(tightened),
            )
            previous = sum(
                int(item["max_count"])
                for item in baseline["allowances"]["unowned_debt"]
            )
            current = sum(
                int(item["max_count"])
                for item in tightened["allowances"]["unowned_debt"]
            )
            print(
                "Doctrine baseline tightened: "
                f"{previous} -> {current} allowed legacy occurrences."
            )
            return 0
        comparison = compare_to_baseline(
            census=census,
            baseline=baseline,
        )
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "result": comparison,
                        "census_summary": census["summary"],
                        "source": census["source"],
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _print_text_result(
                comparison=comparison,
                census=census,
            )
        status = comparison["status"]
        if status == "pass":
            return 0
        if status == "fail":
            return 1
        return 2
    except (
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        print(f"DOCTRINE_RATCHET_ERROR: {exc}", file=sys.stderr)
        return 2
if __name__ == "__main__":
    raise SystemExit(main())
