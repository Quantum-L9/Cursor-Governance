"""Unit tests for the Claude Agent SDK adapter. No network, no SDK import required."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ADAPTER = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ADAPTER / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


agent = _load("l9_agent")
validator = _load("validate_agent_sdk_env")
CFG = agent.load_config(ADAPTER / "config.yaml")
REPO = agent.REPO


@pytest.mark.parametrize("rel", ["CANONICAL_LAW.md", "INVARIANTS.md", "ORG_INVARIANTS.yaml", "CODEOWNERS", ".env",
                                 ".github/workflows/ci.yml", "rulesets/main.json", "policies/x.yaml", "security/a.md"])
def test_protected_paths_denied(rel):
    assert agent.is_protected(str(REPO / rel), CFG)


@pytest.mark.parametrize("rel", ["README.md", "environment/agents/adapters/claude-agent-sdk/l9_agent.py", "docs/x.md"])
def test_unprotected_paths_allowed(rel):
    assert not agent.is_protected(str(REPO / rel), CFG)


def test_outside_repo_is_protected():
    assert agent.is_protected("/etc/passwd", CFG)


def test_deny_shape():
    out = agent.deny({"hook_event_name": "PreToolUse"}, "nope")
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "nope" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_governor_veto_maps_to_deny():
    out = agent.map_launcher_result(2, "", "blocked by law", "governor", {"hook_event_name": "PreToolUse"}, 2, "s.py")
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_observer_veto_code_does_not_deny():
    out = agent.map_launcher_result(2, "", "x", "observer", {"hook_event_name": "PreToolUse"}, 2, "s.py")
    assert out == {}


def test_observer_stdout_becomes_context():
    out = agent.map_launcher_result(0, "advice", "", "observer", {"hook_event_name": "PostToolUse"}, 2, "s.py")
    assert out["hookSpecificOutput"]["additionalContext"] == "advice"


def test_audit_record_and_write(tmp_path):
    rec = agent.audit_record({"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "s1"}, "tu1")
    log = tmp_path / "audit.jsonl"
    agent.write_audit(rec, log)
    line = json.loads(log.read_text().splitlines()[0])
    assert line["tool"] == "Bash" and line["tool_use_id"] == "tu1" and "ts" in line


def test_config_validates():
    assert validator.validate(CFG) == []


def test_validator_catches_missing_project():
    bad = dict(CFG, setting_sources=["user"])
    assert any(e.startswith("G_SETTING_SOURCES") for e in validator.validate(bad))


def test_validator_catches_unnamed_deny():
    bad = dict(CFG, disallowed_tools=[{"rule": "WebFetch"}])
    assert any(e.startswith("G_DENY_INVARIANT") for e in validator.validate(bad))


def test_report_schema_requires_core_keys():
    assert set(agent.REPORT_SCHEMA["required"]) == {"summary", "findings", "files_changed"}
