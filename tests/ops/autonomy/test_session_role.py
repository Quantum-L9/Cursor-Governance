"""Swarm-child role registry (ops/autonomy/session_role.py).

A role record only narrows what a session may do, so self-registration is safe; an
unregistered or foreign record never makes a session a child.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

import projection_mode  # noqa: E402
import session_role  # noqa: E402


@pytest.fixture
def roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("L9_SESSION_ROLE_DIR", str(tmp_path / "roles"))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "local-child-1")
    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    return tmp_path / "roles"


def test_an_unregistered_session_is_not_a_child(roles: Path) -> None:
    assert session_role.is_child() is False
    assert session_role.child_record() == {}


def test_register_child_marks_only_this_session(roles: Path) -> None:
    path = session_role.register_child("session_cto_1")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["role"] == "swarm_child" and record["cto_session"] == "session_cto_1"
    assert session_role.is_child() is True
    assert session_role.is_child("another-session") is False


def test_a_record_naming_another_session_is_ignored(roles: Path) -> None:
    path = session_role.register_child("session_cto_1")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["session_id"] = "someone-else"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert session_role.is_child() is False


def test_session_envs_match_the_mode_resolver() -> None:
    assert session_role.SESSION_ENVS == projection_mode.SESSION_ENVS


def test_unresolved_session_cannot_register(roles: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in session_role.SESSION_ENVS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="SESSION_UNRESOLVED"):
        session_role.register_child("session_cto_1")


def test_cli_status_exit_codes(roles: Path) -> None:
    assert session_role.main(["status"]) == 1
    assert session_role.main(["register-child", "--cto-session", "session_cto_1"]) == 0
    assert session_role.main(["status"]) == 0
    assert session_role.main(["clear"]) == 0
    assert session_role.main(["status"]) == 1


def test_remote_session_id_maps_cse_to_the_cross_session_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_REMOTE_SESSION_ID", "cse_017abc")
    assert session_role.remote_session_id() == "session_017abc"
    monkeypatch.delenv("CLAUDE_CODE_REMOTE_SESSION_ID")
    assert session_role.remote_session_id() == ""


def test_child_prompt_tells_the_child_to_register_and_pins_no_remediation() -> None:
    import cto_mode  # noqa: PLC0415

    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "session_cto_z")
    assert 'session_role.py" register-child --cto-session session_cto_z' in text
    assert "PR_REMEDIATE=0" in text
    assert text.index("ROLE REGISTRATION") < text.index("coding_agent_mode.py")
