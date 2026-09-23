"""The handoff JSON Schemas are the machine form of the code — they must agree.

``ops/memory/schemas/*.schema.json`` is what an operator or another agent reads;
``ops/memory/session_handoff.py`` / ``governance_handoff.py`` are what the Stop
hooks enforce. A schema that drifts from the code documents a contract nobody
runs, so each case below is judged by BOTH and must get the same verdict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from ops.memory import governance_handoff as gh
from ops.memory import session_handoff as sh

SCHEMAS = Path(__file__).resolve().parents[3] / "ops" / "memory" / "schemas"


def _schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


SESSION = _schema(sh.HANDOFF_SCHEMA)
GOVERNANCE = _schema(gh.GOVERNANCE_SCHEMA)


def _code_accepts(module: Any, doc: object) -> bool:
    try:
        module.normalize(doc)
    except sh.HandoffError:
        return False
    return True


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


def _session(**extra: object) -> dict[str, Any]:
    return {**sh.example(7), **extra}


def _governance(**extra: object) -> dict[str, Any]:
    return {**gh.example(7), **extra}


CASES = [
    ("session example", sh, SESSION, _session()),
    (
        "session minimal",
        sh,
        SESSION,
        {"schema": sh.HANDOFF_SCHEMA, "pr_number": 7, "objective": "o", "status": "s"},
    ),
    ("session string items", sh, SESSION, _session(human_actions=["rotate the key"])),
    ("session null section", sh, SESSION, _session(risks=None)),
    ("session wrong schema", sh, SESSION, _session(schema="v0")),
    ("session no status", sh, SESSION, {k: v for k, v in _session().items() if k != "status"}),
    ("session blank objective", sh, SESSION, _session(objective="  ")),
    ("session pr as string", sh, SESSION, _session(pr_number="7")),
    ("session pr zero", sh, SESSION, _session(pr_number=0)),
    ("session friction misplaced", sh, SESSION, _session(governance_friction=[])),
    ("session unknown key", sh, SESSION, _session(summary="x")),
    ("session list not list", sh, SESSION, _session(risks="one")),
    ("session item missing required", sh, SESSION, _session(blocked=[{"blocker": "b"}])),
    ("session too many items", sh, SESSION, _session(risks=["r"] * (sh.MAX_ITEMS + 1))),
    ("session not an object", sh, SESSION, ["not", "an", "object"]),
    ("governance example", gh, GOVERNANCE, _governance()),
    ("governance minimal", gh, GOVERNANCE, {"schema": gh.GOVERNANCE_SCHEMA, "pr_number": 7}),
    ("governance string items", gh, GOVERNANCE, _governance(degraded_bootstrap=["memory_mcp"])),
    ("governance repo section", gh, GOVERNANCE, _governance(decisions=[])),
    ("governance wrong schema", gh, GOVERNANCE, _governance(schema=sh.HANDOFF_SCHEMA)),
    ("governance no pr", gh, GOVERNANCE, {"schema": gh.GOVERNANCE_SCHEMA}),
    ("governance bad item", gh, GOVERNANCE, _governance(blockers=[{"unblock": "x"}])),
]


@pytest.mark.parametrize(("label", "module", "schema", "doc"), CASES, ids=[c[0] for c in CASES])
def test_code_and_schema_give_the_same_verdict(
    label: str, module: Any, schema: dict[str, Any], doc: object
) -> None:
    schema_ok = Draft202012Validator(schema).is_valid(doc)
    assert schema_ok == _code_accepts(module, doc), label


def test_the_embedded_examples_validate() -> None:
    for schema in (SESSION, GOVERNANCE):
        for example in schema["examples"]:
            Draft202012Validator(schema).validate(example)
