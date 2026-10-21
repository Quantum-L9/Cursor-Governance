"""Behavioral tests for the coding-agent canonical-binding gate.

The gate is mechanical enforcement of the ``l9-coding-agent`` law that a
verified canonical binding precedes mutation: it denies file mutations only
while a run is active (``.l9/coding-agent/run.json``) and that run has neither
a BOUND/CURRENT record from the coding-agent verifier nor an explicit,
verbatim user reauthorization. Everything else passes untouched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import coding_agent_binding_gate as gate  # noqa: E402

RUN = {
    "schema": gate.RUN_SCHEMA,
    "started_at": "2026-10-21T00:00:00Z",
    "binding_record": "binding.json",
}
RECORD = {
    "verifier": "l9-coding-agent/scripts/verify_canonical_binding.py",
    "status": "BOUND",
    "reason": "PROJECTION_BUNDLE_VERIFIED",
}


def start_run(workspace: Path, *, record: dict | None = RECORD, run: dict | None = None) -> Path:
    run_dir = workspace / gate.RUN_DIR
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / gate.RUN_FILE).write_text(json.dumps(run if run is not None else RUN))
    if record is not None:
        (run_dir / gate.RECORD_FILE).write_text(json.dumps(record))
    return run_dir


def edit(workspace: Path, rel: str = "src/app.py", tool: str = "Edit") -> gate.Decision:
    return gate.evaluate(tool, {"file_path": str(workspace / rel)}, cwd=workspace, env={})


def test_no_active_run_allows_everything(tmp_path: Path) -> None:
    assert edit(tmp_path).allow
    assert gate.evaluate("Write", {"file_path": "relative.py"}, cwd=tmp_path, env={}).allow


def test_non_mutating_tools_are_ignored(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    assert gate.evaluate("Read", {"file_path": str(tmp_path / "x")}, cwd=tmp_path, env={}).allow
    assert gate.evaluate("Bash", {"command": "rm -rf src"}, cwd=tmp_path, env={}).allow


def test_bound_record_allows_mutation(tmp_path: Path) -> None:
    start_run(tmp_path)
    decision = edit(tmp_path)
    assert decision.allow and decision.reason == "canonical binding BOUND"


def test_current_record_allows_mutation(tmp_path: Path) -> None:
    start_run(tmp_path, record={**RECORD, "status": "CURRENT"})
    assert edit(tmp_path).allow


@pytest.mark.parametrize("tool", sorted(gate.MUTATING_TOOLS))
def test_active_run_without_a_record_denies_every_file_tool(tmp_path: Path, tool: str) -> None:
    start_run(tmp_path, record=None)
    decision = edit(tmp_path, tool=tool)
    assert not decision.allow
    assert "no verified canonical binding" in decision.reason
    assert "verify_canonical_binding.py --bundle" in decision.reason
    assert "reauthorized_unknown" in decision.reason


@pytest.mark.parametrize("status", ["REJECTED", "BLOCKED", "STALE", None])
def test_non_bound_record_denies(tmp_path: Path, status: str | None) -> None:
    record = {**RECORD, "status": status, "reason": "SOURCE_DIGEST_NOT_CURRENT"}
    if status is None:
        record.pop("status")
    start_run(tmp_path, record=record)
    decision = edit(tmp_path)
    assert not decision.allow
    assert (
        status or "absent"
    ) in decision.reason and "SOURCE_DIGEST_NOT_CURRENT" in decision.reason


def test_record_from_another_verifier_is_not_a_binding(tmp_path: Path) -> None:
    start_run(tmp_path, record={**RECORD, "verifier": "someone-else/verify.py"})
    assert not edit(tmp_path).allow


def test_explicit_reauthorization_carries_the_run(tmp_path: Path) -> None:
    run = {**RUN, "reauthorized_unknown": {"instruction": "proceed with the binding Unknown"}}
    start_run(tmp_path, record=None, run=run)
    decision = edit(tmp_path)
    assert decision.allow and "reauthorized" in decision.reason


def test_empty_reauthorization_does_not(tmp_path: Path) -> None:
    run = {**RUN, "reauthorized_unknown": {"instruction": "   "}}
    start_run(tmp_path, record=None, run=run)
    assert not edit(tmp_path).allow


def test_malformed_run_state_fails_closed(tmp_path: Path) -> None:
    run_dir = start_run(tmp_path, record=None)
    (run_dir / gate.RUN_FILE).write_text("{not json")
    decision = edit(tmp_path)
    assert not decision.allow and "unreadable" in decision.reason
    (run_dir / gate.RUN_FILE).write_text(json.dumps({"schema": "l9.other/v1"}))
    decision = edit(tmp_path)
    assert not decision.allow and gate.RUN_SCHEMA in decision.reason


def test_run_state_files_themselves_stay_writable(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    for rel in (f"{gate.RUN_DIR}/{gate.RECORD_FILE}", f"{gate.RUN_DIR}/{gate.RUN_FILE}"):
        decision = edit(tmp_path, rel=rel, tool="Write")
        assert decision.allow and decision.reason == "coding-agent run state"


def test_run_is_found_above_a_nested_path_and_not_in_a_sibling_tree(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    start_run(workspace, record=None)
    assert not edit(workspace, rel="deep/er/file.py").allow
    other = tmp_path / "other"
    other.mkdir()
    assert edit(other).allow


def test_breakglass_needs_a_reason_not_a_flag(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    denied = gate.evaluate(
        "Edit",
        {"file_path": str(tmp_path / "a.py")},
        cwd=tmp_path,
        env={gate.BREAKGLASS_ENV: "1"},
    )
    assert not denied.allow
    allowed = gate.evaluate(
        "Edit",
        {"file_path": str(tmp_path / "a.py")},
        cwd=tmp_path,
        env={gate.BREAKGLASS_ENV: "incident 42: binding authority offline"},
    )
    assert allowed.allow and "breakglass" in allowed.reason


def test_cli_denies_as_a_pretooluse_decision(tmp_path: Path) -> None:
    start_run(tmp_path, record=None)
    event = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "x.py")},
        "cwd": str(tmp_path),
    }
    proc = subprocess.run(
        [sys.executable, str(REPO / "ops/autonomy/coding_agent_binding_gate.py")],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    output = json.loads(proc.stdout)["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert output["permissionDecisionReason"].startswith("coding-agent binding gate:")


def test_cli_is_silent_when_nothing_is_active(tmp_path: Path) -> None:
    event = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "x.py")},
        "cwd": str(tmp_path),
    }
    proc = subprocess.run(
        [sys.executable, str(REPO / "ops/autonomy/coding_agent_binding_gate.py")],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and proc.stdout == ""
