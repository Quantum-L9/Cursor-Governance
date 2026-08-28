#!/usr/bin/env python3
"""
compile_contract.py — l9-claude-coding-contract-compiler v2.7.0

Deterministic emitter: compile a canonical campaign spec (YAML/JSON) into schema-valid
Claude Code contract instances. This is the piece that removes the model from the
determinism-critical emit path — Claude/authors decide WHAT (the spec); this script fixes
the IDs, handoff seams, source-commit contiguity, and chain_digest.

    python scripts/compile_contract.py --spec campaign-spec.yaml --out DIR \
        [--validate] [--emit-artifacts] [--config thresholds.json]

Exit codes: 0 = all instances emitted and (if --validate) green; 1 = fail-closed
(invalid instance, broken chain, scope/DPK violation, or an item that does not fit one
session). 2 = usage/load error.

Single source of truth for the digest: imported `compute_chain_digest` from validate_chain
(the same function the chain validator uses) — no re-implementation, no drift.
"""

import argparse
import importlib.util
import json
import pathlib
import re
import shlex
import sys
from types import ModuleType

HERE = pathlib.Path(__file__).resolve().parent
SCHEMA_DIR = HERE.parent / "schemas"

#: Namespace for this pack's sibling scripts in ``sys.modules``.
_PACK = "l9_ccc"


def _sibling(name: str) -> ModuleType:
    """Import a sibling script by path, under a pack-unique module name.

    Several L9 skill packs ship scripts with identical basenames —
    ``validate_contract.py``, ``_common.py``, ``self_test.py``. A bare
    ``import validate_contract`` after ``sys.path.insert`` resolves through the
    flat ``sys.modules`` namespace, so whichever pack imported first wins. That
    is not theoretical: on 2026-08-28 two packs' ``_common.py`` collided and
    broke test collection, and CodeQL read this module's ``vc.main(argv)``
    against ``skills/l9-repository-renovation/scripts/validate_contract.py``,
    whose ``main()`` takes no arguments — a false "too many arguments" alert
    produced by exactly this ambiguity.

    Loading by explicit file location under ``l9_ccc.*`` makes the resolution
    exact for the interpreter and for any reader or analyzer.
    """
    spec = importlib.util.spec_from_file_location(f"{_PACK}.{name}", HERE / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - packaging fault
        raise ImportError(f"cannot load sibling script: {name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gcs = _sibling("generate_claude_settings")  # optional artifacts
gpf = _sibling("generate_preflight")
pdc = _sibling("plan_decomposition")  # fits_one, thresholds
vc = _sibling("validate_contract")  # per-instance gate; its main() takes argv
_validate_chain_mod = _sibling("validate_chain")  # single digest + seam source
compute_chain_digest = _validate_chain_mod.compute_chain_digest
validate_chain = _validate_chain_mod.validate_chain

DEFAULT_DENIED = [
    "Bash(git push:*)",
    "Bash(git merge:*)",
    "Bash(gh pr create:*)",
    "Bash(gh pr merge:*)",
    "Bash(gh api *repos*:*)",
    "Bash(npm publish:*)",
]
DEFAULT_HALT = [
    "git_push",
    "pr_open",
    "pr_merge",
    "required_check_change",
    "ruleset_change",
    "branch_protection_change",
]

SECTION_NAMES = [
    "Resume-From",
    "Mandate",
    "Prerequisite Contract",
    "Scope Lock",
    "Package Layout",
    "Registry/Config Authority",
    "Risk/Tier Policy",
    "Context Normalization",
    "Input Acquisition",
    "Deterministic Planner",
    "Safe Executor",
    "Evidence Enrichment",
    "Fail-Closed Evaluator",
    "Workflow Architecture",
    "Matrix/Parallel Execution",
    "Runtime Guarantee Preservation",
    "Self-Modification Protection",
    "Schemas",
    "Test Contract",
    "Failure Evidence",
    "Documentation",
    "Required File Manifest",
    "Commit Plan",
    "Validation Commands",
    "Acceptance Criteria",
    "Non-Goals Verification",
    "Required Validation Report",
    "Definition of Done",
    "Handoff",
    "Governance",
]
DPK_WEIGHTS = {
    "repo_clarity": 10,
    "arch_mapping": 15,
    "local_reproducibility": 10,
    "test_eval_coverage": 15,
    "security_boundaries": 10,
    "observability_integrity": 15,
    "deploy_rollback": 10,
    "transition_clarity": 15,
}
DEFAULT_NA_14 = "Single focused-session additive change; no parallel/matrix execution track."


def load(path):
    text = pathlib.Path(path).read_text()
    if str(path).endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError:
            sys.exit("PyYAML required for YAML specs: pip install pyyaml")
        return yaml.safe_load(text)
    return json.loads(text)


def validate_command_list(commands, field):
    """Validate canonical shell command strings structurally without executing target code."""
    errors = []
    if not isinstance(commands, list) or not commands:
        return [f"SPEC: {field}: at least one command is required"]
    seen = set()
    for i, command in enumerate(commands):
        if not isinstance(command, str) or not command.strip():
            errors.append(f"SPEC: {field}[{i}]: command must be a non-empty string")
            continue
        if "\n" in command or "\r" in command:
            errors.append(f"SPEC: {field}[{i}]: command must be a single-line shell command")
        if command in seen:
            errors.append(f"SPEC: {field}[{i}]: duplicate command is not allowed")
        seen.add(command)
    return errors


def validate_spec(spec):
    """Fail-closed canonical-spec validation. Critical execution rules do not depend on jsonschema."""
    errors = []
    if not isinstance(spec, dict):
        return ["SPEC: root must be an object"]
    camp = spec.get("campaign")
    items = spec.get("items")
    if not isinstance(camp, dict):
        return ["SPEC: campaign is required"]
    validation = camp.get("validation")
    if not isinstance(validation, dict):
        errors.append(
            "SPEC: campaign.validation is required; declare target-native cold_resume.commands "
            "and commit_gate.commands. No validation ecosystem is inferred."
        )
    else:
        cold = validation.get("cold_resume", {})
        gate = validation.get("commit_gate", {})
        errors.extend(
            validate_command_list(cold.get("commands"), "campaign.validation.cold_resume.commands")
        )
        errors.extend(
            validate_command_list(gate.get("commands"), "campaign.validation.commit_gate.commands")
        )
    if not isinstance(items, list) or not items:
        errors.append("SPEC: items must contain at least one contract")
    else:
        for i, item in enumerate(items):
            proof = item.get("verify_proof") if isinstance(item, dict) else None
            if not isinstance(proof, str) or not proof.strip():
                errors.append(f"SPEC: items[{i}].verify_proof must be a non-empty runnable command")
            elif "\n" in proof or "\r" in proof:
                errors.append(f"SPEC: items[{i}].verify_proof must be a single-line shell command")
            commits = (item.get("sizing", {}) if isinstance(item, dict) else {}).get("commits")
            if commits != 1:
                errors.append(
                    f"SPEC: items[{i}].sizing.commits must equal 1; "
                    "decompose multi-commit work into ordered contracts"
                )

    sp = SCHEMA_DIR / "campaign-spec.schema.json"
    try:
        import jsonschema
    except ImportError:
        return errors
    schema = json.loads(sp.read_text())
    store = {f.name: json.loads(f.read_text()) for f in SCHEMA_DIR.glob("*.schema.json")}
    resolver = jsonschema.RefResolver(
        base_uri=SCHEMA_DIR.as_uri() + "/", referrer=schema, store=store
    )
    v = jsonschema.Draft202012Validator(schema, resolver=resolver)
    errors.extend(
        f"SPEC: {list(e.path)}: {e.message}"
        for e in sorted(v.iter_errors(spec), key=lambda e: list(e.path))
    )
    return errors


def glob_to_re(g):
    out, i = "", 0
    while i < len(g):
        if g[i : i + 2] == "**":
            out += ".*"
            i += 2
        elif g[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(g[i])
            i += 1
    return re.compile("^" + out + "$")


def owns_path_check(in_scope_paths, owns):
    """DPK doctrine: in_scope MUST be within boundaries.owns. Enforced only when owns carries
    path-like globs (has '/', '*', or a file extension); pure domain labels can't gate paths."""
    path_globs = [g for g in owns if ("/" in g or "*" in g or re.search(r"\.[a-z0-9]+$", g))]
    if not path_globs:
        return [], "skipped (no path-like owns globs in manifest.boundaries.owns)"
    pats = [glob_to_re(g) for g in path_globs]
    bad = [p for p in in_scope_paths if not any(pat.match(p) for pat in pats)]
    return (
        [f"SCOPE: in_scope path '{p}' is outside manifest.boundaries.owns" for p in bad],
        f"enforced against {len(path_globs)} owns globs",
    )


def dpk_readiness(cats, manifest, rollback_target, has_ai, eval_suite):
    reasons = []
    if not manifest.get("ownership", {}).get("operational_owner"):
        reasons.append("missing production operations owner in .ai/manifest.yaml")
    if not rollback_target:
        reasons.append("no machine-executable rollback target")
    if has_ai and not eval_suite:
        reasons.append("AI feature without evaluation suite")
    if reasons:
        return {
            "total": 0,
            "band": "rejected",
            "categories": cats,
            "red_line_triggered": True,
            "red_line_reasons": reasons,
        }
    total = sum(min(cats.get(k, 0), w) for k, w in DPK_WEIGHTS.items())
    band = (
        "independently_operable"
        if total >= 90
        else "conditionally_clear"
        if total >= 80
        else "rejected"
    )
    return {"total": total, "band": band, "categories": cats, "red_line_triggered": False}


def build_sections(na_map):
    out = []
    for n, name in enumerate(SECTION_NAMES):
        e = {"number": n, "name": name, "status": "present"}
        if str(n) in na_map:
            e["status"] = "not_applicable"
            e["not_applicable_reason"] = na_map[str(n)]
        out.append(e)
    return out


def unique_commands(commands):
    """Stable, order-preserving deduplication for canonical command projections."""
    return list(dict.fromkeys(commands))


def branch_assertion(branch):
    """Executable equality assertion. Unlike the v2.6.2 comment form, this actually fails on mismatch."""
    return f'test "$(git rev-parse --abbrev-ref HEAD)" = {shlex.quote(branch)}'


def commit_subject(contract_id):
    """Machine-stable one-commit identity. Keep user-controlled titles out of shell assertions."""
    return contract_id


def head_commit_assertion(subject):
    return f'test "$(git show -s --format=%s HEAD)" = {shlex.quote(subject)}'


def build_instance(
    camp, item, prev_item, idx, all_ids, prev_id, next_id, digest, commit_range, dpk_block, errors
):
    cid = all_ids[idx]
    branch = camp["target_branch"]
    is_terminal = next_id is None
    allowed = item["allowed_files"]
    in_scope = [
        {"id": i + 1, "deliverable": a["deliverable"], "path": a["path"]}
        for i, a in enumerate(allowed)
    ]

    # preserved: forbidden_paths default behavior_unchanged, overridden by explicit 'preserved'
    override = {p["path"]: p["guarantee"] for p in item.get("preserved", [])}
    preserved = []
    for fp in item.get("forbidden_paths", []):
        preserved.append({"path": fp, "guarantee": override.get(fp, "behavior_unchanged")})
    for p in item.get("preserved", []):
        if p["path"] not in item.get("forbidden_paths", []):
            preserved.append({"path": p["path"], "guarantee": p["guarantee"]})

    does_not_own = camp["dpk"]["manifest"].get("boundaries", {}).get("does_not_own", [])
    hard_oos = list(dict.fromkeys(item.get("forbidden_capabilities", []) + does_not_own))
    if not hard_oos:
        hard_oos = ["remote mutation outside terminal make pr delivery"]

    # DPK scope doctrine: in_scope within owns
    owns = camp["dpk"]["manifest"].get("boundaries", {}).get("owns", [])
    scope_errs, _ = owns_path_check([a["path"] for a in allowed], owns)
    errors.extend(f"[{cid}] {e}" for e in scope_errs)

    na = {"14": DEFAULT_NA_14}
    na.update({str(k): v for k, v in item.get("not_applicable_sections", {}).items()})

    ea = {
        "denied_tools": camp.get("denied_tools", DEFAULT_DENIED),
        "dry_run_mapping": "plan_mode",
        "may_read_repository": True,
        "may_modify_worktree": True,
        "may_run_local_tests": True,
        "may_create_local_commits": True,
        "may_rewrite_unpushed_local_commits": False,
    }

    validation = camp["validation"]
    cold_resume = list(validation["cold_resume"]["commands"])
    commit_validation = list(validation["commit_gate"]["commands"])

    resume_commands = [branch_assertion(branch)]
    if prev_id:
        resume_commands.append(head_commit_assertion(commit_subject(prev_id)))
    resume_commands.extend(cold_resume)
    if prev_item is not None:
        # Contract N+1 proves N with the minimum sufficient predecessor evidence:
        # exact predecessor HEAD identity plus N's dedicated completion proof.
        # Do not replay N's repository-wide commit gate; that duplicates work needlessly.
        resume_commands.append(prev_item["verify_proof"])
    resume_commands = unique_commands(resume_commands)

    current_commit_gate = unique_commands(commit_validation + [item["verify_proof"]])

    if prev_id:
        prerequisite = {"id": prev_id, "required_state": "committed_and_validated"}
        assumptions = [f"{prev_id} committed_and_validated"]
    else:
        prerequisite = camp.get("base_prerequisite")
        if prerequisite:
            assumptions = [f"{prerequisite['id']} {prerequisite['required_state']}"]
        else:
            assumptions = []

    return {
        "executor": "claude-code",
        "contract_id": cid,
        "contract_version": camp["contract_version"],
        "target_repo": camp["target_repo"],
        "target_branch": branch,
        "pr_title": f"PR-{item['key']} — {item['title']}",
        "prerequisite_contract": prerequisite,
        "resume_from": {
            "assumes_already_green": assumptions,
            "verify_before_starting": resume_commands,
            "if_assumption_false": "HALT RESUME_PRECONDITION_NOT_SATISFIED",
        },
        "execution_authority": ea,
        "halt_boundary": camp.get("halt_boundary", DEFAULT_HALT),
        "commit_gate": {"required_before_commit": current_commit_gate},
        "git_workflow": {
            "shared_branch": branch,
            "commit_policy": "exactly_one_local_commit_per_contract",
            "commit_subject": commit_subject(cid),
            "commit_command": f"git commit -m {json.dumps(commit_subject(cid))}",
            "completion_proof": item["verify_proof"],
            "push_policy": "terminal_contract_only_via_make_pr",
            "terminal_delivery": {
                "authorized": is_terminal,
                "command": "make pr" if is_terminal else None,
            },
        },
        "scope_lock": {
            "in_scope": in_scope,
            "hard_out_of_scope": hard_oos,
            "preserved_files": preserved,
            "must_not_add": hard_oos,
        },
        "sections": build_sections(na),
        "agent_self_approval_forbidden": True,
        "promotion_ready": False,
        "handoff": {
            "next_session_may_assume_green": [f"{cid} committed_and_validated"],
            "next_contract": next_id,
            "chain_digest": digest,
        },
        "dpk": dpk_block,
        "session_budget": {
            "estimated_new_files": item["sizing"]["new_files"],
            "estimated_modified_files": item["sizing"]["modified_files"],
            "estimated_test_cases": item["sizing"]["test_cases"],
            "fits_one_session": True,
            "source_commits": commit_range,
        },
    }


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--emit-artifacts", action="store_true")
    ap.add_argument("--config", default=None, help="JSON overriding plan_decomposition thresholds")
    args = ap.parse_args(argv[1:])

    spec = load(args.spec)
    spec_errs = validate_spec(spec)
    if spec_errs:
        print("\n".join(spec_errs), file=sys.stderr)
        return 1

    camp, items = spec["campaign"], spec["items"]
    cfg = dict(pdc.DEFAULTS)
    if args.config:
        cfg.update(json.loads(pathlib.Path(args.config).read_text()))

    prefix, ver = camp["id_prefix"], camp["contract_version"]
    all_ids = [f"{prefix}-PR-{it['key']}-v{ver}" for it in items]
    digest = compute_chain_digest(all_ids)

    errors = []
    # Fit check — fail-closed; decomposition is authored, never invented (skill doctrine)
    for it in items:
        m = {
            "new_files": it["sizing"]["new_files"],
            "commits": it["sizing"]["commits"],
            "matrix_cases": it["sizing"].get("matrix_cases", 0),
            "deliverables": len(it["allowed_files"]),
        }
        ok, reasons = pdc.fits_one(m, cfg)
        if not ok:
            errors.append(
                f"[PR-{it['key']}] DECOMPOSE_REQUIRED: {'; '.join(reasons)} — "
                f"split this item into ordered sub-items in the spec; do not compress."
            )

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    instances, commit_cursor = [], 1
    for idx, it in enumerate(items):
        # schema + validate_spec enforce exactly one local commit per contract
        commit_range = [commit_cursor]
        commit_cursor += 1
        prev_id = all_ids[idx - 1] if idx > 0 else None
        next_id = all_ids[idx + 1] if idx < len(items) - 1 else None
        dpk = camp["dpk"]
        readiness = dpk_readiness(
            it["readiness"]["categories"],
            dpk["manifest"],
            dpk["rollback_target"],
            dpk.get("has_ai_feature", False),
            dpk.get("evaluation_suite"),
        )
        dpk_block = {
            "manifest": dpk["manifest"],
            "rollback_target": dpk["rollback_target"],
            "has_ai_feature": dpk.get("has_ai_feature", False),
            "broken_alert_runbook_links": False,
            "categories": it["readiness"]["categories"],
            "readiness": readiness,
        }
        if dpk.get("evaluation_suite") is not None:
            dpk_block["evaluation_suite"] = dpk["evaluation_suite"]
        prev_item = items[idx - 1] if idx > 0 else None
        inst = build_instance(
            camp,
            it,
            prev_item,
            idx,
            all_ids,
            prev_id,
            next_id,
            digest,
            commit_range,
            dpk_block,
            errors,
        )
        instances.append(inst)
        (out / f"PR-{it['key']}.contract.json").write_text(json.dumps(inst, indent=2) + "\n")

    print(f"emitted {len(instances)} instances -> {out}")
    print(f"chain_digest: {digest}")

    if errors:
        print("\nFAIL-CLOSED:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    if args.validate:
        nfail = 0
        for it in items:
            p = str(out / f"PR-{it['key']}.contract.json")
            rc = vc.main(["compile_contract", p])
            if rc != 0:
                nfail += 1
        chain_errs = validate_chain(instances)
        print(f"\nper-instance: {len(items) - nfail} pass / {nfail} fail")
        print(f"chain: {'VALID' if not chain_errs else 'INVALID'}")
        for e in chain_errs:
            print(f"  {e}", file=sys.stderr)
        if nfail or chain_errs:
            return 1

    if args.emit_artifacts:
        for it in items:
            p = str(out / f"PR-{it['key']}.contract.json")
            d = out / "artifacts" / f"PR-{it['key']}"
            _run(gcs, ["x", p, "--output-dir", str(d)])
            _run(gpf, ["x", p, "--output-dir", str(d)])
        print(f"artifacts -> {out / 'artifacts'}")

    return 0


def _run(mod, argv):
    """generate_* scripts use argparse in main(); invoke with a patched argv."""
    old = sys.argv
    sys.argv = argv
    try:
        mod.main()
    finally:
        sys.argv = old


if __name__ == "__main__":
    sys.exit(main(sys.argv))
