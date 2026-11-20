"""A registered /lcto swarm child edits files only with its own coding-agent mode ACTIVE.

The CTO child prompt makes coding-agent mode the child's first action after role
registration; the binding gate makes it mechanical for the file tools. Solo sessions
are untouched: the role only narrows (L9-MONOTONIC-001).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import coding_agent_binding_gate as gate  # noqa: E402
import host_binding  # noqa: E402
import session_role  # noqa: E402

SID = "sess-child"
DIGEST = "sha256:" + hashlib.sha256(gate.MODE_CONTRACT.read_bytes()).hexdigest()


def child(sid: str | None) -> bool:
    return sid == SID


def solo(_sid: str | None) -> bool:
    return False


def mode_state(workspace: Path, **overrides: object) -> Path:
    state = {
        "schema": gate.MODE_STATE_SCHEMA,
        "session_id": SID,
        "contract_digest": DIGEST,
        "last_contract_digest": DIGEST,
        "last_mode": "ACTIVE",
    }
    state.update(overrides)
    path = workspace / gate.MODE_STATE_DIR / gate.MODE_STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def write(workspace: Path, rel: str = "src/app.py", **kw: object) -> gate.Decision:
    target = workspace / rel
    return gate.evaluate(
        "Write",
        {"file_path": str(target), "content": "x"},
        cwd=workspace,
        env={},
        session_id=SID,
        **kw,  # type: ignore[arg-type]
    )


def test_solo_session_is_unaffected_without_mode(tmp_path: Path) -> None:
    decision = write(tmp_path, is_child=solo)
    assert decision.allow


def test_child_without_mode_is_denied_with_the_fix(tmp_path: Path) -> None:
    decision = write(tmp_path, is_child=child)
    assert not decision.allow
    assert "coding_agent_mode.py" in decision.reason and "CTO-BLOCKER" in decision.reason


def test_child_with_active_mode_for_this_session_is_allowed(tmp_path: Path) -> None:
    mode_state(tmp_path)
    decision = write(tmp_path, is_child=child)
    assert decision.allow


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"last_mode": "BLOCKED"}, "not ACTIVE"),
        ({"last_mode": None}, "not evaluated"),
        ({"session_id": "someone-else"}, "another session"),
        ({"last_contract_digest": "sha256:old"}, "older contract"),
        ({"contract_digest": "sha256:old"}, "older contract"),
        ({"schema": "wrong"}, gate.MODE_STATE_SCHEMA),
    ],
)
def test_child_mode_state_that_does_not_prove_active_denies(
    tmp_path: Path, overrides: dict, fragment: str
) -> None:
    mode_state(tmp_path, **overrides)
    decision = write(tmp_path, is_child=child)
    assert not decision.allow
    assert fragment in decision.reason


def test_child_cannot_write_its_mode_state_through_a_file_tool(tmp_path: Path) -> None:
    mode_state(tmp_path)
    decision = write(tmp_path, ".l9/coding-agent-mode/session.json", is_child=child)
    assert not decision.allow
    assert "coding-agent mode state" in decision.reason


def test_non_mutating_tools_and_breakglass_pass_for_a_child(tmp_path: Path) -> None:
    read = gate.evaluate("Read", {}, cwd=tmp_path, env={}, session_id=SID, is_child=child)
    assert read.allow
    decision = gate.evaluate(
        "Write",
        {"file_path": str(tmp_path / "a.py")},
        cwd=tmp_path,
        env={gate.BREAKGLASS_ENV: "operator recovery"},
        session_id=SID,
        is_child=child,
    )
    assert decision.allow


def test_main_reads_the_payload_session_and_the_role_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    roles = tmp_path / "roles"
    monkeypatch.setenv("L9_SESSION_ROLE_DIR", str(roles))
    session_role.register_child("session_cto", session_id=SID)
    event = {
        "session_id": SID,
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "a.py"), "content": "x"},
    }
    code = gate.main(io.StringIO(json.dumps(event)))
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    mode_state(tmp_path)
    code = gate.main(io.StringIO(json.dumps(event)))
    assert code == 0
    assert capsys.readouterr().out == ""

    event["session_id"] = "solo-session"
    (tmp_path / gate.MODE_STATE_DIR / gate.MODE_STATE_FILE).unlink()
    code = gate.main(io.StringIO(json.dumps(event)))
    assert code == 0
    assert capsys.readouterr().out == ""


WRAP = (
    REPO
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "coding_agent_binding_gate_wrap.py"
)


def _wrap_with_brain(monkeypatch: pytest.MonkeyPatch, brain_main: object) -> object:
    import importlib.util
    import types

    surface = types.ModuleType("surface_detect")
    surface.cursor_host_present = lambda: False  # type: ignore[attr-defined]
    surface.claude_runtime_present = lambda: True  # type: ignore[attr-defined]
    brain = types.ModuleType("coding_agent_binding_gate")
    brain.main = brain_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "surface_detect", surface)
    monkeypatch.setitem(sys.modules, "coding_agent_binding_gate", brain)
    spec = importlib.util.spec_from_file_location("l9_test_binding_wrap", WRAP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _boom() -> int:
    raise RuntimeError("brain fault")


@pytest.mark.parametrize("brain_main", [_boom, lambda: 1])
def test_wrapper_turns_a_brain_fault_into_a_deny(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], brain_main: object
) -> None:
    wrap = _wrap_with_brain(monkeypatch, brain_main)
    code = wrap.main()  # type: ignore[attr-defined]
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "failing closed" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_wrapper_passes_a_brain_decision_through(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wrap = _wrap_with_brain(monkeypatch, lambda: 0)
    code = wrap.main()  # type: ignore[attr-defined]
    assert code == 0
    assert capsys.readouterr().out == ""


def test_claude_code_host_default_binding_does_not_satisfy_the_child_gate(
    tmp_path: Path,
) -> None:
    """The Claude Code host binds the coding projection by default (2026-11-20, option B).

    That is a host binding, not coding-agent mode: a registered child whose host default
    bound the projection is still denied until it turns the mode ACTIVE itself.
    """
    # Imported at module top: a wrapper test above puts the governance clone first on sys.path.
    assert Path(host_binding.__file__).resolve().parent == REPO / "ops" / "autonomy"

    def admitted(_binding: Path, _root: Path | None) -> dict:
        return {"status": host_binding.ADMITTED, "reason": "test"}

    def current(_base, _ws, _root) -> dict:
        return {"status": host_binding.BASE_CURRENT, "authority_main": "f" * 40}

    report = host_binding.evaluate(
        "claude-code", workspace=tmp_path, verify=admitted, verify_base=current
    )
    assert report["status"] == "BOUND"
    assert [item["ref"] for item in report["load"]] == ["l9.projection/coding-agent-execution@1"]

    denied = write(tmp_path, is_child=child)
    assert not denied.allow
    assert "coding-agent mode is not on" in denied.reason
    # Nothing the host binding reads or prints is a mode state the gate accepts.
    assert not (tmp_path / gate.MODE_STATE_DIR).exists()
    source = Path(gate.__file__).read_text(encoding="utf-8")
    assert "host_binding" not in source and "host-bindings" not in source

    mode_state(tmp_path)
    assert write(tmp_path, is_child=child).allow
