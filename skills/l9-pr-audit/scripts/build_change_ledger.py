#!/usr/bin/env python3
"""Build deterministic PR-audit census and adversarial seeds from a read-only PR snapshot.

The output is machine-owned census material, not a verdict. It enumerates changed
surfaces, changed symbols, audit obligations, claim seeds, and falsification seeds
that the semantic auditor must disposition. It never decides architecture correctness
or mutates a repository.

Input JSON shape (minimal):
{
  "repository": "owner/repo",
  "pr_number": 1,
  "base_sha": "...",
  "head_sha": "...",
  "intent": {
    "source_kind": "ORIGINAL_PR_PROMPT|LATEST_USER|PR_BODY|ISSUE|UNKNOWN",
    "scope_patterns": ["src/foo/**"],
    "objectives": [{"objective_id": "REQ-1"}],
    "explicit_non_goals": ["..."]
  },
  "files": [{
    "path":"src/x.py","status":"modified","additions":1,"deletions":0,
    "patch":"...", "base_content":"optional", "head_content":"optional"
  }],
  "ci_failures": [{"name":"test","required":true,"conclusion":"failure"}],
  "review_threads": [{"thread_id":"RT1","is_resolved":false,"author":"bot","path":"src/x.py"}]
}
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import deterministic_closure as dc

SCHEMA = "l9.pr-audit.change-ledger.v1.4"
GENERATOR_VERSION = "1.4.0"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
TEST_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java")
ARCH_PATTERNS = {
    "NEW_REGISTRY": re.compile(r"\b(?:class|def)\s+\w*Registry\b|\bregistry\s*=", re.I),
    "NEW_FACTORY": re.compile(r"\b(?:class|def)\s+\w*Factory\b|\bfactory\s*=", re.I),
    "NEW_ADAPTER": re.compile(r"\b(?:class|def)\s+\w*Adapter\b", re.I),
    "NEW_SERVICE": re.compile(r"\b(?:class|def)\s+\w*Service\b", re.I),
    "NEW_MANAGER": re.compile(r"\b(?:class|def)\s+\w*Manager\b", re.I),
    "NEW_PROTOCOL_OR_INTERFACE": re.compile(r"\bProtocol\b|\bInterface\b|\bABC\b", re.I),
    "COMPATIBILITY_LAYER": re.compile(
        r"\bcompat(?:ibility)?\b|\blegacy\b|\bbackward[- ]compat", re.I
    ),
    "FEATURE_FLAG": re.compile(r"\bfeature[_ -]?flag\b|\bENABLE_[A-Z0-9_]+\b"),
}
SUPPRESSION = re.compile(
    r"#\s*noqa\b|type:\s*ignore|eslint-disable|NOSONAR|continue-on-error", re.I
)
FAILURE_PATH = re.compile(
    r"\b(?:try\s*:|except\b|raise\b|timeout\b|retries?\b|retry\b|subprocess\b|requests\.|httpx\.|"
    r"socket\b|permission\b|auth(?:entication|orization)?\b|rollback\b|cleanup\b|finally\s*:)",
    re.I,
)
DEPS = {
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "poetry.lock",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
}
GENERATED_HINTS = ("generated/", "dist/", "build/", "manifest.json", "skill-registry.json")
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".whl",
    ".bin",
    ".exe",
    ".dmg",
}
CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"}
DOC_SUFFIXES = {".md", ".rst", ".adoc"}
AUDIT_DOMAINS = (
    "INTENT_SCOPE",
    "COMMUNICATION_CONTRACTS",
    "ROUTING_INTEGRATION",
    "OWNERSHIP_AUTHORITY",
    "STRUCTURE_SOURCE_OF_TRUTH",
    "SCHEMA_CONFIGURATION",
    "SECURITY",
    "RELIABILITY_OBSERVABILITY",
    "TESTING_VALIDATION",
    "LEVERAGE_SIMPLICITY",
    "CROSS_PR",
    "CHANGE_DISCIPLINE",
)
PATCH_SYMBOL_PATTERNS = (
    ("CLASS", re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("FUNCTION_OR_METHOD", re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")),
    (
        "FUNCTION_OR_METHOD",
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("),
    ),
    (
        "INTERFACE_OR_PROTOCOL",
        re.compile(
            r"^\s*(?:export\s+)?(?:interface|type|protocol)\s+([A-Za-z_$][A-Za-z0-9_$]*)\b", re.I
        ),
    ),
    ("CONFIG_OR_SCHEMA_KEY", re.compile(r'^\s*["\']?([A-Za-z_][A-Za-z0-9_.-]*)["\']?\s*[:=]')),
)
SEMANTIC_CLASSES = {"SOURCE", "TEST", "CONFIGURATION", "SCHEMA", "WORKFLOW"}


def classify_artifact(path: str) -> str:
    p = Path(path.lower())
    name = p.name
    suffix = p.suffix.lower()
    if is_test(path):
        return "TEST"
    if name in DEPS:
        return "DEPENDENCY_MANIFEST"
    if path.lower().startswith(".github/workflows/"):
        return "WORKFLOW"
    if any(h in path.lower() for h in GENERATED_HINTS):
        return "GENERATED"
    if "schema" in name and suffix in {".json", ".yaml", ".yml"}:
        return "SCHEMA"
    if suffix in BINARY_SUFFIXES:
        return "BINARY_OPAQUE"
    if suffix in DOC_SUFFIXES:
        return "DOCUMENTATION"
    if suffix in CONFIG_SUFFIXES:
        return "CONFIGURATION"
    if suffix in TEST_SUFFIXES or suffix in {
        ".py",
        ".sql",
        ".sh",
        ".bash",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
    }:
        return "SOURCE"
    return "OTHER"


def is_test(path: str) -> bool:
    p = Path(path.lower())
    if {"test", "tests"} & set(p.parts[:-1]):
        return True
    name = p.name
    if not name.endswith(TEST_SUFFIXES):
        return False
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or ".spec." in name
        or ".test." in name
    )


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def removed_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )


def oid(prefix: str, *parts: Any) -> str:
    payload = "\x1f".join(str(p) for p in parts)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:12]}"


def in_declared_scope(path: str, patterns: list[str]) -> bool | None:
    if not patterns:
        return None
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def load(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("snapshot root must be object")
    return doc


def validate_snapshot(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("repository", "pr_number", "base_sha", "head_sha", "files"):
        if key not in doc:
            errors.append(f"missing {key}")
    if not isinstance(doc.get("pr_number"), int) or int(doc.get("pr_number", 0)) < 1:
        errors.append("pr_number must be positive integer")
    for key in ("base_sha", "head_sha"):
        if not isinstance(doc.get(key), str) or not SHA_RE.fullmatch(doc[key]):
            errors.append(f"{key} must be exact SHA")
    if not isinstance(doc.get("files"), list):
        errors.append("files must be array")
    return errors


def _python_symbols(content: str) -> dict[tuple[str, str], str]:
    """Return {(kind, qualname): normalized_ast_dump} for Python class/function symbols."""
    tree = ast.parse(content)
    out: dict[tuple[str, str], str] = {}

    def walk(body: list[ast.stmt], parents: list[str]) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qual = ".".join(parents + [node.name])
                out[("CLASS", qual)] = ast.dump(node, include_attributes=False)
                walk(node.body, parents + [node.name])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = ".".join(parents + [node.name])
                kind = "METHOD" if parents else "FUNCTION"
                out[(kind, qual)] = ast.dump(node, include_attributes=False)

    walk(tree.body, [])
    return out


def _patch_named_symbols(text: str) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for line in text.splitlines():
        for kind, pattern in PATCH_SYMBOL_PATTERNS:
            match = pattern.search(line)
            if match:
                out.add((kind, match.group(1)))
                break
    return out


def changed_symbols_for_file(
    raw: dict[str, Any], pr: int, classification: str
) -> list[dict[str, Any]]:
    path = str(raw["path"])
    status = str(raw.get("status") or "modified").lower()
    patch = str(raw.get("patch") or "")
    base_content = raw.get("base_content")
    head_content = raw.get("head_content")
    symbols: list[dict[str, Any]] = []

    if (
        path.lower().endswith(".py")
        and isinstance(base_content, str)
        and isinstance(head_content, str)
    ):
        try:
            before = _python_symbols(base_content)
            after = _python_symbols(head_content)
            for key in sorted(set(before) | set(after)):
                if key not in before:
                    change = "ADDED"
                elif key not in after:
                    change = "REMOVED"
                elif before[key] != after[key]:
                    change = "MODIFIED"
                else:
                    continue
                kind, name = key
                symbols.append(
                    {
                        "symbol_id": oid("SYM", pr, path, kind, name, change),
                        "pr_number": pr,
                        "path": path,
                        "symbol_name": name,
                        "symbol_kind": kind,
                        "change_type": change,
                        "detection_method": "PYTHON_AST",
                        "detection_confidence": "EXACT_STATIC",
                        "deterministic_state": "REQUIRES_JUDGMENT",
                    }
                )
        except SyntaxError:
            # Deliberate: the blob is whatever the PR contains at this path, so
            # it need not parse — a partial file, a template, or a .py that is
            # invalid on this Python version. AST symbol extraction is
            # best-effort, and an unparseable file simply contributes no
            # symbols; the caller below falls back to the non-AST census rather
            # than treating this as an error.
            pass

    if not symbols and classification in SEMANTIC_CLASSES:
        added = _patch_named_symbols(added_lines(patch))
        removed = _patch_named_symbols(removed_lines(patch))
        for kind, name in sorted(added | removed):
            if (kind, name) in added and (kind, name) in removed:
                change = "MODIFIED"
            elif (kind, name) in added:
                change = "ADDED"
            else:
                change = "REMOVED"
            symbols.append(
                {
                    "symbol_id": oid("SYM", pr, path, kind, name, change),
                    "pr_number": pr,
                    "path": path,
                    "symbol_name": name,
                    "symbol_kind": kind,
                    "change_type": change,
                    "detection_method": "PATCH_REGEX",
                    "detection_confidence": "HEURISTIC",
                    "deterministic_state": "REQUIRES_JUDGMENT",
                }
            )

    if not symbols and classification in SEMANTIC_CLASSES:
        change = "ADDED" if status == "added" else "REMOVED" if status == "deleted" else "MODIFIED"
        symbols.append(
            {
                "symbol_id": oid("SYM", pr, path, "FILE_SCOPE", "<file-scope>", change),
                "pr_number": pr,
                "path": path,
                "symbol_name": "<file-scope>",
                "symbol_kind": "FILE_SCOPE",
                "change_type": change,
                "detection_method": "FILE_FALLBACK",
                "detection_confidence": "HEURISTIC",
                "deterministic_state": "REQUIRES_JUDGMENT",
            }
        )
    return symbols


def _claim_seed(
    pr: int, kind: str, subject: str, assertion: str, materiality: str = "MATERIAL"
) -> dict[str, Any]:
    return {
        "claim_id": oid("CLM", pr, kind, subject),
        "pr_number": pr,
        "claim_kind": kind,
        "subject": subject,
        "assertion": assertion,
        "materiality": materiality,
        "source": "MACHINE_SEEDED",
    }


def _falsification_seed(
    claim: dict[str, Any],
    attack_class: str,
    hypothesis: str,
    suggested_method: str,
    judgment_mode: str,
) -> dict[str, Any]:
    return {
        "falsification_id": oid("FAL", claim["claim_id"], attack_class),
        "claim_id": claim["claim_id"],
        "source": "MACHINE_SEEDED",
        "attack_class": attack_class,
        "hypothesis": hypothesis,
        "suggested_method": suggested_method,
        "judgment_mode": judgment_mode,
    }


def build(doc: dict[str, Any]) -> dict[str, Any]:
    errors = validate_snapshot(doc)
    if errors:
        raise ValueError("invalid snapshot: " + "; ".join(errors))

    pr = doc["pr_number"]
    intent = doc.get("intent") if isinstance(doc.get("intent"), dict) else {}
    scope_patterns = [str(x) for x in intent.get("scope_patterns", []) if x]
    obligations: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    artifact_inventory: list[dict[str, Any]] = []
    changed_symbols: list[dict[str, Any]] = []
    claim_seeds: list[dict[str, Any]] = []
    falsification_seeds: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    stats = {
        "files_changed": 0,
        "files_added": 0,
        "files_deleted": 0,
        "files_modified": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "test_files_changed": 0,
        "production_files_changed": 0,
        "dependency_files_changed": 0,
        "generated_like_files_changed": 0,
        "architectural_growth_candidates": 0,
        "failure_path_candidates": 0,
        "changed_symbols": 0,
        "closure_seeds": 0,
        "public_contract_deltas": 0,
        "failure_edges": 0,
    }

    objective_ids: list[str] = []
    for raw_objective in intent.get("objectives", []) or []:
        if isinstance(raw_objective, dict):
            objective_id = str(raw_objective.get("objective_id") or "").strip()
        else:
            objective_id = str(raw_objective).strip()
        if objective_id:
            objective_ids.append(objective_id)
            obligations.append(
                {
                    "obligation_id": oid("OBJ", pr, objective_id),
                    "pr_number": pr,
                    "kind": "OBJECTIVE",
                    "subject": objective_id,
                    "deterministic_state": "REQUIRES_JUDGMENT",
                }
            )
            claim = _claim_seed(
                pr,
                "OBJECTIVE",
                objective_id,
                f"Objective {objective_id} is satisfied by the audited PR state.",
            )
            claim_seeds.append(claim)
            falsification_seeds.append(
                _falsification_seed(
                    claim,
                    "NEGATIVE_REQUIREMENT_SEARCH",
                    f"A required behavior, acceptance criterion, or non-goal for {objective_id} is missing, contradicted, or violated.",
                    "Search authoritative intent, changed surfaces, tests, and directly coupled consumers for an unsatisfied requirement or forbidden expansion.",
                    "HYBRID",
                )
            )

    for domain in AUDIT_DOMAINS:
        claim = _claim_seed(
            pr,
            "AUDIT_DOMAIN",
            domain,
            f"Audit domain {domain} is correctly dispositioned for PR #{pr}.",
        )
        claim_seeds.append(claim)
        falsification_seeds.append(
            _falsification_seed(
                claim,
                "COUNTEREXAMPLE_SEARCH",
                f"Material evidence exists that contradicts the proposed {domain} disposition.",
                "Search the complete in-scope artifact and boundary inventory for contradictory evidence, bypasses, duplicate ownership, or missing controls relevant to the domain.",
                "HYBRID",
            )
        )

    for raw in doc["files"]:
        if not isinstance(raw, dict) or not raw.get("path"):
            continue
        path = str(raw["path"])
        if path in seen_paths:
            raise ValueError(f"duplicate changed file: {path}")
        seen_paths.add(path)
        status = str(raw.get("status") or "modified").lower()
        additions = int(raw.get("additions") or 0)
        deletions = int(raw.get("deletions") or 0)
        patch = str(raw.get("patch") or "")
        added = added_lines(patch)
        classification = classify_artifact(path)
        scope_state = in_declared_scope(path, scope_patterns)
        stats["files_changed"] += 1
        stats["lines_added"] += additions
        stats["lines_deleted"] += deletions
        if status == "added":
            stats["files_added"] += 1
        elif status == "deleted":
            stats["files_deleted"] += 1
        else:
            stats["files_modified"] += 1
        if is_test(path):
            stats["test_files_changed"] += 1
        else:
            stats["production_files_changed"] += 1
        if Path(path).name in DEPS:
            stats["dependency_files_changed"] += 1
        if any(h in path.lower() for h in GENERATED_HINTS):
            stats["generated_like_files_changed"] += 1

        artifact_inventory.append(
            {
                "artifact_id": oid("ART", pr, path),
                "path": path,
                "classification": classification,
                "roles": ["CHANGED"],
                "status": status,
                "scope_state": (
                    "OUTSIDE_DECLARED_SCOPE"
                    if scope_state is False
                    else "INSIDE_DECLARED_SCOPE"
                    if scope_state is True
                    else "SCOPE_UNSPECIFIED"
                ),
            }
        )

        obligations.append(
            {
                "obligation_id": oid("SURF", pr, path),
                "pr_number": pr,
                "kind": "CHANGED_SURFACE",
                "subject": path,
                "deterministic_state": (
                    "OUTSIDE_DECLARED_SCOPE"
                    if scope_state is False
                    else "INSIDE_DECLARED_SCOPE"
                    if scope_state is True
                    else "SCOPE_UNSPECIFIED"
                ),
            }
        )

        file_symbols = changed_symbols_for_file(raw, pr, classification)
        extra_symbols = dc.additional_symbol_deltas(raw, pr, classification)
        file_symbols = list(
            {item["symbol_id"]: item for item in (file_symbols + extra_symbols)}.values()
        )
        changed_symbols.extend(file_symbols)
        stats["changed_symbols"] += len(file_symbols)
        for sym in file_symbols:
            obligations.append(
                {
                    "obligation_id": oid("OBLSYM", pr, sym["symbol_id"]),
                    "pr_number": pr,
                    "kind": "CHANGED_SYMBOL",
                    "subject": sym["symbol_id"],
                    "deterministic_state": "REQUIRES_JUDGMENT",
                }
            )
            subject = f"{path}:{sym['symbol_name']}"
            claim = _claim_seed(
                pr,
                "CHANGED_SYMBOL",
                subject,
                f"Changed symbol {subject} is authorized, architecturally aligned, and sufficiently validated.",
            )
            claim["machine_symbol_id"] = sym["symbol_id"]
            claim_seeds.append(claim)
            falsification_seeds.append(
                _falsification_seed(
                    claim,
                    "COUNTEREXAMPLE_SEARCH",
                    f"The changed symbol {subject} contains an unauthorized behavior change, hidden regression, bypass, untested branch, or unnecessary responsibility expansion.",
                    "Inspect the symbol delta plus callers/consumers/tests; seek a concrete input, path, owner conflict, or contract condition that makes the positive claim false.",
                    "HYBRID",
                )
            )

        if status == "deleted" and is_test(path):
            candidates.append(
                {
                    "candidate_id": oid("ANTI", pr, path, "deleted_test"),
                    "kind": "DELETED_TEST",
                    "path": path,
                    "detail": "executable test file deleted",
                }
            )
        if SUPPRESSION.search(added):
            candidates.append(
                {
                    "candidate_id": oid("ANTI", pr, path, "suppression"),
                    "kind": "SUPPRESSION_OR_IGNORE_ADDED",
                    "path": path,
                    "detail": "new suppression/ignore/gate weakening token detected in added lines",
                }
            )
        for kind, pattern in ARCH_PATTERNS.items():
            if pattern.search(added):
                candidates.append(
                    {
                        "candidate_id": oid("ARCH", pr, path, kind),
                        "kind": kind,
                        "path": path,
                        "detail": "new architectural construct candidate detected from added lines",
                    }
                )
                obligations.append(
                    {
                        "obligation_id": oid("OBLARCH", pr, path, kind),
                        "pr_number": pr,
                        "kind": "ARCHITECTURAL_GROWTH",
                        "subject": f"{path}:{kind}",
                        "deterministic_state": "REQUIRES_JUDGMENT",
                    }
                )
                stats["architectural_growth_candidates"] += 1
        if FAILURE_PATH.search(added):
            candidates.append(
                {
                    "candidate_id": oid("FAIL", pr, path),
                    "kind": "FAILURE_PATH_CHANGE",
                    "path": path,
                    "detail": "changed failure/error/retry/cleanup/auth behavior candidate",
                }
            )
            obligations.append(
                {
                    "obligation_id": oid("OBLFAIL", pr, path),
                    "pr_number": pr,
                    "kind": "FAILURE_PATH",
                    "subject": path,
                    "deterministic_state": "REQUIRES_JUDGMENT",
                }
            )
            stats["failure_path_candidates"] += 1

    for failure in doc.get("ci_failures") or []:
        if not isinstance(failure, dict):
            continue
        name = str(failure.get("name") or "UNKNOWN")
        conclusion = str(failure.get("conclusion") or "UNKNOWN")
        obligations.append(
            {
                "obligation_id": oid("CI", pr, name),
                "pr_number": pr,
                "kind": "CI_FAILURE",
                "subject": name,
                "deterministic_state": conclusion.upper(),
            }
        )

    for thread in doc.get("review_threads") or []:
        if not isinstance(thread, dict) or thread.get("is_resolved") is True:
            continue
        tid = str(thread.get("thread_id") or thread.get("id") or "UNKNOWN")
        obligations.append(
            {
                "obligation_id": oid("REV", pr, tid),
                "pr_number": pr,
                "kind": "REVIEW_THREAD",
                "subject": tid,
                "deterministic_state": "UNRESOLVED",
            }
        )

    for raw in doc["files"]:
        if not isinstance(raw, dict) or not raw.get("path"):
            continue
        path = str(raw["path"])
        if not is_test(path) and str(raw.get("status") or "modified").lower() != "deleted":
            obligations.append(
                {
                    "obligation_id": oid("TEST", pr, path),
                    "pr_number": pr,
                    "kind": "TEST_DISCRIMINATION",
                    "subject": path,
                    "deterministic_state": "REQUIRES_JUDGMENT",
                }
            )

    closure_seeds, closure_summary = dc.build_closure_seeds(doc, artifact_inventory, candidates)
    stats["closure_seeds"] = closure_summary["closure_seed_count"]
    stats["public_contract_deltas"] = closure_summary["public_contract_delta_count"]
    stats["failure_edges"] = closure_summary["failure_edge_count"]

    readiness_claim = _claim_seed(
        pr,
        "READINESS",
        f"PR-{pr}",
        f"PR #{pr} is ready according to the audit's final readiness state.",
    )
    claim_seeds.append(readiness_claim)
    falsification_seeds.append(
        _falsification_seed(
            readiness_claim,
            "STALE_EVIDENCE_CHECK",
            f"A current blocker, stale head, unresolved thread, failing required check, or unsupported positive claim makes PR #{pr} not ready.",
            "Re-resolve the current head, required checks, unresolved review threads, blocking findings/Unknowns, and material claim/falsification state.",
            "HYBRID",
        )
    )
    convergence_claim = _claim_seed(
        pr,
        "CONVERGENCE",
        f"AUDIT-PR-{pr}",
        f"The audit has converged for PR #{pr}; no material audit objective remains undiscovered.",
    )
    claim_seeds.append(convergence_claim)
    falsification_seeds.append(
        _falsification_seed(
            convergence_claim,
            "OMISSION_SEARCH",
            f"A material changed symbol, artifact, claim, counterexample, finding, obligation, boundary, or Unknown for PR #{pr} remains undiscovered or unreconciled.",
            "Reconcile machine census against the final artifact/symbol/claim/falsification ledgers and perform a bounded adversarial omission search.",
            "HYBRID",
        )
    )

    return {
        "schema_version": SCHEMA,
        "generator_version": GENERATOR_VERSION,
        "repository": doc["repository"],
        "pr_number": pr,
        "base_sha": doc["base_sha"],
        "head_sha": doc["head_sha"],
        "intent_source_kind": intent.get("source_kind", "UNKNOWN"),
        "original_pr_prompt_available": bool(intent.get("original_pr_prompt_available", False)),
        "diff_summary": stats,
        "artifact_inventory": artifact_inventory,
        "changed_symbols": changed_symbols,
        "deterministic_candidates": candidates,
        "obligations": obligations,
        "claim_seeds": claim_seeds,
        "falsification_seeds": falsification_seeds,
        "closure_seeds": closure_seeds,
        "closure_summary": closure_summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(load(args.snapshot))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
