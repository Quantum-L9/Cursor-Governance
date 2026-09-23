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
        "governance_friction": [{"item": "budget tight"}],
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


def test_friction_is_split_out_of_the_repository_brief() -> None:
    repo, friction = sh.split(sh.normalize(_brief()))
    assert sh.FRICTION not in repo
    assert friction == [{"item": "budget tight"}]
    text = sh.friction_text(friction, repository="Org/repo", pr="Org/repo#7")
    assert "Org/repo#7" in text and "- budget tight" in text


def test_the_request_carries_the_full_shape_for_this_publication() -> None:
    reason = sh.request_reason(pr_label="Org/repo#7", pr_number=7)
    for key in ("objective", "blocked", "human_actions", "governance_friction", '"pr_number": 7'):
        assert key in reason
