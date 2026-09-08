#!/usr/bin/env python3
"""Characterization of the deterministic router brain (VSP phase 0).

These tests pin the behaviour of ``route_prompt`` that the Virtual Skill Plane
must preserve: lexical matching, typo tolerance, positive / negative /
required signals, thresholds, explicit-only exclusion, explicit-hint handling,
description fallback, one primary, at most two supports.

They run against a synthetic registry so a manifest edit cannot silently move
the goalposts, plus a handful of live-registry probes for the planning
doctrine that phase 3 resolves.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ROUTER_PATH = ROOT / "ops" / "skill_routing" / "route_prompt.py"
REGISTRY_PATH = ROOT / "ops" / "generated" / "skill-registry.json"


def _load_router():
    spec = importlib.util.spec_from_file_location("l9_skill_routing_char", ROUTER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def router():
    return _load_router()


@pytest.fixture(scope="module")
def live_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _skill(name: str, invocation: str = "model_allowed", **extra: Any) -> dict[str, Any]:
    record = {
        "name": name,
        "path": f"skills/{name}",
        "skill_md": f"skills/{name}/SKILL.md",
        "skill_sha256": "0" * 64,
        "invocation": invocation,
        "composition_role": "general",
        "description": extra.pop("description", f"{name} description use when needed"),
        "when_to_use": extra.pop("when_to_use", ""),
        "reason": "",
        "disable_model_invocation": invocation == "explicit_only",
        "user_invocable": True,
    }
    record.update(extra)
    return record


def synthetic_registry() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "generation_id": "g" * 64,
        "source": "skills/AUTONOMY_MANIFEST.yaml",
        "source_manifest_sha256": "a" * 64,
        "source_skill_corpus_sha256": "b" * 64,
        "routing": {
            "force_threshold": 8,
            "advisory_threshold": 6,
            "max_primary": 1,
            "max_supporting": 2,
            "trivial_patterns": [r"^fix (the )?typo\b"],
            "routes": [
                {
                    "id": "alpha",
                    "primary": "l9-alpha",
                    "signal_weight": 8,
                    "positive_signals": ["alpha task", "run alpha"],
                    "negative_signals": ["not alpha"],
                    "supporting": ["l9-support-one", "l9-support-two", "l9-support-three"],
                },
                {
                    "id": "beta",
                    "primary": "l9-beta",
                    "signal_weight": 8,
                    "positive_signals": ["beta task"],
                    "supporting": ["l9-structured-reasoning"],
                },
                {
                    "id": "hinted",
                    "primary": "l9-hinted",
                    "signal_weight": 8,
                    "hint_allowed": True,
                    "required_any": ["hinted operation"],
                    "positive_signals": ["hinted operation", "run hinted"],
                    "supporting": ["l9-support-one"],
                },
                {
                    "id": "locked",
                    "primary": "l9-locked",
                    "signal_weight": 8,
                    "positive_signals": ["locked operation"],
                    "supporting": [],
                },
                {
                    "id": "soft",
                    "primary": "l9-soft",
                    "signal_weight": 3,
                    "positive_signals": ["soft one", "soft two"],
                    "supporting": [],
                },
            ],
        },
        "skills": [
            _skill("l9-alpha"),
            _skill("l9-beta"),
            _skill("l9-soft"),
            _skill("l9-support-one"),
            _skill("l9-support-two"),
            _skill("l9-support-three"),
            _skill("l9-structured-reasoning"),
            _skill("l9-hinted", "explicit_only"),
            _skill("l9-locked", "explicit_only"),
            _skill(
                "l9-describe-only",
                description="use when the user needs telemetry ingestion pipelines rebuilt",
                when_to_use="rebuilding telemetry ingestion pipelines for observability",
            ),
        ],
    }


# --- lexical brain ---------------------------------------------------------


def test_exact_positive_route(router):
    got = router.route_prompt("please run alpha now", synthetic_registry())
    assert got is not None
    assert got["primary"] == "l9-alpha"
    assert got["source"] == "route"
    assert got["route_id"] == "alpha"


def test_typo_tolerance_on_long_tokens(router):
    got = router.route_prompt("hinted operatoin please", synthetic_registry())
    assert got is not None and got["primary"] == "l9-hinted"


def test_trivial_prompt_no_route(router):
    assert router.route_prompt("fix the typo in README", synthetic_registry()) is None
    assert router.route_prompt("", synthetic_registry()) is None
    assert router.route_prompt("   ", synthetic_registry()) is None


def test_negative_signal_blocks_primary(router):
    got = router.route_prompt("alpha task but not alpha", synthetic_registry())
    assert got is None or got["primary"] != "l9-alpha"


def test_supporting_capped_at_two_and_excludes_explicit(router):
    got = router.route_prompt("alpha task", synthetic_registry())
    assert got is not None
    assert len(got["supporting"]) <= 2
    assert got["supporting"] == ["l9-support-one", "l9-support-two"]


def test_explicit_only_without_hint_never_routes(router):
    got = router.route_prompt("locked operation now", synthetic_registry())
    assert got is None or got["primary"] != "l9-locked"


def test_explicit_hint_route_source(router):
    got = router.route_prompt("run the hinted operation", synthetic_registry())
    assert got is not None
    assert got["primary"] == "l9-hinted"
    assert got["source"] == "explicit_hint"


def test_explicit_hint_requires_required_any(router):
    got = router.route_prompt("run hinted", synthetic_registry())
    assert got is None or got["primary"] != "l9-hinted"


def test_advisory_route_below_force_threshold(router):
    got = router.route_prompt("soft one and soft two", synthetic_registry())
    assert got is not None
    assert got["primary"] == "l9-soft"
    assert got["source"] == "advisory_route"
    assert router.route_prompt("soft one only", synthetic_registry()) is None


def test_description_fallback(router):
    got = router.route_prompt(
        "rebuild the telemetry ingestion pipelines for observability", synthetic_registry()
    )
    assert got is not None
    assert got["primary"] == "l9-describe-only"
    assert got["source"] == "description"
    assert got["supporting"] == ["l9-structured-reasoning"]


def test_one_primary_only(router):
    got = router.route_prompt("alpha task and beta task", synthetic_registry())
    assert got is not None
    assert isinstance(got["primary"], str)


def test_malformed_registry_is_not_silently_routed(router):
    assert router.route_prompt("alpha task", {}) is None
    broken = synthetic_registry()
    broken["routing"]["routes"] = [{"id": "no-primary"}]
    assert router.route_prompt("alpha task", broken) is None


# --- deterministic ties ------------------------------------------------------


def _tie_registry(order: list[str]) -> dict[str, Any]:
    reg = synthetic_registry()
    routes = {
        "tie-b": {
            "id": "tie-b",
            "primary": "l9-tie-b",
            "signal_weight": 8,
            "positive_signals": ["tie task"],
            "supporting": [],
        },
        "tie-a": {
            "id": "tie-a",
            "primary": "l9-tie-a",
            "signal_weight": 8,
            "positive_signals": ["tie task"],
            "supporting": [],
        },
    }
    reg["routing"]["routes"] = [routes[name] for name in order]
    reg["skills"] += [_skill("l9-tie-a"), _skill("l9-tie-b")]
    return reg


def test_equal_score_is_independent_of_manifest_order(router):
    first = router.route_prompt("tie task", _tie_registry(["tie-b", "tie-a"]))
    second = router.route_prompt("tie task", _tie_registry(["tie-a", "tie-b"]))
    assert first is not None and second is not None
    assert first["route_id"] == second["route_id"] == "tie-a"


def test_explicit_priority_outranks_route_id(router):
    reg = _tie_registry(["tie-a", "tie-b"])
    reg["routing"]["routes"][1]["priority"] = 5
    got = router.route_prompt("tie task", reg)
    assert got is not None and got["route_id"] == "tie-b"


def test_registry_reorder_preserves_selection(router):
    base = synthetic_registry()
    shuffled = copy.deepcopy(base)
    shuffled["routing"]["routes"].reverse()
    shuffled["skills"].reverse()
    for prompt in ("alpha task", "beta task", "soft one and soft two", "run the hinted operation"):
        assert router.route_prompt(prompt, base) == router.route_prompt(prompt, shuffled)


# --- planning doctrine (resolved in VSP phase 3) -----------------------------


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("plan this before coding", "l9-plan-simple"),
        ("create an execution plan for this feature", "l9-plan-simple"),
        ("prepare a PE campaign", "l9-plan"),
        (
            "make campaign INTENT=brief.md and take this brief through completed",
            "l9-pe-campaign-activate",
        ),
    ],
)
def test_planning_doctrine(router, live_registry, prompt, expected):
    got = router.route_prompt(prompt, live_registry)
    assert got is not None, prompt
    assert got["primary"] == expected


def test_rule_and_router_agree_on_ordinary_planning(router, live_registry):
    """The always-apply rule must not carry a competing planning mapping."""
    rule = (ROOT / "rules" / "23-l9-skill-routing.mdc").read_text(encoding="utf-8")
    assert "Common triggers" not in rule
    got = router.route_prompt("plan this before coding", live_registry)
    assert got is not None and got["primary"] == "l9-plan-simple"
