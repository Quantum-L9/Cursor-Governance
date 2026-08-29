"""Remediator verify must not enter the ceremony reader wave."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from local_execution_gate import (  # noqa: E402
    REMEDIATOR_ENV,
    command_runs_reader_wave,
    evaluate,
    remediator_env_active,
)


def test_command_runs_reader_wave_detects_ceremony_goals() -> None:
    assert command_runs_reader_wave("make pr-check") == "make pr-check"
    assert command_runs_reader_wave("PR_BASE=origin/main make pr") == "make pr"
    assert "run_pr_gate.sh" in (command_runs_reader_wave("bash ops/scripts/run_pr_gate.sh") or "")
    assert command_runs_reader_wave("L9_REMEDIATOR=1 make precommit-repo") is None


def test_evaluate_denies_pr_check_when_remediator_env_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(REMEDIATOR_ENV, "1")
    assert remediator_env_active() is True
    reason = evaluate("Bash", {"command": "make pr-check"}, root=tmp_path)
    assert reason is not None
    assert "reader wave" in reason
    assert "make precommit-repo" in reason
    monkeypatch.delenv(REMEDIATOR_ENV, raising=False)
    assert evaluate("Bash", {"command": "make pr-check"}, root=tmp_path) is None
    assert (
        evaluate("Bash", {"command": "L9_REMEDIATOR=1 make precommit-repo"}, root=tmp_path) is None
    )


def test_evaluate_denies_inline_remediator_assignment(tmp_path: Path) -> None:
    reason = evaluate("Bash", {"command": "L9_REMEDIATOR=1 make pr-check"}, root=tmp_path)
    assert reason is not None
    assert "reader wave" in reason


def test_cursor_shell_denies_pr_check_when_remediator_env_set(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import json
    from io import StringIO

    import local_execution_gate as gate

    monkeypatch.setenv(REMEDIATOR_ENV, "1")
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(json.dumps({"command": "make pr-check"})),
    )
    assert gate.main_cursor_shell() == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["permission"] == "deny"
    assert "reader wave" in payload["user_message"]
