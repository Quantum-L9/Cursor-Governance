#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import load_json, matches_any, run, safe_cli_path, utc_now, write_json
from validate_contract import validate

FORBIDDEN_ADDED_LINE_PATTERNS = {
    "unfinished_marker": re.compile(r"\b(?:TBD|TO_BE_DECIDED|INSERT_HERE)\b", re.I),
    # Match only real VCS conflict markers (git's 7-char forms), not decorative
    # `====`/`----` documentation underlines: the opener/closer need a trailing space
    # or end-of-line, and the separator is exactly seven `=` (mirrors audit_repository).
    "conflict_marker": re.compile(r"^(?:<<<<<<<(?:\s|$)|={7}$|>>>>>>>(?:\s|$))"),
    "placeholder_ellipsis": re.compile(r"(?:implement here|placeholder|pseudo[- ]?code)", re.I),
}


def changed_files(repo: Path, base_ref: str) -> tuple[list[str], str | None]:
    merge_base = run(["git", "merge-base", base_ref, "HEAD"], cwd=repo, timeout=30)
    if merge_base["exit_code"] != 0:
        return [], f"cannot resolve merge-base with {base_ref}: {merge_base['output'].strip()}"
    base = merge_base["output"].strip()
    committed = run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=repo, timeout=30)
    working = run(["git", "diff", "--name-only"], cwd=repo, timeout=30)
    staged = run(["git", "diff", "--cached", "--name-only"], cwd=repo, timeout=30)
    if any(item["exit_code"] != 0 for item in (committed, working, staged)):
        return [], "failed to enumerate changed files"
    names = set()
    for result in (committed, working, staged):
        names.update(line.strip() for line in result["output"].splitlines() if line.strip())
    return sorted(names), None


def added_lines(repo: Path, base_ref: str) -> tuple[list[dict[str, Any]], str | None]:
    merge_base = run(["git", "merge-base", base_ref, "HEAD"], cwd=repo, timeout=30)
    if merge_base["exit_code"] != 0:
        return [], f"cannot resolve merge-base with {base_ref}"
    base = merge_base["output"].strip()
    commands = [
        ["git", "diff", "--unified=0", f"{base}...HEAD"],
        ["git", "diff", "--unified=0"],
        ["git", "diff", "--cached", "--unified=0"],
    ]
    records: list[dict[str, Any]] = []
    for command in commands:
        result = run(command, cwd=repo, timeout=60)
        if result["exit_code"] != 0:
            return [], f"failed to inspect added lines: {result['command_text']}"
        current_path = ""
        for line in result["output"].splitlines():
            if line.startswith("+++ b/"):
                current_path = line[6:]
            elif line.startswith("+") and not line.startswith("+++"):
                records.append({"path": current_path, "text": line[1:]})
    return records, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a repository renovation PR pack.")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("pr-pack-validation.json"))
    args = parser.parse_args()

    repo = args.repo.resolve()
    contract = load_json(args.contract)
    evidence = load_json(args.evidence)
    before = load_json(args.before)
    after = load_json(args.after)
    errors = validate(contract)

    if evidence.get("contract_id") != contract.get("contract_id"):
        errors.append("validation evidence contract_id does not match")
    if evidence.get("status") != "passed":
        errors.append("validation evidence is not passed")
    required_ids = {
        item["id"] for item in contract.get("validation_matrix", []) if item.get("required", True)
    }
    passed_ids = {item["id"] for item in evidence.get("records", []) if item.get("exit_code") == 0}
    missing = sorted(required_ids - passed_ids)
    if missing:
        errors.append(f"required validation records missing or failed: {', '.join(missing)}")

    if before.get("audit_id") == after.get("audit_id") and before.get("findings") != after.get(
        "findings"
    ):
        errors.append("before and after audits share an id but differ in content")
    after_high = [
        item for item in after.get("findings", []) if item.get("severity") in {"critical", "high"}
    ]
    before_high_ids = {
        item["id"]
        for item in before.get("findings", [])
        if item.get("severity") in {"critical", "high"}
    }
    introduced_high = [item for item in after_high if item.get("id") not in before_high_ids]
    if introduced_high:
        errors.append("after audit introduces new high or critical findings")

    # Prefer the immutable base_commit; base_ref can move and misalign the baseline.
    # Access defensively: a malformed contract must yield a clean failure, not a crash.
    repository = contract.get("repository") if isinstance(contract.get("repository"), dict) else {}
    base = repository.get("base_commit") or repository.get("base_ref")
    changed: list[str] = []
    lines: list[dict[str, Any]] = []
    outside: list[str] = []
    forbidden_changed: list[str] = []
    if not isinstance(base, str) or not base:
        errors.append("contract repository base_commit/base_ref is missing or invalid")
    else:
        changed, changed_error = changed_files(repo, base)
        if changed_error:
            errors.append(changed_error)
        allowed = contract.get("scope", {}).get("allowed_paths", [])
        forbidden = contract.get("scope", {}).get("forbidden_paths", [])
        outside = [path for path in changed if not matches_any(path, allowed)]
        forbidden_changed = [path for path in changed if matches_any(path, forbidden)]
        if outside:
            errors.append(f"changed files outside allowed scope: {', '.join(outside)}")
        if forbidden_changed:
            errors.append(f"forbidden paths changed: {', '.join(forbidden_changed)}")

        lines, line_error = added_lines(repo, base)
        if line_error:
            errors.append(line_error)
    marker_hits: list[dict[str, str]] = []
    for record in lines:
        for name, pattern in FORBIDDEN_ADDED_LINE_PATTERNS.items():
            if pattern.search(record["text"]):
                marker_hits.append(
                    {"kind": name, "path": record["path"], "text": record["text"][:300]}
                )
    if marker_hits:
        errors.append("new unfinished or conflict markers exist in the change set")

    diff_check = run(["git", "diff", "--check"], cwd=repo, timeout=60)
    if diff_check["exit_code"] != 0:
        errors.append("git diff --check failed")

    payload = {
        "schema_version": "pr-pack-validation-1.0",
        "generated_at": utc_now(),
        "contract_id": contract.get("contract_id"),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "changed_files": changed,
        "outside_scope": outside,
        "forbidden_changed": forbidden_changed,
        "marker_hits": marker_hits,
        "validation_records": sorted(passed_ids),
        "diff_check": diff_check,
    }
    write_json(safe_cli_path(args.output), payload)
    print(
        json.dumps(
            {"status": payload["status"], "changed_files": len(changed), "errors": errors}, indent=2
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
