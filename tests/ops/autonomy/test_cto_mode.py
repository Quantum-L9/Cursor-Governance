"""CTO mode: opt-in activation that binds only admitted, verified projections."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import cto_mode  # noqa: E402

TC = "l9.projection/technical-coordination@1"
SID = "session-a"


@pytest.fixture(autouse=True)
def _no_ambient_session(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in cto_mode.SESSION_ENVS:
        monkeypatch.delenv(name, raising=False)


def _verify(status_by_ref: dict[str, str]):
    def verify(binding: Path, _root: Path | None) -> dict:
        ref = yaml.safe_load(binding.read_text())["input"]["authority"]["projection_profile_ref"]
        status = status_by_ref.get(ref, "BLOCKED")
        return {"status": status, "reason": "ADMITTED" if status == cto_mode.ADMITTED else "X"}

    return verify


def _contract(tmp_path: Path, **overrides) -> Path:
    doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
    for key, value in overrides.items():
        doc[key] = value
    path = tmp_path / "MODE.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def test_contract_is_opt_in_and_selects_technical_coordination() -> None:
    doc = cto_mode.load_contract()
    assert doc["activation"]["default"] is False
    assert doc["activation"]["always_enabled"] is False
    assert doc["activation"]["repository_presence_alone_activates"] is False
    refs = [p["ref"] for p in doc["selection"]["projections"]]
    assert refs[0] == TC


def test_off_by_default(tmp_path: Path) -> None:
    report = cto_mode.evaluate(tmp_path, verify=_verify({TC: cto_mode.ADMITTED}), session_id=SID)
    assert report["mode"] == "OFF"
    assert "load" not in report


def test_requested_and_admitted_is_active_with_composed_view(tmp_path: Path) -> None:
    cto_mode.request(tmp_path, session_id=SID)
    report = cto_mode.evaluate(tmp_path, verify=_verify({TC: cto_mode.ADMITTED}), session_id=SID)
    assert report["mode"] == "ACTIVE"
    assert report["load"] == [
        {
            "ref": TC,
            "composed_view": str(
                REPO / "generated/governance/technical_coordination/composed.json"
            ),
            "provenance": None,
        }
    ]


@pytest.mark.parametrize("status", ["BUNDLE_VERIFIED", "BLOCKED", "REJECTED", "STALE"])
def test_required_projection_not_admitted_blocks_and_loads_nothing(
    tmp_path: Path, status: str
) -> None:
    cto_mode.request(tmp_path, session_id=SID)
    report = cto_mode.evaluate(tmp_path, verify=_verify({TC: status}), session_id=SID)
    assert report["mode"] == "BLOCKED"
    assert report["load"] == []
    assert [b["ref"] for b in report["blockers"]] == [TC]


def test_optional_projection_unavailable_does_not_block(tmp_path: Path) -> None:
    doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
    doc["selection"]["projections"][0]["required"] = False
    path = tmp_path / "MODE.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    cto_mode.request(tmp_path, contract_path=path, session_id=SID)
    report = cto_mode.evaluate(tmp_path, contract_path=path, verify=_verify({}), session_id=SID)
    assert report["mode"] == "ACTIVE"
    assert report["load"] == []
    assert report["projections"][0]["status"] == "BLOCKED"


def test_contract_change_after_request_is_stale(tmp_path: Path) -> None:
    path = _contract(tmp_path)
    cto_mode.request(tmp_path, contract_path=path, session_id=SID)
    path.write_text(path.read_text() + "# widened\n")
    report = cto_mode.evaluate(
        tmp_path, contract_path=path, verify=_verify({TC: cto_mode.ADMITTED}), session_id=SID
    )
    assert report["mode"] == "STALE"


@pytest.mark.parametrize(
    "mutation, reason",
    [
        ({"activation": {"default": True, "always_enabled": False}}, "MODE_MUST_BE_OPT_IN"),
        ({"activation": {"default": False, "always_enabled": True}}, "MODE_MUST_BE_OPT_IN"),
        ({"selection": {"projections": []}}, "SELECTION_EMPTY"),
        (
            {"selection": {"projections": [{"ref": TC, "binding": "nope.yaml", "required": True}]}},
            "BINDING_ABSENT",
        ),
        (
            {
                "selection": {
                    "projections": [
                        {
                            "ref": "l9.projection/other@1",
                            "binding": "governance/cto-mode/bindings/technical-coordination.yaml",
                            "required": True,
                        }
                    ]
                }
            },
            "BINDING_REF_MISMATCH",
        ),
    ],
)
def test_malformed_contract_fails_closed(tmp_path: Path, mutation: dict, reason: str) -> None:
    path = _contract(tmp_path, **mutation)
    with pytest.raises(cto_mode.ContractError, match=reason):
        cto_mode.load_contract(path)
    (tmp_path / cto_mode.STATE_REL).parent.mkdir(parents=True)
    (tmp_path / cto_mode.STATE_REL).write_text("{}")
    report = cto_mode.evaluate(
        tmp_path, contract_path=path, verify=_verify({TC: cto_mode.ADMITTED}), session_id=SID
    )
    assert report["mode"] == "REJECTED"


def test_corrupt_state_is_rejected(tmp_path: Path) -> None:
    (tmp_path / cto_mode.STATE_REL).parent.mkdir(parents=True)
    (tmp_path / cto_mode.STATE_REL).write_text('{"schema": "other"}')
    assert cto_mode.evaluate(tmp_path, verify=_verify({}), session_id=SID)["mode"] == "REJECTED"


def test_cli_on_blocks_without_admitted_bundle_then_off_removes_only_state(tmp_path: Path) -> None:
    keep = tmp_path / ".l9" / "keep.txt"
    keep.parent.mkdir(parents=True)
    keep.write_text("unrelated")
    script = REPO / "ops/autonomy/cto_mode.py"
    on = subprocess.run(
        [sys.executable, str(script), "on", "--workspace", str(tmp_path), "--session-id", SID],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(on.stdout)
    # No admitted technical-coordination bundle is committed yet: the real verifier blocks.
    assert on.returncode == 3, on.stdout + on.stderr
    assert report["mode"] == "BLOCKED"
    assert report["load"] == []
    off = subprocess.run(
        [sys.executable, str(script), "off", "--workspace", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(off.stdout) == {"mode": "OFF", "state_removed": True}
    assert not (tmp_path / cto_mode.STATE_REL).exists()
    assert keep.read_text() == "unrelated"


def test_request_from_another_session_does_not_carry_over(tmp_path: Path) -> None:
    cto_mode.request(tmp_path, session_id=SID)
    report = cto_mode.evaluate(
        tmp_path, verify=_verify({TC: cto_mode.ADMITTED}), session_id="session-b"
    )
    assert report["mode"] == "OFF"
    assert report["reason"] == "REQUESTED_IN_ANOTHER_SESSION"
    assert "load" not in report


def test_unresolvable_session_never_activates(tmp_path: Path) -> None:
    with pytest.raises(cto_mode.ContractError, match="SESSION_UNRESOLVED"):
        cto_mode.request(tmp_path)
    cto_mode.request(tmp_path, session_id=SID)
    report = cto_mode.evaluate(tmp_path, verify=_verify({TC: cto_mode.ADMITTED}))
    assert report["mode"] == "OFF"
    assert report["reason"] == "SESSION_UNRESOLVED"


def test_session_resolves_from_host_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    assert cto_mode.resolve_session_id() is None
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "default")
    assert cto_mode.resolve_session_id() is None
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "cc-1")
    assert cto_mode.resolve_session_id() == "cc-1"
    monkeypatch.setenv("CURSOR_SESSION_ID", "cur-1")
    assert cto_mode.resolve_session_id() == "cur-1"
    assert cto_mode.resolve_session_id("explicit") == "explicit"
