#!/usr/bin/env python3
"""Deterministically validate GAR cross-file runtime and package readiness."""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema
import yaml

sys.dont_write_bytecode = True

PACK_VERSION = "0.8.2"
EXPECTED_EVAL_MAX = 61
FORBIDDEN_DIR_NAMES = {"__pycache__", "__MACOSX", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_FILE_NAMES = {".DS_Store", "Thumbs.db"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".swp", ".tmp", ".log"}
CURRENT_MARKER_ROOTS = {
    "SKILL.md",
    "runtime",
    "contracts",
    "integrations",
    "kernels",
    "catalogs",
    "bindings",
    "scripts",
    "evals",
    "schemas",
    "fixtures",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"YAML parse failed for {path}: {exc}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"JSON parse failed for {path}: {exc}")


def path_without_anchor(ref: str) -> str:
    return ref.split("#", 1)[0]


def resolve_ref(root: Path, ref: str, *, base: Path | None = None) -> Path:
    raw = path_without_anchor(ref)
    if raw.startswith("../") and base is not None:
        return (base / raw).resolve()
    if raw.startswith("../"):
        return (root / raw).resolve()
    if base is not None and raw.startswith("references/"):
        candidate = (base / raw).resolve()
        if candidate.exists():
            return candidate
    return (root / raw).resolve()


def parse_semver(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(value).strip())
    if not match:
        fail(f"invalid semantic version: {value!r}")
    return tuple(int(x) for x in match.groups())


def compatible(version: str, spec: str) -> bool:
    current = parse_semver(version)
    clauses = spec.split()
    for clause in clauses:
        if clause.startswith(">="):
            if not current >= parse_semver(clause[2:]):
                return False
        elif clause.startswith("<="):
            if not current <= parse_semver(clause[2:]):
                return False
        elif clause.startswith("=="):
            if not current == parse_semver(clause[2:]):
                return False
        elif clause.startswith(">"):
            if not current > parse_semver(clause[1:]):
                return False
        elif clause.startswith("<"):
            if not current < parse_semver(clause[1:]):
                return False
        else:
            fail(f"unsupported compatibility clause: {clause!r}")
    return True


def extract_skill_version(skill_text: str) -> str:
    match = re.search(r"(?m)^\s{2}version:\s*([^\s]+)\s*$", skill_text)
    if not match:
        fail("SKILL.md metadata version missing")
    return match.group(1)


def walk_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_values(item)


def iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def collect_declared_contract_ids(root: Path) -> set[str]:
    declared: set[str] = set()
    keys = {"contract_id", "integration_id", "profile_id", "runtime_id"}
    for path in root.rglob("*.yaml"):
        obj = load_yaml(path)
        for key, value in walk_values(obj):
            if key in keys and isinstance(value, str):
                declared.add(value)
        if isinstance(obj, dict):
            for top in ("contract", "metadata", "adr"):
                node = obj.get(top)
                if isinstance(node, dict) and isinstance(node.get("id"), str):
                    declared.add(node["id"])
    return declared


def validate_python_no_required_stub(path: Path) -> None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"Python syntax failed for {path}: {exc}")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                fail(f"stub-like function body in shipped script: {path}:{node.lineno} {node.name}")
            if len(body) == 1 and isinstance(body[0], ast.Raise):
                call = body[0].exc
                if (
                    isinstance(call, ast.Call)
                    and getattr(call.func, "id", None) == "NotImplementedError"
                ):
                    fail(
                        f"NotImplementedError stub in shipped script: {path}:{node.lineno} {node.name}"
                    )


def import_decision_validator(path: Path):
    spec = importlib.util.spec_from_file_location("gar_product_validator", path)
    if spec is None or spec.loader is None:
        fail("cannot load product architecture decision validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_decision_failure(module, decision: dict[str, Any], needle: str) -> None:
    try:
        module.validate(decision)
    except Exception as exc:
        if needle not in str(exc):
            fail(
                f"negative decision validation failed for wrong reason: expected {needle!r}, got {exc}"
            )
        return
    fail(f"negative decision validation unexpectedly passed: {needle}")


def validate_hygiene(root: Path) -> list[Path]:
    files = [p for p in root.rglob("*") if p.is_file()]
    if not files:
        fail("empty skill pack")
    for path in root.rglob("*"):
        if path.is_symlink():
            fail(f"symlink is not allowed in distributable skill pack: {path.relative_to(root)}")
        if path.is_dir() and path.name in FORBIDDEN_DIR_NAMES:
            fail(f"forbidden residue directory: {path.relative_to(root)}")
        if path.is_file() and (
            path.name in FORBIDDEN_FILE_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES
        ):
            fail(f"forbidden residue file: {path.relative_to(root)}")
    return files


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    if not (root / "SKILL.md").is_file():
        fail(f"pack root not found: {root}")

    # Inventory and final-state hygiene first. Run again after all validator imports/execution.
    files = validate_hygiene(root)

    # Parse every structured artifact and syntax-check every shipped Python script.
    for path in files:
        if path.suffix in {".yaml", ".yml"}:
            load_yaml(path)
        elif path.suffix == ".json":
            load_json(path)
        elif path.suffix == ".py":
            validate_python_no_required_stub(path)

    manifest = load_yaml(root / "runtime/MANIFEST.yaml")
    run_state = load_yaml(root / "runtime/RUN_STATE.yaml")
    state_machine = load_yaml(root / "runtime/STATE_MACHINE.yaml")
    foursome = load_yaml(root / "integrations/REASONING_FOURSOME_BINDING.yaml")
    load_yaml(root / "contracts/L9_ARCHITECTURE_PROFILE.yaml")
    convergence = load_yaml(root / "contracts/CONVERGENCE.yaml")
    reason_codes = load_yaml(root / "catalogs/REASON_CODES.yaml")
    behavior = load_yaml(root / "evals/BEHAVIOR_CONFORMANCE.yaml")
    architect = load_yaml(root / "kernels/ARCHITECT_KERNEL.yaml")

    # Release identity is pack-level. Independently owned semantic artifacts keep independent versions.
    manifest_version = str(manifest["manifest"]["version"])
    skill_version = extract_skill_version((root / "SKILL.md").read_text(encoding="utf-8"))
    if manifest_version != PACK_VERSION:
        fail(f"manifest release version {manifest_version!r} != {PACK_VERSION}")
    if skill_version != PACK_VERSION:
        fail(f"SKILL.md release version {skill_version!r} != {PACK_VERSION}")
    compatibility = str(run_state["runtime_compatibility"]["requires"])
    if not compatible(PACK_VERSION, compatibility):
        fail(f"run-state compatibility {compatibility!r} does not admit runtime {PACK_VERSION}")

    # Every manifest-declared path must resolve. Optional and historical paths are checked too.
    for owner_name, spec in manifest["semantic_owners"].items():
        ref = spec.get("owner")
        if not ref:
            fail(f"semantic owner {owner_name} has no owner path")
        if not resolve_ref(root, ref).exists():
            fail(f"semantic owner {owner_name} path does not resolve: {ref}")
    for ref in manifest["load_order"]:
        if not resolve_ref(root, ref).exists():
            fail(f"load_order path does not resolve: {ref}")
    for name, spec in manifest.get("optional_load", {}).items():
        for ref in spec.get("artifacts", []):
            if not resolve_ref(root, ref).exists():
                fail(f"optional_load path does not resolve: {name} -> {ref}")
    historical = manifest.get("historical_artifacts", {})
    for ref in historical.get("artifacts", []):
        if not resolve_ref(root, ref, base=root / "runtime").exists():
            fail(f"historical artifact path does not resolve: {ref}")
    for name, ref in manifest.get("package_validation_refs", {}).items():
        if name == "rule":
            continue
        if not resolve_ref(root, ref).is_file():
            fail(f"package validator path does not resolve: {name} -> {ref}")

    # State-machine graph, action, and contract wiring must resolve exactly.
    raw_states = state_machine.get("states", {})
    if isinstance(raw_states, dict):
        states = set(raw_states)
    else:
        states = {x.get("state_id") for x in raw_states if isinstance(x, dict)}
    actions = {x["action_id"] for x in state_machine.get("actions", [])}
    if None in states or not states or not actions:
        fail("state-machine states/actions are incomplete")
    declared_contract_ids = collect_declared_contract_ids(root)
    for transition in state_machine.get("transitions", []):
        tid = transition.get("transition_id")
        if transition.get("from") not in states:
            fail(f"{tid} references unknown source state {transition.get('from')}")
        if transition.get("to") not in states:
            fail(f"{tid} references unknown target state {transition.get('to')}")
        if transition.get("on_failure") and transition["on_failure"] not in states:
            fail(f"{tid} references unknown on_failure state {transition['on_failure']}")
        for action in transition.get("actions", []):
            if action not in actions:
                fail(f"{tid} references unknown action {action}")
        for contract_id in transition.get("requires_contracts", []):
            if contract_id not in declared_contract_ids:
                fail(f"{tid} references undeclared contract {contract_id}")

    # Every explicit evaluator ID used by machine-readable YAML must be registered, including anchored refs.
    registry = load_yaml(root / "runtime/EVALUATOR_REGISTRY.yaml")
    registered_evaluators = {x["evaluator_id"] for x in registry.get("evaluators", [])}
    evaluator_token = re.compile(r"(?<![A-Z0-9_-])(EVAL-[A-Z0-9-]+)\b")
    for path in root.rglob("*.yaml"):
        obj = load_yaml(path)
        for value in iter_strings(obj):
            for evaluator_id in evaluator_token.findall(value):
                if evaluator_id not in registered_evaluators:
                    fail(
                        f"unregistered evaluator {evaluator_id} referenced by {path.relative_to(root)}"
                    )

    # Exact target binding must exist across state, boot, workflow, and convergence.
    target = run_state["instance_template"].get("target")
    required_target_fields = {
        "status",
        "requested_refs",
        "bound_refs",
        "artifact_types",
        "revision_or_version_refs",
        "inspection_scope",
        "correction_scope",
        "excluded_scope",
        "inaccessible_scope",
        "ambiguity_refs",
        "evidence_refs",
        "observed_at",
    }
    if not target or not required_target_fields.issubset(target):
        fail("run state target binding is incomplete")
    if "target_binding_state" not in run_state.get("state_enums", {}):
        fail("target binding enum missing")

    boot_steps = {x["step"]: x for x in manifest["boot_sequence"]["steps"]}
    if boot_steps.get("BIND_TARGET", {}).get("state_target") != "$.target":
        fail("manifest BIND_TARGET boot step missing or misbound")

    clauses = {x["clause_id"]: x for x in state_machine["normative_clauses"]}
    if "WF-TARGET-001" not in clauses:
        fail("WF-TARGET-001 missing")
    if state_machine.get("state_bindings", {}).get("target") != "$.target":
        fail("state machine target binding missing")
    t001 = next((x for x in state_machine["transitions"] if x["transition_id"] == "T-001"), None)
    if not t001 or "target_binding_status == BOUND" not in t001.get("gates", []):
        fail("T-001 does not gate on exact target binding")
    act_intake = next((x for x in state_machine["actions"] if x["action_id"] == "ACT-INTAKE"), None)
    if not act_intake or "resolve_exact_target_binding" not in act_intake.get("side_effects", []):
        fail("ACT-INTAKE does not resolve exact target binding")

    reason_set = {x["code"] for x in reason_codes["reason_codes"]}
    if "TARGET_BINDING_UNRESOLVED" not in reason_set:
        fail("TARGET_BINDING_UNRESOLVED reason code missing")

    conv_props = convergence["convergence_gate"]["required_properties"]
    if not any(x.get("id") == "CV-015-TARGET-BINDING-CURRENT" for x in conv_props):
        fail("target-binding convergence property missing")
    if not any(x.get("id") == "FC-010" for x in convergence["false_completion_checks"]):
        fail("target-binding false-completion check missing")

    # Signal Leverage propagation semantics must remain separate from Gate routing.
    dis = foursome.get("transport_boundary_disambiguation", {})
    if (
        dis.get("signal_kernel_term_mapping", {}).get("routing_does_not_mean")
        != "concrete_inter_node_route_selection_admission_routability_or_transport_execution"
    ):
        fail("Signal/Gate routing disambiguation missing")
    profile_text = (root / "contracts/L9_ARCHITECTURE_PROFILE.yaml").read_text(encoding="utf-8")
    if (
        "Gate_owns_routing_admission_routability_and_routing_seam_trust_not_domain_semantics"
        not in profile_text
    ):
        fail("Gate routing owner law missing")
    if (
        "signal_leverage_may_constrain_eligible_semantic_recipients_and_propagation_path_properties_but_must_not_own_concrete_Gate_route_selection_admission_or_routability"
        not in profile_text
    ):
        fail("Signal/Gate boundary clause missing")

    # Architecture kernel must retain explicit conditional contract/configuration and security lenses.
    lenses = architect.get("analysis_lenses", {})
    for lens in ("CONTRACT_AND_CONFIGURATION", "SECURITY"):
        if lens not in lenses:
            fail(f"architecture lens missing: {lens}")
    method = architect.get("decision_semantics", {}).get("method", [])
    if "activate_and_close_all_material_analysis_lenses" not in method:
        fail("architecture method does not require activated lens closure")
    plan_gate = architect.get("full_plan_promotion_gate", {}).get("all_required", [])
    for requirement in (
        "all_activated_architecture_lens_obligations_are_evaluated",
        "material_security_and_contract_configuration_findings_are_resolved_or_bounded",
    ):
        if requirement not in plan_gate:
            fail(f"full plan gate missing active-lens requirement: {requirement}")
    model = run_state["instance_template"]["system_model"]
    for field in (
        "contracts",
        "configuration_authority",
        "security_boundaries",
        "observability_semantics",
        "validation_ownership",
    ):
        if field not in model:
            fail(f"system model field missing: {field}")

    # Current runtime owners must not reference the retired binding owner.
    current_files = [
        root / "SKILL.md",
        root / "runtime/MANIFEST.yaml",
        root / "runtime/RUN_STATE.yaml",
        root / "runtime/STATE_MACHINE.yaml",
        root / "contracts/CONVERGENCE.yaml",
        root / "contracts/L9_ARCHITECTURE_PROFILE.yaml",
        root / "integrations/L9_RUNTIME_BINDING.yaml",
        root / "integrations/REASONING_FOURSOME_BINDING.yaml",
        root / "kernels/ARCHITECT_KERNEL.yaml",
    ]
    for path in current_files:
        if "REASONING_TRIAD_BINDING" in path.read_text(encoding="utf-8"):
            fail(
                f"retired Triad binding referenced by current runtime owner: {path.relative_to(root)}"
            )

    # Behavioral eval IDs must be contiguous and promotion-blocking.
    cases = behavior["cases"]
    ids = [int(x["case_id"].split("-")[-1]) for x in cases]
    expected = list(range(1, EXPECTED_EVAL_MAX + 1))
    if ids != expected:
        fail(f"behavior eval IDs are not contiguous 001..{EXPECTED_EVAL_MAX:03d}")
    gate = behavior["promotion_gate"]["v1_candidate_requires"]
    expected_gate = [f"GAR-EVAL-{i:03d} == PASS" for i in expected]
    if gate != expected_gate:
        fail("promotion gate does not require every blocking eval in order")

    # JSON Schema must be valid and product-decision behavior must prove both acceptance and rejection paths.
    schema = load_json(root / "schemas/product-architecture-decision.schema.json")
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        fail(f"product architecture decision schema is invalid: {exc}")
    decision_module = import_decision_validator(
        root / "scripts/validate_product_architecture_decision.py"
    )
    fixture = load_json(root / "fixtures/greenfield-decision.json")
    try:
        decision_module.validate(copy.deepcopy(fixture))
    except Exception as exc:
        fail(f"positive product architecture decision fixture failed: {exc}")

    deprecated = copy.deepcopy(fixture)
    deprecated["architecture"]["owner_dispositions"][0]["disposition"] = "HARVEST_THEN_DECIDE"
    expect_decision_failure(decision_module, deprecated, "GAR_DECISION_INVALID")

    mismatch = copy.deepcopy(fixture)
    mismatch["architecture"]["intervention_class"] = "NO_ACTION"
    expect_decision_failure(decision_module, mismatch, "GAR_DECISION_INTERVENTION_FIDELITY")

    missing_signal = copy.deepcopy(fixture)
    missing_signal["reasoning"]["signal_prediction_propagation_ref"] = None
    expect_decision_failure(decision_module, missing_signal, "GAR_DECISION_SIGNAL_UNBOUND")

    unresolved = copy.deepcopy(fixture)
    unresolved["architecture"]["material_unknowns"] = ["fixture unresolved"]
    expect_decision_failure(decision_module, unresolved, "GAR_DECISION_UNRESOLVED")

    # Required current artifacts for this release must exist.
    for ref in (
        "references/reasoning-foursome/04_SIGNAL_LEVERAGE_KERNEL.md",
        "decisions/ADR-L9-GAR-005.yaml",
        "decisions/ADR-L9-GAR-006.yaml",
    ):
        if not (root / ref).is_file():
            fail(f"required artifact missing: {ref}")

    # Unfinished-work markers are forbidden in current executable/normative scope only.
    forbidden_tokens = ("TO" + "DO", "FIX" + "ME", "TB" + "D", "X" + "XX", "HA" + "CK")
    forbidden_re = re.compile(r"\b(?:" + "|".join(forbidden_tokens) + r")\b", re.IGNORECASE)
    for path in files:
        rel = path.relative_to(root)
        first = rel.parts[0]
        if not (str(rel) == "SKILL.md" or first in CURRENT_MARKER_ROOTS):
            continue
        if first == "references" or first == "decisions" or str(rel) == "CHANGELOG.md":
            continue
        if path.suffix not in {".md", ".yaml", ".yml", ".json", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = forbidden_re.search(text)
        if match:
            fail(f"forbidden unfinished-work marker {match.group(0)} in {rel}")

    files = validate_hygiene(root)

    print("GAR_RUNTIME_ALIGNMENT: PASS")
    print(f"version: {PACK_VERSION}")
    print(f"files: {len(files)}")
    print(f"behavior_evals: {len(cases)}")
    print("release_identity: PASS")
    print("manifest_references: PASS")
    print("state_action_contract_wiring: PASS")
    print("evaluator_registration: PASS")
    print("target_binding: PASS")
    print("signal_gate_boundary: PASS")
    print("security_contract_lenses: PASS")
    print("product_decision_positive_negative: PASS")
    print("final_state_hygiene: PASS")


if __name__ == "__main__":
    main()
