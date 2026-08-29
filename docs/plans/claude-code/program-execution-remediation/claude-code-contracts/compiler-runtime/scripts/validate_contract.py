#!/usr/bin/env python3
"""Validate a compiled Claude coding contract against bundled JSON schemas + Claude-fit
+ DPK-1.0 readiness rules.

Usage:
    python scripts/validate_contract.py path/to/contract.yaml

Exit codes: 0 = valid, 1 = invalid, 2 = usage/load error.
Determinism-critical: Claude INVOKES this; it does not reason the result.

v2.7.0: target-aware validation + one-commit/single-delivery Claude-fit checks; the v2.1.0 checks (read_only_authority, session_budget, halt_codes)
are invoked from run_claude_fit_checks() inside main(). Prior builds appended them below
`sys.exit(main(...))`, so they never ran as a CLI and NameError'd on import; that dead
monkey-patch has been removed.
"""
import json, sys, pathlib

DPK_WEIGHTS = {"repo_clarity":10,"arch_mapping":15,"local_reproducibility":10,
    "test_eval_coverage":15,"security_boundaries":10,"observability_integrity":15,
    "deploy_rollback":10,"transition_clarity":15}

HALT_CODES = {
    "HALT RESUME_PRECONDITION_NOT_SATISFIED",
    "HALT PR_PREREQUISITE_NOT_SATISFIED",
    "HALT PR_A_PREREQUISITE_NOT_SATISFIED",
    "HALT PR_C_PREREQUISITE_NOT_SATISFIED",
    "HALT SCOPE_VIOLATION",
    "HALT EVIDENCE_MISSING",
    "HALT REMOTE_MUTATION_BLOCKED",
}

def _load(path):
    text = pathlib.Path(path).read_text()
    if path.endswith((".yaml",".yml")):
        try:
            import yaml
        except ImportError:
            print("PyYAML required for YAML contracts", file=sys.stderr); sys.exit(2)
        return yaml.safe_load(text)
    return json.loads(text)

def dpk_score(contract):
    """Compute DPK readiness. Returns (total, band, red_line_reasons)."""
    dpk = contract.get("dpk", {})
    cats = dpk.get("categories", {})
    reasons = []
    manifest = dpk.get("manifest", {})
    if not manifest.get("ownership", {}).get("operational_owner"):
        reasons.append("missing production operations owner in .ai/manifest.yaml")
    if not dpk.get("rollback_target"):
        reasons.append("no machine-executable rollback target")
    if dpk.get("has_ai_feature") and not dpk.get("evaluation_suite"):
        reasons.append("AI feature without evaluation suite")
    if dpk.get("broken_alert_runbook_links"):
        reasons.append("broken alert->runbook reference link")
    if reasons:
        return 0, "rejected", reasons
    total = sum(min(cats.get(k,0), w) for k,w in DPK_WEIGHTS.items())
    band = ("independently_operable" if total>=90 else
            "conditionally_clear" if total>=80 else "rejected")
    return total, band, reasons

# ── Claude-fit checks (v2.1.0, now actually invoked) ────────────

def check_read_only_authority(contract, fit):
    """read_only_authority items must be {resource: str, method: GET|LIST}."""
    ro = contract.get("execution_authority", {}).get("read_only_authority", [])
    for i, item in enumerate(ro):
        if not isinstance(item, dict):
            fit.append(f"read_only_authority[{i}]: must be object"); continue
        if "resource" not in item or "method" not in item:
            fit.append(f"read_only_authority[{i}]: missing resource or method")
        if item.get("method") not in ("GET", "LIST"):
            fit.append(f"read_only_authority[{i}]: method must be GET or LIST")

def check_session_budget(contract, fit):
    """If session_budget present, fits_one_session must be bool; a false claim needs a reason."""
    sb = contract.get("session_budget")
    if sb is None:
        return  # optional
    if not isinstance(sb.get("fits_one_session"), bool):
        fit.append("session_budget: fits_one_session must be boolean")
    if sb.get("fits_one_session") is False and not sb.get("decomposition_reason"):
        fit.append("session_budget: decomposition_reason required when fits_one_session=false")

def check_halt_codes(contract, fit):
    """resume_from.if_assumption_false must be a known halt code (belt-and-braces vs the schema enum)."""
    code = contract.get("resume_from", {}).get("if_assumption_false", "")
    if code and code not in HALT_CODES:
        fit.append(f"halt code unknown: '{code}'")

def check_handoff_seam_shape(contract, fit):
    """Internal handoff tokens represent locally committed + validated predecessor state."""
    green = contract.get("handoff", {}).get("next_session_may_assume_green", [])
    for i, tok in enumerate(green):
        if not (isinstance(tok, str) and tok.endswith(" committed_and_validated")):
            fit.append(
                f"handoff.next_session_may_assume_green[{i}]: must be a "
                f"'<contract-id> committed_and_validated' handshake token, got {tok!r}")


def check_git_workflow(contract, fit):
    git = contract.get("git_workflow", {})
    cid = contract.get("contract_id")
    branch = contract.get("target_branch")
    if git.get("shared_branch") != branch:
        fit.append("git_workflow.shared_branch must equal target_branch")
    if git.get("commit_policy") != "exactly_one_local_commit_per_contract":
        fit.append("git_workflow.commit_policy must require exactly one local commit per contract")
    if git.get("commit_subject") != cid:
        fit.append("git_workflow.commit_subject must equal contract_id exactly")
    expected_commit = f'git commit -m {json.dumps(cid)}'
    if git.get("commit_command") != expected_commit:
        fit.append("git_workflow.commit_command must be the compiler-derived exact one-commit command")
    proof = git.get("completion_proof")
    gate = contract.get("commit_gate", {}).get("required_before_commit", [])
    if not proof or proof not in gate:
        fit.append("git_workflow.completion_proof must be present in commit_gate.required_before_commit")
    if git.get("push_policy") != "terminal_contract_only_via_make_pr":
        fit.append("git_workflow.push_policy must be terminal_contract_only_via_make_pr")
    delivery = git.get("terminal_delivery", {})
    if delivery.get("authorized") is True and delivery.get("command") != "make pr":
        fit.append("authorized terminal delivery command must be exactly 'make pr'")
    if delivery.get("authorized") is False and delivery.get("command") is not None:
        fit.append("nonterminal delivery command must be null")


def check_remote_mutation_denials(contract, fit):
    denied = contract.get("execution_authority", {}).get("denied_tools", [])
    if not any("git push" in d for d in denied):
        fit.append("direct git push must remain denied; terminal delivery is only via make pr")
    if not any("gh pr create" in d or "gh pr *" in d for d in denied):
        fit.append("direct PR creation must remain denied; terminal delivery is only via make pr")

def run_claude_fit_checks(contract, fit):
    if contract.get("executor") != "claude-code":
        fit.append("executor must be claude-code")
    if not contract.get("resume_from"):
        fit.append("resume_from block missing")
    if not contract.get("handoff"):
        fit.append("handoff block missing")
    ea = contract.get("execution_authority", {})
    if len(ea.get("denied_tools", [])) < 5:
        fit.append("halt boundary must be >=5 denied_tools entries")
    check_read_only_authority(contract, fit)
    check_session_budget(contract, fit)
    check_halt_codes(contract, fit)
    check_handoff_seam_shape(contract, fit)
    check_git_workflow(contract, fit)
    check_remote_mutation_denials(contract, fit)

def main(argv):
    if len(argv)!=2:
        print(__doc__); return 2
    schema_dir = pathlib.Path(__file__).resolve().parent.parent/"schemas"
    schema_path = schema_dir/"coding-contract.schema.json"
    if not schema_path.exists():
        print(f"schema not found: {schema_path}", file=sys.stderr); return 2
    try:
        import jsonschema
    except ImportError:
        print("jsonschema required", file=sys.stderr); return 2

    contract = _load(argv[1])
    schema = json.loads(schema_path.read_text())
    store = {f.name: json.loads(f.read_text()) for f in schema_dir.glob("*.schema.json")}
    resolver = jsonschema.RefResolver(base_uri=schema_dir.as_uri()+"/", referrer=schema, store=store)
    validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(contract), key=lambda e: list(e.path))

    fit = []
    run_claude_fit_checks(contract, fit)

    # DPK gate
    dpk_msgs = []
    total, band, red = dpk_score(contract)
    if red:
        for r in red: dpk_msgs.append(f"DPK red-line (score=0): {r}")
    elif contract.get("promotion_ready") and total < 90:
        dpk_msgs.append(f"promotion_ready=true but DPK score {total} < 90 ({band})")

    if not errors and not fit and not dpk_msgs:
        print(f"VALID: schema + Claude-fit + DPK (score={total}, band={band})")
        return 0
    for e in errors: print(f"SCHEMA: {list(e.path)}: {e.message}")
    for f in fit: print(f"CLAUDE-FIT: {f}")
    for m in dpk_msgs: print(f"DPK: {m}")
    return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
