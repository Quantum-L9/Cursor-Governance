"""PICKUP-only hydrate facts must not count as task-bearing memory."""

from __future__ import annotations

from ops.graphiti.hydration import compile_session_packet as comp


def test_pickup_restatement_counts_as_empty_task_state(monkeypatch, tmp_path):
    monkeypatch.setattr(
        comp,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(
        comp,
        "_search_facts",
        lambda *a, **k: [
            {"fact": "Claude-Code Agent requested to continue from the latest Graphiti PICKUP."},
            {"fact": "The next action involves resuming from the latest Graphiti PICKUP."},
        ],
    )
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-restatement", agent_id="cursor"
    )
    assert packet["hydrate_stats"]["raw_facts"] == 2
    assert packet["hydrate_stats"]["facts_returned"] == 0
    assert packet["hydrate_stats"]["empty_task_state"] is True
    assert packet["fact_previews"] == []
    ctx = comp.format_additional_context(packet)
    assert "facts_returned=0" in ctx
