#!/usr/bin/env python3
"""Validate a codebase-only PR-remediation run report, fail closed."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "run-report.schema.json"
READY_BOOL_FIELDS = [
    "head_sha_matches_remote",
    "required_checks_green",
    "mergeable",
    "review_decision_acceptable",
    "worktree_clean",
]
FORBIDDEN_CI_MUTATION_PREFIXES = (
    ".github/workflows/",
    ".github/actions/",
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_errors(report: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except Exception:
        return ["validator dependency missing: jsonschema is required for authoritative validation"]
    schema = load(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"schema: {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(report), key=lambda item: list(item.path))
    ]


def is_forbidden_ci_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized.startswith(FORBIDDEN_CI_MUTATION_PREFIXES)


def invariants(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    run = report.get("run", {})
    preflight = report.get("preflight", {})
    cycles = report.get("cycles", [])
    gates = report.get("gates", {})
    findings = report.get("findings", {})
    signals = report.get("ci_pipeline_signals", [])
    readiness = report.get("pr_readiness", {})
    escalation = report.get("terminal_escalation", {})
    convergence = report.get("convergence", {})
    summary = report.get("summary", {})
    deliverable = report.get("deliverable", {})

    max_cycles = run.get("configured_max_cycles")
    pr = run.get("pr", {}) if isinstance(run.get("pr"), dict) else {}
    cycles_run = pr.get("cycles_run")
    if not isinstance(max_cycles, int) or not 1 <= max_cycles <= 3:
        errors.append("invariant: configured_max_cycles must be 1..3")
    if not isinstance(cycles_run, int) or not 0 <= cycles_run <= 3:
        errors.append("invariant: cycles_run must be 0..3")
    if isinstance(cycles_run, int) and len(cycles) != cycles_run:
        errors.append(f"invariant: cycles length {len(cycles)} != cycles_run {cycles_run}")
    if isinstance(max_cycles, int) and isinstance(cycles_run, int) and cycles_run > max_cycles:
        errors.append("invariant: cycles_run exceeds configured_max_cycles")

    pushes = 0
    commits: list[str] = []
    for index, cycle in enumerate(cycles, 1):
        if cycle.get("cycle_number") != index:
            errors.append(f"invariant: cycle {index} must have cycle_number {index}")
        if cycle.get("ci_pipeline_mutations_attempted") != 0:
            errors.append(f"invariant: cycle {index} attempted CI-pipeline mutation")
        push = cycle.get("push_count")
        commit = cycle.get("commit_sha")
        changes = cycle.get("changes_applied")
        if push == 1:
            pushes += 1
            if not commit:
                errors.append(f"invariant: cycle {index} pushed without commit_sha")
            else:
                commits.append(commit)
            if cycle.get("local_verify_green") is not True:
                errors.append(f"invariant: cycle {index} pushed before local verify")
            if not isinstance(changes, int) or changes < 1:
                errors.append(f"invariant: cycle {index} pushed with no codebase changes")
        elif push == 0 and commit is not None:
            errors.append(f"invariant: cycle {index} has commit_sha with zero pushes")

    push_record = gates.get("push_record", {})
    pr_push = push_record.get("push_count_this_cycle")
    pr_commit = push_record.get("commit_sha")
    changed_paths = push_record.get("changed_paths", [])
    if pr_push == 1 and not pr_commit:
        errors.append("invariant: final push record pushed without commit")
    if pr_push == 0 and pr_commit is not None:
        errors.append("invariant: final push record has commit with zero pushes")
    if push_record.get("ci_pipeline_files_in_commit") != 0:
        errors.append("invariant: CI-pipeline files must not enter the PR commit")
    if isinstance(changed_paths, list):
        for path in changed_paths:
            if isinstance(path, str) and (is_forbidden_ci_path(path) or path.startswith("issues/ci-pipeline/")):
                errors.append(f"invariant: forbidden CI-pipeline or handoff path in commit: {path}")
        if push_record.get("files_in_commit") != len(changed_paths):
            errors.append("invariant: files_in_commit must equal changed_paths length")

    local = gates.get("local_verify_log", {})
    registry = gates.get("gate_registry", {})
    if pr_push == 1:
        if local.get("all_green") is not True:
            errors.append("invariant: final push requires all_green local verification")
        if local.get("gates_run") != registry.get("locally_reproducible_gates"):
            errors.append("invariant: locally run gate count must equal locally reproducible gate count")

    reply = gates.get("reply_record", {})
    total = reply.get("threads_total")
    replied = reply.get("threads_replied")
    resolved = reply.get("threads_resolved")
    human = reply.get("threads_requiring_human")
    routed_ci = reply.get("threads_routed_ci")
    if all(isinstance(value, int) for value in (total, replied, resolved, human, routed_ci)):
        if replied != total:
            errors.append("invariant: every thread must receive exactly one reply")
        if resolved + human + routed_ci != total:
            errors.append("invariant: resolved + human + CI-routed threads must equal total threads")

    for item_index, item in enumerate(findings.get("applied", []) or []):
        if item.get("repair_domain") != "codebase":
            errors.append(f"invariant: findings.applied[{item_index}] is not codebase-owned")
        file_path = str(item.get("file", ""))
        if is_forbidden_ci_path(file_path):
            errors.append(f"invariant: applied finding targets forbidden CI path: {file_path}")
    for bucket in ("deferred", "rejected", "human_decision"):
        for item_index, item in enumerate(findings.get(bucket, []) or []):
            if not str(item.get("reason", "")).strip():
                errors.append(f"invariant: findings.{bucket}[{item_index}] requires a reason")

    if not isinstance(signals, list):
        errors.append("invariant: ci_pipeline_signals must be an array")
        signals = []
    fingerprints: set[str] = set()
    issue_paths: set[str] = set()
    blocking_ci_paths: set[str] = set()
    for index, signal in enumerate(signals):
        if not isinstance(signal, dict):
            errors.append(f"invariant: ci_pipeline_signals[{index}] must be an object")
            continue
        signal_id = signal.get("id", f"index-{index}")
        fingerprint = str(signal.get("fingerprint", ""))
        issue_path = str(signal.get("issue_file_path", ""))
        if fingerprint in fingerprints:
            errors.append(f"invariant: duplicate CI root-cause fingerprint: {fingerprint}")
        fingerprints.add(fingerprint)
        if issue_path in issue_paths:
            errors.append(f"invariant: duplicate CI issue-file path: {issue_path}")
        issue_paths.add(issue_path)
        if signal.get("repair_attempted") is not False:
            errors.append(f"invariant: CI repair attempted for {signal_id}")
        if signal.get("repository_files_modified") != []:
            errors.append(f"invariant: CI signal {signal_id} modified repository files")
        if signal.get("classification") != "CI_PIPELINE_SIGNAL":
            errors.append(f"invariant: CI signal {signal_id} classification invalid")
        if signal.get("downstream_owner") != "ci_remediation_agent":
            errors.append(f"invariant: CI signal {signal_id} has wrong downstream owner")
        if signal.get("source_repo") != run.get("repo"):
            errors.append(f"invariant: CI signal {signal_id} source_repo mismatch")
        if signal.get("source_pr") != pr.get("number"):
            errors.append(f"invariant: CI signal {signal_id} source_pr mismatch")
        if signal.get("blocks_pr") is True:
            blocking_ci_paths.add(issue_path)

    classified = gates.get("classified_findings", {})
    classified_ci = classified.get("ci_pipeline_signal", 0)
    if isinstance(classified_ci, int) and classified_ci < len(signals):
        errors.append("invariant: classified CI findings cannot be fewer than unique CI root causes")
    if reply.get("ci_issue_files_created") != len(signals):
        errors.append("invariant: reply_record.ci_issue_files_created must equal CI root-cause count")
    if summary.get("ci_pipeline_signals") != len(signals):
        errors.append("invariant: summary.ci_pipeline_signals must equal CI root-cause count")
    if deliverable.get("ci_issue_file_count") != len(signals):
        errors.append("invariant: deliverable.ci_issue_file_count must equal CI root-cause count")
    if deliverable.get("contains_ci_issue_files") is not (len(signals) > 0):
        errors.append("invariant: contains_ci_issue_files must reflect CI root-cause count")

    codebase_blockers = readiness.get("codebase_blockers_remaining")
    ci_blockers = readiness.get("ci_pipeline_blockers_remaining")
    total_blockers = readiness.get("blocking_findings_remaining")
    if all(isinstance(value, int) for value in (codebase_blockers, ci_blockers, total_blockers)):
        if total_blockers != codebase_blockers + ci_blockers:
            errors.append("invariant: blocking_findings_remaining must equal codebase + CI blockers")
        if ci_blockers != len(blocking_ci_paths):
            errors.append("invariant: ci_pipeline_blockers_remaining must equal blocking CI signals")

    ready = readiness.get("ready") is True
    if ready:
        for field in READY_BOOL_FIELDS:
            if readiness.get(field) is not True:
                errors.append(f"invariant: ready requires {field}=true")
        if readiness.get("draft") is not False:
            errors.append("invariant: ready requires draft=false")
        for field in (
            "actionable_threads_remaining",
            "human_decisions_remaining",
            "ci_pipeline_threads_remaining",
            "codebase_blockers_remaining",
            "ci_pipeline_blockers_remaining",
            "blocking_findings_remaining",
        ):
            if readiness.get(field) != 0:
                errors.append(f"invariant: ready requires {field}=0")

    status = convergence.get("convergence_status")
    exhausted = convergence.get("cycles_exhausted") is True
    mode = escalation.get("mode")
    human_remaining = readiness.get("human_decisions_remaining", 0)
    actionable_remaining = readiness.get("actionable_threads_remaining", 0)
    non_ci_blockers = sum(
        value for value in (codebase_blockers, human_remaining, actionable_remaining)
        if isinstance(value, int)
    )

    if status == "converged":
        if not ready:
            errors.append("invariant: converged requires pr_readiness.ready=true")
        if mode != "none":
            errors.append("invariant: converged run must not terminally escalate")
        if exhausted:
            errors.append("invariant: converged run cannot be cycles_exhausted")
    else:
        if ready:
            errors.append("invariant: non-converged run cannot claim ready=true")
        if isinstance(ci_blockers, int) and ci_blockers > 0 and non_ci_blockers == 0:
            if mode != "ci_signal_bundle":
                errors.append("invariant: CI-only blocker run must use ci_signal_bundle")
            elif set(escalation.get("issue_paths", [])) != blocking_ci_paths:
                errors.append("invariant: ci_signal_bundle paths must equal blocking CI issue paths")
        elif exhausted or status == "blocked":
            if mode not in {"github_issue", "fallback_artifact"}:
                errors.append("invariant: codebase/human blocked run requires terminal issue or fallback")

    if exhausted:
        if cycles_run != max_cycles:
            errors.append("invariant: cycles_exhausted requires cycles_run == configured_max_cycles")
    if isinstance(cycles_run, int) and isinstance(max_cycles, int) and cycles_run == max_cycles and status != "converged" and not exhausted:
        errors.append("invariant: non-converged max-cycle run must set cycles_exhausted=true")

    if convergence.get("pushes_total") != pushes:
        errors.append("invariant: convergence.pushes_total must equal cycle push sum")
    if convergence.get("commits_pushed") != commits:
        errors.append("invariant: commits_pushed must equal pushed cycle commit SHAs in order")
    if run.get("mode") == "dry_run" and pushes != 0:
        errors.append("invariant: dry_run cannot push")
    if preflight.get("mutation_authorized") is not True and pushes != 0:
        errors.append("invariant: unauthorized run cannot push")

    if mode in {"github_issue", "fallback_artifact"}:
        connected = preflight.get("github_connection_established") is True
        repo_resolved = preflight.get("repo_resolved") is True
        issue_write = preflight.get("issue_write_available") is True
        if connected and repo_resolved and issue_write:
            if mode == "fallback_artifact" and not escalation.get("creation_attempted"):
                errors.append("invariant: connected writable GitHub path must attempt codebase issue creation before fallback")
            if mode == "fallback_artifact" and not escalation.get("creation_error"):
                errors.append("invariant: failed GitHub issue attempt requires creation_error")
        elif mode != "fallback_artifact":
            errors.append("invariant: unavailable GitHub issue path requires fallback_artifact")
    if mode == "ci_signal_bundle" and escalation.get("creation_attempted") is not False:
        errors.append("invariant: ci_signal_bundle must not attempt consumer-repo issue creation")

    required_delivery = (
        "created",
        "contains_run_report",
        "contains_convergence_report",
        "contains_pr_ready_evidence",
    )
    if any(deliverable.get(field) is not True for field in required_delivery):
        errors.append("invariant: final deterministic deliverable is mandatory")
    if mode == "fallback_artifact" and deliverable.get("contains_issue_fallback") is not True:
        errors.append("invariant: fallback issue must be included in deliverable")
    return errors


def validate(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["structure: report root must be object"]
    return schema_errors(report) + invariants(report)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_report")
    args = parser.parse_args()
    path = Path(args.run_report)
    if not path.is_file():
        print(f"FAIL: not a file: {path}", file=sys.stderr)
        return 2
    try:
        report = load(path)
    except Exception as exc:
        print(f"FAIL: cannot parse report: {exc}", file=sys.stderr)
        return 2
    errors = validate(report)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: run report validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
