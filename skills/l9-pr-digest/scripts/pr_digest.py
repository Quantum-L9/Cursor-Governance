#!/usr/bin/env python3
"""Deterministic, read-only PR digest for the L9 pre-remediation gate."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "l9.pr_digest.v1"
DECISIONS = {
    "READY_FOR_REMEDIATION", "READY_WITH_NON_BLOCKING_NOTES",
    "NARROW_BEFORE_REMEDIATION", "ARCHITECTURE_REPAIR_BEFORE_REMEDIATION",
    "CI_OR_EXECUTION_FAILURE", "INTENT_UNKNOWN_REVIEW_REQUIRED", "BLOCKED", "UNKNOWN",
}
CI_FAIL = {"failure", "failed", "cancelled", "timed_out", "action_required"}
CI_ACCEPT = {"success", "skipped", "neutral"}
DEPS = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "poetry.lock", "uv.lock",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.toml",
    "Cargo.lock", "go.mod", "go.sum",
}
LOCKS = {"poetry.lock", "uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock", "go.sum"}
MANIFESTS = {"requirements.txt", "requirements-dev.txt", "pyproject.toml", "package.json", "Cargo.toml", "go.mod"}
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz", ".whl", ".bin", ".exe", ".dmg"}
GOV_PREFIX = (".github/workflows/", "rules/", "ops/config/", "skills/AUTONOMY_MANIFEST.yaml")
GENERATED = ("generated/", "dist/", "build/", "manifest.json", "skill-registry.json")
PATTERNS = {
    "new_registry": re.compile(r"\b(class|def)\s+\w*Registry\b|\bregistry\s*=", re.I),
    "new_factory": re.compile(r"\b(class|def)\s+\w*Factory\b|\bfactory\s*=", re.I),
    "new_adapter": re.compile(r"\b(class|def)\s+\w*Adapter\b", re.I),
    "new_service": re.compile(r"\b(class|def)\s+\w*Service\b", re.I),
    "compatibility_layer_added": re.compile(r"\bcompat(?:ibility)?\b|\blegacy\b|\bbackward[- ]compat", re.I),
    "feature_flag_added": re.compile(r"\bfeature[_ -]?flag\b|\bENABLE_[A-Z0-9_]+\b"),
    "suppression_or_ignore_added": re.compile(r"#\s*noqa\b|type:\s*ignore|eslint-disable|NOSONAR|continue-on-error", re.I),
    "timeout_or_retry_increase": re.compile(r"\b(timeout|max_retries|retries|retry_count)\b", re.I),
    "debug_artifact": re.compile(r"\bprint\s*\(|console\.log\s*\(|breakpoint\s*\(|pdb\.set_trace", re.I),
    "placeholder_added": re.compile(r"\b(?:FIXME|TBD|PLACEHOLDER)\b", re.I),
}


def run(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=False)
    if proc.returncode:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout


def live_evidence(repo: str, pr: int, workspace: Path | None) -> dict[str, Any]:
    fields = "number,title,body,baseRefName,baseRefOid,headRefName,headRefOid,commits,files,statusCheckRollup"
    doc = json.loads(run(["gh", "pr", "view", str(pr), "--repo", repo, "--json", fields], workspace))
    return {
        "repository": repo,
        "pr_number": doc.get("number"),
        "title": doc.get("title") or "",
        "body": doc.get("body") or "",
        "base_ref": doc.get("baseRefName"),
        "base_sha": doc.get("baseRefOid"),
        "head_ref": doc.get("headRefName"),
        "head_sha": doc.get("headRefOid"),
        "commits": [c.get("oid") for c in doc.get("commits", []) if c.get("oid")],
        "files": [
            {"path": f.get("path"), "status": f.get("status") or "modified",
             "additions": int(f.get("additions") or 0), "deletions": int(f.get("deletions") or 0), "patch": None}
            for f in doc.get("files", [])
        ],
        "ci_checks": [
            {"name": c.get("name") or c.get("context") or "UNKNOWN",
             "conclusion": c.get("conclusion") or c.get("state") or "UNKNOWN"}
            for c in doc.get("statusCheckRollup") or []
        ],
    }


def git_patches(workspace: Path | None, base: str | None, head: str | None) -> tuple[str | None, dict[str, str]]:
    if not workspace or not base or not head:
        return None, {}
    try:
        merge_base = run(["git", "merge-base", base, head], workspace).strip() or None
        text = run(["git", "diff", "--no-ext-diff", "--unified=1", base, head], workspace)
    except RuntimeError:
        return None, {}
    patches: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            patches.setdefault(current, [])
        if current:
            patches[current].append(line)
    return merge_base, {path: "\n".join(lines) for path, lines in patches.items()}


def section_line(text: str, names: tuple[str, ...]) -> str | None:
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        match = re.match(r"^#+\s*(.+?)\s*$", raw.strip())
        if not match or match.group(1).strip().lower() not in names:
            continue
        for line in lines[idx + 1:]:
            value = line.strip()
            if value.startswith("#"):
                break
            if value and not value.startswith("<!--"):
                return value.lstrip("-* ")[:1000]
    return None


def non_goals(text: str) -> list[str]:
    out: list[str] = []
    active = False
    for raw in text.splitlines():
        value = raw.strip()
        if re.match(r"^#+\s*(non[- ]?goals?|out of scope)\b", value, re.I):
            active = True
            continue
        if active and value.startswith("#"):
            break
        if active and value.startswith(("-", "*")):
            out.append(value[1:].strip())
    return out[:30]


def intent_of(evidence: dict[str, Any]) -> tuple[dict[str, Any], str]:
    explicit = evidence.get("intent")
    if isinstance(explicit, dict) and explicit.get("requested_outcome"):
        return explicit, "explicit_task_contract"
    body = str(evidence.get("body") or "").strip()
    title = str(evidence.get("title") or "").strip()
    if body:
        outcome = section_line(body, ("problem", "objective", "why", "summary"))
        if not outcome:
            outcome = next((line.strip(" -*#\t") for line in body.splitlines() if line.strip() and not line.lstrip().startswith("<!--")), None)
        return {"requested_outcome": outcome, "explicit_scope": [], "explicit_non_goals": non_goals(body),
                "acceptance_criteria": [], "source_excerpt": body[:4000], "pr_title": title or None}, "pr_body"
    if title:
        return {"requested_outcome": title, "explicit_scope": [], "explicit_non_goals": [],
                "acceptance_criteria": [], "source_excerpt": title, "pr_title": title}, "pr_title"
    return {"requested_outcome": None, "explicit_scope": [], "explicit_non_goals": [],
            "acceptance_criteria": [], "source_excerpt": None}, "UNKNOWN"


def tokens(text: str | None) -> set[str]:
    stop = {"the", "and", "for", "with", "this", "that", "from", "into", "apply", "feat", "fix", "chore", "style"}
    return {word for word in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(word) >= 4 and word not in stop}


def is_test(path: str) -> bool:
    p = Path(path.lower())
    if {"test", "tests"} & set(p.parts[:-1]):
        return True
    name = p.name
    if not name.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java")):
        return False
    return name.startswith("test_") or name.endswith("_test.py") or ".spec." in name or ".test." in name


def added_lines(patch: str) -> str:
    return "\n".join(line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))


def format_only(patch: str) -> bool:
    added = [line[1:].strip() for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line[1:].strip() for line in patch.splitlines() if line.startswith("-") and not line.startswith("---")]
    return bool(added and removed and sorted(added) == sorted(removed))


def question(code: str, paths: list[str], text: str) -> dict[str, Any]:
    return {"code": code, "evidence_paths": sorted(set(paths)), "question": text}


def growth(kind: str, path: str) -> dict[str, Any]:
    return {"kind": kind, "path": path, "classification": "UNKNOWN", "evidence": "deterministic_diff"}


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
    if intent_source == "pr_body" and len(title_tokens) >= 2 and len(outcome_tokens) >= 2 and not title_tokens & outcome_tokens:
        flag("title_body_intent_mismatch", None, "PR title and explicit body intent section share no material terms")
        questions.append(question("intent_conflict", [], "Which intent source is authoritative: the PR title or the conflicting PR body task statement?"))

    paths = [str(item.get("path") or "") for item in files]
    added_paths = [str(item.get("path") or "") for item in files if str(item.get("status") or "").lower() in {"added", "a"}]
    deleted_paths = [str(item.get("path") or "") for item in files if str(item.get("status") or "").lower() in {"deleted", "removed", "d"}]
    dependency_paths = [path for path in paths if Path(path).name in DEPS]
    for path in dependency_paths:
        flag("new_dependency_or_dependency_surface", path, "dependency manifest or lock surface changed")
        expansion.append(growth("dependency_change", path))

    base_top = set(evidence.get("base_top_level_directories") or [])
    if base_top:
        for directory in sorted({path.split("/", 1)[0] for path in added_paths if "/" in path} - base_top):
            expansion.append(growth("new_top_level_directory", directory))
            questions.append(question("new_top_level_directory", [directory], "Is this genuinely new top-level owner required by the task or duplicating an existing owner?"))

    structural: dict[tuple[str, str], list[str]] = {}
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
            structural.setdefault((kind, owner), []).append(path)
    for (kind, owner), evidence_paths in sorted(structural.items()):
        if kind == "new_adapter" and "/adapters/" in owner and len(evidence_paths) < 2:
            continue
        expansion.append(growth(kind, owner))
        questions.append(question(kind, evidence_paths, f"Is this {kind.replace('_', ' ')} required by the task and owned by the canonical seam?"))

    governance_paths = [path for path in paths if path.startswith(GOV_PREFIX) or path in {"Makefile", "AGENTS.md", "CANONICAL_LAW.md"}]
    if governance_paths:
        flag("workflow_or_governance_change", None, "workflow/governance surface changed")
        questions.append(question("governance_scope", governance_paths, "Is this governance change required by the PR intent?"))

    production = [path for path in paths if not is_test(path) and Path(path).suffix.lower() not in {".md", ".rst", ".txt"}]
    tests = [path for path in paths if is_test(path)]
    if production and not tests:
        flag("production_code_without_tests", None, "production surface changed with no test file in the diff")
    for path in deleted_paths:
        if is_test(path):
            flag("deleted_test", path, "executable test file deleted", "blocking_review")

    binaries = [path for path in paths if Path(path).suffix.lower() in BINARY]
    for path in binaries:
        flag("unexpected_binary", path, "binary/package artifact changed")
    if binaries:
        questions.append(question("binary_change", binaries, "Are these binary/package artifacts explicitly required and source-traceable for the stated PR intent?"))

    lockfiles = {Path(path).name for path in paths if Path(path).name in LOCKS}
    manifests = {Path(path).name for path in paths if Path(path).name in MANIFESTS}
    if lockfiles and not manifests:
        flag("unrelated_lockfile_churn", None, f"lockfile changed without source manifest: {sorted(lockfiles)}")
    generated = [path for path in paths if any(hint in path.lower() for hint in GENERATED)]
    if generated and not [path for path in paths if path not in generated]:
        flag("generated_file_changed_without_source_change", None, "generated-looking files changed without observable source")

    pattern_hits: dict[str, list[str]] = {code: [] for code in PATTERNS}
    format_candidates = 0
    for item in files:
        path, patch = str(item.get("path") or ""), str(item.get("patch") or "")
        plus = added_lines(patch)
        if patch and format_only(patch):
            format_candidates += 1
        for code, pattern in PATTERNS.items():
            if plus and pattern.search(plus):
                pattern_hits[code].append(path)
                flag(code, path, f"added lines matched deterministic {code} pattern", "blocking_review" if code == "suppression_or_ignore_added" else "review")
        if plus and re.search(r"(?m)^\s*TODO\b", plus):
            flag("TODO_added", path, "TODO marker added")
    if len(files) >= 8 and format_candidates >= max(4, len(files) // 2):
        flag("broad_formatting_noise", None, f"{format_candidates}/{len(files)} changed files appear formatting-heavy")
    for code in ("new_registry", "new_factory", "new_adapter", "new_service", "compatibility_layer_added", "feature_flag_added"):
        for path in pattern_hits[code]:
            expansion.append(growth(code.replace("_added", ""), path))
            questions.append(question(code, [path], f"Is this {code.replace('_', ' ')} necessary, or anticipatory/duplicate architecture?"))

    checks = [{"name": str(check.get("name") or "UNKNOWN"), "conclusion": str(check.get("conclusion") or "UNKNOWN")} for check in evidence.get("ci_checks") or []]
    ci_failure = any(check["conclusion"].lower() in CI_FAIL for check in checks)
    if not checks:
        unknowns.append("CI_evidence_missing")
    elif any(check["conclusion"].lower() not in CI_FAIL | CI_ACCEPT for check in checks):
        unknowns.append("CI_evidence_incomplete")

    narrowing = [
        {"reason": item["code"], "path": item["path"], "action": "remove_or_justify_before_remediation"}
        for item in flags if item["code"] in {"suppression_or_ignore_added", "deleted_test"}
    ]
    if ci_failure:
        decision = "CI_OR_EXECUTION_FAILURE"
    elif any(item["severity"] == "blocking" for item in flags):
        decision = "BLOCKED"
    elif intent_source == "UNKNOWN" and (questions or expansion):
        decision = "INTENT_UNKNOWN_REVIEW_REQUIRED"
    elif questions:
        decision = "UNKNOWN"
    elif narrowing:
        decision = "NARROW_BEFORE_REMEDIATION"
    elif unknowns:
        decision = "READY_WITH_NON_BLOCKING_NOTES" if unknowns == ["CI_evidence_missing"] else "UNKNOWN"
    elif flags:
        decision = "READY_WITH_NON_BLOCKING_NOTES"
    else:
        decision = "READY_FOR_REMEDIATION"

    remediation_findings = [
        {"code": item["code"], "path": item["path"], "detail": item["detail"], "action": "inspect_and_fix_only_if_validated"}
        for item in flags if item["code"] != "broad_formatting_noise"
    ]
    return {
        "schema": SCHEMA,
        "PR_identity": {"repository": evidence.get("repository"), "pr_number": evidence.get("pr_number"),
                        "base_ref": evidence.get("base_ref"), "base_sha": base, "head_ref": evidence.get("head_ref"),
                        "head_sha": head, "merge_base": merge_base, "commits": evidence.get("commits") or []},
        "intent_identity": {"source": intent_source, **intent},
        "evidence": {"files": files, "diff_summary": {"changed_files": len(files),
                     "lines_added": sum(int(item.get("additions") or 0) for item in files),
                     "lines_deleted": sum(int(item.get("deletions") or 0) for item in files),
                     "files_added": len(added_paths), "files_deleted": len(deleted_paths), "test_files": tests,
                     "production_files": production, "dependency_files": dependency_paths, "binary_files": binaries,
                     "generated_like_files": generated}, "CI_checks": checks},
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
            "accepted_change_scope": intent.get("explicit_scope") or [intent.get("requested_outcome")],
            "files_or_symbols_requiring_attention": sorted({item.get("path") for item in flags if item.get("path")}),
            "findings_to_fix": remediation_findings,
            "expansion_to_remove": narrowing,
            "architecture_invariants_to_preserve": [],
            "tests_to_add_or_repair": [item["path"] for item in flags if item["code"] == "deleted_test" and item.get("path")],
            "CI_failures_relevant_to_remediation": [check for check in checks if check["conclusion"].lower() in CI_FAIL],
            "explicit_non_goals": intent.get("explicit_non_goals") or [],
            "UNKNOWNs": sorted(set(unknowns)),
            "acceptance_criteria": intent.get("acceptance_criteria") or [],
        },
    }


def validate(doc: dict[str, Any]) -> list[str]:
    required = {"PR_identity", "intent_identity", "evidence", "deterministic_findings", "judgement_findings",
                "expansion_items", "required_narrowing", "remediation_findings", "unknowns", "decision", "confidence",
                "LLM_judgement_used", "LLM_judgement_questions", "remediation_packet"}
    errors = [f"missing required field: {field}" for field in sorted(required - set(doc))]
    if doc.get("decision") not in DECISIONS:
        errors.append("invalid decision")
    identity = doc.get("PR_identity") or {}
    if not identity.get("base_sha") or not identity.get("head_sha"):
        errors.append("exact base/head SHA not bound")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--repo")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", type=Path)
    args = parser.parse_args()
    if args.validate_only:
        errors = validate(json.loads(args.validate_only.read_text(encoding="utf-8")))
        if errors:
            print("\n".join(f"FAIL: {error}" for error in errors), file=sys.stderr)
            return 1
        print("PASS: PR digest schema and exact revision binding")
        return 0
    if args.fixture:
        evidence = json.loads(args.fixture.read_text(encoding="utf-8"))
    else:
        if not args.repo or not args.pr_number:
            parser.error("provide --fixture or both --repo and --pr-number")
        evidence = live_evidence(args.repo, args.pr_number, args.workspace)
    if args.base_sha:
        evidence["base_sha"] = args.base_sha
    if args.head_sha:
        evidence["head_sha"] = args.head_sha
    if args.intent:
        evidence["intent"] = json.loads(args.intent.read_text(encoding="utf-8"))
    result = digest(evidence, args.workspace)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    errors = validate(result)
    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
