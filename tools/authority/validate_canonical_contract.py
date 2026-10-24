#!/usr/bin/env python3
# pyright: strict
"""Validate a governance artifact against its ``canonical.schema.*.v1`` document-type schema.

The schemas under ``contracts/schemas/`` are written in a small declarative vocabulary, not
JSON Schema. This validator interprets exactly that vocabulary and fails closed on anything
outside it. Nothing here is doctrine: every requirement comes from the schema files, and every
resolution rule this validator needs that the schemas do not state is declared by the caller's
generation binding (``schema_resolution`` / ``validation_rule_disposition`` in
``skills/l9-global-architect/bindings/GOVERNANCE_GENERATION.yaml``).

Interpreted vocabulary:

* ``inheritance.extends`` -- a schema's ``required_sections`` are the union of its chain's,
  nearest schema winning. A base that resolves to no file is BLOCKED unless the binding
  declares it an abstract root.
* named types -- resolved from the single schema in the same ``schema_family`` that declares a
  ``type_registry``.
* field specs -- ``required``, ``type``, ``fields``, ``item_schema``, ``items``, ``enum``,
  ``const``, ``min_items``, ``allow_empty``, ``unique_items``, ``minimum``, ``maximum``,
  ``default`` (documentation only); ``collection_semantics.default_allow_empty``.
* ``minimum_viable_instance_requirements.required`` of the declared schema.
* ``conditional_rules`` -- the phrase forms parsed by ``_CONDITION`` and ``_REQUIREMENT``.
* ``validation_rules`` -- each id is evaluated here (``_RULES``), delegated to the generator
  named by the binding, or declared as semantic review with a rationale. An id in none of
  those three is BLOCKED: no rule is silently counted as passing.

Exit codes: 0 VALID, 1 INVALID, 2 usage, 3 BLOCKED.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_ROOT = REPO_ROOT / "contracts/schemas"

_BASE_TYPES = {"string", "list", "map", "boolean", "integer", "number", "any", "null"}
_SPEC_KEYS = {
    "required",
    "type",
    "fields",
    "item_schema",
    "items",
    "enum",
    "const",
    "min_items",
    "allow_empty",
    "unique_items",
    "minimum",
    "maximum",
    "default",
}
_TYPE_KEYS = {"base", "pattern", "format", "items", "unique_items", "minimum", "maximum", "any_of"}
_ABSENT = object()


def _load_canonical() -> ModuleType:
    key = "authority_canonical_json"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(
        key, Path(__file__).resolve().parent / "canonical_json.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("tools/authority/canonical_json.py is not importable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


canonical = _load_canonical()


class SchemaBlocked(Exception):
    """The schema vocabulary or its references cannot be resolved; no verdict is possible."""


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    message: str


@dataclass
class Result:
    schema_ref: str
    findings: list[Finding] = field(default_factory=lambda: [])
    blocked: list[Finding] = field(default_factory=lambda: [])
    evaluated_rules: list[str] = field(default_factory=lambda: [])
    delegated_rules: dict[str, str] = field(default_factory=lambda: {})
    semantic_review_rules: dict[str, str] = field(default_factory=lambda: {})

    @property
    def status(self) -> str:
        if self.blocked:
            return "BLOCKED"
        return "INVALID" if self.findings else "VALID"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_ref": self.schema_ref,
            "status": self.status,
            "findings": [vars(f) for f in self.findings],
            "blocked": [vars(f) for f in self.blocked],
            "evaluated_rules": sorted(self.evaluated_rules),
            "delegated_rules": dict(sorted(self.delegated_rules.items())),
            "semantic_review_rules": dict(sorted(self.semantic_review_rules.items())),
        }


@dataclass(frozen=True)
class Disposition:
    """How the caller's binding disposes of rules this validator does not evaluate."""

    abstract_roots: frozenset[str] = frozenset()
    delegated: Mapping[str, str] = field(default_factory=lambda: {})
    semantic_review: Mapping[str, str] = field(default_factory=lambda: {})

    @classmethod
    def from_binding(cls, binding: Mapping[str, Any]) -> Disposition:
        resolution = _as_map(binding.get("schema_resolution"))
        roots = [str(r.get("schema_id")) for r in _as_maps(resolution.get("abstract_roots"))]
        rules = _as_map(binding.get("validation_rule_disposition"))
        delegated: dict[str, str] = {}
        for owner, ids in _as_map(rules.get("delegated")).items():
            for rule_id in _as_list(ids):
                delegated[str(rule_id)] = str(owner)
        review = {
            str(r.get("rule")): str(r.get("rationale"))
            for r in _as_maps(rules.get("semantic_review"))
        }
        return cls(frozenset(roots), delegated, review)


# --------------------------------------------------------------------------- helpers


def _as_map(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return cast(list[Any], value) if isinstance(value, list) else []


def _as_maps(value: Any) -> list[dict[str, Any]]:
    return [cast(dict[str, Any], v) for v in _as_list(value) if isinstance(v, dict)]


def _same(a: Any, b: Any) -> bool:
    return canonical.canonical_json(a) == canonical.canonical_json(b)


def _get(document: Any, dotted: str) -> Any:
    node: Any = document
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return _ABSENT
        node = cast(dict[str, Any], node)[part]
    return node


# --------------------------------------------------------------------------- schemas


class SchemaSet:
    """The schema files under one root, resolved by ``schema_id`` and ``schema_family``."""

    def __init__(self, root: Path, abstract_roots: frozenset[str]) -> None:
        self.root = root
        self.abstract_roots = abstract_roots
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, schema_id: str) -> dict[str, Any]:
        if schema_id not in self._cache:
            path = self.root / f"{schema_id}.yaml"
            if not path.is_file():
                raise SchemaBlocked(f"schema {schema_id} resolves to no file under {self.root}")
            document = _as_map(canonical.load_yaml(path.read_text(encoding="utf-8")))
            if document.get("schema_id") != schema_id:
                raise SchemaBlocked(f"{path} does not declare schema_id {schema_id}")
            self._cache[schema_id] = document
        return self._cache[schema_id]

    def chain(self, schema_id: str) -> list[dict[str, Any]]:
        """Root-first inheritance chain; abstract roots contribute nothing."""
        ordered: list[dict[str, Any]] = []
        visiting: set[str] = set()

        def visit(current: str) -> None:
            if current in visiting:
                raise SchemaBlocked(f"inheritance cycle through {current}")
            if current in self.abstract_roots:
                return
            visiting.add(current)
            schema = self.load(current)
            for base in _as_list(_as_map(schema.get("inheritance")).get("extends")):
                visit(str(base))
            if schema not in ordered:
                ordered.append(schema)
            visiting.discard(current)

        visit(schema_id)
        return ordered

    def type_registry(self, family: str) -> dict[str, Any]:
        owners = [
            p
            for p in sorted(self.root.glob("canonical.schema.*.yaml"))
            if "type_registry:" in p.read_text(encoding="utf-8")
        ]
        registries: list[dict[str, Any]] = []
        for path in owners:
            schema = self.load(path.name.removesuffix(".yaml"))
            if schema.get("schema_family") == family and "type_registry" in schema:
                registries.append(_as_map(schema["type_registry"]))
        if len(registries) != 1:
            raise SchemaBlocked(
                f"schema_family {family} declares {len(registries)} type registries; need exactly 1"
            )
        return registries[0]


# --------------------------------------------------------------------------- field specs


class _Checker:
    def __init__(self, types: Mapping[str, Any], default_allow_empty: bool, result: Result):
        self.types = types
        self.default_allow_empty = default_allow_empty
        self.result = result

    def fail(self, rule: str, path: str, message: str) -> None:
        self.result.findings.append(Finding(rule, path, message))

    def block(self, path: str, message: str) -> None:
        self.result.blocked.append(Finding("SCHEMA-VOCABULARY", path, message))

    # -- types

    def type_ok(self, value: Any, type_name: Any, path: str) -> bool:
        if type_name is None:
            return value is None
        if isinstance(type_name, dict):
            return self.inline_ok(value, cast(dict[str, Any], type_name), path)
        name = str(type_name)
        if name in _BASE_TYPES:
            return self.base_ok(value, name)
        if name not in self.types:
            self.block(path, f"type {name!r} is neither a base type nor in the type registry")
            return True
        return self.inline_ok(value, _as_map(self.types[name]), path)

    def base_ok(self, value: Any, name: str) -> bool:
        if name == "string":
            return isinstance(value, str)
        if name == "list":
            return isinstance(value, list)
        if name == "map":
            return isinstance(value, dict)
        if name == "boolean":
            return isinstance(value, bool)
        if name == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if name == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if name == "null":
            return value is None
        return True  # any

    def inline_ok(self, value: Any, spec: dict[str, Any], path: str) -> bool:
        unknown = set(spec) - _TYPE_KEYS - _SPEC_KEYS
        if unknown:
            self.block(path, f"unknown type keys {sorted(unknown)}")
            return True
        if "any_of" in spec:
            return any(self.type_ok(value, alt, path) for alt in _as_list(spec["any_of"]))
        if "enum" in spec:
            return any(_same(value, option) for option in _as_list(spec["enum"]))
        base = str(spec.get("base", "any"))
        if base not in _BASE_TYPES:
            return self.type_ok(value, base, path)
        if not self.base_ok(value, base):
            return False
        if "pattern" in spec and not re.search(str(spec["pattern"]), str(value)):
            return False
        if "format" in spec and not self.format_ok(str(value), str(spec["format"]), path):
            return False
        if "minimum" in spec and value < spec["minimum"]:
            return False
        if "maximum" in spec and value > spec["maximum"]:
            return False
        if "items" in spec:
            if not all(self.type_ok(v, spec["items"], path) for v in _as_list(value)):
                return False
        if spec.get("unique_items"):
            seen = [canonical.canonical_json(v) for v in _as_list(value)]
            if len(seen) != len(set(seen)):
                return False
        return True

    def format_ok(self, value: str, fmt: str, path: str) -> bool:
        if fmt == "date":
            try:
                _dt.date.fromisoformat(value)
            except ValueError:
                return False
            return len(value) == 10
        if fmt == "date-time":
            if "T" not in value:
                return False
            try:
                _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return False
            return True
        self.block(path, f"unknown format {fmt!r}")
        return True

    # -- field specs

    def check(self, value: Any, spec: Any, path: str) -> None:
        if not isinstance(spec, dict):
            self.block(path, "field spec is not a mapping")
            return
        spec = cast(dict[str, Any], spec)
        unknown = set(spec) - _SPEC_KEYS
        if unknown:
            self.block(path, f"unknown field-spec keys {sorted(unknown)}")
        if value is _ABSENT:
            if spec.get("required") is True:
                self.fail("REQUIRED", path, "required but absent")
            return
        if "const" in spec and not _same(value, spec["const"]):
            self.fail("CONST", path, f"must equal {spec['const']!r}, found {value!r}")
        if "enum" in spec and not any(_same(value, o) for o in _as_list(spec["enum"])):
            self.fail("ENUM", path, f"{value!r} not in {spec['enum']!r}")
        if "type" in spec and not self.type_ok(value, spec["type"], path):
            self.fail("TYPE", path, f"{value!r} is not {spec['type']!r}")
        if "items" in spec:
            for i, item in enumerate(_as_list(value)):
                if not self.type_ok(item, spec["items"], f"{path}[{i}]"):
                    self.fail("ITEMS", f"{path}[{i}]", f"{item!r} violates {spec['items']!r}")
        if isinstance(value, list):
            self.check_collection(cast(list[Any], value), spec, path)
        elif isinstance(value, dict) and self.default_allow_empty is False and not value:
            if spec.get("required") is True and spec.get("allow_empty") is not True:
                if "fields" not in spec:
                    self.fail("GOV-CONTRACT-011", path, "required collection is empty")
        if "minimum" in spec and isinstance(value, (int, float)) and value < spec["minimum"]:
            self.fail("MINIMUM", path, f"{value!r} < {spec['minimum']!r}")
        if "maximum" in spec and isinstance(value, (int, float)) and value > spec["maximum"]:
            self.fail("MAXIMUM", path, f"{value!r} > {spec['maximum']!r}")
        if "fields" in spec:
            if not isinstance(value, dict):
                self.fail("TYPE", path, "must be a mapping")
                return
            mapping = cast(dict[str, Any], value)
            for name, sub in _as_map(spec["fields"]).items():
                self.check(mapping.get(name, _ABSENT), sub, f"{path}.{name}")
        if "item_schema" in spec:
            if not isinstance(value, list):
                self.fail("TYPE", path, "must be a list")
                return
            for i, item in enumerate(cast(list[Any], value)):
                if not isinstance(item, dict):
                    self.fail("TYPE", f"{path}[{i}]", "list item must be a mapping")
                    continue
                entry = cast(dict[str, Any], item)
                for name, sub in _as_map(spec["item_schema"]).items():
                    self.check(entry.get(name, _ABSENT), sub, f"{path}[{i}].{name}")

    def check_collection(self, value: list[Any], spec: dict[str, Any], path: str) -> None:
        if "min_items" in spec and len(value) < int(spec["min_items"]):
            self.fail("MIN_ITEMS", path, f"{len(value)} items < {spec['min_items']}")
        allow_empty = spec.get("allow_empty", self.default_allow_empty)
        if not value and spec.get("required") is True and allow_empty is not True:
            self.fail("GOV-CONTRACT-011", path, "required collection is empty")
        list_string = spec.get("type") == "list_string"
        if spec.get("unique_items") or list_string:
            rendered = [canonical.canonical_json(v) for v in value]
            if len(rendered) != len(set(rendered)):
                self.fail("UNIQUE_ITEMS", path, "items are not unique")


# --------------------------------------------------------------------------- conditional rules

_LITERAL = r"(?P<lit>[A-Za-z0-9_.-]+)"
_CONDITION = re.compile(r"^(?P<path>[A-Za-z0-9_.\[\]*]+) (?P<op>==|!=) " + _LITERAL + r"$")
_REQUIREMENT = re.compile(
    r"^(?:corresponding )?(?P<path>[A-Za-z0-9_.\[\]*]+) (?P<pred>"
    r"is integer >= 1|has at least 1 item|is null or absent|is empty or absent|is null"
    r"|is non-null|is non-empty|contains (?P<item>[A-Za-z0-9_.-]+)|== (?P<eq>[A-Za-z0-9_.-]+))$"
)
_EITHER_UNIQUE = re.compile(
    r"^either rule priorities are unique or (?P<path>[A-Za-z0-9_.]+) == (?P<eq>[A-Za-z0-9_.-]+)$"
)


def _literal(text: str) -> Any:
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered == "null":
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def _scopes(document: Any, when_path: str) -> list[tuple[str, Any, str]]:
    """``(scope_path, scope_node, leaf)`` per item when the path iterates ``[*]``."""
    if "[*]" not in when_path:
        parent, _, leaf = when_path.rpartition(".")
        return [(parent, _get(document, parent) if parent else document, leaf)]
    head, _, tail = when_path.partition("[*].")
    items = _get(document, head)
    return [(f"{head}[{i}]", item, tail) for i, item in enumerate(_as_list(items))]


def _resolve(scope: Any, document: Any, raw: str, when_head: str) -> Any:
    """A requirement path: ``x[*].y`` and ``action.y`` mean the matched item; a bare leaf
    means a sibling of the condition's leaf; a dotted path is absolute."""
    if "[*]." in raw:
        return _get(scope, raw.split("[*].", 1)[1])
    if "." not in raw:
        return _get(scope, raw)
    head, _, rest = raw.partition(".")
    if when_head and (head == when_head.rstrip("s") or head == when_head):
        return _get(scope, rest)
    return _get(document, raw)


def _predicate(value: Any, match: re.Match[str]) -> bool:
    pred = match.group("pred")
    if pred == "is integer >= 1":
        return isinstance(value, int) and not isinstance(value, bool) and value >= 1
    if pred == "has at least 1 item":
        return isinstance(value, list) and len(cast(list[Any], value)) >= 1
    if pred == "is null or absent":
        return value is _ABSENT or value is None
    if pred == "is empty or absent":
        return value is _ABSENT or value in ([], {}, "", None)
    if pred == "is null":
        return value is None
    if pred == "is non-null":
        return value is not _ABSENT and value is not None
    if pred == "is non-empty":
        return value is not _ABSENT and value not in ([], {}, "", None)
    if match.group("item") is not None:
        return any(_same(v, _literal(match.group("item"))) for v in _as_list(value))
    return value is not _ABSENT and _same(value, _literal(match.group("eq")))


def _conditional(document: Any, rule: Mapping[str, Any], index: int, checker: _Checker) -> None:
    where = f"conditional_rules[{index}]"
    when = _CONDITION.match(str(rule.get("when", "")))
    if when is None:
        checker.block(where, f"unparsed condition {rule.get('when')!r}")
        return
    when_path = when.group("path")
    when_head = when_path.split("[*]")[0] if "[*]" in when_path else ""
    # Parse every requirement before evaluating any: vocabulary this validator does not
    # understand is BLOCKED even when its condition does not fire for this document.
    parsed: list[tuple[str, re.Match[str] | None, re.Match[str] | None]] = []
    for requirement in _as_list(rule.get("require")):
        text = str(requirement)
        either = _EITHER_UNIQUE.match(text)
        req = None if either is not None else _REQUIREMENT.match(text)
        if either is None and req is None:
            checker.block(where, f"unparsed requirement {text!r}")
            return
        parsed.append((text, either, req))
    for scope_path, scope, leaf in _scopes(document, when_path):
        actual = _get(scope, leaf)
        matched = actual is not _ABSENT and _same(actual, _literal(when.group("lit")))
        if (when.group("op") == "==") != matched:
            continue
        for text, either, req in parsed:
            if either is not None:
                rules = _as_maps(_get(document, "decision_model.rules"))
                priorities = [r.get("priority") for r in rules]
                unique = len(priorities) == len(set(map(repr, priorities)))
                tiebreak = _get(scope, either.group("path"))
                if not (unique or _same(tiebreak, _literal(either.group("eq")))):
                    checker.fail("CONDITIONAL", scope_path or "$", f"{when_path}: {text}")
                continue
            assert req is not None
            value = _resolve(scope, document, req.group("path"), when_head)
            if not _predicate(value, req):
                checker.fail("CONDITIONAL", scope_path or "$", f"{when_path}: {text}")


# --------------------------------------------------------------------------- validation rules

RuleCheck = Callable[[dict[str, Any], _Checker], None]


def _kind_is(kind: str, rule: str) -> RuleCheck:
    def check(doc: dict[str, Any], checker: _Checker) -> None:
        if _get(doc, "metadata.kind") != kind:
            checker.fail(rule, "$.metadata.kind", f"must equal {kind}")

    return check


def _contract_id(doc: dict[str, Any], checker: _Checker) -> None:
    grammar = r"^[A-Z][A-Z0-9]*(\.[A-Z][A-Z0-9_]*)+\.\d{3}$"
    if not re.match(grammar, str(_get(doc, "metadata.contract_id"))):
        checker.fail("GOV-CONTRACT-001", "$.metadata.contract_id", "violates contract ID grammar")


def _unique_clauses(doc: dict[str, Any], checker: _Checker) -> None:
    ids = [c.get("clause_id") for c in _as_maps(doc.get("normative_clauses"))]
    duplicates = sorted({str(i) for i in ids if ids.count(i) > 1})
    if duplicates:
        checker.fail("GOV-CONTRACT-003", "$.normative_clauses", f"duplicate clause_id {duplicates}")


def _active_declares(doc: dict[str, Any], checker: _Checker) -> None:
    if _get(doc, "metadata.status") != "active":
        return
    for section in ("authority", "scope", "enforcement", "evidence_obligations"):
        if doc.get(section) in (None, [], {}):
            checker.fail("GOV-CONTRACT-004", f"$.{section}", "active contract must declare it")


def _no_warning_blockers(doc: dict[str, Any], checker: _Checker) -> None:
    severity = _get(doc, "enforcement.severity")
    if severity in ("blocker", "major") and _get(doc, "enforcement.failure_mode") == "warn":
        checker.fail("GOV-CONTRACT-005", "$.enforcement", f"{severity} may not fail with warn")


def _active_digest(doc: dict[str, Any], checker: _Checker) -> None:
    if _get(doc, "metadata.status") == "active" and _get(doc, "integrity.content_digest") is None:
        checker.fail("GOV-CONTRACT-008", "$.integrity.content_digest", "active requires a digest")


def _structural(doc: dict[str, Any], checker: _Checker) -> None:
    """Evaluated by the field-spec pass; registered so the id is counted as evaluated."""


def _forbidden_not_expected(doc: dict[str, Any], checker: _Checker) -> None:
    expected = _get(doc, "invariant_definition.expected_state")
    for state in _as_list(_get(doc, "invariant_definition.forbidden_states")):
        if expected is not _ABSENT and _same(state, expected):
            checker.fail(
                "INV-CONTRACT-004", "$.invariant_definition", "forbidden overlaps expected"
            )


def _sourced_inputs(doc: dict[str, Any], checker: _Checker) -> None:
    for i, item in enumerate(_as_maps(doc.get("policy_inputs"))):
        if not str(item.get("source") or "").strip():
            checker.fail("POLICY-CONTRACT-002", f"$.policy_inputs[{i}].source", "no source")


def _deterministic_priority(doc: dict[str, Any], checker: _Checker) -> None:
    rules = _as_maps(_get(doc, "decision_model.rules"))
    priorities = [repr(r.get("priority")) for r in rules]
    duplicated = len(priorities) != len(set(priorities))
    tiebreak = _get(doc, "decision_model.priority_tiebreaker")
    if duplicated and tiebreak != "rule_id_ascending":
        checker.fail(
            "POLICY-CONTRACT-007", "$.decision_model", "duplicate priorities need rule_id_ascending"
        )


def _workflow_references(doc: dict[str, Any], checker: _Checker) -> None:
    states = {str(s.get("state_id")) for s in _as_maps(doc.get("states"))}
    actions = {str(a.get("action_id")) for a in _as_maps(doc.get("actions"))}
    workflow = _as_map(doc.get("workflow"))
    named = [str(workflow.get("initial_state"))]
    named += [str(s) for s in _as_list(workflow.get("terminal_states"))]
    named += [str(s) for s in _as_list(workflow.get("failure_states"))]
    for state in named:
        if state not in states:
            checker.fail("WF-CONTRACT-002", "$.workflow", f"state {state!r} is not declared")
    for i, transition in enumerate(_as_maps(doc.get("transitions"))):
        for end in ("from", "to"):
            if str(transition.get(end)) not in states:
                checker.fail(
                    "WF-CONTRACT-002",
                    f"$.transitions[{i}].{end}",
                    f"state {transition.get(end)!r} is not declared",
                )
        for action in _as_list(transition.get("actions")):
            if str(action) not in actions:
                checker.fail(
                    "WF-CONTRACT-002",
                    f"$.transitions[{i}].actions",
                    f"action {action!r} is not declared",
                )


def _non_idempotent_compensation(doc: dict[str, Any], checker: _Checker) -> None:
    for i, action in enumerate(_as_maps(doc.get("actions"))):
        if action.get("idempotency") == "non_idempotent" and action.get("compensation") is None:
            checker.fail(
                "WF-CONTRACT-004", f"$.actions[{i}]", "non-idempotent action needs compensation"
            )


def _named_property(doc: dict[str, Any], checker: _Checker) -> None:
    if not str(_get(doc, "property.property_id") or "").strip():
        checker.fail(
            "EVIDENCE-CONTRACT-002", "$.property.property_id", "evidence names no property"
        )


_RULES: dict[str, RuleCheck] = {
    "GOV-CONTRACT-001": _contract_id,
    "GOV-CONTRACT-003": _unique_clauses,
    "GOV-CONTRACT-004": _active_declares,
    "GOV-CONTRACT-005": _no_warning_blockers,
    "GOV-CONTRACT-008": _active_digest,
    "GOV-CONTRACT-011": _structural,
    "INV-CONTRACT-001": _kind_is("invariant", "INV-CONTRACT-001"),
    "INV-CONTRACT-004": _forbidden_not_expected,
    "POLICY-CONTRACT-001": _kind_is("policy", "POLICY-CONTRACT-001"),
    "POLICY-CONTRACT-002": _sourced_inputs,
    "POLICY-CONTRACT-003": _structural,
    "POLICY-CONTRACT-007": _deterministic_priority,
    "WF-CONTRACT-001": _kind_is("workflow", "WF-CONTRACT-001"),
    "WF-CONTRACT-002": _workflow_references,
    "WF-CONTRACT-004": _non_idempotent_compensation,
    "WF-CONTRACT-005": _structural,
    "WF-CONTRACT-007": _structural,
    "EVIDENCE-CONTRACT-001": _kind_is("evidence", "EVIDENCE-CONTRACT-001"),
    "EVIDENCE-CONTRACT-002": _named_property,
    "EVIDENCE-CONTRACT-004": _structural,
    "EVIDENCE-CONTRACT-006": _structural,
}
"""Rules this validator evaluates. ``_structural`` ids are decided by the field-spec and
conditional-rule passes (the schema states the same requirement as a field spec or a
conditional rule); the id is registered so its coverage is explicit."""


# --------------------------------------------------------------------------- entry points


def validate(
    document: Any,
    schema_id: str,
    *,
    schema_root: Path = DEFAULT_SCHEMA_ROOT,
    disposition: Disposition | None = None,
) -> Result:
    disposition = disposition or Disposition()
    result = Result(schema_ref=schema_id)
    try:
        schemas = SchemaSet(schema_root, disposition.abstract_roots)
        chain = schemas.chain(schema_id)
        declared = schemas.load(schema_id)
        types = schemas.type_registry(str(declared.get("schema_family")))
    except SchemaBlocked as exc:
        result.blocked.append(Finding("SCHEMA-RESOLUTION", schema_id, str(exc)))
        return result
    if not isinstance(document, dict):
        result.findings.append(Finding("TYPE", "$", "document must be a mapping"))
        return result
    doc = cast(dict[str, Any], document)

    default_allow_empty = True
    sections: dict[str, Any] = {}
    for schema in chain:
        semantics = _as_map(schema.get("collection_semantics"))
        if "default_allow_empty" in semantics:
            default_allow_empty = bool(semantics["default_allow_empty"])
        sections.update(_as_map(schema.get("required_sections")))
    checker = _Checker(types, default_allow_empty, result)

    for name, spec in sections.items():
        checker.check(doc.get(name, _ABSENT), spec, f"$.{name}")
    minimum = _as_list(
        _as_map(declared.get("minimum_viable_instance_requirements")).get("required")
    )
    for name in minimum:
        if str(name) not in doc:
            checker.fail("MINIMUM_VIABLE", f"$.{name}", "required by minimum viable instance")

    for schema in chain:
        for i, rule in enumerate(_as_maps(schema.get("conditional_rules"))):
            _conditional(doc, rule, i, checker)
        for rule in _as_maps(schema.get("validation_rules")):
            rule_id = str(rule.get("id"))
            if rule_id in _RULES:
                _RULES[rule_id](doc, checker)
                result.evaluated_rules.append(rule_id)
            elif rule_id in disposition.delegated:
                result.delegated_rules[rule_id] = disposition.delegated[rule_id]
            elif rule_id in disposition.semantic_review:
                result.semantic_review_rules[rule_id] = disposition.semantic_review[rule_id]
            else:
                checker.block(
                    f"validation_rules.{rule_id}",
                    "rule is not evaluated here and the binding neither delegates it nor "
                    "declares it semantic review",
                )
    return result


def validate_binding_sources(
    binding_path: Path, *, repo_root: Path = REPO_ROOT
) -> dict[str, Result]:
    """Validate every ``schema_aligned_sources`` entry a generation binding declares."""
    binding = _as_map(canonical.load_yaml(binding_path.read_text(encoding="utf-8")))
    disposition = Disposition.from_binding(binding)
    root = repo_root / str(_as_map(binding.get("schema_resolution")).get("schema_root"))
    pack = binding_path.parent.parent
    results: dict[str, Result] = {}
    for source in _as_maps(binding.get("schema_aligned_sources")):
        rel = str(source.get("path"))
        path = pack / rel
        try:
            document = canonical.load_yaml(path.read_text(encoding="utf-8"))
        except (OSError, canonical.CanonicalizationError) as exc:
            result = Result(schema_ref=str(source.get("schema_ref")))
            result.blocked.append(Finding("SOURCE", rel, str(exc)))
            results[rel] = result
            continue
        results[rel] = validate(
            document, str(source.get("schema_ref")), schema_root=root, disposition=disposition
        )
    return results


def _exit_code(statuses: Sequence[str]) -> int:
    if "BLOCKED" in statuses:
        return 3
    return 1 if "INVALID" in statuses else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--binding", type=Path, help="validate a generation binding's sources")
    group.add_argument("--schema", help="schema_id to validate PATH against")
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--schema-root", type=Path, default=DEFAULT_SCHEMA_ROOT)
    parser.add_argument("--disposition-from", type=Path, help="binding supplying dispositions")
    args = parser.parse_args(argv)

    if args.binding is not None:
        results = validate_binding_sources(args.binding.resolve())
    else:
        if args.path is None:
            parser.error("--schema requires PATH")
        disposition = Disposition()
        if args.disposition_from is not None:
            disposition = Disposition.from_binding(
                _as_map(canonical.load_yaml(args.disposition_from.read_text(encoding="utf-8")))
            )
        document = canonical.load_yaml(args.path.read_text(encoding="utf-8"))
        results = {
            str(args.path): validate(
                document, args.schema, schema_root=args.schema_root, disposition=disposition
            )
        }
    print(json.dumps({k: v.as_dict() for k, v in results.items()}, indent=2, sort_keys=True))
    return _exit_code([r.status for r in results.values()])


if __name__ == "__main__":
    sys.exit(main())
