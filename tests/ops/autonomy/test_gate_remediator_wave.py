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
