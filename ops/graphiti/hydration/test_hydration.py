"""Unit tests for hydrate/close pipeline (no live Graphiti required)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GRAPHITI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GRAPHITI))

from episode_contract import EpisodeContract  # noqa: E402

from ops.graphiti.hydration import close_session as cs  # noqa: E402
from ops.graphiti.hydration import compile_session_packet as comp  # noqa: E402
from ops.graphiti.hydration import identity as ident  # noqa: E402
from ops.graphiti.hydration import transcript as tr  # noqa: E402


def test_identity_requires_agent_id(monkeypatch):
    monkeypatch.delenv("L9_MEMORY_AGENT_ID", raising=False)
    with pytest.raises(ident.IdentityError):
        ident.resolve_write_identity(surface="cursor")


def test_identity_cursor_stamp():
    got = ident.resolve_write_identity(explicit_agent_id="cursor", surface="cursor")
    assert got["agent_id"] == "cursor"
    assert "agent=cursor;kind=lesson" == ident.stamp_source_description("cursor", "lesson")


def test_identity_claude_cannot_impersonate_cursor():
    with pytest.raises(ident.IdentityError):
        ident.resolve_write_identity(
            explicit_agent_id="cursor",
            explicit_user_id="cursor_agent",
            surface="claude-code",
        )


def test_episode_contract_requires_agent_id():
    with pytest.raises(Exception):
        EpisodeContract(
            name="test-episode",
            episode_body="hello world body",
            source="text",
            source_description="x",
            reference_time=datetime.now(UTC),
            group_id="cursor-governance",
            agent_id="",
        )


def test_transcript_cap_and_redact(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps({"role": "user", "content": "email me at a@b.com please"})
        + "\n"
        + json.dumps({"role": "assistant", "content": "ok"})
        + "\n",
        encoding="utf-8",
    )
    text, source = tr.load_transcript_excerpt(transcript_path=str(path), max_chars=500)
    assert source == "stdin_transcript_path"
    assert "a@b.com" not in text
    assert "EMAIL_REDACTED" in text


def test_compile_packet_fail_open(monkeypatch, tmp_path):
    monkeypatch.setattr(
        comp,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(comp, "_search_facts", lambda *a, **k: [])
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-1", agent_id="cursor"
    )
    assert packet["agent_id"] == "cursor"
    assert packet["next_action_contract"]["next_action"]
    assert "hydrate_stats" in packet
    assert packet["hydrate_stats"]["facts_returned"] == 0
    assert packet["hydrate_stats"]["search_queries_used"] >= 1
    ctx = comp.format_additional_context(packet)
    assert "next=" in ctx
    assert "facts_returned=" in ctx
    assert "memory-bank" not in ctx
    assert "hydrate_stats" in ctx


def test_compile_packet_with_pickup(monkeypatch, tmp_path):
    monkeypatch.setattr(
        comp,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(
        comp,
        "_search_facts",
        lambda *a, **k: [
            {
                "fact": json.dumps(
                    {
                        "type": "PICKUP",
                        "active_objective": "Ship hydrate pipeline",
                        "next_action": "Run unit tests then install hooks",
                    }
                )
            }
        ],
    )
    packet = comp.compile_session_packet(
        project_dir=tmp_path, conversation_id="sess-2", agent_id="cursor"
    )
    assert packet["active_objective"] == "Ship hydrate pipeline"
    assert "Run unit tests" in packet["next_action_contract"]["next_action"]
    assert packet["hydrate_stats"]["facts_returned"] == 1
    assert packet["hydrate_stats"]["pickup_parsed"] is True
    ctx = comp.format_additional_context(packet)
    assert "next=" in ctx
    assert "facts_returned=1" in ctx
    assert "pickup_parsed=yes" in ctx
    assert "memory-bank" not in ctx
    assert '"hydrate_stats"' in ctx


def test_extract_pickup_pipe_line():
    facts = [
        {
            "fact": (
                "PICKUP|objective=Validate hydrate close|next=Re-run sessionStart|"
                "agent=cursor|session=abc"
            )
        }
    ]
    got = comp._extract_pickup(facts)
    assert got["active_objective"] == "Validate hydrate close"
    assert got["next_action"] == "Re-run sessionStart"


def test_extract_pickup_graphiti_paraphrase():
    facts = [
        {
            "fact": (
                "The objective is to continue work in Cursor-Governance by "
                "resuming from the latest Graphiti PICKUP."
            )
        }
    ]
    got = comp._extract_pickup(facts)
    assert "Cursor-Governance" in got["active_objective"]
    assert "resuming from" in got["next_action"].lower()


def test_phase_a_without_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("MEMORY_PHASE_B_RESOLVE_SM", "0")
    monkeypatch.delenv("MEMORY_DISTILL_S3_BUCKET", raising=False)
    monkeypatch.setattr(
        cs,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: finish the PR", "test"))
    writes: list[dict] = []

    def fake_write(body, **kwargs):
        writes.append({"body": body, **kwargs})
        return {"written": True, "dry_run": True, "kind": kwargs["kind"]}

    monkeypatch.setattr(cs, "_write_kind", fake_write)
    monkeypatch.setattr(cs, "already_closed", lambda *a, **k: False)
    monkeypatch.setattr(cs, "write_receipt", lambda *a, **k: None)

    # Prevent graphiti_env_loader from re-injecting OPENAI_API_KEY mid-close.
    import graphiti_memory_client as gmc

    monkeypatch.setattr(gmc, "load_env", lambda: None)

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-1",
        reason="user_close",
        agent_id="cursor",
        dry_run=True,
    )
    assert report["phase_a"] is True
    assert report["phase_b"] is False
    assert any(w.get("kind") == "pickup_context" for w in writes)
    assert any("openai_key" in w for w in report["warnings"])


def test_phase_b_success_with_mocked_transport(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("MEMORY_DISTILL_S3_BUCKET", raising=False)
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "0")
    monkeypatch.setattr(
        cs,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: ship phase b", "test"))
    monkeypatch.setattr(cs, "already_closed", lambda *a, **k: False)
    monkeypatch.setattr(cs, "write_receipt", lambda *a, **k: None)
    monkeypatch.setattr(
        cs,
        "_write_kind",
        lambda body, **kwargs: {"written": True, "kind": kwargs["kind"]},
    )
    import graphiti_memory_client as gmc

    monkeypatch.setattr(gmc, "load_env", lambda: None)

    packet = {
        "packet_id": "abcdef0123456789",
        "session_id": "close-b",
        "promotion_decisions": [
            {
                "kind": "lesson",
                "body": "Use fixed-host OpenAI helper for Phase B.",
                "decision": "promote",
                "score": 0.9,
            }
        ],
        "pickup": {
            "active_objective": "Finish Phase B restore",
            "next_action": "Open PR after pr-check",
            "context_slice": "phase b",
            "blockers": [],
        },
        "do_not_promote": [],
    }
    monkeypatch.setattr(cs, "_distill_signal_packet", lambda **k: (packet, ""))

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-b",
        agent_id="cursor",
        dry_run=True,
    )
    assert report["phase_a"] is True
    assert report["phase_b"] is True
    assert report["receipt"]["phase_b"] is True
    assert report.get("promoted") == 1


def test_enqueue_fail_loud(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMORY_PHASE_B", "0")
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "1")
    monkeypatch.setenv("MEMORY_DISTILL_S3_BUCKET", "l9-test-distill")
    monkeypatch.setattr(
        cs,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: enqueue me", "test"))
    monkeypatch.setattr(cs, "already_closed", lambda *a, **k: False)
    monkeypatch.setattr(cs, "write_receipt", lambda *a, **k: None)
    monkeypatch.setattr(
        cs,
        "_write_kind",
        lambda body, **kwargs: {"written": True, "kind": kwargs["kind"]},
    )
    import graphiti_memory_client as gmc

    monkeypatch.setattr(gmc, "load_env", lambda: None)

    def boom(**kwargs):
        raise RuntimeError("s3 put-object failed: AccessDenied")

    import ops.graphiti.distill_queue.enqueue as enq

    monkeypatch.setattr(enq, "enqueue_job", boom)

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-enq",
        agent_id="cursor",
        dry_run=False,
    )
    assert report["phase_a"] is True
    assert report["enqueue_ok"] is False
    assert report["receipt"]["enqueue_ok"] is False
    assert any("enqueue failed" in w for w in report["warnings"])


def test_idempotent_reclose(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cs,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("x", "test"))
    monkeypatch.setattr(cs, "already_closed", lambda *a, **k: True)
    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-2",
        agent_id="cursor",
        dry_run=False,
    )
    assert report["status"] == "idempotent_skip"


def test_phase_a_kept_when_phase_b_would_exceed_budget(monkeypatch, tmp_path):
    """Synthetic clock: after Phase A, remaining budget < 3s → skip B."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    monkeypatch.setattr(
        cs,
        "resolve_group_id",
        lambda p: {"group_id": "cursor-governance", "readonly": False},
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("user: hi", "test"))
    monkeypatch.setattr(cs, "already_closed", lambda *a, **k: False)
    monkeypatch.setattr(cs, "write_receipt", lambda *a, **k: None)
    monkeypatch.setattr(
        cs,
        "_write_kind",
        lambda body, **kwargs: {"written": True, "kind": kwargs["kind"]},
    )

    t = {"v": 1000.0}

    def clock():
        return t["v"]

    # Advance clock during Phase A writes by patching _heuristic_pickup side
    real_heuristic = cs._heuristic_pickup

    def slow_heuristic(**kwargs):
        t["v"] += 28.0  # leave < 3s of 30s budget
        return real_heuristic(**kwargs)

    monkeypatch.setattr(cs, "_heuristic_pickup", slow_heuristic)

    called_b = {"n": 0}

    def no_b(**kwargs):
        called_b["n"] += 1
        return None, "should not be called"

    monkeypatch.setattr(cs, "_distill_signal_packet", no_b)

    report = cs.close_session(
        project_dir=tmp_path,
        session_id="close-budget",
        agent_id="cursor",
        dry_run=True,
        clock=clock,
    )
    assert report["phase_a"] is True
    assert report["phase_b"] is False
    assert called_b["n"] == 0
    assert any("insufficient time" in w for w in report["warnings"])


def test_readonly_group_warns(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cs,
        "resolve_group_id",
        lambda p: {"group_id": "igor-workspace", "readonly": True, "warning": "readonly"},
    )
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **k: ("", "none"))
    report = cs.close_session(
        project_dir=tmp_path, session_id="ro", agent_id="cursor", dry_run=True
    )
    assert report["status"] == "skipped"
    assert any("write blocked" in w for w in report["warnings"])
