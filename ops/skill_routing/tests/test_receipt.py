"""Conversation-scoped atomic route receipts (VSP phase 5)."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.skill_routing import receipt as rc  # noqa: E402
from ops.skill_routing import session_locator as loc  # noqa: E402

GEN = "a" * 64
IDENTITY = {"generation_id": GEN, "source_manifest_sha256": "b" * 64}


def locator(conversation: str, roots: list[str], state_root: Path) -> loc.RouteLocator:
    built = loc.locator_from_payload(
        {"conversation_id": conversation, "workspace_roots": roots}, state_root
    )
    assert built is not None
    return built


def materialized(skill_md: Path) -> dict:
    return {
        "primary": {
            "name": "l9-a",
            "skill_md": str(skill_md),
            "invocation": "model_allowed",
            "sha256": "c" * 64,
        },
        "supporting": [],
    }


@pytest.fixture
def skill_md(tmp_path: Path) -> Path:
    path = tmp_path / "skills" / "l9-a" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: l9-a\n---\n", encoding="utf-8")
    return path


def routed(state: Path, conversation: str, roots: list[str], skill_md: Path, **kw) -> Path:
    receipt = rc.build_receipt(
        status="routed",
        locator=locator(conversation, roots, state),
        generation_id=GEN,
        registry_identity=IDENTITY,
        decision={"route_id": "r", "score": 8, "source": "route"},
        materialized=materialized(skill_md),
        prompt="secret prompt text",
        **kw,
    )
    return rc.write_receipt(receipt, state)


def test_layout_and_no_raw_prompt(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    path = routed(state, "conv-A", [str(tmp_path)], skill_md)
    assert path == state / loc.conversation_key("conv-A") / "current.json"
    text = path.read_text(encoding="utf-8")
    assert "secret prompt text" not in text
    data = json.loads(text)
    assert data["schema"] == rc.RECEIPT_SCHEMA
    assert data["prompt_sha256"] == rc.prompt_digest("secret prompt text")
    assert data["decision"]["primary"]["skill_md"] == str(skill_md)


def test_conversation_a_cannot_consume_b(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    roots = [str(tmp_path)]
    routed(state, "conv-A", roots, skill_md)
    routed(state, "conv-B", roots, skill_md)
    got = rc.read_receipt("conv-A", state_root=state, generation_id=GEN, workspace_roots=roots)
    assert got["conversation_id"] == "conv-A"
    # Copy B's receipt into A's slot: identity mismatch is rejected.
    key_a = loc.conversation_key("conv-A")
    key_b = loc.conversation_key("conv-B")
    (state / key_a / "current.json").write_bytes((state / key_b / "current.json").read_bytes())
    with pytest.raises(rc.ReceiptError, match="conversation"):
        rc.read_receipt("conv-A", state_root=state, generation_id=GEN)


def test_same_workspace_different_conversations_are_separate(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    roots = [str(tmp_path)]
    a = routed(state, "conv-A", roots, skill_md)
    b = routed(state, "conv-B", roots, skill_md)
    assert a != b
    assert a.parent != b.parent


def test_different_workspace_same_conversation_rejected(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    routed(state, "conv-A", [str(tmp_path / "ws1")], skill_md)
    with pytest.raises(rc.ReceiptError, match="workspace"):
        rc.read_receipt(
            "conv-A", state_root=state, generation_id=GEN, workspace_roots=[str(tmp_path / "ws2")]
        )


@pytest.mark.parametrize("status", ["no_route", "disabled", "degraded"])
def test_non_route_states_overwrite_routed(tmp_path: Path, skill_md: Path, status: str):
    state = tmp_path / "routes"
    roots = [str(tmp_path)]
    routed(state, "conv-A", roots, skill_md)
    receipt = rc.build_receipt(
        status=status,
        locator=locator("conv-A", roots, state),
        generation_id=GEN,
        registry_identity=IDENTITY,
        reason="test",
    )
    rc.write_receipt(receipt, state)
    got = rc.read_receipt("conv-A", state_root=state, generation_id=GEN)
    assert got["status"] == status
    assert "decision" not in got


def test_current_generation_replaces_previous_atomically(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    roots = [str(tmp_path)]
    path = routed(state, "conv-A", roots, skill_md, now=1000.0)
    routed(state, "conv-A", roots, skill_md, now=2000.0)
    data = json.loads(path.read_text())
    assert data["issued_at"] == 2000.0
    leftovers = [p for p in path.parent.iterdir() if p.name != "current.json"]
    assert leftovers == []


def test_concurrent_writers_never_tear(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    roots = [str(tmp_path)]
    errors: list[Exception] = []

    def writer(i: int) -> None:
        try:
            for _ in range(20):
                routed(state, "conv-A", roots, skill_md, now=float(i))
        except Exception as exc:  # pragma: no cover - surfaced via assertion
            errors.append(exc)

    def reader() -> None:
        path = state / loc.conversation_key("conv-A") / "current.json"
        for _ in range(200):
            if path.exists():
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    threads.append(threading.Thread(target=reader))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_stale_rejected(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    routed(state, "conv-A", [str(tmp_path)], skill_md, now=1000.0, ttl=10)
    rc.read_receipt("conv-A", state_root=state, generation_id=GEN, now=1005.0)
    with pytest.raises(rc.ReceiptError, match="expired"):
        rc.read_receipt("conv-A", state_root=state, generation_id=GEN, now=1011.0)


def test_malformed_and_absent_rejected(tmp_path: Path):
    state = tmp_path / "routes"
    with pytest.raises(rc.ReceiptError, match="absent"):
        rc.read_receipt("conv-A", state_root=state)
    path = state / loc.conversation_key("conv-A") / "current.json"
    path.parent.mkdir(parents=True)
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(rc.ReceiptError, match="malformed"):
        rc.read_receipt("conv-A", state_root=state)
    path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    with pytest.raises(rc.ReceiptError, match="missing fields"):
        rc.read_receipt("conv-A", state_root=state)


def test_missing_materialized_skill_rejected(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    routed(state, "conv-A", [str(tmp_path)], skill_md)
    skill_md.unlink()
    with pytest.raises(rc.ReceiptError, match="materialized primary missing"):
        rc.read_receipt("conv-A", state_root=state, generation_id=GEN)


def test_registry_generation_mismatch_rejected(tmp_path: Path, skill_md: Path):
    state = tmp_path / "routes"
    routed(state, "conv-A", [str(tmp_path)], skill_md)
    with pytest.raises(rc.ReceiptError, match="generation"):
        rc.read_receipt("conv-A", state_root=state, generation_id="f" * 64)
    # Explicitly un-bound reads (diagnostics) still work.
    assert (
        rc.read_receipt("conv-A", state_root=state, require_generation=False)["status"] == "routed"
    )


def test_routed_requires_decision_and_status_enum(tmp_path: Path):
    state = tmp_path / "routes"
    built = locator("conv-A", [], state)
    with pytest.raises(rc.ReceiptError):
        rc.build_receipt(status="routed", locator=built, generation_id=GEN, registry_identity={})
    with pytest.raises(rc.ReceiptError):
        rc.build_receipt(status="maybe", locator=built, generation_id=GEN, registry_identity={})


def test_state_root_env_injection(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(loc.STATE_ROOT_ENV, str(tmp_path / "injected"))
    assert loc.default_state_root() == tmp_path / "injected"
    monkeypatch.delenv(loc.STATE_ROOT_ENV)
    assert loc.default_state_root() == Path.home() / ".cursor" / "l9" / "routes"
