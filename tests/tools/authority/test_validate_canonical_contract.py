"""The canonical-schema validator accepts the GAR contracts and rejects each defect class."""

from __future__ import annotations

import copy
import importlib.util
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
PACK = REPO / "skills/l9-global-architect"
BINDING = PACK / "bindings/GOVERNANCE_GENERATION.yaml"
SCHEMAS = REPO / "contracts/schemas"


def _load(name: str) -> ModuleType:
    key = f"authority_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, REPO / f"tools/authority/{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


v = _load("validate_canonical_contract")
cj = _load("canonical_json")
DISPOSITION = v.Disposition.from_binding(cj.load_yaml(BINDING.read_text(encoding="utf-8")))


def _doc(rel: str) -> dict[str, Any]:
    return cj.load_yaml((PACK / rel).read_text(encoding="utf-8"))


def _validate(doc: Any, schema: str, root: Path = SCHEMAS) -> Any:
    return v.validate(doc, schema, schema_root=root, disposition=DISPOSITION)


def test_every_declared_gar_source_validates() -> None:
    results = v.validate_binding_sources(BINDING)
    assert len(results) == 5
    for rel, result in results.items():
        assert result.status == "VALID", (rel, result.as_dict())


def test_every_schema_rule_is_accounted_for() -> None:
    """No validation rule is silently counted: each is evaluated, delegated or reviewed."""
    for result in v.validate_binding_sources(BINDING).values():
        accounted = (
            set(result.evaluated_rules)
            | set(result.delegated_rules)
            | set(result.semantic_review_rules)
        )
        schema_ids = {
            str(rule["id"])
            for schema in v.SchemaSet(SCHEMAS, DISPOSITION.abstract_roots).chain(result.schema_ref)
            for rule in schema.get("validation_rules", [])
        }
        assert accounted == schema_ids


WORKFLOW = "canonical.schema.workflow_contract.v1"
EVIDENCE = "canonical.schema.evidence_contract.v1"
POLICY = "canonical.schema.policy_contract.v1"
INVARIANT = "canonical.schema.invariant_contract.v1"


def _drop(path: str) -> Callable[[dict[str, Any]], None]:
    def mutate(doc: dict[str, Any]) -> None:
        *parents, leaf = path.split(".")
        node: Any = doc
        for part in parents:
            node = node[part]
        del node[leaf]

    return mutate


def _set(path: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def mutate(doc: dict[str, Any]) -> None:
        *parents, leaf = path.split(".")
        node: Any = doc
        for part in parents:
            node = node[part]
        node[leaf] = value

    return mutate


def _dup_clause(doc: dict[str, Any]) -> None:
    doc["normative_clauses"].append(copy.deepcopy(doc["normative_clauses"][0]))


def _ghost_transition(doc: dict[str, Any]) -> None:
    doc["transitions"][0]["to"] = "NO_SUCH_STATE"


def _ghost_failure_route(doc: dict[str, Any]) -> None:
    doc["transitions"][0]["on_failure"] = "NO_SUCH_STATE"


def _clauses_indented_into_scope(doc: dict[str, Any]) -> None:
    """The defect ARCHITECTURAL_INTEGRITY.yaml shipped with before 0.7.1."""
    doc["scope"]["normative_clauses"] = doc.pop("normative_clauses")


def _duplicate_priority_without_tiebreak(doc: dict[str, Any]) -> None:
    rules = doc["decision_model"]["rules"]
    rules[1]["priority"] = rules[0]["priority"]
    doc["decision_model"]["priority_tiebreaker"] = "none"


def _unbounded_retry(doc: dict[str, Any]) -> None:
    for action in doc["actions"]:
        if action["retry"] == "bounded_retry":
            action["retry_bound"] = None
            return
    raise AssertionError("fixture has no bounded_retry action")


CASES = [
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _drop("scope.resources"), "REQUIRED"),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _set("metadata.kind", "recipe"), "ENUM"),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _set("metadata.contract_id", "gar.wf"), "TYPE"),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _set("metadata.version", "v1"), "TYPE"),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _set("normative_clauses", []), "MIN_ITEMS"),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _dup_clause, "GOV-CONTRACT-003"),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _ghost_transition, "WF-CONTRACT-002"),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _ghost_failure_route, "WF-CONTRACT-002"),
    (
        "contracts/ARCHITECTURAL_INTEGRITY.yaml",
        INVARIANT,
        _clauses_indented_into_scope,
        "SECTION-MISNESTED",
    ),
    (
        "runtime/STATE_MACHINE.yaml",
        WORKFLOW,
        _set("enforcement.failure_mode", "warn"),
        "GOV-CONTRACT-005",
    ),
    (
        "runtime/STATE_MACHINE.yaml",
        WORKFLOW,
        _set("workflow.explicit_cycle_rules", []),
        "CONDITIONAL",
    ),
    ("runtime/STATE_MACHINE.yaml", WORKFLOW, _unbounded_retry, "CONDITIONAL"),
    (
        "runtime/STATE_MACHINE.yaml",
        WORKFLOW,
        _set("integrity.canonical_serialization", "x"),
        "CONST",
    ),
    (
        "contracts/CONVERGENCE.yaml",
        EVIDENCE,
        _set("result.valid_states", ["pass", "fail"]),
        "CONDITIONAL",
    ),
    ("contracts/CONVERGENCE.yaml", EVIDENCE, _set("result.unknown_is_pass", True), "CONST"),
    ("contracts/CONVERGENCE.yaml", EVIDENCE, _set("freshness.max_age", "P1D"), "CONDITIONAL"),
    # its priorities are unique, so the tiebreaker alone may be anything under explicit_priority;
    # under any other strategy the schema requires priority_tiebreaker == none
    (
        "contracts/OUTCOME_OWNERSHIP.yaml",
        POLICY,
        _set("decision_model.conflict_strategy", "deny_wins"),
        "CONDITIONAL",
    ),
    (
        "contracts/OUTCOME_OWNERSHIP.yaml",
        POLICY,
        _duplicate_priority_without_tiebreak,
        "POLICY-CONTRACT-007",
    ),
    ("contracts/ARCHITECTURAL_INTEGRITY.yaml", INVARIANT, _drop("normative_clauses"), "REQUIRED"),
    (
        "contracts/ARCHITECTURAL_INTEGRITY.yaml",
        INVARIANT,
        _set("metadata.kind", "policy"),
        "INV-CONTRACT-001",
    ),
]


@pytest.mark.parametrize(("rel", "schema", "mutate", "rule"), CASES)
def test_each_defect_class_is_invalid(
    rel: str, schema: str, mutate: Callable[[dict[str, Any]], None], rule: str
) -> None:
    doc = _doc(rel)
    mutate(doc)
    result = _validate(doc, schema)
    assert result.status == "INVALID", result.as_dict()
    assert rule in {f.rule for f in result.findings}, result.as_dict()


def _schema_copy(tmp_path: Path, rel: str, transform: Callable[[str], str]) -> Path:
    root = tmp_path / "schemas"
    shutil.copytree(SCHEMAS, root)
    path = root / rel
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")
    return root


@pytest.mark.parametrize(
    ("schema_file", "old", "new"),
    [
        # an unknown field-spec keyword
        (
            "canonical.schema.workflow_contract.v1.yaml",
            "initial_state: {type: string, required: true}",
            "initial_state: {type: string, required: true, max_length: 8}",
        ),
        # an unparseable conditional phrase
        (
            "canonical.schema.workflow_contract.v1.yaml",
            "require: [workflow.cycle_bound is integer >= 1]",
            "require: [workflow.cycle_bound must be sensible]",
        ),
        # a validation rule nobody evaluates, delegates or reviews
        (
            "canonical.schema.workflow_contract.v1.yaml",
            "  - {id: WF-CONTRACT-001,",
            "  - {id: WF-CONTRACT-099, severity: blocker, rule: new.}\n  - {id: WF-CONTRACT-001,",
        ),
        # an unknown named type
        (
            "canonical.schema.workflow_contract.v1.yaml",
            "initial_state: {type: string,",
            "initial_state: {type: state_name,",
        ),
    ],
)
def test_unknown_vocabulary_is_blocked_not_passed(
    tmp_path: Path, schema_file: str, old: str, new: str
) -> None:
    root = _schema_copy(tmp_path, schema_file, lambda s: s.replace(old, new, 1))
    assert old in (SCHEMAS / schema_file).read_text(encoding="utf-8")
    result = _validate(_doc("runtime/STATE_MACHINE.yaml"), WORKFLOW, root)
    assert result.status == "BLOCKED", result.as_dict()


def test_unresolved_base_schema_is_blocked(tmp_path: Path) -> None:
    root = _schema_copy(
        tmp_path,
        "canonical.schema.workflow_contract.v1.yaml",
        lambda s: s.replace(
            "extends: [canonical.schema.governance_contract.v1]",
            "extends: [canonical.schema.governance_contract.v1, canonical.schema.missing.v1]",
        ),
    )
    result = _validate(_doc("runtime/STATE_MACHINE.yaml"), WORKFLOW, root)
    assert result.status == "BLOCKED"


def test_without_the_binding_disposition_nothing_passes() -> None:
    result = v.validate(_doc("runtime/STATE_MACHINE.yaml"), WORKFLOW, schema_root=SCHEMAS)
    assert result.status == "BLOCKED"


def test_architectural_integrity_core_clauses_are_top_level() -> None:
    """AI-001..AI-005 are referenced by the kernel, workflow and evidence obligations."""
    doc = _doc("contracts/ARCHITECTURAL_INTEGRITY.yaml")
    ids = [c["clause_id"] for c in doc["normative_clauses"]]
    assert ids[:5] == ["AI-001", "AI-002", "AI-003", "AI-004", "AI-005"]
    assert "normative_clauses" not in doc["scope"]
