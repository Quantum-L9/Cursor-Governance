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


def _clear_host_session(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in cto_mode.SESSION_ENVS:
        monkeypatch.delenv(name, raising=False)


def test_unresolvable_session_never_activates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_host_session(monkeypatch)
    with pytest.raises(cto_mode.ContractError, match="SESSION_UNRESOLVED"):
        cto_mode.request(tmp_path)
    cto_mode.request(tmp_path, session_id=SID)
    report = cto_mode.evaluate(tmp_path, verify=_verify({TC: cto_mode.ADMITTED}))
    assert report["mode"] == "OFF"
    assert report["reason"] == "SESSION_UNRESOLVED"


def test_session_resolves_from_host_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_host_session(monkeypatch)
    assert cto_mode.resolve_session_id() is None
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "default")
    assert cto_mode.resolve_session_id() is None
    monkeypatch.setenv("CURSOR_CONVERSATION_ID", "conv-1")
    assert cto_mode.resolve_session_id() == "conv-1"
    monkeypatch.setenv("CLAUDE_CODE_REMOTE_SESSION_ID", "cse-1")
    assert cto_mode.resolve_session_id() == "conv-1"
    monkeypatch.delenv("CURSOR_CONVERSATION_ID")
    assert cto_mode.resolve_session_id() == "cse-1"
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "cc-1")
    assert cto_mode.resolve_session_id() == "cc-1"
    monkeypatch.setenv("CURSOR_SESSION_ID", "cur-1")
    assert cto_mode.resolve_session_id() == "cur-1"
    assert cto_mode.resolve_session_id("explicit") == "explicit"


@pytest.mark.parametrize(
    "script",
    ["cto_mode.py", "architect_mode.py", "coding_agent_mode.py"],
)
def test_cli_on_binds_the_host_conversation_without_a_session_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str
) -> None:
    monkeypatch.setenv("CURSOR_CONVERSATION_ID", "conv-auto")
    on = subprocess.run(
        [
            sys.executable,
            str(REPO / "ops/autonomy" / script),
            "on",
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(on.stdout)
    assert on.returncode == 3, on.stdout + on.stderr
    assert report["mode"] == "BLOCKED"
    assert "SESSION_UNRESOLVED" not in on.stdout
    state = json.loads(next(tmp_path.glob(".l9/*-mode/session.json")).read_text())
    assert state["session_id"] == "conv-auto"


# --- operating protocol: the CTO swarm invariants (operator-directed 2026-11-13) ---

SWARM_INVARIANTS = {
    "minimal_operator_pings",
    "swarm_never_pings_operator",
    "frictionless_cto_swarm_channel",
    "operator_approves_merges_only",
    "publisher_owns_its_pr",
    "cto_integrates_never_remediates",
    "fixed_reusable_pool",
    "repositories_attached_at_launch",
    "every_launched_session_reports_by_transcript",
    "scope_corrections_interrupt",
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
    assert "a shallow checkout gives a false ADMITTED_REVISION_NOT_INTEGRATED" in text


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
            'l9-coding-agent skill; coding_agent_mode.py" on ACTIVE; CTO-STATUS: ready-to-merge; '
            "CTO-STATUS: idle; CTO ASSIGN; never call add_repo for it; Attach your primary "
            "repository (access push) and Quantum-L9/Cursor-Governance; "
            "CTO TRANSFER <new session id>; You own every PR you published until it merges; "
            'session_role.py" register-child --cto-session {cto_session} PR_REMEDIATE=0; '
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
    assert "rev-parse --is-shallow-repository prints false" in text
    assert "HEAD must equal its origin/main" in text
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


def test_cursor_registers_from_the_local_checkout_without_add_repo() -> None:
    """Copilot on #1020: the shared prompt must not require Claude cloud attachment."""
    protocol = cto_mode.load_contract()["operating_protocol"]
    invariant = protocol["invariants"]["repositories_attached_at_launch"]
    assert "On Cursor" in invariant
    assert "does not call add_repo" in invariant
    brief = " ".join(protocol["child_brief_must_include"])
    assert "skip add_repo and register_repo_root" in brief
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    assert "On Cursor the workspace is already a local checkout" in text
    assert "do not call add_repo or register_repo_root" in text
    assert text.index("L9_AUTHORITY_ROOT") < text.index("L9_AUTHORITY_MANAGED_ROOT")


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


# --- protocol v2: fixed pool, publisher-owned PRs, CTO never remediates (2026-11-16) ---


def test_publisher_owns_its_pr_and_the_cto_never_remediates() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    assert protocol["version"] == 2
    invariants = protocol["invariants"]
    owner = invariants["publisher_owns_its_pr"]
    assert "ready to merge" in owner
    assert "never merges" in owner.lower()
    assert "never adds scope to a running lane" in owner
    cto = invariants["cto_integrates_never_remediates"]
    assert "never through a subagent" in cto
    assert "never pushes to a lane's branch" in cto
    assert "never remediates" in cto
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    assert "OWN YOUR PR" in text
    assert "CTO-STATUS: ready-to-merge" in text
    assert "CTO-STATUS: idle" in text
    assert "never rebase or force-push" in text
    assert "Do not subscribe to" not in text
    check_in = " ".join(protocol["check_in"])
    assert "CTO REMEDIATE" in check_in
    assert "Never push to a lane's branch" in check_in
    assert "yourself, surgically" not in check_in


def test_pool_is_capped_at_five_and_reused_never_relaunched() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    pool = protocol["invariants"]["fixed_reusable_pool"]
    assert "at most five" in pool
    assert "no session is launched after bootstrap" in pool
    assert "at most five" in protocol["roles"]["swarm"]
    assert "launch nothing" in " ".join(protocol["check_in"])
    assert any("at most five" in rule for rule in protocol["child_launch_rules"])
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    # ASSIGN is the only widening verb, and only for an idle agent.
    assert "CTO ASSIGN <lane-id>" in text
    assert "valid only while you are idle" in text
    assert "They narrow or clarify scope; they never widen it" in text


def test_dot_github_is_the_source_and_lane_repos_are_attached_before_registration() -> None:
    """Evidence 2026-11-17: the environment repository list attaches nothing to a child."""
    protocol = cto_mode.load_contract()["operating_protocol"]
    launch = protocol["transport"]["claude-code"]["child_launch"]
    assert "source_url https://github.com/Quantum-L9/.github" in launch
    assert "source_revision" not in launch
    invariant = protocol["invariants"]["repositories_attached_at_launch"]
    assert "does not attach" in invariant
    assert "never mid-campaign" in invariant
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    assert "Attach your primary repository (access push) and Quantum-L9/Cursor-Governance" in text
    assert "never call add_repo for it" in text
    assert "never mid-lane" in text
    assert "never work around it with a raw push" in text


def test_every_launched_session_gets_the_rendered_prompt() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    rule = protocol["invariants"]["every_launched_session_reports_by_transcript"]
    assert "operator drives directly" in rule
    assert "never asks for, or invites, a reply" in rule
    assert any("including one the operator will drive" in r for r in protocol["child_launch_rules"])


def test_scope_corrections_interrupt_and_handoff_keeps_the_pool() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    assert protocol["transport"]["claude-code"]["scope_correction_priority"] == "now"
    assert "before it publishes" in protocol["invariants"]["scope_corrections_interrupt"]
    handoff = " ".join(protocol["handoff"])
    assert "adopts the pool" in handoff
    assert "nothing is relaunched" in handoff


def test_cursor_slots_continue_by_re_dispatch_within_the_five_slot_cap() -> None:
    """Copilot on #1004: a Cursor Task ends, so reuse is per logical slot, not per session."""
    pool = cto_mode.load_contract()["operating_protocol"]["invariants"]["fixed_reusable_pool"]
    assert "five logical pool" in pool
    assert "re-dispatching it as a new Task" in pool
    assert "not a new pool member" in pool


def test_owner_keeps_a_repair_path_after_taking_another_lane() -> None:
    """Copilot on #1004: a late finding on a ready lane goes back to its owner."""
    protocol = cto_mode.load_contract()["operating_protocol"]
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s")
    assert "You own every PR you published until it merges" in text
    assert "CTO REMEDIATE <pr> restores that PR's lane scope" in text
    assert "ready to merge but not yet merged does not make you non-idle" in text
    assert "after that agent has taken another lane" in " ".join(protocol["check_in"])


def test_coordinator_transfer_is_explicit_and_re_registers_the_role() -> None:
    """Copilot on #1004: a successor CTO needs a defined way to take the pool."""
    protocol = cto_mode.load_contract()["operating_protocol"]
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "s_old")
    assert "until it sends CTO TRANSFER <new session id>" in text
    assert "re-run the ROLE REGISTRATION command below with --cto-session <new session id>" in text
    assert "a TRANSFER from any other session is ignored" in text
    handoff = " ".join(protocol["handoff"])
    assert "CTO TRANSFER" in handoff
    assert "register-child --cto-session" in handoff
    assert "never changes who the coordinator is" in handoff


def test_missing_handoff_section_fails_closed(tmp_path: Path) -> None:
    doc = yaml.safe_load(cto_mode.MODE_CONTRACT.read_text())
    del doc["operating_protocol"]["handoff"]
    path = tmp_path / "MODE.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    with pytest.raises(cto_mode.ContractError, match="SECTION_MALFORMED: handoff"):
        cto_mode.load_contract(path)


def test_cto_to_swarm_transport_is_pre_approved_in_the_claude_settings_template() -> None:
    """Invariant frictionless_cto_swarm_channel: the CTO's send tool never waits on the operator.

    The tool the contract names for CTO -> swarm messages on Claude Code must be
    allowed outright in the settings every Claude Code session is projected from,
    and never routed back to a prompt by an ask or deny rule.
    """
    protocol = cto_mode.load_contract()["operating_protocol"]
    tool = protocol["transport"]["claude-code"]["cto_to_swarm"]
    template = json.loads(
        (REPO / "environment/agents/adapters/claude-code/settings.template.json").read_text()
    )
    permissions = template["permissions"]
    assert tool in permissions["allow"]
    assert tool not in permissions.get("ask", [])
    assert tool not in permissions.get("deny", [])


# --- child launch: .github as start source, managed authority root (2026-11-17) ---

FROZEN_PREFIXES = (
    '"$HOME/.cursor-governance/.venv/bin/python" '
    '"$HOME/.cursor-governance/ops/autonomy/session_role.py" register-child',
    '"$HOME/.cursor-governance/.venv/bin/python" '
    '"$HOME/.cursor-governance/ops/autonomy/coding_agent_mode.py" on',
)
GITHUB_SOURCE = "https://github.com/Quantum-L9/.github"


def test_child_launch_names_the_dot_github_source() -> None:
    protocol = cto_mode.load_contract()["operating_protocol"]
    claude = protocol["transport"]["claude-code"]
    assert f"source_url {GITHUB_SOURCE}" in claude["child_launch"]
    assert claude["child_session"]["source_url"] == GITHUB_SOURCE
    rules = " ".join(protocol["child_launch_rules"])
    assert GITHUB_SOURCE in rules
    for reason in ("private", "dot-named", "add_repo refuses", "fixed at"):
        assert reason in rules
    assert "ff.sh --ssot" in rules
    assert "launch-spec" in rules


def test_child_prompt_never_clones_dot_github_and_keeps_the_frozen_prefixes() -> None:
    text = projection_mode.render_child_prompt(cto_mode.load_contract(), "session_cto_f")
    assert "clone Quantum-L9/.github" not in text
    assert "WITHOUT --depth" not in text
    assert "never clone, branch or push it" in text
    for prefix in FROZEN_PREFIXES:
        assert prefix in text
    assert "--authority-root <resolved>" in text
    assert "L9_AUTHORITY_ROOT" in text
    assert "L9_AUTHORITY_MANAGED_ROOT" in text
    assert "coding_projection_status.py" in text
    assert "missing default path is not by itself a CTO-BLOCKER" in text
    assert "ensure_authority_checkout.sh" in text
    # Attaching repositories precedes role registration.
    assert text.index("REPOSITORIES (precondition of role registration") < text.index(
        "FIRST ACTION, ROLE REGISTRATION"
    )
    assert 'ff.sh" --ssot' in text
    # A child's only source is Quantum-L9/.github, so Setup starts DEGRADED with no
    # governance clone; the prompt must name the one materialize command the
    # Setup stub's user-scope rule allows, ahead of the ff.sh catch-up.
    materialize = 'bash "$HOME/.l9/bin/l9-materialize-governance"'
    assert materialize in text
    assert text.index(materialize) < text.index('ff.sh" --ssot')
    template = cto_mode.load_contract()["operating_protocol"]["child_system_prompt"]
    assert template.count("{") == template.count("{cto_session}")


def test_launch_spec_shape() -> None:
    spec = projection_mode.build_launch_spec(
        cto_mode.load_contract(),
        "session_cto_l",
        ["acme/lane", "ACME/lane"],
        title="Lane A",
        tags=["lane:a"],
    )
    assert spec["schema"] == "l9.cto-child-launch-spec/v1"
    assert spec["grants_permission"] is False
    create = spec["create_session"]
    assert create["source_url"] == GITHUB_SOURCE
    assert create["permission_mode"] == "auto"
    assert create["tags"] == ["cto:session_cto_l", "lane:a"]
    assert create["title"] == "Lane A"
    assert create["append_system_prompt"] == projection_mode.render_child_prompt(
        cto_mode.load_contract(), "session_cto_l"
    )
    assert "send_message" not in json.dumps(spec)
    assert spec["add_repo"] == [
        {"owner": "acme", "repo": "lane", "access": "push"},
        {"owner": "Quantum-L9", "repo": "Cursor-Governance", "access": "read"},
    ]


def test_launch_spec_governance_lane_repo_is_push_once() -> None:
    spec = projection_mode.build_launch_spec(
        cto_mode.load_contract(), "s", ["Quantum-L9/Cursor-Governance"]
    )
    assert spec["add_repo"] == [
        {"owner": "Quantum-L9", "repo": "Cursor-Governance", "access": "push"}
    ]
    assert "title" not in spec["create_session"]


@pytest.mark.parametrize(
    ("lanes", "reason"),
    [
        ([], "LANE_REPO_REQUIRED"),
        (["no-slash"], "LANE_REPO_MALFORMED"),
        (["a/b/c"], "LANE_REPO_MALFORMED"),
        (["Quantum-L9/.github"], "LANE_REPO_IS_SESSION_SOURCE"),
    ],
)
def test_launch_spec_rejects_bad_lane_repos(lanes: list[str], reason: str) -> None:
    with pytest.raises(cto_mode.ContractError, match=reason):
        projection_mode.build_launch_spec(cto_mode.load_contract(), "s", lanes)


def test_launch_spec_without_declared_child_session_fails_closed() -> None:
    contract = cto_mode.load_contract()
    del contract["operating_protocol"]["transport"]["claude-code"]["child_session"]
    with pytest.raises(cto_mode.ContractError, match="CHILD_SESSION_UNDECLARED"):
        projection_mode.build_launch_spec(contract, "s", ["acme/lane"])


def test_launch_spec_cli_prints_json(tmp_path: Path) -> None:
    out = subprocess.run(
        [
            sys.executable,
            str(REPO / "ops/autonomy/cto_mode.py"),
            "launch-spec",
            "--cto-session",
            "session_cto_c",
            "--lane-repo",
            "acme/lane",
            "--tag",
            "lane:x",
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    spec = json.loads(out)
    assert spec["create_session"]["source_url"] == GITHUB_SOURCE
    assert "cto:session_cto_c" in spec["create_session"]["tags"]
    assert not (tmp_path / ".l9").exists()


@pytest.mark.parametrize("argv", [[], ["--cto-session", "s"], ["--lane-repo", "a/b"]])
def test_launch_spec_cli_requires_session_and_lane(argv: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "ops/autonomy/cto_mode.py"), "launch-spec", *argv],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


@pytest.mark.parametrize("module", ["architect_mode.py", "coding_agent_mode.py"])
def test_launch_spec_is_cto_only(module: str) -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "ops/autonomy" / module), "launch-spec"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "invalid choice: 'launch-spec'" in result.stderr
