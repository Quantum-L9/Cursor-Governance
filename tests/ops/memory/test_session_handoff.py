"""ops/memory/session_handoff.py — the agent-authored post-publish brief."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.memory import session_handoff as sh


def _brief(**extra: object) -> dict:
    return {
        "schema": sh.HANDOFF_SCHEMA,
        "pr_number": 7,
        "objective": "Ship it",
        "status": "PR open",
        "blocked": [{"item": "payments", "blocker": "no key", "unblock": "add key"}],
        "human_actions": ["rotate the key"],
        **extra,
    }


def test_load_binds_the_brief_to_its_publication(tmp_path: Path) -> None:
    path = tmp_path / sh.HANDOFF_REL
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_brief()), encoding="utf-8")
    assert sh.load(tmp_path, pr_number=7)["objective"] == "Ship it"
    with pytest.raises(sh.HandoffError, match="not this publication"):
        sh.load(tmp_path, pr_number=8)


def test_a_missing_or_malformed_handoff_is_a_handoff_error(tmp_path: Path) -> None:
    with pytest.raises(sh.HandoffError, match="no handoff file"):
        sh.load(tmp_path)
    path = tmp_path / sh.HANDOFF_REL
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(sh.HandoffError, match="not readable JSON"):
        sh.load(tmp_path)


def test_required_fields_and_schema_are_enforced() -> None:
    with pytest.raises(sh.HandoffError, match="schema"):
        sh.normalize({**_brief(), "schema": "v0"})
    with pytest.raises(sh.HandoffError, match="status"):
        sh.normalize({**_brief(), "status": ""})
    with pytest.raises(sh.HandoffError, match="must be a list"):
        sh.normalize({**_brief(), "risks": "one"})


def test_string_items_are_accepted_for_structured_sections() -> None:
    brief = sh.normalize(_brief())
    assert brief["human_actions"] == [{"action": "rotate the key"}]


def test_pr_number_must_be_a_positive_integer() -> None:
    for bad in (None, "7", 0, True):
        with pytest.raises(sh.HandoffError, match="pr_number"):
            sh.normalize({**_brief(), "pr_number": bad})


def test_unknown_sections_are_refused_and_misplaced_ones_are_named() -> None:
    with pytest.raises(sh.HandoffError, match="unknown section"):
        sh.normalize({**_brief(), "summary": "x"})
    with pytest.raises(
        sh.HandoffError, match="governance_friction belongs in .l9/memory/governance-handoff.json"
    ):
        sh.normalize({**_brief(), "governance_friction": [{"item": "budget tight"}]})


def test_one_request_carries_only_the_missing_handoffs() -> None:
    rel = str(sh.HANDOFF_REL)
    gov = (".l9/memory/governance-handoff.json", "l9.governance_handoff.v1", {"pr_number": 7})
    both = sh.request_reason(
        pr_label="Org/repo#7",
        pr_number=7,
        missing={rel: "absent", gov[0]: "absent"},
        governance=gov,
    )
    for key in ("objective", "blocked", "human_actions", '"pr_number": 7', gov[1]):
        assert key in both
    only_repo = sh.request_reason(
        pr_label="Org/repo#7", pr_number=7, missing={rel: "absent"}, governance=gov
    )
    assert gov[1] not in only_repo and sh.HANDOFF_SCHEMA in only_repo
    only_gov = sh.request_reason(
        pr_label="Org/repo#7", pr_number=7, missing={gov[0]: "absent"}, governance=gov
    )
    assert gov[1] in only_gov and f"1) {rel}" not in only_gov


def test_the_example_is_itself_a_valid_brief() -> None:
    assert sh.normalize(sh.example(7), pr_number=7)["objective"]
