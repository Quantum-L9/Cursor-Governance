"""Coding-agent mode: opt-in binding of the coding-agent execution projection, no skill."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import architect_mode  # noqa: E402
import coding_agent_mode  # noqa: E402
import projection_mode  # noqa: E402

SID = "session-a"
REF = "l9.projection/coding-agent-execution@1"
BINDING = "governance/authority-bindings/coding-agent-execution.yaml"


@pytest.fixture(autouse=True)
def _no_ambient_session(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in coding_agent_mode.SESSION_ENVS:
        monkeypatch.delenv(name, raising=False)


def _verify(status: str):
    return lambda _binding, _root: {"status": status, "reason": status}


def test_contract_is_opt_in_skill_free_and_selects_the_execution_projection() -> None:
    doc = coding_agent_mode.load_contract()
    assert doc["activation"]["default"] is False
    assert doc["activation"]["always_enabled"] is False
    assert doc["activation"]["skill_presence_alone_activates"] is False
    assert doc["intended_consumer"]["depends_on_skill"] is False
    assert doc["activation"]["entrypoint"] == "commands/coding-agent.md"
    assert doc["selection"]["projections"] == [
        {
            "ref": REF,
            "binding": BINDING,
            "required": True,
            "basis": "l9.domain-consumer-binding/coding-agent@1 predecessor_profiles",
            "purpose": (
                "Execution invariants, contracts and the authority model for bounded code changes"
            ),
        }
    ]


def test_binding_is_read_through_its_own_shape_and_status_reader() -> None:
    doc = yaml.safe_load((REPO / BINDING).read_text())
    ref, verifier = projection_mode.binding_profile(doc)
    assert ref == REF
    assert verifier == "ops/scripts/coding_projection_status.py"
    views = projection_mode.binding_views(doc)
    assert [v.name for v in views] == [
        "authority_model.projection.json",
        "contracts.projection.json",
        "invariants.projection.json",
    ]


def test_active_loads_every_execution_projection(tmp_path: Path) -> None:
    coding_agent_mode.request(tmp_path, session_id=SID)
    report = coding_agent_mode.evaluate(
        tmp_path, verify=_verify(coding_agent_mode.ADMITTED), session_id=SID
    )
    assert report["mode"] == "ACTIVE"
    [item] = report["load"]
    assert item["ref"] == REF
    assert "composed_view" not in item
    assert len(item["views"]) == 3 and all(Path(v).is_file() for v in item["views"])


@pytest.mark.parametrize("status", ["STALE", "BLOCKED", "UNVERIFIED", "REJECTED"])
def test_unverified_projection_blocks_the_mode(tmp_path: Path, status: str) -> None:
    coding_agent_mode.request(tmp_path, session_id=SID)
    report = coding_agent_mode.evaluate(tmp_path, verify=_verify(status), session_id=SID)
    assert report["mode"] == "BLOCKED"
    assert [b["ref"] for b in report["blockers"]] == [REF]
    assert report["load"] == []


@pytest.mark.parametrize(
    "classifier, expected",
    [
        (
            {"status": "BOUND", "detail": "d", "admission": {"status": "ADMITTED_AND_CURRENT"}},
            "ADMITTED_AND_CURRENT",
        ),
        (
            {"status": "CURRENT", "detail": "d", "admission": {"status": "ADMITTED_AND_CURRENT"}},
            "ADMITTED_AND_CURRENT",
        ),
        (
            {"status": "BOUND", "detail": "d", "admission": {"status": "ADMISSION_UNRESOLVED"}},
            "BLOCKED",
        ),
        ({"status": "BOUND", "detail": "d"}, "BLOCKED"),
        (
            {"status": "STALE", "detail": "d", "admission": {"status": "ADMITTED_AND_CURRENT"}},
            "STALE",
        ),
        ({"status": "UNVERIFIED", "detail": "d"}, "UNVERIFIED"),
    ],
)
def test_classifier_verdict_admits_only_a_verified_and_admitted_bundle(
    classifier: dict, expected: str
) -> None:
    assert projection_mode.coding_verdict(classifier)["status"] == expected


def test_modes_keep_separate_state(tmp_path: Path) -> None:
    coding_agent_mode.request(tmp_path, session_id=SID)
    assert (tmp_path / ".l9/coding-agent-mode/session.json").is_file()
    other = architect_mode.evaluate(
        tmp_path, verify=_verify(architect_mode.ADMITTED), session_id=SID
    )
    assert other["mode"] == "OFF"
    assert coding_agent_mode.release(tmp_path) is True


def test_command_is_registered() -> None:
    manifest = yaml.safe_load((REPO / "commands/COMMANDS_MANIFEST.yaml").read_text())
    assert {"slash": "/coding-agent", "file": "commands/coding-agent.md", "enabled": True} in (
        manifest["commands"]
    )
    command = (REPO / "commands/coding-agent.md").read_text()
    assert "ops/autonomy/coding_agent_mode.py" in command
    assert "does not invoke or\nrequire the `l9-coding-agent` skill" in command


def test_cli_without_authority_checkout_blocks(tmp_path: Path) -> None:
    script = REPO / "ops/autonomy/coding_agent_mode.py"
    proc = subprocess.run(
        [sys.executable, str(script), "on", "--workspace", str(tmp_path), "--session-id", SID],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    report = json.loads(proc.stdout)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert report["mode"] == "BLOCKED"
    assert report["load"] == []
