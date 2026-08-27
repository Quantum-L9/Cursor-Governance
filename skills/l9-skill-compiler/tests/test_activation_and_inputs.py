# ruff: noqa: E402
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import bind_inputs as bi
import evaluate_activation as ea

LIVE = {"l9-dag-authoring", "l9-structured-reasoning", "l9-wire-skill-into-repo"}


def load(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as handle:
        return json.load(handle)


def test_all_activation_fixtures_pass():
    result = ea.evaluate(load("self-ir.json"), live_skills=LIVE)
    assert result["status"] == "PASS", result["results"]


def test_required_fixture_classes_present():
    result = ea.evaluate(load("self-ir.json"), live_skills=LIVE)
    assert result["missing_classes"] == []


def test_sibling_collision_routes_elsewhere():
    result = ea.evaluate(load("self-ir.json"), live_skills=LIVE)
    collisions = [item for item in result["results"] if item["class"] == "sibling_collision"]
    assert collisions
    assert all(item["status"] == "pass" and not item["fired"] for item in collisions)


def test_missing_class_is_reported():
    data = load("self-ir.json")
    data["activation_evals"] = [
        item for item in data["activation_evals"] if item["class"] != "sibling_collision"
    ]
    result = ea.evaluate(data, live_skills=LIVE)
    assert "sibling_collision" in result["missing_classes"]
    assert result["status"] == "FAIL"


def test_valid_compile_request_binds():
    assert bi.bind(load("compile-request.valid.json")) == []


def test_invalid_compile_request_is_rejected():
    errors = bi.bind(load("compile-request.invalid.json"))
    assert errors
    assert any("portable" in error for error in errors)
