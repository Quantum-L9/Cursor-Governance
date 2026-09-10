"""Plan-skill memory prefetch — fires before either planner drafts."""

from __future__ import annotations

import io
import json
import sys
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

    def fake_run(argv: list[str], *, cwd: Path) -> SimpleNamespace:
        if "hydrate" in argv:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"status": "OK", "ok": True}),
                stderr="",
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


def test_disabled_switch_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_PLAN_MEMORY_PREFETCH", "0")
    result = hook.run_for_payload(
        {"prompt": "/l9-plan x", "composerMode": "plan"},
        workspace=tmp_path,
        force=True,
    )
    assert result["status"] == "SKIP"
    assert result["reason"] == "disabled"
