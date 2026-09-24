"""The handoff JSON Schemas are the machine form of the code — they must agree.

``ops/memory/schemas/*.schema.json`` is what an operator or another agent reads;
``ops/memory/session_handoff.py`` / ``governance_handoff.py`` are what the Stop
hooks enforce. A schema that drifts from the code documents a contract nobody
runs (``ops/memory/HANDOFF_CONTRACT.md``: "holds them to the same verdict on
every case").

The table below is generated per section of each schema, so a section added to
the code is covered without a new line here. Every fixture carries its EXPECTED
verdict and both judges must reach it: agreement alone would let the runtime and
the schema be wrong together.

Two rules are deliberately NOT in the table because JSON Schema cannot express
them, and each schema says so in its own text; they have their own tests below:

* the aggregate byte cap of the normalized brief (32 KiB / 12 KiB);
* ``pr_number`` equal to THIS publication's number (a fact outside the file).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from jsonschema import Draft202012Validator

from ops.memory import governance_handoff as gh
from ops.memory import session_handoff as sh

SCHEMAS = Path(__file__).resolve().parents[3] / "ops" / "memory" / "schemas"


def _schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


SESSION = _schema(sh.HANDOFF_SCHEMA)
GOVERNANCE = _schema(gh.GOVERNANCE_SCHEMA)

ACCEPT, REJECT = True, False
LONG = "x" * (sh.MAX_TEXT * 4)
#: Whitespace to both judges (str.isspace and the regex ``\S`` agree on these).
BLANKS = ("", " ", "   ", "\t\n", " ", "\x1f")


class Kind(NamedTuple):
    name: str
    module: Any
    schema: dict[str, Any]
    required_text: tuple[str, ...]
    text_lists: tuple[str, ...]
    structured: dict[str, tuple[str, tuple[str, ...]]]
    #: Sections of the OTHER handoff: refused here, naming the other file.
    foreign: tuple[str, ...]

    def base(self) -> dict[str, Any]:
        return self.module.example(7)

    def minimal(self) -> dict[str, Any]:
        doc: dict[str, Any] = {"schema": self.base()["schema"], "pr_number": 7}
        doc.update({key: f"the {key}" for key in self.required_text})
        return doc


KINDS = (
    Kind(
        "session",
        sh,
        SESSION,
        ("objective", "status"),
        sh.TEXT_LISTS,
        sh.STRUCTURED,
        tuple(gh.SECTIONS),
    ),
    Kind(
        "governance",
        gh,
        GOVERNANCE,
        (),
        (),
        gh.SECTIONS,
        # sorted: KEYS is a frozenset, and its iteration order changes with the
        # per-process hash seed; pytest-xdist workers must collect identical ids.
        tuple(sorted(sh.KEYS - {"schema", "pr_number"})),
    ),
)


class Case(NamedTuple):
    label: str
    kind: Kind
    doc: object
    expected: bool


def _with(doc: dict[str, Any], **changes: object) -> dict[str, Any]:
    return {**doc, **changes}


def _without(doc: dict[str, Any], key: str) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k != key}


def _cases(kind: Kind) -> Iterator[tuple[str, object, bool]]:
    base, minimal = kind.base(), kind.minimal()
    sections = (*kind.text_lists, *kind.structured)

    # -- valid baselines ----------------------------------------------------
    yield "example", base, ACCEPT
    yield "minimal (every optional section absent)", minimal, ACCEPT

    # -- not an object ------------------------------------------------------
    for label, doc in (("list", [base]), ("string", "x"), ("null", None), ("number", 7)):
        yield f"document is a {label}", doc, REJECT

    # -- required fields missing -------------------------------------------
    for key in ("schema", "pr_number", *kind.required_text):
        yield f"required {key} missing", _without(base, key), REJECT

    # -- wrong schema -------------------------------------------------------
    other = sh.HANDOFF_SCHEMA if kind.module is gh else gh.GOVERNANCE_SCHEMA
    for value in (other, f"{base['schema'][:-1]}2", "", None, 1):
        yield f"schema={value!r}", _with(base, schema=value), REJECT

    # -- pr_number ----------------------------------------------------------
    for value in (0, -1, "7", True, False, None, 7.5, [7], {"n": 7}, float("nan")):
        yield f"pr_number={value!r}", _with(base, pr_number=value), REJECT
    for value in (1, 7, 10**12, 7.0):
        yield f"pr_number={value!r}", _with(base, pr_number=value), ACCEPT

    # -- unknown top-level keys --------------------------------------------
    for key in ("summary", "notes", "observed", ""):
        yield f"unknown key {key!r}", _with(base, **{key: []}), REJECT

    # -- fields placed in the wrong handoff --------------------------------
    for key in kind.foreign:
        yield f"{key} belongs in the other handoff", _with(base, **{key: []}), REJECT
    if kind.module is sh:
        yield "governance_friction alias", _with(base, governance_friction=[]), REJECT

    # -- required strings ---------------------------------------------------
    for key in kind.required_text:
        for blank in BLANKS:
            yield f"{key}={blank!r}", _with(base, **{key: blank}), REJECT
        for value in (None, 1, ["x"], {"x": 1}):
            yield f"{key}={value!r}", _with(base, **{key: value}), REJECT
        yield f"{key} zero-width space is not whitespace", _with(base, **{key: "​"}), ACCEPT
        yield f"{key} oversized value is truncated", _with(base, **{key: LONG}), ACCEPT

    for key in sections:
        # -- optional sections absent / null / empty ------------------------
        yield f"{key} absent", _without(base, key), ACCEPT
        yield f"{key} null", _with(base, **{key: None}), ACCEPT
        yield f"{key} empty", _with(base, **{key: []}), ACCEPT
        for value in ("one", {"x": 1}, 1, True):
            yield f"{key} not a list ({value!r})", _with(base, **{key: value}), REJECT

    for key in kind.text_lists:
        yield f"{key} item", _with(base, **{key: ["done"]}), ACCEPT
        yield f"{key} oversized item", _with(base, **{key: [LONG]}), ACCEPT
        for blank in BLANKS:
            yield f"{key} item {blank!r}", _with(base, **{key: [blank]}), REJECT
        for value in (None, 1, {"item": "x"}, ["x"]):
            yield f"{key} item {value!r}", _with(base, **{key: [value]}), REJECT
        yield f"{key} 40 items", _with(base, **{key: ["r"] * sh.MAX_ITEMS}), ACCEPT
        yield f"{key} 41 items", _with(base, **{key: ["r"] * (sh.MAX_ITEMS + 1)}), REJECT

    for key, (req, optional) in kind.structured.items():
        full = {req: "the thing", **{name: f"the {name}" for name in optional}}
        # -- bare-string shorthand -----------------------------------------
        yield f"{key} bare string", _with(base, **{key: ["rotate the key"]}), ACCEPT
        yield f"{key} oversized bare string", _with(base, **{key: [LONG]}), ACCEPT
        for blank in BLANKS:
            yield f"{key} bare string {blank!r}", _with(base, **{key: [blank]}), REJECT
        # -- valid structured items ----------------------------------------
        yield f"{key} full object", _with(base, **{key: [full]}), ACCEPT
        yield f"{key} required-only object", _with(base, **{key: [{req: "x"}]}), ACCEPT
        yield f"{key} mixed string and object", _with(base, **{key: ["x", full]}), ACCEPT
        yield f"{key} extra item key", _with(base, **{key: [{**full, "extra": 1}]}), ACCEPT
        yield f"{key} oversized required", _with(base, **{key: [{req: LONG}]}), ACCEPT
        # -- the required field --------------------------------------------
        yield f"{key} object without {req}", _with(base, **{key: [_without(full, req)]}), REJECT
        for blank in BLANKS:
            doc = _with(base, **{key: [{**full, req: blank}]})
            yield f"{key}.{req}={blank!r}", doc, REJECT
        for value in (None, 1, ["x"], {"x": 1}):
            yield f"{key}.{req}={value!r}", _with(base, **{key: [{**full, req: value}]}), REJECT
        # -- each optional field -------------------------------------------
        for name in optional:
            for value in (None, *BLANKS, LONG):
                doc = _with(base, **{key: [{**full, name: value}]})
                yield f"{key}.{name}={value[:8] if value else value!r}", doc, ACCEPT
            for value in (0, 1, False, True, [], ["x"], {}, {"x": 1}):
                doc = _with(base, **{key: [{**full, name: value}]})
                yield f"{key}.{name}={value!r}", doc, REJECT
        # -- items that are neither string nor object ----------------------
        for value in (None, 1, True, [req]):
            yield f"{key} item {value!r}", _with(base, **{key: [value]}), REJECT
        # -- item count ----------------------------------------------------
        yield f"{key} 40 items", _with(base, **{key: ["i"] * sh.MAX_ITEMS}), ACCEPT
        yield f"{key} 41 items", _with(base, **{key: ["i"] * (sh.MAX_ITEMS + 1)}), REJECT


CASES = [Case(f"{k.name}: {label}", k, doc, exp) for k in KINDS for label, doc, exp in _cases(k)]


def _runtime_accepts(module: Any, doc: object) -> bool:
    try:
        module.normalize(doc)
    except sh.HandoffError:
        return False
    return True


@pytest.mark.parametrize("case", CASES, ids=[c.label for c in CASES])
def test_runtime_and_schema_reach_the_expected_verdict(case: Case) -> None:
    runtime = _runtime_accepts(case.kind.module, case.doc)
    schema = Draft202012Validator(case.kind.schema).is_valid(case.doc)
    assert (runtime, schema) == (case.expected, case.expected), (
        f"{case.label}: runtime={runtime} schema={schema} expected={case.expected}"
    )


def test_the_table_covers_every_case_class() -> None:
    """The classes the contract requires are present for both handoffs."""
    for kind in KINDS:
        labels = " | ".join(c.label for c in CASES if c.kind is kind)
        for fragment in (
            "required pr_number missing",
            "schema=",
            "pr_number=0",
            "unknown key",
            "absent",
            " null",
            " empty",
            "bare string",
            "full object",
            "' '",
            "41 items",
            "oversized",
            "belongs in the other handoff",
        ):
            assert fragment in labels, (kind.name, fragment)
    assert len(CASES) > 500


def test_the_table_is_identical_in_every_process() -> None:
    """pytest-xdist requires every worker to collect the same ids in the same order.

    Two interpreters with different hash seeds must generate the same labels.
    """
    probe = (
        "import json, tests.ops.memory.test_handoff_schemas as t;"
        "print(json.dumps([c.label for c in t.CASES]))"
    )
    root = Path(__file__).resolve().parents[3]
    runs = [
        subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=True,
            cwd=root,
            env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(root)},
        ).stdout
        for seed in ("1", "2")
    ]
    assert runs[0] == runs[1]
    assert json.loads(runs[0]) == [c.label for c in CASES]


# -- structure ----------------------------------------------------------------


def test_the_schemas_are_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(SESSION)
    Draft202012Validator.check_schema(GOVERNANCE)


def test_keys_sections_and_limits_match_the_code() -> None:
    assert set(SESSION["properties"]) == set(sh.KEYS)
    assert set(GOVERNANCE["properties"]) == set(gh.KEYS)
    assert SESSION["properties"]["schema"]["const"] == sh.HANDOFF_SCHEMA
    assert GOVERNANCE["properties"]["schema"]["const"] == gh.GOVERNANCE_SCHEMA
    for schema, spec in ((SESSION, sh.STRUCTURED), (GOVERNANCE, gh.SECTIONS)):
        for key, (required, optional) in spec.items():
            section = schema["properties"][key]
            assert section["maxItems"] == sh.MAX_ITEMS
            obj = section["items"]["oneOf"][1]
            assert obj["required"] == [required], key
            assert set(obj["properties"]) == {required, *optional}, key
    for key in sh.TEXT_LISTS:
        assert SESSION["properties"][key]["maxItems"] == sh.MAX_ITEMS


def test_the_embedded_examples_validate() -> None:
    for schema in (SESSION, GOVERNANCE):
        for example in schema["examples"]:
            Draft202012Validator(schema).validate(example)


# -- wrong handoff: refused AND told where it belongs --------------------------


def test_every_section_of_the_other_handoff_is_named_in_the_refusal() -> None:
    assert set(gh.SECTIONS) <= set(sh.MISPLACED)
    assert set(sh.KEYS) - {"schema", "pr_number"} == set(gh.MISPLACED)
    for kind, target in ((KINDS[0], str(gh.GOVERNANCE_REL)), (KINDS[1], str(sh.HANDOFF_REL))):
        for key in kind.foreign:
            with pytest.raises(sh.HandoffError, match=f"{key} belongs in {target}"):
                kind.module.normalize(_with(kind.base(), **{key: []}))


# -- normalization the verdicts imply -----------------------------------------


def test_an_integral_float_pr_number_normalizes_to_the_integer() -> None:
    for kind in KINDS:
        brief = kind.module.normalize(_with(kind.base(), pr_number=7.0))
        assert brief["pr_number"] == 7 and type(brief["pr_number"]) is int


def test_null_empty_and_blank_optional_fields_are_omitted_not_stored() -> None:
    for value in (None, "", "   "):
        brief = sh.normalize(_with(sh.example(7), blocked=[{"item": "x", "unblock": value}]))
        assert brief["blocked"] == [{"item": "x"}]


def test_an_oversized_value_is_truncated_to_the_item_cap() -> None:
    brief = sh.normalize(_with(sh.example(7), objective=LONG, risks=[LONG]))
    assert len(brief["objective"]) == sh.MAX_TEXT and brief["objective"].endswith("…")
    assert len(brief["risks"][0]) == sh.MAX_TEXT


def test_absent_and_null_sections_normalize_to_empty() -> None:
    brief = sh.normalize(_with(KINDS[0].minimal(), risks=None))
    assert all(brief[key] == [] for key in (*sh.TEXT_LISTS, *sh.STRUCTURED))


# -- the two rules JSON Schema cannot express (declared, tested here) ---------


@pytest.mark.parametrize(
    ("kind", "cap"), [(KINDS[0], sh.MAX_HANDOFF_BYTES), (KINDS[1], gh.MAX_GOVERNANCE_BYTES)]
)
def test_the_aggregate_byte_cap_is_runtime_only_and_declared(kind: Kind, cap: int) -> None:
    """Each value is valid and the schema accepts; the normalized total is over the cap."""
    doc = kind.base()
    for key, (req, optional) in kind.structured.items():
        doc[key] = [{req: LONG, **{n: LONG for n in optional}}] * sh.MAX_ITEMS
    assert Draft202012Validator(kind.schema).is_valid(doc)
    with pytest.raises(sh.HandoffError, match=f"the cap is {cap}"):
        kind.module.normalize(doc)
    assert str(cap) in kind.schema["description"], "the schema must declare the cap it cannot hold"


@pytest.mark.parametrize("kind", KINDS, ids=[k.name for k in KINDS])
def test_the_publication_binding_is_runtime_only_and_declared(kind: Kind) -> None:
    doc = kind.base()
    assert Draft202012Validator(kind.schema).is_valid(doc)
    assert kind.module.normalize(doc, pr_number=7)["pr_number"] == 7
    with pytest.raises(sh.HandoffError, match="is not this publication"):
        kind.module.normalize(doc, pr_number=8)
    assert "pr-summary.json" in kind.schema["properties"]["pr_number"]["description"]
