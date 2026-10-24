"""The shared canonicalizer is the producer's digest, byte for byte, and fails closed."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
AUTHORITY = REPO / "tools/authority"


def _load(name: str) -> ModuleType:
    key = f"authority_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, AUTHORITY / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


cj = _load("canonical_json")


def _producer_artifacts() -> list[Path]:
    root = REPO / "generated/governance"
    return sorted(root.glob("*/projections/*.json")) + sorted(root.glob("*/composed.json"))


def test_reproduces_every_committed_producer_digest() -> None:
    """Quantum-L9/.github's compiler emitted these digests; the shared canonicalizer must agree."""
    artifacts = _producer_artifacts()
    assert artifacts, "no producer-emitted projection artifacts are committed"
    for path in artifacts:
        document = json.loads(path.read_text(encoding="utf-8"))
        field = "projection_digest" if "projection_digest" in document else "composition_digest"
        body = {k: v for k, v in document.items() if k != field}
        assert cj.semantic_digest(body) == document[field], path


def test_normalize_rekeys_by_string_form_and_sorts_lexically() -> None:
    assert cj.canonical_json({10: "a", 2: "b"}) == '{"10":"a","2":"b"}'
    assert cj.canonical_json({"b": [3, 1], "a": None}) == '{"a":null,"b":[3,1]}'


def test_bytes_become_hex_mapping() -> None:
    assert cj.normalize(b"\x00\xff") == {"$bytes_hex": "00ff"}


@pytest.mark.parametrize(
    "value",
    [{1: "x", "1": "y"}, float("nan"), float("inf"), {"when": __import__("datetime").date.today()}],
)
def test_unrepresentable_values_fail_closed(value: Any) -> None:
    with pytest.raises(cj.CanonicalizationError):
        cj.canonical_json(value)


def test_yaml_dates_stay_lexical_strings() -> None:
    unquoted = cj.load_yaml("introduced_at: 2026-08-26\n")
    quoted = cj.load_yaml("introduced_at: '2026-08-26'\n")
    assert unquoted == {"introduced_at": "2026-08-26"}
    assert cj.semantic_digest(unquoted) == cj.semantic_digest(quoted)


def test_yaml_scalars_otherwise_keep_safe_loader_types() -> None:
    assert cj.load_yaml("a: 1\nb: true\nc: null\nd: 1.5\n") == {
        "a": 1,
        "b": True,
        "c": None,
        "d": 1.5,
    }


@pytest.mark.parametrize(
    "text",
    ["a: 1\na: 2\n", "a: 1\n---\nb: 2\n", "a: [unclosed\n", "a: !!timestamp 2026-08-26\n"],
)
def test_yaml_ambiguity_fails_closed(text: str) -> None:
    with pytest.raises(cj.CanonicalizationError):
        cj.load_yaml(text)


@pytest.mark.parametrize("module_name", ["produce_projection_bundle", "verify_coding_projection"])
def test_existing_tools_delegate_to_the_one_digest(module_name: str) -> None:
    module = _load(module_name)
    sample = {"z": [1, {"y": "é"}], "a": True, 3: None}
    assert module._canonical_digest(sample) == cj.semantic_digest(sample)
