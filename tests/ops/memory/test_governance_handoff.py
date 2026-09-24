"""ops/memory/governance_handoff.py — the post-publish governance-only brief."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.memory import governance_handoff as gh


def _brief(**extra: object) -> dict:
    return {
        "schema": gh.GOVERNANCE_SCHEMA,
        "pr_number": 7,
        "environment_friction": [{"item": "cold start", "detail": "27s", "impact": "budget"}],
        "blockers": [{"item": "push", "blocker": "gate", "unblock": "open PR first"}],
        "degraded_bootstrap": ["memory_mcp"],
        **extra,
    }


def test_load_binds_the_brief_to_its_publication(tmp_path: Path) -> None:
    path = tmp_path / gh.GOVERNANCE_REL
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_brief()), encoding="utf-8")
    brief = gh.load(tmp_path, pr_number=7)
    assert brief["degraded_bootstrap"] == [{"component": "memory_mcp"}]
    assert brief["workarounds"] == [] and brief["governance_actions"] == []
    with pytest.raises(gh.HandoffError, match="not this publication"):
        gh.load(tmp_path, pr_number=8)


def test_missing_and_malformed_files_are_handoff_errors(tmp_path: Path) -> None:
    with pytest.raises(gh.HandoffError, match="no governance handoff file"):
        gh.load(tmp_path)
    path = tmp_path / gh.GOVERNANCE_REL
    path.parent.mkdir(parents=True)
    path.write_text("[", encoding="utf-8")
    with pytest.raises(gh.HandoffError, match="not readable JSON"):
        gh.load(tmp_path)


def test_repository_sections_are_refused_and_named() -> None:
    with pytest.raises(gh.HandoffError, match="decisions belongs in .l9/memory/handoff.json"):
        gh.normalize(_brief(decisions=[{"decision": "x"}]))
    with pytest.raises(gh.HandoffError, match="schema"):
        gh.normalize(_brief(schema="l9.session_handoff.v1"))


def test_an_all_empty_brief_is_empty() -> None:
    assert gh.is_empty(gh.normalize({"schema": gh.GOVERNANCE_SCHEMA, "pr_number": 7}))
    assert not gh.is_empty(gh.normalize(_brief()))


def test_the_cap_is_enforced() -> None:
    huge = _brief(environment_friction=[{"item": "x" * 1100}] * 40)
    with pytest.raises(gh.HandoffError, match="cap"):
        gh.normalize(huge)


def test_the_record_labels_observed_receipts_and_fits_the_surface_cap() -> None:
    text = gh.record_text(
        gh.normalize(_brief()),
        {"bootstrap_receipt": {"state": "DEGRADED"}},
        repository="Org/repo",
        pr_label="Org/repo#7",
        session_id="s1",
    )
    assert "Governance handoff from Org/repo (Org/repo#7)" in text
    assert "cold start — detail: 27s; impact: budget" in text
    assert "observed by the hook (verbatim from receipts, not agent-authored):" in text
    assert "workarounds: none" in text
    missing = gh.record_text(
        None,
        {"hook_skips_this_session": ["x" * 20000]},
        repository="O/r",
        pr_label="O/r#1",
        session_id="s",
    )
    assert "agent governance handoff: NOT CAPTURED" in missing
    assert len(missing.encode("utf-8")) <= gh.MAX_RECORD_BYTES
    assert missing.endswith("[truncated to the 16 KiB record cap]")


def test_the_example_is_itself_a_valid_brief() -> None:
    brief = gh.normalize(gh.example(7), pr_number=7)
    assert all(brief[key] for key in gh.SECTIONS)


def test_the_record_names_the_writing_agent_never_a_literal() -> None:
    text = gh.record_text(
        gh.normalize(_brief()),
        {},
        repository="Org/repo",
        pr_label="Org/repo#7",
        session_id="s1",
        agent_id="claude-code-mobile",
    )
    assert "agent claude-code-mobile." in text.splitlines()[0]
    assert "agent claude-code." not in text
