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


CTO_SELECTION = [
    TC,
    "l9.projection/architecture@1",
    "l9.projection/governance@1",
    "l9.projection/evidence-provenance@1",
    "l9.projection/contracts-conformance@1",
    "l9.projection/capabilities-dependencies@1",
    "l9.projection/identity-attribution@1",
    "l9.projection/strategic-value@1",
]


ALL_ADMITTED = dict.fromkeys(CTO_SELECTION, cto_mode.ADMITTED)


def test_selection_is_the_owner_confirmed_set_all_required() -> None:
    doc = cto_mode.load_contract()
    projections = doc["selection"]["projections"]
    assert [p["ref"] for p in projections] == CTO_SELECTION
    assert all(p["required"] is True for p in projections)
    assert doc["selection"]["status"] == "complete"


@pytest.mark.parametrize("ref", CTO_SELECTION)
def test_each_selected_binding_names_cto_mode_and_pins_its_bundle(ref: str) -> None:
    entry = next(p for p in cto_mode.load_contract()["selection"]["projections"] if p["ref"] == ref)
    binding = yaml.safe_load((REPO / entry["binding"]).read_text())
    assert "cto_mode_active" in binding["load_condition"]["when"]
    assert binding["load_condition"]["repository_presence_alone_loads"] is False
    pins = binding["input"]["authority"]
    lock = json.loads((REPO / binding["input"]["bundle"]["path"] / "bundle.lock.json").read_text())
    assert lock["projection_profile"] == {"ref": ref, "digest": pins["projection_profile_digest"]}
    decided = {
        (d["candidate_ref"], d["candidate_digest"]) for d in binding["admission"]["decisions"]
    }
    assert (ref, pins["projection_profile_digest"]) in decided


def test_off_by_default(tmp_path: Path) -> None:
    report = cto_mode.evaluate(tmp_path, verify=_verify({TC: cto_mode.ADMITTED}), session_id=SID)
    assert report["mode"] == "OFF"
    assert "load" not in report


def test_requested_and_admitted_is_active_with_composed_view(tmp_path: Path) -> None:
    cto_mode.request(tmp_path, session_id=SID)
    report = cto_mode.evaluate(tmp_path, verify=_verify(ALL_ADMITTED), session_id=SID)
    assert report["mode"] == "ACTIVE"
    assert [item["ref"] for item in report["load"]] == CTO_SELECTION
    composed = str(REPO / "generated/governance/technical_coordination/composed.json")
    assert report["load"][0] == {
        "ref": TC,
        "composed_view": composed,
        "views": [composed],
        "provenance": None,
    }
    assert all(Path(item["composed_view"]).is_file() for item in report["load"])


@pytest.mark.parametrize("status", ["BUNDLE_VERIFIED", "BLOCKED", "REJECTED", "STALE"])
def test_required_projection_not_admitted_blocks_and_loads_nothing(
    tmp_path: Path, status: str
) -> None:
    cto_mode.request(tmp_path, session_id=SID)
    report = cto_mode.evaluate(
        tmp_path, verify=_verify({**ALL_ADMITTED, TC: status}), session_id=SID
    )
    assert report["mode"] == "BLOCKED"
    assert report["load"] == []
    assert [b["ref"] for b in report["blockers"]] == [TC]


def test_optional_projection_unavailable_does_not_block(tmp_path: Path) -> None:
    doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
    doc["selection"]["projections"][0]["required"] = False
    path = tmp_path / "MODE.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    cto_mode.request(tmp_path, contract_path=path, session_id=SID)
    report = cto_mode.evaluate(
        tmp_path,
        contract_path=path,
        verify=_verify({**ALL_ADMITTED, TC: "BLOCKED"}),
        session_id=SID,
    )
    assert report["mode"] == "ACTIVE"
    assert [item["ref"] for item in report["load"]] == CTO_SELECTION[1:]
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
                            "binding": "governance/projection-bindings/technical-coordination.yaml",
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
    # Admission is resolved against an authority checkout; without one nothing is loaded.
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


# --- operating protocol: the CTO swarm invariants (operator-directed 2026-11-13) ---

SWARM_INVARIANTS = {
    "minimal_operator_pings",
    "swarm_never_pings_operator",
    "frictionless_cto_swarm_channel",
    "operator_approves_merges_only",
    "swarm_publishes_then_stands_down",
    "cto_integrates_and_fixes_surgically",
}


def test_child_launch_puts_reporting_in_the_system_prompt_and_never_a_send_tool() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    rules = " ".join(protocol["child_launch_rules"])
    assert "launch system prompt" in rules
    assert "never instructs" in rules
    briefs = " ".join(protocol["child_brief_must_include"])
    assert "never ask the operator to approve publishing" in briefs


def test_contract_carries_the_swarm_invariants_and_grants_no_permission() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    assert protocol["grants_permission"] is False
    assert SWARM_INVARIANTS <= set(protocol["invariants"])
    assert "cannot be delegated" in protocol["roles"]["cto"]
    briefs = " ".join(protocol["child_brief_must_include"])
    assert "coding-agent mode" in briefs.lower()
    assert "non-shallow" in briefs
    assert "never a cross-session send tool" in briefs
    claude = protocol["transport"]["claude-code"]
    assert claude["cto_to_swarm"] == "mcp__claude-code-remote__send_message"
    assert "list_events" in claude["swarm_to_cto"]
    # Safety notifications are never suppressed by the minimal-ping invariant.
    assert "never suppressed" in protocol["invariants"]["minimal_operator_pings"]


@pytest.mark.parametrize("statuses", ["admitted", "blocked"])
def test_operating_protocol_is_emitted_when_active_or_blocked(
    tmp_path: Path, statuses: str
) -> None:
    cto_mode.request(tmp_path, session_id=SID)
    by_ref = ALL_ADMITTED if statuses == "admitted" else {**ALL_ADMITTED, TC: "BLOCKED"}
    report = cto_mode.evaluate(tmp_path, verify=_verify(by_ref), session_id=SID)
    assert report["mode"] == ("ACTIVE" if statuses == "admitted" else "BLOCKED")
    assert report["operating_protocol"] == cto_mode.load_contract()["operating_protocol"]


def test_operating_protocol_is_not_emitted_when_off(tmp_path: Path) -> None:
    report = cto_mode.evaluate(tmp_path, verify=_verify(ALL_ADMITTED), session_id=SID)
    assert report["mode"] == "OFF"
    assert "operating_protocol" not in report


@pytest.mark.parametrize(
    ("protocol", "reason"),
    [
        ("text", "OPERATING_PROTOCOL_MALFORMED"),
        ({"grants_permission": True, "invariants": {"x": "y"}}, "MUST_GRANT_NO_PERMISSION"),
        ({"invariants": {"x": "y"}}, "MUST_GRANT_NO_PERMISSION"),
        ({"grants_permission": False, "invariants": {}}, "INVARIANTS_EMPTY"),
        ({"grants_permission": False, "invariants": {"x": " "}}, "INVARIANT_MALFORMED"),
    ],
)
def test_malformed_operating_protocol_fails_closed(
    tmp_path: Path, protocol: object, reason: str
) -> None:
    path = _contract(tmp_path, operating_protocol=protocol)
    with pytest.raises(cto_mode.ContractError, match=reason):
        cto_mode.load_contract(path)


# --- canonical child launch prompt (rendered, never hand-written) ---

import projection_mode  # noqa: E402


def test_child_prompt_renders_the_reporting_route_and_names_no_send_tool() -> None:
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "session_cto_x")
    assert "session_cto_x" in text
    assert "{cto_session}" not in text
    for prefix in ("CTO-STATUS:", "CTO-QUESTION:", "CTO-BLOCKER:"):
        assert prefix in text
    assert "send_message" not in text
    assert "never call a cross-session messaging tool" in text
    assert "Never ask the operator to approve publishing" in text
    assert "a shallow clone gives a false ADMITTED_REVISION_NOT_INTEGRATED" in text


def test_child_prompt_cli_prints_plain_text(tmp_path: Path) -> None:
    out = subprocess.run(
        [
            sys.executable,
            str(REPO / "ops/autonomy/cto_mode.py"),
            "child-prompt",
            "--cto-session",
            "session_cto_y",
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.startswith("ROLE: CODING AGENT")
    assert "session_cto_y" in out


def test_child_prompt_requires_a_cto_session() -> None:
    with pytest.raises(cto_mode.ContractError, match="CTO_SESSION_UNRESOLVED"):
        projection_mode.render_child_prompt(cto_mode.load_contract(), " ")


@pytest.mark.parametrize(
    ("template", "reason"),
    [
        ("", "CHILD_SYSTEM_PROMPT_MALFORMED"),
        ("CTO-STATUS: CTO-QUESTION: CTO-BLOCKER: only", "CHILD_SYSTEM_PROMPT_INCOMPLETE"),
        (
            "{cto_session} CTO-STATUS: CTO-QUESTION: CTO-BLOCKER: Never invoke the "
            'l9-coding-agent skill; coding_agent_mode.py" on ACTIVE; CTO-STATUS: stood-down; '
            "report via send_message",
            "CHILD_SYSTEM_PROMPT_NAMES_SEND_TOOL",
        ),
    ],
)
def test_malformed_child_prompt_fails_closed(tmp_path: Path, template: str, reason: str) -> None:
    doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
    doc["operating_protocol"]["child_system_prompt"] = template
    path = tmp_path / "MODE.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    with pytest.raises(cto_mode.ContractError, match=reason):
        cto_mode.load_contract(path)


def test_child_prompt_deploys_agents_with_coding_agent_mode_enabled() -> None:
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "session_cto_z")
    assert 'ops/autonomy/coding_agent_mode.py" on --workspace' in text
    assert "Make NO code change until it reports ACTIVE" in text
    assert "WITHOUT --depth" in text
    protocol = cto_mode.load_contract()["operating_protocol"]
    assert "not counted as deployed until" in " ".join(protocol["child_launch_rules"])
    assert "coding-agent mode is ACTIVE" in " ".join(protocol["check_in"])


def test_child_prompt_without_coding_agent_mode_fails_closed(tmp_path: Path) -> None:
    doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
    doc["operating_protocol"]["child_system_prompt"] = (
        "{cto_session} CTO-STATUS: CTO-QUESTION: CTO-BLOCKER: ACTIVE, start coding now."
    )
    path = tmp_path / "MODE.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    with pytest.raises(cto_mode.ContractError, match="CHILD_SYSTEM_PROMPT_INCOMPLETE"):
        cto_mode.load_contract(path)


# --- complete-protocol validation and per-host continuation (Codex review on #968) ---


@pytest.mark.parametrize(
    "section", ["roles", "pre_launch", "child_brief_must_include", "child_launch_rules", "check_in"]
)
def test_missing_or_mistyped_protocol_section_fails_closed(tmp_path: Path, section: str) -> None:
    for broken in (None, "text", [] if section != "roles" else {}):
        doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
        if broken is None:
            del doc["operating_protocol"][section]
        else:
            doc["operating_protocol"][section] = broken
        path = tmp_path / "MODE.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False))
        with pytest.raises(cto_mode.ContractError, match=f"SECTION_MALFORMED: {section}"):
            cto_mode.load_contract(path)


@pytest.mark.parametrize("host", ["claude-code", "cursor"])
def test_every_host_transport_declares_how_a_stopped_child_is_continued(
    tmp_path: Path, host: str
) -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    assert protocol["transport"][host]["continuation"].strip()
    doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
    del doc["operating_protocol"]["transport"][host]["continuation"]
    path = tmp_path / "MODE.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    with pytest.raises(cto_mode.ContractError, match=f"TRANSPORT_INCOMPLETE: {host}"):
        cto_mode.load_contract(path)


def test_cursor_continuation_is_re_dispatch_not_wakeup() -> None:
    cursor = cto_mode.load_contract()["operating_protocol"]["transport"]["cursor"]
    assert "re-dispatching the same lane" in cursor["continuation"]
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    assert "re-dispatching your lane" in text


def test_swarm_uses_the_coding_agent_mode_and_projection_never_the_skill() -> None:
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    assert "l9.projection/coding-agent-execution@1" in text
    assert "Never invoke the l9-coding-agent skill" in text
    briefs = " ".join(cto_mode.load_contract()["operating_protocol"]["child_brief_must_include"])
    assert "never the l9-coding-agent skill" in briefs


# --- stand-down and CTO-owned integration (operator directive 2026-11-13) ---


def test_agents_stand_down_after_publishing_and_the_cto_integrates_itself() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    invariants = protocol["invariants"]
    assert "stands down" in invariants["swarm_publishes_then_stands_down"]
    assert "never adds scope" in invariants["swarm_publishes_then_stands_down"]
    cto = invariants["cto_integrates_and_fixes_surgically"]
    assert "never through a subagent" in cto and "surgical" in cto
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    assert "Do not subscribe to, watch, remediate or re-test a published PR" in text
    assert "CTO-STATUS: stood-down" in text
