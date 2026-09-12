#!/usr/bin/env python3
"""Validate Idea Foundry code-realization and birth-ready payload invariants."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any

from _common import (
    FoundryContractError,
    git_output,
    load_yaml_mapping,
    require_schema,
    semantic_yaml_digest,
    sha256_file,
    tracked_tree_digest,
    valid_sha256,
)

REQUIRED_PATHS = [
    "pyproject.toml",
    ".l9/architecture.yaml",
    "src",
    "tests",
    "scripts/inventory_check.py",
    "docs/idea-origin/AUTHORITY_MAP.yaml",
    "docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml",
    "docs/idea-origin/TRACEABILITY.yaml",
    "docs/idea-origin/UNKNOWN_REGISTER.md",
    "docs/idea-origin/FOUNDRY_RECEIPT.yaml",
    "docs/idea-origin/FOUNDRY_INDEX.json",
]

SCHEMAS = {
    "docs/idea-origin/AUTHORITY_MAP.yaml": "l9.idea-foundry.authority-map/v1",
    "docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml": "l9.idea-foundry.implementation-blueprint/v1",
    "docs/idea-origin/TRACEABILITY.yaml": "l9.idea-foundry.traceability/v1",
    "docs/idea-origin/FOUNDRY_RECEIPT.yaml": "l9.idea-foundry.receipt/v1",
    ".l9/architecture.yaml": "l9.architecture-spec/v1",
}

AUTHORITY_STATES = {
    "CANONICAL",
    "LOCKED",
    "ACCEPTED",
    "PROPOSED",
    "HYPOTHESIS",
    "UNKNOWN",
    "REJECTED",
    "DEFERRED",
    "SUPERSEDED",
}
REUSE_DISPOSITIONS = {
    "CONSUME_UPSTREAM",
    "ADAPT_UPSTREAM",
    "HARVEST_THEN_DECIDE",
    "OWN_LOCALLY",
    "DEFER_OUTSIDE_SLICE",
    "BLOCKED_UNKNOWN",
}
PLAN_HANDOFFS = {"EMBEDDED", "EMBEDDED_PRE_BIRTH"}
TRACE_STATUSES = {"IMPLEMENTED", "PARTIAL", "DEFERRED", "BLOCKED"}
RUN_STATUSES = {
    "INTAKE",
    "MODELED",
    "PLANNED",
    "CODE_REALIZED_LOCAL",
    "BIRTH_READY",
    "LOCAL_BIRTH_PASS",
    "PROVISIONAL_REPOSITORY",
    "QUARANTINED",
    "BLOCKED",
}
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java", ".kt", ".rb"}
PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\bHACK\b", re.IGNORECASE),
    re.compile(r"NotImplementedError"),
    re.compile(r"placeholder[-_ ]only", re.IGNORECASE),
]
GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")


def fail_if(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        failures.append(message)


def mapping(value: object, label: str, failures: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        failures.append(f"{label} must be a mapping")
        return {}
    return value


def sequence(value: object, label: str, failures: list[str], *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list):
        failures.append(f"{label} must be a list")
        return []
    if nonempty and not value:
        failures.append(f"{label} must not be empty")
    return value


def nonempty_string(value: object, label: str, failures: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{label} must be a non-empty string")
        return ""
    return value.strip()


def validate_python_syntax(paths: list[Path], root: Path, failures: list[str]) -> None:
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path.relative_to(root)), "exec")
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            failures.append(f"python syntax/read failure {path.relative_to(root)}: {exc}")


def load_contracts(root: Path, failures: list[str]) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for rel, schema in SCHEMAS.items():
        try:
            data = load_yaml_mapping(root / rel)
            require_schema(data, schema, rel)
            contracts[rel] = data
        except FoundryContractError as exc:
            failures.append(str(exc))
    return contracts


def validate_authority(authority: dict[str, Any], failures: list[str]) -> None:
    sequence(authority.get("sources"), "AUTHORITY_MAP.sources", failures, nonempty=True)
    claims = sequence(authority.get("claims"), "AUTHORITY_MAP.claims", failures, nonempty=True)
    sequence(authority.get("conflicts"), "AUTHORITY_MAP.conflicts", failures)
    seen: set[str] = set()
    for i, raw in enumerate(claims):
        claim = mapping(raw, f"AUTHORITY_MAP.claims[{i}]", failures)
        cid = nonempty_string(claim.get("id"), f"AUTHORITY_MAP.claims[{i}].id", failures)
        if cid and cid in seen:
            failures.append(f"AUTHORITY_MAP duplicate claim id: {cid}")
        seen.add(cid)
        sequence(claim.get("source_refs"), f"AUTHORITY_MAP.claims[{i}].source_refs", failures, nonempty=True)
        if claim.get("state") not in AUTHORITY_STATES:
            failures.append(
                f"AUTHORITY_MAP.claims[{i}].state must be one of {sorted(AUTHORITY_STATES)}"
            )
        nonempty_string(claim.get("statement"), f"AUTHORITY_MAP.claims[{i}].statement", failures)


def validate_blueprint(blueprint: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    identity = mapping(blueprint.get("identity"), "IMPLEMENTATION_BLUEPRINT.identity", failures)
    nonempty_string(identity.get("repository"), "IMPLEMENTATION_BLUEPRINT.identity.repository", failures)
    nonempty_string(identity.get("package"), "IMPLEMENTATION_BLUEPRINT.identity.package", failures)

    objective = mapping(blueprint.get("objective"), "IMPLEMENTATION_BLUEPRINT.objective", failures)
    nonempty_string(objective.get("product_thesis"), "IMPLEMENTATION_BLUEPRINT.objective.product_thesis", failures)
    nonempty_string(
        objective.get("first_executable_outcome"),
        "IMPLEMENTATION_BLUEPRINT.objective.first_executable_outcome",
        failures,
    )

    compilation = mapping(blueprint.get("compilation"), "IMPLEMENTATION_BLUEPRINT.compilation", failures)
    fail_if(compilation.get("ingress_role") != "PRE_CODE_SSOT", "compilation.ingress_role must be PRE_CODE_SSOT", failures)
    fail_if(
        compilation.get("authority_map_ref") != "docs/idea-origin/AUTHORITY_MAP.yaml",
        "compilation.authority_map_ref must point to docs/idea-origin/AUTHORITY_MAP.yaml",
        failures,
    )
    fail_if(
        not valid_sha256(compilation.get("source_inventory_digest")),
        "compilation.source_inventory_digest must be sha256:<64 lowercase hex>",
        failures,
    )
    fail_if(
        compilation.get("raw_source_after_acceptance") != "EVIDENCE_ONLY",
        "compilation.raw_source_after_acceptance must be EVIDENCE_ONLY",
        failures,
    )
    fail_if(
        compilation.get("change_policy") != "EARLIEST_INVALID_LAYER",
        "compilation.change_policy must be EARLIEST_INVALID_LAYER",
        failures,
    )

    mapping(blueprint.get("beneficiary"), "IMPLEMENTATION_BLUEPRINT.beneficiary", failures)
    reuse = sequence(blueprint.get("reuse_map"), "IMPLEMENTATION_BLUEPRINT.reuse_map", failures)
    for i, raw in enumerate(reuse):
        item = mapping(raw, f"reuse_map[{i}]", failures)
        nonempty_string(item.get("responsibility"), f"reuse_map[{i}].responsibility", failures)
        disposition = item.get("disposition")
        if disposition not in REUSE_DISPOSITIONS:
            failures.append(f"reuse_map[{i}].disposition must be one of {sorted(REUSE_DISPOSITIONS)}")
        evidence = sequence(item.get("evidence_refs"), f"reuse_map[{i}].evidence_refs", failures)
        if disposition != "DEFER_OUTSIDE_SLICE" and not evidence:
            failures.append(f"reuse_map[{i}] disposition {disposition!r} requires evidence_refs")
        if disposition in {"CONSUME_UPSTREAM", "ADAPT_UPSTREAM"}:
            nonempty_string(item.get("verified_owner"), f"reuse_map[{i}].verified_owner", failures)

    leverage = mapping(
        blueprint.get("constellation_leverage"),
        "IMPLEMENTATION_BLUEPRINT.constellation_leverage",
        failures,
    )
    nonempty_string(
        leverage.get("highest_leverage_move"),
        "constellation_leverage.highest_leverage_move",
        failures,
    )
    for field in (
        "upstream_reuse",
        "duplicate_owners_avoided",
        "compounding_contracts",
        "future_actions_accelerated",
        "speculative_abstractions_rejected",
    ):
        sequence(leverage.get(field), f"constellation_leverage.{field}", failures)

    acceptance = mapping(blueprint.get("acceptance"), "IMPLEMENTATION_BLUEPRINT.acceptance", failures)
    sequence(acceptance.get("path"), "acceptance.path", failures, nonempty=True)
    sequence(acceptance.get("evidence_required"), "acceptance.evidence_required", failures, nonempty=True)
    sequence(blueprint.get("validation_obligations"), "validation_obligations", failures, nonempty=True)

    planning = mapping(blueprint.get("planning"), "IMPLEMENTATION_BLUEPRINT.planning", failures)
    fail_if(planning.get("owner") != "l9-plan-simple", "planning.owner must be l9-plan-simple", failures)
    nonempty_string(planning.get("plan_document_ref"), "planning.plan_document_ref", failures)
    fail_if(not valid_sha256(planning.get("plan_digest")), "planning.plan_digest must be sha256:<64 lowercase hex>", failures)
    fail_if(planning.get("validation_status") != "PASSED", "planning.validation_status must be PASSED", failures)
    handoff = planning.get("plan_handoff")
    if handoff not in PLAN_HANDOFFS:
        failures.append(f"planning.plan_handoff must be one of {sorted(PLAN_HANDOFFS)}")
    fallback = planning.get("compatibility_fallback")
    if not isinstance(fallback, bool):
        failures.append("planning.compatibility_fallback must be boolean")
    if handoff == "EMBEDDED":
        fail_if(fallback is not False, "first-class EMBEDDED handoff cannot be marked compatibility fallback", failures)
        nonempty_string(planning.get("mode_evidence_ref"), "planning.mode_evidence_ref", failures)
    if handoff == "EMBEDDED_PRE_BIRTH":
        fail_if(fallback is not True, "legacy EMBEDDED_PRE_BIRTH must set compatibility_fallback: true", failures)
        nonempty_string(planning.get("fallback_reason"), "planning.fallback_reason", failures)

    questions = mapping(
        blueprint.get("architecture_questions"),
        "IMPLEMENTATION_BLUEPRINT.architecture_questions",
        failures,
    )
    for name in ("direction", "constellation_alignment", "first_order"):
        answer = mapping(questions.get(name), f"architecture_questions.{name}", failures)
        nonempty_string(answer.get("verdict"), f"architecture_questions.{name}.verdict", failures)
        sequence(answer.get("evidence_refs"), f"architecture_questions.{name}.evidence_refs", failures, nonempty=True)

    return planning


def validate_traceability(traceability: dict[str, Any], failures: list[str]) -> None:
    capabilities = sequence(traceability.get("capabilities"), "TRACEABILITY.capabilities", failures, nonempty=True)
    seen: set[str] = set()
    for i, raw in enumerate(capabilities):
        item = mapping(raw, f"TRACEABILITY.capabilities[{i}]", failures)
        cid = nonempty_string(item.get("id"), f"TRACEABILITY.capabilities[{i}].id", failures)
        if cid and cid in seen:
            failures.append(f"TRACEABILITY duplicate capability id: {cid}")
        seen.add(cid)
        status = item.get("status")
        if status not in TRACE_STATUSES:
            failures.append(f"TRACEABILITY.capabilities[{i}].status must be one of {sorted(TRACE_STATUSES)}")
        requirement_refs = sequence(item.get("requirement_refs"), f"TRACEABILITY.capabilities[{i}].requirement_refs", failures)
        sequence(item.get("architecture_refs"), f"TRACEABILITY.capabilities[{i}].architecture_refs", failures)
        sequence(item.get("harvest_refs"), f"TRACEABILITY.capabilities[{i}].harvest_refs", failures)
        plan_refs = sequence(item.get("plan_todo_refs"), f"TRACEABILITY.capabilities[{i}].plan_todo_refs", failures)
        impl_paths = sequence(item.get("implementation_paths"), f"TRACEABILITY.capabilities[{i}].implementation_paths", failures)
        evidence_refs = sequence(item.get("evidence_refs"), f"TRACEABILITY.capabilities[{i}].evidence_refs", failures)
        sequence(item.get("unknown_ids"), f"TRACEABILITY.capabilities[{i}].unknown_ids", failures)
        if status == "IMPLEMENTED":
            if not requirement_refs:
                failures.append(f"TRACEABILITY capability {cid or i} IMPLEMENTED without requirement_refs")
            if not plan_refs:
                failures.append(f"TRACEABILITY capability {cid or i} IMPLEMENTED without plan_todo_refs")
            if not impl_paths:
                failures.append(f"TRACEABILITY capability {cid or i} IMPLEMENTED without implementation_paths")
            if not evidence_refs:
                failures.append(f"TRACEABILITY capability {cid or i} IMPLEMENTED without evidence_refs")
    decisions = sequence(traceability.get("implementation_decisions"), "TRACEABILITY.implementation_decisions", failures)
    for i, raw in enumerate(decisions):
        item = mapping(raw, f"TRACEABILITY.implementation_decisions[{i}]", failures)
        nonempty_string(item.get("id"), f"implementation_decisions[{i}].id", failures)
        nonempty_string(item.get("statement"), f"implementation_decisions[{i}].statement", failures)
        if item.get("source_truth") is not False:
            failures.append(f"implementation_decisions[{i}].source_truth must be false")
        nonempty_string(item.get("rationale"), f"implementation_decisions[{i}].rationale", failures)
        sequence(item.get("affected_paths"), f"implementation_decisions[{i}].affected_paths", failures, nonempty=True)


def validate_receipt(receipt: dict[str, Any], blueprint_planning: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    run = mapping(receipt.get("run"), "FOUNDRY_RECEIPT.run", failures)
    if run.get("status") not in RUN_STATUSES:
        failures.append(f"FOUNDRY_RECEIPT.run.status must be one of {sorted(RUN_STATUSES)}")
    source = mapping(receipt.get("source"), "FOUNDRY_RECEIPT.source", failures)
    nonempty_string(source.get("input_ref"), "FOUNDRY_RECEIPT.source.input_ref", failures)
    fail_if(not valid_sha256(source.get("inventory_digest")), "FOUNDRY_RECEIPT source.inventory_digest invalid", failures)

    composition = mapping(receipt.get("composition"), "FOUNDRY_RECEIPT.composition", failures)
    mapping(composition.get("intelligence_harvest"), "composition.intelligence_harvest", failures)
    mapping(composition.get("gar"), "composition.gar", failures)
    planning = mapping(composition.get("planning"), "composition.planning", failures)
    fail_if(planning.get("owner") != "l9-plan-simple", "receipt planning.owner must be l9-plan-simple", failures)
    fail_if(planning.get("validation_status") != "PASSED", "receipt planning.validation_status must be PASSED", failures)
    fail_if(planning.get("plan_handoff") not in PLAN_HANDOFFS, f"receipt planning.plan_handoff must be one of {sorted(PLAN_HANDOFFS)}", failures)
    fail_if(not valid_sha256(planning.get("plan_digest")), "receipt planning.plan_digest invalid", failures)
    nonempty_string(planning.get("plan_document_ref"), "receipt planning.plan_document_ref", failures)
    if blueprint_planning:
        for field in ("plan_document_ref", "plan_digest", "validation_status", "plan_handoff"):
            if planning.get(field) != blueprint_planning.get(field):
                failures.append(f"receipt planning.{field} does not match blueprint planning.{field}")

    payload = mapping(receipt.get("payload"), "FOUNDRY_RECEIPT.payload", failures)
    fail_if(payload.get("freeze_binding") != "EXTERNAL_RECEIPT", "FOUNDRY_RECEIPT payload.freeze_binding must be EXTERNAL_RECEIPT", failures)
    fail_if(
        payload.get("resume_index_ref") != "docs/idea-origin/FOUNDRY_INDEX.json",
        "FOUNDRY_RECEIPT payload.resume_index_ref must point to docs/idea-origin/FOUNDRY_INDEX.json",
        failures,
    )

    validation = mapping(receipt.get("validation"), "FOUNDRY_RECEIPT.validation", failures)
    sequence(validation.get("commands"), "FOUNDRY_RECEIPT.validation.commands", failures, nonempty=True)
    sequence(validation.get("results"), "FOUNDRY_RECEIPT.validation.results", failures, nonempty=True)

    mapping(receipt.get("birth"), "FOUNDRY_RECEIPT.birth", failures)
    deployment = mapping(receipt.get("deployment"), "FOUNDRY_RECEIPT.deployment", failures)
    fail_if(deployment.get("performed") is not False, "FOUNDRY_RECEIPT deployment.performed must be false", failures)
    sequence(receipt.get("unknowns"), "FOUNDRY_RECEIPT.unknowns", failures)
    sequence(receipt.get("deferred"), "FOUNDRY_RECEIPT.deferred", failures)
    return planning


def validate_index(
    root: Path,
    index: dict[str, Any],
    authority_path: Path,
    blueprint_path: Path,
    trace_path: Path,
    receipt_path: Path,
    architecture_path: Path,
    receipt_planning: dict[str, Any],
    inventory_digest: object,
    failures: list[str],
) -> None:
    fail_if(index.get("schema") != "l9.idea-foundry.index/v1", "FOUNDRY_INDEX schema mismatch", failures)
    source = mapping(index.get("source"), "FOUNDRY_INDEX.source", failures)
    fail_if(source.get("inventory_digest") != inventory_digest, "FOUNDRY_INDEX source inventory digest mismatch", failures)
    compiled = mapping(index.get("compiled_intent"), "FOUNDRY_INDEX.compiled_intent", failures)
    fail_if(compiled.get("pre_code_ingress") != "docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml", "FOUNDRY_INDEX pre_code_ingress mismatch", failures)
    fail_if(compiled.get("raw_source_policy") != "EVIDENCE_ONLY_AFTER_ACCEPTANCE", "FOUNDRY_INDEX raw_source_policy mismatch", failures)
    artifacts = mapping(index.get("artifacts"), "FOUNDRY_INDEX.artifacts", failures)
    expected = {
        "authority_map": (authority_path, semantic_yaml_digest(authority_path)),
        "implementation_blueprint": (blueprint_path, semantic_yaml_digest(blueprint_path)),
        "traceability": (trace_path, semantic_yaml_digest(trace_path)),
        "unknown_register": (root / "docs/idea-origin/UNKNOWN_REGISTER.md", sha256_file(root / "docs/idea-origin/UNKNOWN_REGISTER.md")),
        "foundry_receipt": (receipt_path, semantic_yaml_digest(receipt_path)),
        "architecture": (architecture_path, semantic_yaml_digest(architecture_path)),
    }
    for name, (path, digest) in expected.items():
        entry = mapping(artifacts.get(name), f"FOUNDRY_INDEX.artifacts.{name}", failures)
        fail_if(entry.get("path") != path.relative_to(root).as_posix(), f"FOUNDRY_INDEX {name} path mismatch", failures)
        fail_if(entry.get("digest") != digest, f"FOUNDRY_INDEX {name} digest mismatch", failures)

    composition = mapping(index.get("composition"), "FOUNDRY_INDEX.composition", failures)
    planning = mapping(composition.get("planning"), "FOUNDRY_INDEX.composition.planning", failures)
    for field in ("owner", "plan_document_ref", "plan_digest", "validation_status", "plan_handoff"):
        if planning.get(field) != receipt_planning.get(field):
            failures.append(f"FOUNDRY_INDEX planning.{field} does not match receipt")

    lineage = mapping(index.get("lineage"), "FOUNDRY_INDEX.lineage", failures)
    fail_if(lineage.get("inventory_digest") != inventory_digest, "FOUNDRY_INDEX lineage inventory mismatch", failures)
    fail_if(lineage.get("authority_digest") != expected["authority_map"][1], "FOUNDRY_INDEX authority_digest mismatch", failures)
    fail_if(lineage.get("blueprint_digest") != expected["implementation_blueprint"][1], "FOUNDRY_INDEX blueprint_digest mismatch", failures)
    fail_if(lineage.get("traceability_digest") != expected["traceability"][1], "FOUNDRY_INDEX traceability_digest mismatch", failures)
    fail_if(lineage.get("plan_digest") != receipt_planning.get("plan_digest"), "FOUNDRY_INDEX plan_digest mismatch", failures)
    resume = mapping(index.get("resume"), "FOUNDRY_INDEX.resume", failures)
    fail_if(resume.get("entrypoint") != "docs/idea-origin/FOUNDRY_INDEX.json", "FOUNDRY_INDEX resume.entrypoint mismatch", failures)
    fail_if(resume.get("repair_policy") != "EARLIEST_INVALID_LAYER", "FOUNDRY_INDEX repair_policy mismatch", failures)
    deployment = mapping(index.get("deployment"), "FOUNDRY_INDEX.deployment", failures)
    fail_if(deployment.get("performed") is not False, "FOUNDRY_INDEX deployment.performed must be false", failures)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument(
        "--birth-ready",
        action="store_true",
        help="also require clean committed git state and exact external freeze receipt binding",
    )
    parser.add_argument("--freeze-receipt", type=Path)
    args = parser.parse_args()
    root = args.payload.resolve()

    failures: list[str] = []
    observations: list[str] = []

    if not root.is_dir():
        failures.append(f"payload is not a directory: {root}")
    else:
        for rel in REQUIRED_PATHS:
            if not (root / rel).exists():
                failures.append(f"missing required path: {rel}")
    if failures:
        print("FOUNDRY_PAYLOAD: FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    contracts = load_contracts(root, failures)
    authority_path = root / "docs/idea-origin/AUTHORITY_MAP.yaml"
    blueprint_path = root / "docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml"
    trace_path = root / "docs/idea-origin/TRACEABILITY.yaml"
    receipt_path = root / "docs/idea-origin/FOUNDRY_RECEIPT.yaml"
    architecture_path = root / ".l9/architecture.yaml"

    authority = contracts.get("docs/idea-origin/AUTHORITY_MAP.yaml", {})
    blueprint = contracts.get("docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml", {})
    traceability = contracts.get("docs/idea-origin/TRACEABILITY.yaml", {})
    receipt = contracts.get("docs/idea-origin/FOUNDRY_RECEIPT.yaml", {})
    architecture = contracts.get(".l9/architecture.yaml", {})

    validate_authority(authority, failures)
    blueprint_planning = validate_blueprint(blueprint, failures)
    validate_traceability(traceability, failures)
    receipt_planning = validate_receipt(receipt, blueprint_planning, failures)

    # Cross-contract source identity.
    compilation = blueprint.get("compilation") if isinstance(blueprint.get("compilation"), dict) else {}
    receipt_source = receipt.get("source") if isinstance(receipt.get("source"), dict) else {}
    inventory_digest = receipt_source.get("inventory_digest")
    if compilation.get("source_inventory_digest") != inventory_digest:
        failures.append("blueprint compilation source_inventory_digest does not match receipt source.inventory_digest")

    # Product identity and template residue.
    if architecture.get("metadata", {}).get("repository") == "Quantum-L9/l9-repo-template":
        failures.append(".l9/architecture.yaml still identifies the template repository")
    if architecture.get("identity", {}).get("role") == "quantum-l9-python-museum":
        failures.append(".l9/architecture.yaml still carries the template identity role")

    # pyproject must be parseable and identify a real project.
    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject.get("project", {})
        project_name = str(project.get("name", "")).strip()
        if not project_name:
            failures.append("pyproject.toml missing [project].name")
        else:
            observations.append(f"project={project_name}")
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        failures.append(f"pyproject.toml parse failure: {exc}")

    # Product source must contain real code, not docs-only scaffolding.
    src_files = [p for p in (root / "src").rglob("*") if p.is_file()]
    code_files = [p for p in src_files if p.suffix.lower() in CODE_SUFFIXES]
    substantive_code = [p for p in code_files if p.name != "__init__.py" and p.stat().st_size > 20]
    if not substantive_code:
        failures.append("src/ contains no substantive code-bearing source")
    observations.append(f"source_code_files={len(code_files)}")

    # Tests must contain executable assertions/tests, not filenames alone.
    test_files = [p for p in (root / "tests").rglob("*") if p.is_file()]
    recognizable_tests: list[Path] = []
    for path in test_files:
        if "test" not in path.name.lower():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(f"cannot read test {path.relative_to(root)}: {exc}")
            continue
        if re.search(r"\bdef\s+test_", text) or "unittest.TestCase" in text or re.search(r"\b(it|test)\s*\(", text):
            recognizable_tests.append(path)
    if not recognizable_tests:
        failures.append("tests/ contains no recognizably executable tests")
    observations.append(f"recognizable_test_files={len(recognizable_tests)}")

    python_paths = [p for p in code_files + test_files if p.suffix.lower() == ".py"]
    python_paths.append(root / "scripts/inventory_check.py")
    validate_python_syntax(python_paths, root, failures)

    for path in code_files + test_files:
        if path.suffix.lower() not in CODE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(f"cannot read implementation file {path.relative_to(root)}: {exc}")
            continue
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(text):
                failures.append(f"incomplete marker {pattern.pattern!r} in {path.relative_to(root)}")
                break

    unknown_register = root / "docs/idea-origin/UNKNOWN_REGISTER.md"
    try:
        if len(unknown_register.read_text(encoding="utf-8").strip()) < 8:
            failures.append("UNKNOWN_REGISTER.md must explicitly list unknowns or state none")
    except (OSError, UnicodeDecodeError) as exc:
        failures.append(f"cannot read UNKNOWN_REGISTER.md: {exc}")

    # Deterministic downstream ingress must match every source artifact it indexes.
    index_path = root / "docs/idea-origin/FOUNDRY_INDEX.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(index, dict):
            failures.append("FOUNDRY_INDEX root must be a JSON object")
            index = {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"FOUNDRY_INDEX parse failure: {exc}")
        index = {}
    if index:
        validate_index(
            root,
            index,
            authority_path,
            blueprint_path,
            trace_path,
            receipt_path,
            architecture_path,
            receipt_planning,
            inventory_digest,
            failures,
        )

    if args.birth_ready:
        rc, inside = git_output(root, "rev-parse", "--is-inside-work-tree")
        head = ""
        if rc != 0 or inside != "true":
            failures.append("birth-ready payload is not a git working tree")
        else:
            rc, head = git_output(root, "rev-parse", "HEAD")
            if rc != 0 or not GIT_SHA_RE.fullmatch(head):
                failures.append("birth-ready payload has no resolvable 40-hex HEAD commit")
            rc, dirty = git_output(root, "status", "--porcelain", "--untracked-files=all")
            if rc != 0:
                failures.append("cannot inspect git status for birth-ready payload")
            elif dirty:
                failures.append("birth-ready payload git tree is not clean")

        if args.freeze_receipt is None:
            failures.append("--birth-ready requires --freeze-receipt")
        else:
            freeze_path = args.freeze_receipt.resolve()
            if freeze_path == root or root in freeze_path.parents:
                failures.append("freeze receipt must live outside the payload repository")
            elif not freeze_path.is_file():
                failures.append(f"freeze receipt not found: {freeze_path}")
            else:
                try:
                    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    failures.append(f"freeze receipt parse failure: {exc}")
                    freeze = {}
                if freeze.get("schema") != "l9.idea-foundry.freeze-receipt/v1":
                    failures.append("freeze receipt schema mismatch")
                if head and freeze.get("git_revision") != head:
                    failures.append("freeze receipt git_revision does not match current HEAD")
                try:
                    records, tree_digest = tracked_tree_digest(root)
                except FoundryContractError as exc:
                    failures.append(str(exc))
                    records, tree_digest = [], ""
                if tree_digest and freeze.get("tracked_tree_digest") != tree_digest:
                    failures.append("freeze receipt tracked_tree_digest does not match current tracked tree")
                if freeze.get("tracked_file_count") != len(records):
                    failures.append("freeze receipt tracked_file_count does not match current tracked tree")
                if freeze.get("inventory_digest") != inventory_digest:
                    failures.append("freeze receipt inventory_digest does not match Foundry source identity")
                if freeze.get("plan_digest") != receipt_planning.get("plan_digest"):
                    failures.append("freeze receipt plan_digest does not match validated plan")
                if freeze.get("plan_ref") != receipt_planning.get("plan_document_ref"):
                    failures.append("freeze receipt plan_ref does not match validated plan")
                if freeze.get("foundry_index_ref") != "docs/idea-origin/FOUNDRY_INDEX.json":
                    failures.append("freeze receipt foundry_index_ref mismatch")
                if freeze.get("foundry_index_digest") != sha256_file(index_path):
                    failures.append("freeze receipt foundry_index_digest does not match committed index")
                if head and freeze.get("git_revision") == head:
                    observations.append(f"git_head={head}")
                if tree_digest:
                    observations.append(f"tracked_file_count={len(records)}")
                    observations.append(f"tracked_tree_digest={tree_digest}")

    if failures:
        print("FOUNDRY_PAYLOAD: FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("FOUNDRY_PAYLOAD: PASS")
    phase = "BIRTH_READY" if args.birth_ready else "CODE_REALIZED"
    print(f"- phase: {phase}")
    for item in observations:
        print(f"- {item}")
    print(f"- authority_map_semantic_digest={semantic_yaml_digest(authority_path)}")
    print(f"- blueprint_semantic_digest={semantic_yaml_digest(blueprint_path)}")
    print(f"- traceability_semantic_digest={semantic_yaml_digest(trace_path)}")
    print(f"- foundry_index_sha256={sha256_file(index_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
