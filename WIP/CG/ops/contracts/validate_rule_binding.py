#!/usr/bin/env python3
"""Fail-closed validator for canonical Cursor rule activation bindings."""
from __future__ import annotations
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml
ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = Path(__file__).resolve().parent / "adapters"
if str(ADAPTERS) not in sys.path:
    sys.path.insert(0, str(ADAPTERS))
from cursor_rules import (  # noqa: E402
    BINDING_ID_RE,
    OUTPUT_RE,
    RULE_ID_RE,
    RuleBinding,
    binding_activation,
    binding_contract_refs,
    binding_guidance,
    binding_render_config,
    binding_rule_identity,
    discover_rule_bindings,
    glob_is_narrower_or_equal,
)
from resolve_rule_contracts import (  # noqa: E402
    ContractIndex,
    load_contract_index,
    version_matches,
)
HARD_NORMATIVE_RE = re.compile(
    r"\b(?:"
    r"MUST(?:\s+NOT)?|"
    r"SHALL(?:\s+NOT)?|"
    r"NEVER|"
    r"PROHIBITED|"
    r"FORBIDDEN|"
    r"REQUIRED|"
    r"MANDATORY|"
    r"FAIL[-\s]+CLOSED|"
    r"STOP|"
    r"SOURCE\s+OF\s+TRUTH|"
    r"SSOT"
    r")\b",
    re.IGNORECASE,
)
MIGRATION_STATES = {
    "legacy",
    "extracted",
    "hybrid",
    "contract_bound",
    "generated",
    "retired",
}
ACTIVATION_MODES = {
    "always",
    "auto_attached",
    "agent_requested",
    "manual",
}
@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str
    def __str__(self) -> str:
        return f"{self.code}: {self.path}: {self.message}"
def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
def _scope_paths(record: Any) -> list[str]:
    scope = record.document.get("scope")
    if not isinstance(scope, dict):
        return []
    paths = scope.get("paths")
    return [str(item) for item in paths] if isinstance(paths, list) else []
def _validate_scope_narrowing(
    binding: RuleBinding,
    contract_index: ContractIndex,
) -> list[Finding]:
    findings: list[Finding] = []
    activation = binding_activation(binding)
    activation_globs = _as_list(activation.get("globs"))
    for ref in binding_contract_refs(binding):
        contract_id = str(ref.get("contract_id") or "")
        record = contract_index.records.get(contract_id)
        if record is None:
            continue
        owner_paths = _scope_paths(record)
        scope_narrowing = ref.get("scope_narrowing")
        narrowed_paths: list[str] = []
        if isinstance(scope_narrowing, dict):
            narrowed_paths = [
                str(item)
                for item in _as_list(scope_narrowing.get("paths"))
            ]
        projected_paths = narrowed_paths or [
            str(item) for item in activation_globs
        ]
        if not owner_paths:
            continue
        for candidate in projected_paths:
            if candidate.startswith("!"):
                continue
            if any(
                glob_is_narrower_or_equal(candidate, owner)
                for owner in owner_paths
            ):
                continue
            findings.append(
                Finding(
                    "RULE-BIND-SCOPE-WIDEN",
                    binding.relative_path,
                    f"{contract_id} projected path {candidate!r} is not "
                    f"provably inside contract paths {owner_paths!r}",
                )
            )
    return findings
def validate_binding(
    binding: RuleBinding,
    contract_index: ContractIndex,
    root: Path,
) -> list[Finding]:
    findings: list[Finding] = []
    path = binding.relative_path
    data = binding.data
    identity = data.get("binding_identity")
    target = data.get("target")
    rule_identity = binding_rule_identity(binding)
    activation = binding_activation(binding)
    render = binding_render_config(binding)
    guidance = binding_guidance(binding)
    if not isinstance(identity, dict):
        findings.append(Finding("RULE-BIND-IDENTITY", path, "missing binding_identity"))
        return findings
    if not BINDING_ID_RE.fullmatch(binding.binding_id):
        findings.append(
            Finding(
                "RULE-BIND-ID",
                path,
                f"invalid binding ID {binding.binding_id!r}",
            )
        )
    status = str(identity.get("status") or "")
    if status not in {"draft", "review", "active", "deprecated", "retired"}:
        findings.append(
            Finding("RULE-BIND-STATUS", path, f"invalid status {status!r}")
        )
    if not isinstance(target, dict):
        findings.append(Finding("RULE-BIND-TARGET", path, "missing target mapping"))
    else:
        if target.get("platform") != "cursor":
            findings.append(
                Finding("RULE-BIND-PLATFORM", path, "target.platform must be cursor")
            )
        if target.get("format") != "mdc":
            findings.append(
                Finding("RULE-BIND-FORMAT", path, "target.format must be mdc")
            )
        if not OUTPUT_RE.fullmatch(binding.output_path):
            findings.append(
                Finding(
                    "RULE-BIND-OUTPUT",
                    path,
                    f"invalid output_path {binding.output_path!r}",
                )
            )
    rule_id = str(rule_identity.get("rule_id") or "")
    if not RULE_ID_RE.fullmatch(rule_id):
        findings.append(
            Finding("RULE-BIND-RULE-ID", path, f"invalid rule_id {rule_id!r}")
        )
    mode = str(activation.get("mode") or "")
    if mode not in ACTIVATION_MODES:
        findings.append(
            Finding("RULE-BIND-ACTIVATION", path, f"invalid activation mode {mode!r}")
        )
    globs = _as_list(activation.get("globs"))
    if mode == "always":
        if globs:
            findings.append(
                Finding(
                    "RULE-BIND-ALWAYS-GLOBS",
                    path,
                    "always activation cannot declare globs",
                )
            )
        if not str(activation.get("justification_ref") or "").strip():
            findings.append(
                Finding(
                    "RULE-BIND-ALWAYS-JUSTIFICATION",
                    path,
                    "always activation requires justification_ref",
                )
            )
    if mode == "auto_attached" and not globs:
        findings.append(
            Finding(
                "RULE-BIND-AUTO-GLOBS",
                path,
                "auto_attached activation requires globs",
            )
        )
    if mode in {"agent_requested", "manual"}:
        description = str(
            activation.get("description")
            or rule_identity.get("description")
            or ""
        ).strip()
        if not description:
            findings.append(
                Finding(
                    "RULE-BIND-DESCRIPTION",
                    path,
                    f"{mode} activation requires a description",
                )
            )
    refs = binding_contract_refs(binding)
    if binding.migration_state in {"contract_bound", "generated"} and not refs:
        findings.append(
            Finding(
                "RULE-BIND-NO-CONTRACTS",
                path,
                f"{binding.migration_state} binding requires contract_bindings",
            )
        )
    seen_refs: set[tuple[str, str]] = set()
    for ref in refs:
        contract_id = str(ref.get("contract_id") or "")
        constraint = str(ref.get("version_constraint") or "*")
        clauses = _as_list(ref.get("clauses"))
        record = contract_index.records.get(contract_id)
        if record is None:
            findings.append(
                Finding(
                    "RULE-BIND-CONTRACT-MISSING",
                    path,
                    f"unresolved contract {contract_id!r}",
                )
            )
            continue
        if record.status != "active":
            findings.append(
                Finding(
                    "RULE-BIND-CONTRACT-LIFECYCLE",
                    path,
                    f"{contract_id} status is {record.status!r}, not active",
                )
            )
        try:
            matches = version_matches(record.version, constraint)
        except ValueError as exc:
            findings.append(
                Finding("RULE-BIND-VERSION-CONSTRAINT", path, str(exc))
            )
            matches = False
        if not matches:
            findings.append(
                Finding(
                    "RULE-BIND-VERSION",
                    path,
                    f"{contract_id}@{record.version} does not satisfy {constraint!r}",
                )
            )
        if not clauses:
            findings.append(
                Finding(
                    "RULE-BIND-CLAUSES",
                    path,
                    f"{contract_id} must reference explicit clauses",
                )
            )
        for raw_clause in clauses:
            clause_id = str(raw_clause)
            key = (contract_id, clause_id)
            if key in seen_refs:
                findings.append(
                    Finding(
                        "RULE-BIND-DUPLICATE-CLAUSE",
                        path,
                        f"duplicate clause reference {contract_id}:{clause_id}",
                    )
                )
            seen_refs.add(key)
            if clause_id not in record.clauses:
                findings.append(
                    Finding(
                        "RULE-BIND-CLAUSE-MISSING",
                        path,
                        f"{contract_id} has no clause {clause_id!r}",
                    )
                )
    findings.extend(_validate_scope_narrowing(binding, contract_index))
    inline = _as_list(guidance.get("inline"))
    for index, item in enumerate(inline):
        if not isinstance(item, dict):
            findings.append(
                Finding(
                    "RULE-BIND-GUIDANCE-SHAPE",
                    path,
                    f"guidance.inline[{index}] must be a mapping",
                )
            )
            continue
        text = str(item.get("text") or "")
        if HARD_NORMATIVE_RE.search(text):
            findings.append(
                Finding(
                    "RULE-BIND-GUIDANCE-NORMATIVE",
                    path,
                    f"guidance.inline[{index}] contains hard normative doctrine",
                )
            )
    refs_guidance = _as_list(guidance.get("refs"))
    for raw_ref in refs_guidance:
        reference = str(raw_ref)
        reference_path = root / reference
        if reference.startswith(("http://", "https://")):
            findings.append(
                Finding(
                    "RULE-BIND-GUIDANCE-NETWORK",
                    path,
                    "guidance refs must be repository-local for deterministic builds",
                )
            )
        elif not reference_path.exists():
            findings.append(
                Finding(
                    "RULE-BIND-GUIDANCE-MISSING",
                    path,
                    f"guidance ref does not exist: {reference}",
                )
            )
    renderer = str(render.get("renderer") or "")
    if renderer != "cursor_mdc_v1":
        findings.append(
            Finding(
                "RULE-BIND-RENDERER",
                path,
                f"unsupported renderer {renderer!r}",
            )
        )
    budget = render.get("context_budget_bytes")
    if (
        not isinstance(budget, int)
        or isinstance(budget, bool)
        or budget <= 0
    ):
        findings.append(
            Finding(
                "RULE-BIND-CONTEXT-BUDGET",
                path,
                "context_budget_bytes must be a positive integer",
            )
        )
    if binding.migration_state not in MIGRATION_STATES:
        findings.append(
            Finding(
                "RULE-BIND-MIGRATION",
                path,
                f"invalid migration_state {binding.migration_state!r}",
            )
        )
    if binding.migration_state == "generated" and status != "active":
        findings.append(
            Finding(
                "RULE-BIND-GENERATED-STATUS",
                path,
                "generated migration state requires active binding status",
            )
        )
    return findings
def validate_all_bindings(
    root: Path = ROOT,
    registry_path: Path | None = None,
) -> list[Finding]:
    bindings = discover_rule_bindings(root)
    index = load_contract_index(root, registry_path)
    findings: list[Finding] = []
    ids: dict[str, str] = {}
    outputs: dict[str, str] = {}
    for binding in bindings:
        prior_id = ids.get(binding.binding_id)
        if prior_id:
            findings.append(
                Finding(
                    "RULE-BIND-DUPLICATE-ID",
                    binding.relative_path,
                    f"{binding.binding_id} already owned by {prior_id}",
                )
            )
        else:
            ids[binding.binding_id] = binding.relative_path
        prior_output = outputs.get(binding.output_path)
        if prior_output:
            findings.append(
                Finding(
                    "RULE-BIND-DUPLICATE-OUTPUT",
                    binding.relative_path,
                    f"{binding.output_path} already owned by {prior_output}",
                )
            )
        else:
            outputs[binding.output_path] = binding.relative_path
        findings.extend(validate_binding(binding, index, root))
    return sorted(
        findings,
        key=lambda item: (item.path.casefold(), item.code, item.message),
    )
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    args = parser.parse_args()
    try:
        findings = validate_all_bindings(args.root.resolve(), args.registry)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"RULE_BINDING_VALIDATION_ERROR: {exc}", file=sys.stderr)
        return 2
    if findings:
        print(f"FAIL ({len(findings)})")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("PASS: rule activation bindings")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
