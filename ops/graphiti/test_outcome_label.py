"""Acceptance tests for implicit outcome labels (harvest c-implicit-outcome-label)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from outcome_label import label_for, load_outcome_map, write_outcome_label  # noqa: E402

PAIRS = (
    ("WARN_AND_LOG", "edited_file", "CORRECT"),
    ("WARN_AND_LOG", "said_fine", "TOO_STRICT"),
    ("BLOCK_OR_REQUIRE_REVIEW", "added_header", "CORRECT"),
    ("BLOCK_OR_REQUIRE_REVIEW", "overrode", "TOO_STRICT"),
    ("LOG_ONLY", "error_occurred", "TOO_LENIENT"),
    ("LOG_ONLY", "no_issues", "CORRECT"),
)


def test_map_has_exactly_six_pairs():
    assert len(load_outcome_map()) == 6


@pytest.mark.parametrize(("action", "feedback", "expected"), PAIRS)
def test_declared_pairs_write_lesson(action, feedback, expected):
    captured: list[dict] = []

    def _write(payload: dict) -> dict:
        captured.append(payload)
        return {"ok": True}

    result = write_outcome_label(
        decision_episode_id="ep-decision-1",
        action=action,
        feedback=feedback,
        agent_id="cursor",
        write_fn=_write,
    )
    assert result is not None
    assert result["label"] == expected
    assert result["kind"] == "lesson"
    assert len(captured) == 1
    assert captured[0]["kind"] == "lesson"
    assert captured[0]["agent_id"] == "cursor"
    assert captured[0]["decision_episode_id"] == "ep-decision-1"
    assert expected in captured[0]["episode_body"]


def test_unknown_pair_is_noop():
    calls: list[dict] = []
    result = write_outcome_label(
        decision_episode_id="ep-decision-1",
        action="WARN_AND_LOG",
        feedback="shrugged",
        agent_id="cursor",
        write_fn=lambda p: calls.append(p),
    )
    assert result is None
    assert calls == []
    assert label_for("WARN_AND_LOG", "shrugged") is None


def test_missing_decision_episode_id_fails_closed():
    with pytest.raises(ValueError, match="decision_episode_id"):
        write_outcome_label(
            decision_episode_id="  ",
            action="WARN_AND_LOG",
            feedback="edited_file",
            agent_id="cursor",
            write_fn=lambda p: p,
        )


def test_missing_agent_id_fails_closed():
    with pytest.raises(ValueError, match="agent_id"):
        write_outcome_label(
            decision_episode_id="ep-decision-1",
            action="WARN_AND_LOG",
            feedback="edited_file",
            agent_id="",
            write_fn=lambda p: p,
        )


def test_does_not_import_archive():
    imports = [
        line
        for line in Path(__file__)
        .resolve()
        .parent.joinpath("outcome_label.py")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.lstrip().startswith(("import ", "from "))
    ]
    blob = "\n".join(imports)
    assert "archived" not in blob
    assert "feedback_collector" not in blob
    assert "rule-registry" not in blob
    assert "intelligence" not in blob
