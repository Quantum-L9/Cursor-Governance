# ruff: noqa: E402
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import check_capability_closure as cc

LIVE = {"l9-dag-authoring", "l9-structured-reasoning", "l9-wire-skill-into-repo"}
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def ir():
    with open(os.path.join(HERE, "fixtures", "self-ir.json"), encoding="utf-8") as handle:
        return json.load(handle)


def test_self_pack_is_closed():
    assert cc.check(ir(), REPO, live_skills=LIVE)["result"] in ("CLOSED", "RUNTIME_BOUND")


def test_missing_executable_fails():
    data = ir()
    data["capabilities"][0]["binding"]["target"] = "skills/l9-skill-compiler/scripts/nope.py"
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "FAIL"


def test_placeholder_success_condition_fails():
    data = ir()
    data["capabilities"][0]["binding"]["success_condition"] = "TODO"
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "FAIL"


def test_dead_delegated_skill_fails():
    data = ir()
    for capability in data["capabilities"]:
        if capability["binding"]["kind"] == "DELEGATED_SKILL":
            capability["binding"]["target"] = "l9-does-not-exist"
            break
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "FAIL"


def test_cycle_detected():
    data = ir()
    by_id = {capability["id"]: capability for capability in data["capabilities"]}
    by_id["bind_inputs"]["binding"]["depends_on"] = ["package"]
    result = cc.check(data, REPO, live_skills=LIVE)
    assert result["result"] == "FAIL"
    assert result["cycles"]


def test_unreachable_capability_fails():
    data = ir()
    for node in data["workflow"]["nodes"]:
        if node["id"] == "PACKAGE":
            node["capabilities"] = []
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "FAIL"


def test_bounded_unknown_blocks():
    data = ir()
    data["capabilities"].append(
        {
            "id": "future_thing",
            "required": True,
            "binding": {"kind": "UNKNOWN", "bounded_unknown": True},
        }
    )
    for node in data["workflow"]["nodes"]:
        if node["id"] == "COMPILE_REQUEST":
            node["capabilities"] = ["future_thing"]
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "BLOCKED"


def test_unbounded_unknown_fails():
    data = ir()
    data["capabilities"].append({"id": "sloppy", "required": True, "binding": {"kind": "UNKNOWN"}})
    for node in data["workflow"]["nodes"]:
        if node["id"] == "COMPILE_REQUEST":
            node["capabilities"] = ["sloppy"]
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "FAIL"


def test_external_capability_requires_probe():
    data = ir()
    data["capabilities"].append(
        {
            "id": "ext",
            "required": True,
            "binding": {"kind": "EXTERNAL_CAPABILITY", "target": "svc"},
        }
    )
    for node in data["workflow"]["nodes"]:
        if node["id"] == "COMPILE_REQUEST":
            node["capabilities"] = ["ext"]
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "FAIL"


def test_external_capability_with_probe_is_runtime_bound():
    data = ir()
    data["capabilities"].append(
        {
            "id": "ext",
            "required": True,
            "binding": {
                "kind": "EXTERNAL_CAPABILITY",
                "target": "svc",
                "probe": "GET /health",
                "failure_behavior": "stop and report",
            },
        }
    )
    for node in data["workflow"]["nodes"]:
        if node["id"] == "COMPILE_REQUEST":
            node["capabilities"] = ["ext"]
    assert cc.check(data, REPO, live_skills=LIVE)["result"] == "RUNTIME_BOUND"
