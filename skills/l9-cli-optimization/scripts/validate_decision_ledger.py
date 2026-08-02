#!/usr/bin/env python3
"""Validate the adaptive execution route and evidence/decision ledger."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROUTE_ACTIONS = {"proceed", "proceed_with_validation", "bounded_probe", "blocked_pack"}
FINAL_ACTIONS = ROUTE_ACTIONS
PROOF_STATUSES = {"pending", "satisfied", "blocked"}
CONVERGENCE = {"converged", "partial", "blocked"}
CAPABILITY_GAPS = {
    "inactive_component",
    "miswired_file",
    "dormant_capability",
    "unused_signal",
    "orphaned_config_schema",
    "broken_partial_wiring",
    "latent_capability_wiring",
}
WIRING_STRATEGIES = {
    "activate_latent_capability",
    "repair_wiring",
    "connect_signal_consumer",
    "surface_existing_cli_path",
}


def _ids(items: Any, field: str, pattern: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{field} must be an array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"{field}[{index}] must be an object")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not re.fullmatch(pattern, item_id):
            errors.append(f"{field}[{index}].id is invalid")
            continue
        if item_id in result:
            errors.append(f"duplicate {field} id: {item_id}")
        result[item_id] = item
    return result


def validate_decision_contract(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    route = spec.get("execution_route")
    ledger = spec.get("decision_ledger")
    if not isinstance(route, dict):
        return [
            "execution_route must be an object (pass the combined spec, a pack directory, or DECISION_LEDGER.json beside EXECUTION_ROUTE.json)"
        ]
    if not isinstance(ledger, dict):
        return ["decision_ledger must be an object"]

    if route.get("route_version") != "1.0.0":
        errors.append("execution_route.route_version must be 1.0.0")
    if route.get("task_kind") != "optimize_cli_revision":
        errors.append("execution_route.task_kind must be optimize_cli_revision")
    if route.get("reasoning_depth") not in {"rapid", "standard", "deep"}:
        errors.append("execution_route.reasoning_depth is invalid")
    if route.get("initial_action") not in ROUTE_ACTIONS:
        errors.append("execution_route.initial_action is invalid")
    if route.get("max_cycles") != 3:
        errors.append("execution_route.max_cycles must be 3")
    if not isinstance(route.get("write_action_allowed"), bool):
        errors.append("execution_route.write_action_allowed must be boolean")
    for field in ("epistemic_methods", "required_adapters"):
        value = route.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            errors.append(f"execution_route.{field} must be a non-empty string array")
    route_proofs = _ids(
        route.get("proof_obligations"),
        "execution_route.proof_obligations",
        r"PO-[A-Z0-9-]+",
        errors,
    )
    for proof_id, proof in route_proofs.items():
        if not isinstance(proof.get("description"), str) or not proof["description"].strip():
            errors.append(f"route proof {proof_id} requires description")
        if not isinstance(proof.get("source"), str) or not proof["source"].strip():
            errors.append(f"route proof {proof_id} requires source")

    if ledger.get("ledger_version") != "1.0.0":
        errors.append("decision_ledger.ledger_version must be 1.0.0")
    if not isinstance(ledger.get("objective"), str) or not ledger["objective"].strip():
        errors.append("decision_ledger.objective is required")
    cycle = ledger.get("cycle")
    if not isinstance(cycle, int) or isinstance(cycle, bool) or not 1 <= cycle <= 3:
        errors.append("decision_ledger.cycle must be 1..3")

    claims = _ids(ledger.get("claims"), "decision_ledger.claims", r"CLM-[0-9]{3}", errors)
    if not claims:
        errors.append("decision_ledger.claims must not be empty")
    for claim_id, claim in claims.items():
        if claim.get("grade") not in {"verified", "inferred", "unknown"}:
            errors.append(f"claim {claim_id} grade is invalid")
        evidence = claim.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"claim {claim_id} evidence must be an array")
        if claim.get("grade") == "verified" and not evidence:
            errors.append(f"verified claim {claim_id} requires evidence")
        if not isinstance(claim.get("disconfirming_evidence", []), list):
            errors.append(f"claim {claim_id} disconfirming_evidence must be an array")

    options = _ids(ledger.get("options"), "decision_ledger.options", r"CLI-OPT-[0-9]{3}", errors)
    selected = ledger.get("selected_option_ids")
    if (
        not isinstance(selected, list)
        or not selected
        or not all(isinstance(item, str) for item in selected)
    ):
        errors.append("decision_ledger.selected_option_ids must be a non-empty string array")
        selected = []
    if len(set(selected)) != len(selected):
        errors.append("decision_ledger.selected_option_ids contains duplicates")
    if set(selected) - set(options):
        errors.append("decision_ledger selected option missing from options")
    for option_id, option in options.items():
        if option.get("disposition") not in {"selected", "rejected", "deferred", "candidate"}:
            errors.append(f"option {option_id} disposition is invalid")
        if option_id in selected and option.get("disposition") != "selected":
            errors.append(f"selected option {option_id} must have disposition selected")
        if option.get("reversibility") not in {"reversible", "guarded", "irreversible"}:
            errors.append(f"option {option_id} reversibility is invalid")
        if not isinstance(option.get("tradeoffs"), list):
            errors.append(f"option {option_id} tradeoffs must be an array")

    unknowns = _ids(ledger.get("unknowns"), "decision_ledger.unknowns", r"UNK-[0-9]{3}", errors)
    material_unresolved: set[str] = set()
    for unknown_id, unknown in unknowns.items():
        if not isinstance(unknown.get("material"), bool):
            errors.append(f"unknown {unknown_id} material must be boolean")
        if unknown.get("disposition") not in {
            "resolved",
            "probe",
            "constraint",
            "handoff",
            "block",
        }:
            errors.append(f"unknown {unknown_id} disposition is invalid")
        if unknown.get("material") is True and unknown.get("disposition") != "resolved":
            material_unresolved.add(unknown_id)
        if not isinstance(unknown.get("evidence", []), list):
            errors.append(f"unknown {unknown_id} evidence must be an array")

    _ids(ledger.get("probes"), "decision_ledger.probes", r"PRB-[0-9]{3}", errors)
    ledger_proofs = _ids(
        ledger.get("proof_obligations"),
        "decision_ledger.proof_obligations",
        r"PO-[A-Z0-9-]+",
        errors,
    )
    if set(route_proofs) != set(ledger_proofs):
        errors.append("ledger proof obligations must exactly match routed proof obligations")

    # M1: bind the route's declared adapters/obligations to the spec content, so
    # a hand-authored route that under-declares them cannot pass. Content is only
    # available when the caller supplies optimization/wiring/revision_synthesis.
    optimization = spec.get("optimization")
    if isinstance(optimization, dict):
        synthesis = spec.get("revision_synthesis") or {}
        wiring = spec.get("wiring") or {}
        required_adapters = {"revision_synthesis_leverage", "ecosystem_native_cli"}
        required_pos: set[str] = set()
        if (optimization.get("ownership") or route.get("ownership")) == "repository_owned":
            required_pos.add("PO-UTILIZATION-PROOF")
        if route.get("risk_class") in {"guarded", "irreversible"}:
            required_pos.add("PO-DEPLOY-ROLLBACK")
        capability = (
            bool(wiring.get("analysis_performed"))
            or optimization.get("strategy") in WIRING_STRATEGIES
            or optimization.get("utilization_gap_class") in CAPABILITY_GAPS
        )
        if capability:
            required_adapters.add("latent_capability_reachability")
            required_pos.add("PO-REACHABILITY")
        findings = synthesis.get("findings") or []
        if any(isinstance(f, dict) and f.get("kind") == "docs_code_divergence" for f in findings):
            required_adapters.add("docs_code_divergence")
            required_pos.add("PO-DIVERGENCE")
        declared_adapters = set(route.get("required_adapters") or [])
        missing_adapters = required_adapters - declared_adapters
        if missing_adapters:
            errors.append(
                f"execution_route.required_adapters under-declares content-required adapters: {sorted(missing_adapters)}"
            )
        missing_pos = required_pos - set(route_proofs)
        if missing_pos:
            errors.append(
                f"execution_route.proof_obligations under-declares content-required obligations: {sorted(missing_pos)}"
            )
    for proof_id, proof in ledger_proofs.items():
        if proof.get("status") not in PROOF_STATUSES:
            errors.append(f"proof obligation {proof_id} status is invalid")
        if proof.get("status") == "satisfied" and not proof.get("evidence"):
            errors.append(f"satisfied proof obligation {proof_id} requires evidence")

    revision = spec.get("revision_synthesis", {})
    revision_selected = revision.get("selected_option_ids") if isinstance(revision, dict) else None
    if isinstance(revision_selected, list) and set(selected) != set(revision_selected):
        errors.append("decision ledger selection must match revision synthesis selection")

    decision = ledger.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision_ledger.decision must be an object")
        decision = {}
    if decision.get("final_action") not in FINAL_ACTIONS:
        errors.append("decision_ledger.decision.final_action is invalid")
    for field in ("rationale", "rollback_or_containment"):
        if not isinstance(decision.get(field), str) or not decision[field].strip():
            errors.append(f"decision_ledger.decision.{field} is required")
    if not isinstance(decision.get("tradeoffs"), list):
        errors.append("decision_ledger.decision.tradeoffs must be an array")

    convergence = ledger.get("convergence")
    if not isinstance(convergence, dict):
        errors.append("decision_ledger.convergence must be an object")
        convergence = {}
    if convergence.get("status") not in CONVERGENCE:
        errors.append("decision_ledger.convergence.status is invalid")
    remaining = convergence.get("remaining_material_unknown_ids")
    if not isinstance(remaining, list):
        errors.append("convergence.remaining_material_unknown_ids must be an array")
        remaining = []
    if set(remaining) != material_unresolved:
        errors.append("convergence remaining material unknowns do not match ledger unknowns")

    status = spec.get("status")
    if status == "PR_READY":
        if decision.get("final_action") not in {"proceed", "proceed_with_validation"}:
            errors.append("PR_READY requires proceed or proceed_with_validation final action")
        if convergence.get("status") != "converged":
            errors.append("PR_READY requires converged decision ledger")
        if material_unresolved:
            errors.append("PR_READY cannot retain material unknowns")
        blocked_or_pending = [
            pid for pid, proof in ledger_proofs.items() if proof.get("status") != "satisfied"
        ]
        if blocked_or_pending:
            errors.append(f"PR_READY has unsatisfied proof obligations: {blocked_or_pending}")
    if status == "BLOCKED" and decision.get("final_action") != "blocked_pack":
        errors.append("BLOCKED status requires blocked_pack final action")
    return errors


def _load_contract_input(path: Path) -> dict:
    """Accept a combined spec, a built pack directory, or the pack's split
    evidence/DECISION_LEDGER.json (reassembling execution_route from its
    sibling EXECUTION_ROUTE.json) so the CLI works against real pack output."""
    if path.is_dir():
        evidence = path / "evidence"
        base = evidence if evidence.is_dir() else path
        route = json.loads((base / "EXECUTION_ROUTE.json").read_text(encoding="utf-8"))
        ledger = json.loads((base / "DECISION_LEDGER.json").read_text(encoding="utf-8"))
        return {"execution_route": route, "decision_ledger": ledger}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("spec root must be an object")
    if "execution_route" not in data and path.name == "DECISION_LEDGER.json":
        sibling = path.parent / "EXECUTION_ROUTE.json"
        if not sibling.is_file():
            raise ValueError(
                "DECISION_LEDGER.json has no execution_route; expected sibling "
                "EXECUTION_ROUTE.json next to it, or pass the pack directory / the combined spec"
            )
        return {
            "execution_route": json.loads(sibling.read_text(encoding="utf-8")),
            "decision_ledger": data,
        }
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", nargs="?", type=Path)
    args = parser.parse_args()
    path = args.spec or Path(__file__).resolve().parents[1] / "assets" / "pack-spec.example.json"
    try:
        data = _load_contract_input(path)
        errors = validate_decision_contract(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: adaptive route and evidence decision ledger are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
