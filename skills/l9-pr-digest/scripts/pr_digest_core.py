#!/usr/bin/env python3
"""Deterministic decision engine for l9-pr-digest."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pr_evidence import (
    BINARY,
    CI_ACCEPT,
    CI_FAIL,
    DEPS,
    GENERATED,
    GOV_PREFIX,
    LOCKS,
    MANIFESTS,
    PATTERNS,
    added_lines,
    format_only,
    git_patches,
    growth,
    intent_of,
    is_test,
    question,
    tokens,
)

SCHEMA = "l9.pr_digest.v1"
DECISIONS = {
    "READY_FOR_REMEDIATION",
    "READY_WITH_NON_BLOCKING_NOTES",
    "NARROW_BEFORE_REMEDIATION",
    "ARCHITECTURE_REPAIR_BEFORE_REMEDIATION",
    "CI_OR_EXECUTION_FAILURE",
    "INTENT_UNKNOWN_REVIEW_REQUIRED",
    "BLOCKED",
    "UNKNOWN",
}


def _changed_paths(files: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    paths = [str(item.get("path") or "") for item in files]
    added = [
        str(item.get("path") or "")
        for item in files
        if str(item.get("status") or "").lower() in {"added", "a"}
    ]
    deleted = [
        str(item.get("path") or "")
        for item in files
        if str(item.get("status") or "").lower() in {"deleted", "removed", "d"}
    ]
    return paths, added, deleted


def _structural_growth(
    added_paths: list[str],
    base_top: set[str],
    expansion: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> None:
    if base_top:
        added_top = {path.split("/", 1)[0] for path in added_paths if "/" in path}
        for directory in sorted(added_top - base_top):
            expansion.append(growth("new_top_level_directory", directory))
            questions.append(
                question(
                    "new_top_level_directory",
                    [directory],
                    "Is this new top-level owner required or duplicating an existing owner?",
                )
            )
    grouped: dict[tuple[str, str], list[str]] = {}
    for path in added_paths:
        low = path.lower()
        kind: str | None = None
        owner = path
        if "/adapters/" in low:
            before, after = path.split("/adapters/", 1)
            owner = f"{before}/adapters/{after.split('/', 1)[0]}"
            kind = "new_adapter"
        elif low.endswith(("_adapter.py", "adapter.py")):
            kind = "new_adapter"
        elif "registry" in Path(low).name:
            kind = "new_registry"
        elif "factory" in Path(low).name:
            kind = "new_factory"
        elif low.endswith(("_service.py", "service.py")):
            kind = "new_service"
        elif low.endswith(".schema.json"):
            kind, owner = "new_schema", str(Path(path).parent)
        if kind:
            grouped.setdefault((kind, owner), []).append(path)
    for (kind, owner), evidence_paths in sorted(grouped.items()):
        if kind == "new_adapter" and "/adapters/" in owner and len(evidence_paths) < 2:
            continue
        expansion.append(growth(kind, owner))
        questions.append(
            question(
                kind,
                evidence_paths,
                f"Is this {kind.replace('_', ' ')} required and canonically owned?",
            )
        )


def _patch_findings(
    files: list[dict[str, Any]],
    flag: Any,
    expansion: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> None:
    hits: dict[str, list[str]] = {code: [] for code in PATTERNS}
    format_candidates = 0
    for item in files:
        path = str(item.get("path") or "")
        patch = str(item.get("patch") or "")
        plus = added_lines(patch)
        if patch and format_only(patch):
            format_candidates += 1
        for code, pattern in PATTERNS.items():
            if plus and pattern.search(plus):
                hits[code].append(path)
                severity = "blocking_review" if code == "suppression_or_ignore_added" else "review"
                flag(code, path, f"added lines matched deterministic {code} pattern", severity)
        if plus and re.search(r"(?m)^\s*TODO\b", plus):
            flag("TODO_added", path, "TODO marker added")
    if len(files) >= 8 and format_candidates >= max(4, len(files) // 2):
        flag(
            "broad_formatting_noise",
            None,
            f"{format_candidates}/{len(files)} changed files appear formatting-heavy",
        )
    structural_codes = (
        "new_registry",
        "new_factory",
        "new_adapter",
        "new_service",
        "compatibility_layer_added",
        "feature_flag_added",
    )
    for code in structural_codes:
        for path in hits[code]:
            expansion.append(growth(code.replace("_added", ""), path))
            questions.append(
                question(
                    code,
                    [path],
                    f"Is this {code.replace('_', ' ')} necessary or duplicate architecture?",
                )
            )


def _decision(
    ci_failure: bool,
    flags: list[dict[str, Any]],
    intent_source: str,
    questions: list[dict[str, Any]],
    expansion: list[dict[str, Any]],
    narrowing: list[dict[str, Any]],
    unknowns: list[str],
) -> str:
    if ci_failure:
        return "CI_OR_EXECUTION_FAILURE"
    if "PR_file_inventory_truncated" in unknowns:
        return "BLOCKED"
    if any(item["severity"] == "blocking" for item in flags):
        return "BLOCKED"
    if any(item["severity"] == "blocking_review" for item in flags):
        return "BLOCKED"
    if intent_source == "UNKNOWN" and (questions or expansion):
        return "INTENT_UNKNOWN_REVIEW_REQUIRED"
    if questions:
        return "UNKNOWN"
    if narrowing:
        return "NARROW_BEFORE_REMEDIATION"
    if unknowns:
        if unknowns == ["CI_evidence_missing"]:
            return "READY_WITH_NON_BLOCKING_NOTES"
        return "UNKNOWN"
    if flags:
        return "READY_WITH_NON_BLOCKING_NOTES"
    return "READY_FOR_REMEDIATION"


def digest(evidence: dict[str, Any], workspace: Path | None = None) -> dict[str, Any]:
    base, head = evidence.get("base_sha"), evidence.get("head_sha")
    merge_base, patches = git_patches(workspace, base, head)
    files: list[dict[str, Any]] = []
    for raw in evidence.get("files") or []:
        item = dict(raw)
        path = str(item.get("path") or "")
        if not item.get("patch") and path in patches:
            item["patch"] = patches[path]
        files.append(item)

    intent, intent_source = intent_of(evidence)
    flags: list[dict[str, Any]] = []
    expansion: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    unknowns: list[str] = []
    if not base or not head:
        unknowns.append("exact_base_or_head_sha_missing")
    if intent_source == "UNKNOWN":
        unknowns.append("original_intent_unavailable")

    def flag(code: str, path: str | None, detail: str, severity: str = "review") -> None:
        flags.append({"code": code, "path": path, "detail": detail, "severity": severity})

    title_tokens = tokens(str(evidence.get("title") or ""))
    outcome_tokens = tokens(str(intent.get("requested_outcome") or ""))
    intent_conflicts = (
        intent_source == "pr_body"
        and len(title_tokens) >= 2
        and len(outcome_tokens) >= 2
        and not title_tokens & outcome_tokens
    )
    if intent_conflicts:
        flag(
            "title_body_intent_mismatch",
            None,
            "PR title and explicit body intent section share no material terms",
        )
        questions.append(
            question(
                "intent_conflict",
                [],
                "Which intent source is authoritative: PR title or conflicting PR body?",
            )
        )

    paths, added_paths, deleted_paths = _changed_paths(files)
    dependency_paths = [path for path in paths if Path(path).name in DEPS]
    for path in dependency_paths:
        flag(
            "new_dependency_or_dependency_surface",
            path,
            "dependency manifest or lock surface changed",
        )
        expansion.append(growth("dependency_change", path))
    _structural_growth(
        added_paths,
        set(evidence.get("base_top_level_directories") or []),
        expansion,
        questions,
    )

    governance_files = {"Makefile", "AGENTS.md", "CANONICAL_LAW.md"}
    governance_paths = [
        path for path in paths if path.startswith(GOV_PREFIX) or path in governance_files
    ]
    if governance_paths:
        flag("workflow_or_governance_change", None, "workflow/governance surface changed")
        questions.append(
            question(
                "governance_scope",
                governance_paths,
                "Is this governance change required by the PR intent?",
            )
        )

    production = [
        path
        for path in paths
        if not is_test(path) and Path(path).suffix.lower() not in {".md", ".rst", ".txt"}
    ]
    tests = [path for path in paths if is_test(path)]
    if production and not tests:
        flag(
            "production_code_without_tests",
            None,
            "production surface changed with no test file in the diff",
        )
    for path in deleted_paths:
        if is_test(path):
            flag("deleted_test", path, "executable test file deleted", "blocking_review")

    binaries = [path for path in paths if Path(path).suffix.lower() in BINARY]
    for path in binaries:
        flag("unexpected_binary", path, "binary/package artifact changed")
    if binaries:
        questions.append(
            question(
                "binary_change",
                binaries,
                "Are these binary/package artifacts required and source-traceable?",
            )
        )

    lockfiles = {Path(path).name for path in paths if Path(path).name in LOCKS}
    manifests = {Path(path).name for path in paths if Path(path).name in MANIFESTS}
    if lockfiles and not manifests:
        flag(
            "unrelated_lockfile_churn",
            None,
            f"lockfile changed without source manifest: {sorted(lockfiles)}",
        )
    generated = [path for path in paths if any(hint in path.lower() for hint in GENERATED)]
    if generated and not [path for path in paths if path not in generated]:
        flag(
            "generated_file_changed_without_source_change",
            None,
            "generated-looking files changed without observable source",
        )
    _patch_findings(files, flag, expansion, questions)

    checks = [
        {
            "name": str(check.get("name") or "UNKNOWN"),
            "conclusion": str(check.get("conclusion") or "UNKNOWN"),
        }
        for check in evidence.get("ci_checks") or []
    ]
    required_names = {str(name) for name in (evidence.get("required_check_names") or []) if name}
    relevant_checks = (
        [check for check in checks if check["name"] in required_names] if required_names else checks
    )
    if required_names:
        ci_failure = any(check["conclusion"].lower() in CI_FAIL for check in relevant_checks)
    else:
        ci_failure = False
        if any(check["conclusion"].lower() in CI_FAIL for check in checks):
            unknowns.append("CI_required_set_unavailable")
    if evidence.get("files_truncated"):
        unknowns.append("PR_file_inventory_truncated")
    if not checks:
        unknowns.append("CI_evidence_missing")
    elif any(check["conclusion"].lower() not in CI_FAIL | CI_ACCEPT for check in checks):
        unknowns.append("CI_evidence_incomplete")

    narrowing = [
        {
            "reason": item["code"],
            "path": item["path"],
            "action": "remove_or_justify_before_remediation",
        }
        for item in flags
        if item["code"] in {"suppression_or_ignore_added", "deleted_test"}
    ]
    decision = _decision(
        ci_failure, flags, intent_source, questions, expansion, narrowing, unknowns
    )
    remediation_findings = [
        {
            "code": item["code"],
            "path": item["path"],
            "detail": item["detail"],
            "action": "inspect_and_fix_only_if_validated",
        }
        for item in flags
        if item["code"] != "broad_formatting_noise"
    ]
    return {
        "schema": SCHEMA,
        "PR_identity": {
            "repository": evidence.get("repository"),
            "pr_number": evidence.get("pr_number"),
            "base_ref": evidence.get("base_ref"),
            "base_sha": base,
            "head_ref": evidence.get("head_ref"),
            "head_sha": head,
            "merge_base": merge_base,
            "commits": evidence.get("commits") or [],
        },
        "intent_identity": {"source": intent_source, **intent},
        "evidence": {
            "files": files,
            "diff_summary": {
                "changed_files": len(files),
                "lines_added": sum(int(item.get("additions") or 0) for item in files),
                "lines_deleted": sum(int(item.get("deletions") or 0) for item in files),
                "files_added": len(added_paths),
                "files_deleted": len(deleted_paths),
                "test_files": tests,
                "production_files": production,
                "dependency_files": dependency_paths,
                "binary_files": binaries,
                "generated_like_files": generated,
            },
            "CI_checks": checks,
        },
        "deterministic_findings": flags,
        "judgement_findings": [],
        "expansion_items": expansion,
        "required_narrowing": narrowing,
        "remediation_findings": remediation_findings,
        "unknowns": sorted(set(unknowns)),
        "decision": decision,
        "confidence": "deterministic_evidence_only",
        "LLM_judgement_used": False,
        "LLM_judgement_questions": questions,
        "remediation_packet": {
            "PR_base_and_head": {"base_sha": base, "head_sha": head},
            "accepted_change_scope": [
                item
                for item in (intent.get("explicit_scope") or [intent.get("requested_outcome")])
                if item
            ],
            "files_or_symbols_requiring_attention": sorted(
                {item.get("path") for item in flags if item.get("path")}
            ),
            "findings_to_fix": remediation_findings,
            "expansion_to_remove": narrowing,
            "architecture_invariants_to_preserve": [],
            "tests_to_add_or_repair": [
                item["path"]
                for item in flags
                if item["code"] == "deleted_test" and item.get("path")
            ],
            "CI_failures_relevant_to_remediation": [
                check for check in checks if check["conclusion"].lower() in CI_FAIL
            ],
            "explicit_non_goals": intent.get("explicit_non_goals") or [],
            "UNKNOWNs": sorted(set(unknowns)),
            "acceptance_criteria": intent.get("acceptance_criteria") or [],
        },
    }


def validate(doc: dict[str, Any]) -> list[str]:
    required = {
        "PR_identity",
        "intent_identity",
        "evidence",
        "deterministic_findings",
        "judgement_findings",
        "expansion_items",
        "required_narrowing",
        "remediation_findings",
        "unknowns",
        "decision",
        "confidence",
        "LLM_judgement_used",
        "LLM_judgement_questions",
        "remediation_packet",
    }
    errors = [f"missing required field: {field}" for field in sorted(required - set(doc))]
    if doc.get("decision") not in DECISIONS:
        errors.append("invalid decision")
    identity = doc.get("PR_identity") or {}
    if not identity.get("base_sha") or not identity.get("head_sha"):
        errors.append("exact base/head SHA not bound")
    packet = doc.get("remediation_packet") or {}
    packet_required = {
        "PR_base_and_head",
        "accepted_change_scope",
        "files_or_symbols_requiring_attention",
        "findings_to_fix",
        "expansion_to_remove",
        "architecture_invariants_to_preserve",
        "tests_to_add_or_repair",
        "CI_failures_relevant_to_remediation",
        "explicit_non_goals",
        "UNKNOWNs",
        "acceptance_criteria",
    }
    errors.extend(
        f"missing remediation_packet field: {field}"
        for field in sorted(packet_required - set(packet))
    )
    return errors
