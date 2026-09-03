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
    "READY_FOR_REMEDIATION", "READY_WITH_NON_BLOCKING_NOTES", "NARROW_BEFORE_REMEDIATION",
    "ARCHITECTURE_REPAIR_BEFORE_REMEDIATION", "CI_OR_EXECUTION_FAILURE",
    "INTENT_UNKNOWN_REVIEW_REQUIRED", "BLOCKED", "UNKNOWN",
}
CI_FAIL = {"failure", "failed", "cancelled", "timed_out", "action_required"}
DEPS = {"requirements.txt", "requirements-dev.txt", "pyproject.toml", "poetry.lock", "uv.lock", "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.toml", "Cargo.lock", "go.mod", "go.sum"}
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
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=False)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def live_evidence(repo: str, pr: int, workspace: Path | None) -> dict[str, Any]:
    doc = json.loads(run(["gh", "pr", "view", str(pr), "--repo", repo, "--json", "number,title,body,baseRefName,baseRefOid,headRefName,headRefOid,commits,files,statusCheckRollup"], workspace))
    return {
        "repository": repo, "pr_number": doc.get("number"), "title": doc.get("title") or "", "body": doc.get("body") or "",
        "base_ref": doc.get("baseRefName"), "base_sha": doc.get("baseRefOid"), "head_ref": doc.get("headRefName"), "head_sha": doc.get("headRefOid"),
        "commits": [c.get("oid") for c in doc.get("commits", []) if c.get("oid")],
        "files": [{"path": f.get("path"), "status": f.get("status") or "modified", "additions": int(f.get("additions") or 0), "deletions": int(f.get("deletions") or 0), "patch": None} for f in doc.get("files", [])],
        "ci_checks": [{"name": c.get("name") or c.get("context") or "UNKNOWN", "conclusion": c.get("conclusion") or c.get("state") or "UNKNOWN"} for c in doc.get("statusCheckRollup") or []],
    }


def merge_base(workspace: Path | None, base: str | None, head: str | None) -> str | None:
    if not workspace or not base or not head:
        return None
    try:
        return run(["git", "merge-base", base, head], workspace).strip() or None
    except RuntimeError:
        return None


def git_patches(workspace: Path | None, base: str | None, head: str | None) -> dict[str, str]:
    if not workspace or not base or not head:
        return {}
    try:
        text = run(["git", "diff", "--no-ext-diff", "--unified=1", base, head], workspace)
    except RuntimeError:
        return {}
    out: dict[str, list[str]] = {}; current = None
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]; out.setdefault(current, [])
        if current:
            out[current].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def section_line(text: str, names: tuple[str, ...]) -> str | None:
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        m = re.match(r"^#+\s*(.+?)\s*$", raw.strip())
        if not m or m.group(1).strip().lower() not in names:
            continue
        for line in lines[i + 1:]:
            s = line.strip()
            if s.startswith("#"):
                break
            if s and not s.startswith("<!--"):
                return s.lstrip("-* ")[:1000]
    return None


def non_goals(text: str) -> list[str]:
    out = []; active = False
    for raw in text.splitlines():
        s = raw.strip()
        if re.match(r"^#+\s*(non[- ]?goals?|out of scope)\b", s, re.I):
            active = True; continue
        if active and s.startswith("#"):
            break
        if active and s.startswith(("-", "*")):
            out.append(s[1:].strip())
    return out[:30]


def intent_of(e: dict[str, Any]) -> tuple[dict[str, Any], str]:
    explicit = e.get("intent")
    if isinstance(explicit, dict) and explicit.get("requested_outcome"):
        return explicit, "explicit_task_contract"
    body, title = str(e.get("body") or "").strip(), str(e.get("title") or "").strip()
    if body:
        outcome = section_line(body, ("problem", "objective", "why", "summary"))
        if not outcome:
            outcome = next((x.strip(" -*#\t") for x in body.splitlines() if x.strip() and not x.lstrip().startswith("<!--")), None)
        return {"requested_outcome": outcome, "explicit_scope": [], "explicit_non_goals": non_goals(body), "acceptance_criteria": [], "source_excerpt": body[:4000], "pr_title": title or None}, "pr_body"
    if title:
        return {"requested_outcome": title, "explicit_scope": [], "explicit_non_goals": [], "acceptance_criteria": [], "source_excerpt": title, "pr_title": title}, "pr_title"
    return {"requested_outcome": None, "explicit_scope": [], "explicit_non_goals": [], "acceptance_criteria": [], "source_excerpt": None}, "UNKNOWN"


def tokens(text: str | None) -> set[str]:
    stop = {"the", "and", "for", "with", "this", "that", "from", "into", "apply", "feat", "fix", "chore", "style"}
    return {x for x in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(x) >= 4 and x not in stop}


def is_test(path: str) -> bool:
    p = Path(path.lower()); parts = set(p.parts[:-1]); name = p.name
    if "tests" in parts or "test" in parts:
        return True
    if not name.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java")):
        return False
    return name.startswith("test_") or name.endswith("_test.py") or ".spec." in name or ".test." in name


def added_lines(patch: str) -> str:
    return "\n".join(x[1:] for x in patch.splitlines() if x.startswith("+") and not x.startswith("+++"))


def format_only(patch: str) -> bool:
    a = [x[1:].strip() for x in patch.splitlines() if x.startswith("+") and not x.startswith("+++")]
    r = [x[1:].strip() for x in patch.splitlines() if x.startswith("-") and not x.startswith("---")]
    return bool(a and r and sorted(a) == sorted(r))


def question(code: str, paths: list[str], text: str) -> dict[str, Any]:
    return {"code": code, "evidence_paths": sorted(set(paths)), "question": text}


def growth(kind: str, path: str) -> dict[str, Any]:
    return {"kind": kind, "path": path, "classification": "UNKNOWN", "evidence": "deterministic_diff"}


def digest(e: dict[str, Any], workspace: Path | None = None) -> dict[str, Any]:
    base, head = e.get("base_sha"), e.get("head_sha"); patches = git_patches(workspace, base, head)
    files = []
    for raw in e.get("files") or []:
        f = dict(raw); path = str(f.get("path") or "")
        if not f.get("patch") and path in patches: f["patch"] = patches[path]
        files.append(f)
    intent, source = intent_of(e); flags: list[dict[str, Any]] = []; expansion = []; questions = []; unknowns = []
    if not base or not head: unknowns.append("exact_base_or_head_sha_missing")
    if source == "UNKNOWN": unknowns.append("original_intent_unavailable")
    def flag(code: str, path: str | None, detail: str, severity: str = "review") -> None: flags.append({"code": code, "path": path, "detail": detail, "severity": severity})

    tt, ot = tokens(str(e.get("title") or "")), tokens(str(intent.get("requested_outcome") or ""))
    if source == "pr_body" and len(tt) >= 2 and len(ot) >= 2 and not (tt & ot):
        flag("title_body_intent_mismatch", None, "PR title and explicit body intent section share no material terms")
        questions.append(question("intent_conflict", [], "Which intent source is authoritative: the PR title or the conflicting PR body task statement?"))

    paths = [str(f.get("path") or "") for f in files]
    added = [str(f.get("path") or "") for f in files if str(f.get("status") or "").lower() in {"added", "a"}]
    deleted = [str(f.get("path") or "") for f in files if str(f.get("status") or "").lower() in {"deleted", "removed", "d"}]
    deps = [p for p in paths if Path(p).name in DEPS]
    for p in deps: flag("new_dependency_or_dependency_surface", p, "dependency manifest or lock surface changed"); expansion.append(growth("dependency_change", p))

    base_top = set(e.get("base_top_level_directories") or [])
    if base_top:
        for d in sorted({p.split("/", 1)[0] for p in added if "/" in p} - base_top):
            expansion.append(growth("new_top_level_directory", d)); questions.append(question("new_top_level_directory", [d], "Is this genuinely new top-level owner required by the task or duplicating an existing owner?"))

    structural: dict[tuple[str, str], list[str]] = {}
    for p in added:
        low = p.lower(); kind = None; owner = p
        if "/adapters/" in low:
            before, after = p.split("/adapters/", 1); owner = f"{before}/adapters/{after.split('/', 1)[0]}"; kind = "new_adapter"
        elif low.endswith(("_adapter.py", "adapter.py")): kind = "new_adapter"
        elif "registry" in Path(low).name: kind = "new_registry"
        elif "factory" in Path(low).name: kind = "new_factory"
        elif low.endswith(("_service.py", "service.py")): kind = "new_service"
        elif low.endswith(".schema.json"): kind = "new_schema"; owner = str(Path(p).parent)
        if kind: structural.setdefault((kind, owner), []).append(p)
    for (kind, owner), evidence_paths in sorted(structural.items()):
        if kind == "new_adapter" and "/adapters/" in owner and len(evidence_paths) < 2: continue
        expansion.append(growth(kind, owner)); questions.append(question(kind, evidence_paths, f"Is this {kind.replace('_', ' ')} required by the task and owned by the canonical seam?"))

    if any(p.startswith(GOV_PREFIX) or p in {"Makefile", "AGENTS.md", "CANONICAL_LAW.md"} for p in paths):
        flag("workflow_or_governance_change", None, "workflow/governance surface changed")
        questions.append(question("governance_scope", [p for p in paths if p.startswith(GOV_PREFIX) or p in {"Makefile", "AGENTS.md", "CANONICAL_LAW.md"}], "Is this governance change required by the PR intent?"))

    prod = [p for p in paths if not is_test(p) and Path(p).suffix.lower() not in {".md", ".rst", ".txt"}]
    tests = [p for p in paths if is_test(p)]
    if prod and not tests: flag("production_code_without_tests", None, "production surface changed with no test file in the diff")
    for p in deleted:
        if is_test(p): flag("deleted_test", p, "executable test file deleted", "blocking_review")

    binaries = [p for p in paths if Path(p).suffix.lower() in BINARY]
    for p in binaries: flag("unexpected_binary", p, "binary/package artifact changed")
    if binaries: questions.append(question("binary_change", binaries, "Are these binary/package artifacts explicitly required and source-traceable for the stated PR intent?"))

    locks, manifests = {Path(p).name for p in paths if Path(p).name in LOCKS}, {Path(p).name for p in paths if Path(p).name in MANIFESTS}
    if locks and not manifests: flag("unrelated_lockfile_churn", None, f"lockfile changed without source manifest: {sorted(locks)}")
    generated = [p for p in paths if any(h in p.lower() for h in GENERATED)]
    if generated and not [p for p in paths if p not in generated]: flag("generated_file_changed_without_source_change", None, "generated-looking files changed without observable source")

    hits: dict[str, list[str]] = {k: [] for k in PATTERNS}; fmt = 0
    for f in files:
        path, patch = str(f.get("path") or ""), str(f.get("patch") or ""); plus = added_lines(patch)
        if patch and format_only(patch): fmt += 1
        for code, rx in PATTERNS.items():
            if plus and rx.search(plus): hits[code].append(path); flag(code, path, f"added lines matched deterministic {code} pattern", "blocking_review" if code == "suppression_or_ignore_added" else "review")
        if plus and re.search(r"(?m)^\s*TODO\b", plus): flag("TODO_added", path, "TODO marker added")
    if len(files) >= 8 and fmt >= max(4, len(files) // 2): flag("broad_formatting_noise", None, f"{fmt}/{len(files)} changed files appear formatting-heavy")
    for code in ("new_registry", "new_factory", "new_adapter", "new_service", "compatibility_layer_added", "feature_flag_added"):
        for p in hits[code]:
            expansion.append(growth(code.replace("_added", ""), p)); questions.append(question(code, [p], f"Is this {code.replace('_', ' ')} necessary, or anticipatory/duplicate architecture?"))

    checks = [{"name": str(c.get("name") or "UNKNOWN"), "conclusion": str(c.get("conclusion") or "UNKNOWN")} for c in e.get("ci_checks") or []]
    ci_failure = any(c["conclusion"].lower() in CI_FAIL for c in checks)
    if not checks: unknowns.append("CI_evidence_missing")
    narrowing = [{"reason": f["code"], "path": f["path"], "action": "remove_or_justify_before_remediation"} for f in flags if f["code"] in {"suppression_or_ignore_added", "deleted_test"}]

    if ci_failure: decision = "CI_OR_EXECUTION_FAILURE"
    elif any(f["severity"] == "blocking" for f in flags): decision = "BLOCKED"
    elif source == "UNKNOWN" and (questions or expansion): decision = "INTENT_UNKNOWN_REVIEW_REQUIRED"
    elif questions: decision = "UNKNOWN"
    elif narrowing: decision = "NARROW_BEFORE_REMEDIATION"
    elif unknowns: decision = "READY_WITH_NON_BLOCKING_NOTES" if unknowns == ["CI_evidence_missing"] else "UNKNOWN"
    elif flags: decision = "READY_WITH_NON_BLOCKING_NOTES"
    else: decision = "READY_FOR_REMEDIATION"

    rem = [{"code": f["code"], "path": f["path"], "detail": f["detail"], "action": "inspect_and_fix_only_if_validated"} for f in flags if f["code"] != "broad_formatting_noise"]
    return {
        "schema": SCHEMA,
        "PR_identity": {"repository": e.get("repository"), "pr_number": e.get("pr_number"), "base_ref": e.get("base_ref"), "base_sha": base, "head_ref": e.get("head_ref"), "head_sha": head, "merge_base": merge_base(workspace, base, head), "commits": e.get("commits") or []},
        "intent_identity": {"source": source, **intent},
        "evidence": {"files": files, "diff_summary": {"changed_files": len(files), "lines_added": sum(int(f.get("additions") or 0) for f in files), "lines_deleted": sum(int(f.get("deletions") or 0) for f in files), "files_added": len(added), "files_deleted": len(deleted), "test_files": tests, "production_files": prod, "dependency_files": deps, "binary_files": binaries, "generated_like_files": generated}, "CI_checks": checks},
        "deterministic_findings": flags, "judgement_findings": [], "expansion_items": expansion, "required_narrowing": narrowing, "remediation_findings": rem,
        "unknowns": sorted(set(unknowns)), "decision": decision, "confidence": "deterministic_evidence_only", "LLM_judgement_used": False, "LLM_judgement_questions": questions,
        "remediation_packet": {"PR_base_and_head": {"base_sha": base, "head_sha": head}, "accepted_change_scope": intent.get("explicit_scope") or [intent.get("requested_outcome")], "files_or_symbols_requiring_attention": sorted({f.get("path") for f in flags if f.get("path")}), "findings_to_fix": rem, "expansion_to_remove": narrowing, "architecture_invariants_to_preserve": [], "tests_to_add_or_repair": [f["path"] for f in flags if f["code"] == "deleted_test" and f.get("path")], "CI_failures_relevant_to_remediation": [c for c in checks if c["conclusion"].lower() in CI_FAIL], "explicit_non_goals": intent.get("explicit_non_goals") or [], "UNKNOWNs": sorted(set(unknowns)), "acceptance_criteria": intent.get("acceptance_criteria") or []},
    }


def validate(doc: dict[str, Any]) -> list[str]:
    required = {"PR_identity", "intent_identity", "evidence", "deterministic_findings", "judgement_findings", "expansion_items", "required_narrowing", "remediation_findings", "unknowns", "decision", "confidence", "LLM_judgement_used", "LLM_judgement_questions", "remediation_packet"}
    errors = [f"missing required field: {x}" for x in sorted(required - set(doc))]
    if doc.get("decision") not in DECISIONS: errors.append("invalid decision")
    identity = doc.get("PR_identity") or {}
    if not identity.get("base_sha") or not identity.get("head_sha"): errors.append("exact base/head SHA not bound")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--fixture", type=Path); ap.add_argument("--repo"); ap.add_argument("--pr-number", type=int); ap.add_argument("--workspace", type=Path); ap.add_argument("--base-sha"); ap.add_argument("--head-sha"); ap.add_argument("--intent", type=Path); ap.add_argument("--output", type=Path); ap.add_argument("--validate-only", type=Path); a = ap.parse_args()
    if a.validate_only:
        errors = validate(json.loads(a.validate_only.read_text(encoding="utf-8")))
        if errors: print("\n".join(f"FAIL: {x}" for x in errors), file=sys.stderr); return 1
        print("PASS: PR digest schema and exact revision binding"); return 0
    if a.fixture: evidence = json.loads(a.fixture.read_text(encoding="utf-8"))
    else:
        if not a.repo or not a.pr_number: ap.error("provide --fixture or both --repo and --pr-number")
        evidence = live_evidence(a.repo, a.pr_number, a.workspace)
    if a.base_sha: evidence["base_sha"] = a.base_sha
    if a.head_sha: evidence["head_sha"] = a.head_sha
    if a.intent: evidence["intent"] = json.loads(a.intent.read_text(encoding="utf-8"))
    result = digest(evidence, a.workspace); rendered = json.dumps(result, indent=2) + "\n"
    if a.output: a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(rendered, encoding="utf-8")
    else: print(rendered, end="")
    errors = validate(result)
    if errors: print("\n".join(f"FAIL: {x}" for x in errors), file=sys.stderr); return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
