"""Plan-skill memory prefetch — fires before either planner drafts."""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "hooks"))

import plan_memory_prefetch as hook  # noqa: E402

TEMPLATE = ROOT / "ops" / "hooks" / "hooks.json.template"
SETUP = ROOT / "ops" / "scripts" / "setup_workspace_symlinks.sh"


def test_template_registers_prefetch_after_the_skill_router() -> None:
    events = json.loads(TEMPLATE.read_text(encoding="utf-8"))["hooks"]["beforeSubmitPrompt"]
    commands = [entry["command"] for entry in events]
    assert "./hooks/before-submit-skill-router.py" in commands
    assert "./hooks/plan-memory-prefetch.py --hook" in commands
    assert commands.index("./hooks/before-submit-skill-router.py") < commands.index(
        "./hooks/plan-memory-prefetch.py --hook"
    )


def test_setup_installs_the_prefetch_hook() -> None:
    text = SETUP.read_text(encoding="utf-8")
    assert "plan_memory_prefetch.py:plan-memory-prefetch.py" in text


def test_both_planning_skills_require_prefetch_before_emit() -> None:
    for rel in (
        "skills/l9-plan/SKILL.md",
        "skills/l9-plan-simple/SKILL.md",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "plan_memory_prefetch.py" in text, rel
        assert "MEMORY_PREFETCH" in text, rel
        assert text.index("Memory prefetch") < text.index("Emit PLAN_DOCUMENT"), rel


def test_planning_requested_on_routed_plan_skills() -> None:
    payload = {"prompt": "plan the kernel latch"}
    route = {
        "status": "routed",
        "decision": {"primary": {"name": "l9-plan-simple"}, "supporting": []},
    }
    assert hook.planning_requested(payload, route=route) is True
    route["decision"]["primary"]["name"] = "l9-plan"
    assert hook.planning_requested(payload, route=route) is True
    route["decision"]["primary"]["name"] = "l9-ynp"
    assert hook.planning_requested(payload, route=route) is False


def test_planning_requested_on_composer_plan_mode() -> None:
    assert hook.planning_requested({"composerMode": "plan", "prompt": "x"}) is True
    assert hook.planning_requested({"prompt": "/l9-plan lock a campaign"}) is True


def test_non_plan_prompt_does_not_call_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[object] = []
    monkeypatch.setattr(hook, "prefetch", lambda **k: called.append(k) or {"status": "OK"})
    result = hook.run_for_payload({"prompt": "what time is it"}, force=False)
    assert result["status"] == "SKIP"
    assert called == []


def test_prefetch_writes_conflicts_cite_not_episode_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_PLAN_MEMORY_PREFETCH", raising=False)
    monkeypatch.setenv("L9_MEMORY_ENABLED", "1")

    def fake_run(argv: list[str], *, cwd: Path, timeout: float = 0.0) -> SimpleNamespace:
        if "hydrate" in argv:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"status": "OK", "ok": True}),
                stderr="",
            )
        if "search" in argv:
            return SimpleNamespace(
                returncode=0, stdout=json.dumps({"receipt": {"hits": []}}), stderr=""
            )
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "OK",
                    "ok": True,
                    "namespace": {
                        "write_namespace_hint": "cursor-governance",
                        "repository_identity": "Quantum-L9/Cursor-Governance",
                    },
                    "receipt": {
                        "snapshot_digest": "a" * 64,
                        "checked_record_count": 4,
                        "conflicts": [],
                        "policy_version": "conflicts/v1",
                    },
                }
            ),
            stderr="",
        )

    body = hook.prefetch(
        workspace=tmp_path,
        gov_root=tmp_path,
        task="plan the kernel latch",
        skills=["l9-plan-simple"],
        runner=fake_run,
    )
    assert body["status"] == "OK"
    cite = body["conflicts"]
    assert cite["namespace"] == "cursor-governance"
    assert cite["snapshot_digest"] == "a" * 64
    assert cite["checked_record_count"] == 4
    assert cite["conflicts"] == 0
    assert cite["policy_version"] == "conflicts/v1"
    assert "episode" not in json.dumps(cite)
    saved = json.loads((tmp_path / hook.RECEIPT_REL).read_text(encoding="utf-8"))
    assert saved["conflicts"]["namespace"] == "cursor-governance"


def test_hook_always_continues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    rc = hook.main(["--hook", "--workspace", str(tmp_path)])
    assert rc == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1]) == {"continue": True}


DISTINCTIVE = "Gate hub owns routing; engines never call peers directly (ADR-002)."


def _runner(
    *,
    hydrate: tuple[int, dict[str, object]],
    search: tuple[int, dict[str, object]] | None = None,
    conflicts: tuple[int, dict[str, object]] | None = None,
    slow: set[str] | None = None,
    seen: list[tuple[str, float]] | None = None,
):
    """A memcli stand-in keyed by subcommand, with an optional hang."""
    slow = slow or set()

    def run(argv: list[str], *, cwd: Path, timeout: float) -> SimpleNamespace:
        sub = argv[argv.index("ops.memory.cli") + 1]
        if seen is not None:
            seen.append((sub, timeout))
        if sub in slow:
            # What subprocess.run does to a child that outlives its timeout.
            raise __import__("subprocess").TimeoutExpired(argv, timeout)
        code, doc = {"hydrate": hydrate, "search": search, "conflicts": conflicts}.get(sub) or (
            0,
            {},
        )
        return SimpleNamespace(returncode=code, stdout=json.dumps(doc), stderr="")

    return run


def test_hydrated_records_reach_the_planner(tmp_path: Path) -> None:
    """The repair: a hit must put real content on the planner-facing receipt.

    Pre-repair this receipt kept only status/ok/returncode, so the hook paid
    for the memory reads and the planner still drafted blind.
    """
    body = hook.prefetch(
        workspace=tmp_path,
        gov_root=tmp_path,
        task="plan the gate hub",
        skills=["l9-plan"],
        runner=_runner(
            hydrate=(0, {"status": "OK", "ok": True, "record_ids": ["rec-1"], "record_count": 1}),
            search=(
                0,
                {
                    "receipt": {
                        "hits": [
                            {
                                "record": {
                                    "record_id": "rec-1",
                                    "namespace": "cursor-governance",
                                    "memory_class": "decision",
                                    "content": DISTINCTIVE,
                                }
                            }
                        ]
                    }
                },
            ),
            conflicts=(0, {"receipt": {"conflicts": [], "policy_version": "conflicts/v1"}}),
        ),
    )
    assert body["state"] == hook.STATE_HIT
    assert DISTINCTIVE in json.dumps(body["context"])
    # Provenance from the control plane survives alongside the content.
    assert body["context"][0]["record_id"] == "rec-1"
    assert body["context"][0]["namespace"] == "cursor-governance"
    # And it is on the receipt the planning skills are told to read.
    saved = json.loads((tmp_path / hook.RECEIPT_REL).read_text(encoding="utf-8"))
    assert DISTINCTIVE in json.dumps(saved["context"])


def test_no_hit_is_not_degraded(tmp_path: Path) -> None:
    """Memory answering "nothing" is a different fact from memory not answering."""
    body = hook.prefetch(
        workspace=tmp_path,
        gov_root=tmp_path,
        task="plan",
        skills=["l9-plan"],
        runner=_runner(
            hydrate=(0, {"status": "NO_HITS", "ok": True, "record_ids": []}),
            conflicts=(0, {"receipt": {"conflicts": [], "policy_version": "conflicts/v1"}}),
        ),
    )
    assert body["state"] == hook.STATE_NO_HIT
    assert body["status"] == "OK"
    assert body["context"] == []


def test_unavailable_memory_is_degraded_not_no_hit(tmp_path: Path) -> None:
    body = hook.prefetch(
        workspace=tmp_path,
        gov_root=tmp_path,
        task="plan",
        skills=["l9-plan"],
        runner=_runner(hydrate=(3, {"status": "CANONICAL_UNAVAILABLE", "ok": False})),
    )
    assert body["state"] == hook.STATE_DEGRADED
    assert body["status"] == "WARN"


def test_conflict_evidence_is_its_own_state(tmp_path: Path) -> None:
    body = hook.prefetch(
        workspace=tmp_path,
        gov_root=tmp_path,
        task="plan",
        skills=["l9-plan"],
        runner=_runner(
            hydrate=(0, {"status": "NO_HITS", "ok": True, "record_ids": []}),
            conflicts=(
                0,
                {"receipt": {"conflicts": [{"id": "x"}, {"id": "y"}], "policy_version": "v1"}},
            ),
        ),
    )
    assert body["state"] == hook.STATE_CONFLICT
    assert body["conflicts"]["conflicts"] == 2


def test_slow_memory_stays_inside_the_hook_slot(tmp_path: Path) -> None:
    """Repair D. Every child hangs; the hook must still finish and continue.

    Pre-repair each child could run for the control plane's own 30s timeout,
    so the first one alone outlived the 20s Cursor slot and the adapter was
    killed before writing any receipt.
    """
    seen: list[tuple[str, float]] = []
    started = time.monotonic()
    body = hook.prefetch(
        workspace=tmp_path,
        gov_root=tmp_path,
        task="plan",
        skills=["l9-plan"],
        runner=_runner(
            hydrate=(0, {}),
            slow={"hydrate", "search", "conflicts"},
            seen=seen,
        ),
        deadline_seconds=3.0,
    )
    elapsed = time.monotonic() - started
    assert elapsed < hook.HOOK_SLOT_SECONDS - hook.EMIT_RESERVE_SECONDS
    assert body["state"] == hook.STATE_DEGRADED
    assert body["hydrate"]["timed_out"] is True
    # No child was ever handed more than what remained of the outer deadline.
    assert seen and all(t <= 3.0 for _, t in seen)
    # The receipt still exists: degraded is recorded, not lost.
    assert (tmp_path / hook.RECEIPT_REL).is_file()


def test_default_budget_reserves_time_to_emit() -> None:
    """The budget must leave the hook room to record and print, by construction."""
    assert hook.PREFETCH_DEADLINE_SECONDS + hook.EMIT_RESERVE_SECONDS <= hook.HOOK_SLOT_SECONDS
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))["hooks"]["beforeSubmitPrompt"]
    slot = next(
        entry["timeout"]
        for entry in template
        if entry["command"] == "./hooks/plan-memory-prefetch.py --hook"
    )
    assert hook.HOOK_SLOT_SECONDS == float(slot)


def test_deadline_exhaustion_skips_rather_than_starts_a_doomed_child(tmp_path: Path) -> None:
    seen: list[tuple[str, float]] = []
    body = hook.prefetch(
        workspace=tmp_path,
        gov_root=tmp_path,
        task="plan",
        skills=["l9-plan"],
        runner=_runner(hydrate=(0, {"status": "OK", "record_ids": ["r"]}), seen=seen),
        deadline_seconds=0.0,
    )
    assert [sub for sub, _ in seen] == []
    assert body["state"] == hook.STATE_DEGRADED


def test_disabled_switch_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_PLAN_MEMORY_PREFETCH", "0")
    result = hook.run_for_payload(
        {"prompt": "/l9-plan x", "composerMode": "plan"},
        workspace=tmp_path,
        force=True,
    )
    assert result["status"] == "SKIP"
    assert result["reason"] == "disabled"
