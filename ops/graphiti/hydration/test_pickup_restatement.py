"""A canonical no-hit is an empty task state, never a fabricated PICKUP (stage C4)."""

from __future__ import annotations

from ops.graphiti.hydration import compile_session_packet as comp
from ops.memory import hydration as hyd
from ops.memory.namespace_context import NamespaceContext


def test_canonical_no_hit_reports_empty_task_state(monkeypatch, tmp_path):
    context = NamespaceContext(
        workspace="/w",
        git_root="/w",
        repository_identity="Quantum-L9/Cursor-Governance",
        write_namespace_hint="cursor-governance",
        read_namespace_hints=("cursor-governance",),
        method="registry",
    )
    monkeypatch.setenv("L9_MEMORY_SESSION_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        comp,
        "canonical_hydrate",
        lambda *a, **k: hyd.CanonicalHydration(
            status="NO_HITS",
            namespace_context=context,
            requested_namespaces=("cursor-governance",),
            repository_state_digest="a" * 40,
            task_signature="sig",
            calls=3,
        ),
    )
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-restatement", agent_id="cursor"
    )
    assert packet["hydrate_stats"]["raw_facts"] == 0
    assert packet["hydrate_stats"]["facts_returned"] == 0
    assert packet["hydrate_stats"]["pickup_parsed"] is False
    assert packet["fact_previews"] == []
    assert packet["degraded"] is False
    assert "start from the user request" in packet["active_objective"]
    ctx = comp.format_additional_context(packet)
    assert "facts_returned=0" in ctx
    assert "continuation: none" in ctx
