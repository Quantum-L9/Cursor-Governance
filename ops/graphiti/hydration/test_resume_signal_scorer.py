"""Acceptance tests for resume keep/drop (harvest c-resume-episode-threshold)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.graphiti.hydration import compile_session_packet as comp  # noqa: E402
from ops.graphiti.hydration.archive_transcript import build_document, extract_turns  # noqa: E402
from ops.graphiti.hydration.resume_signal_scorer import (  # noqa: E402
    score_resume_signals,
    should_persist_derived_episode,
    signals_from_close,
)


def test_empty_signals_drop_derived_episode():
    signals = signals_from_close(transcript="", reason="idle", promotion_decisions=[])
    assert signals["action_count"] == 0
    assert signals["file_count"] == 0
    assert signals["decision_count"] == 0
    assert should_persist_derived_episode(signals) is False


def test_high_signal_keeps_derived_episode():
    signals = {
        "action_count": 3,
        "file_count": 5,
        "decision_count": 2,
        "message_count": 10,
        "code_present": True,
        "completed": True,
    }
    assert score_resume_signals(signals) >= 0.99
    assert should_persist_derived_episode(signals) is True


def test_scorer_exception_fail_open():
    class _Boom(dict):
        def get(self, *args, **kwargs):
            raise RuntimeError("scorer boom")

    assert should_persist_derived_episode(_Boom()) is True


def test_compile_packet_still_emits_when_derived_would_drop(monkeypatch, tmp_path):
    monkeypatch.setattr(
        comp,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(comp, "_search_facts", lambda *a, **k: [])
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="low-signal", agent_id="cursor"
    )
    assert packet["next_action_contract"]["next_action"]
    assert "hydrate_stats" in packet
    low = signals_from_close(transcript="", reason="idle")
    assert should_persist_derived_episode(low) is False


def test_archive_transcript_still_writes_low_signal_session(tmp_path):
    import json

    path = tmp_path / "low.jsonl"
    path.write_text(
        json.dumps(
            {
                "role": "user",
                "message": {"content": [{"type": "text", "text": "<user_query>ok</user_query>"}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    turns = extract_turns(path)
    doc = build_document(
        conversation_id="low-signal",
        source_path=path,
        project_dir=str(tmp_path),
        turns=turns,
        host="test-host",
    )
    assert doc["schema"] == "l9-chat-transcript/v1"
    assert doc["turn_count"] == 1
    assert turns[0]["text"] == "ok"
    low = signals_from_close(transcript="ok", reason="idle")
    assert should_persist_derived_episode(low) is False
