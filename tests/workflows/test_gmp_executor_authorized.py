"""Authorized non-interactive GMP executor (slash-gmp)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = ROOT / "workflows" / "gmp_executor.py"
GOV_PY = ROOT / ".venv" / "bin" / "python"
STATE = ROOT / ".l9" / "gmp" / "executor-state.json"

pytestmark = pytest.mark.xdist_group("gmp_executor_authorized")


def _env(**overrides: str) -> dict[str, str]:
    merged = os.environ.copy()
    merged["L9_L4_LOCAL_AUTONOMY"] = "0"
    merged["L9_GMP_DRY_RUN"] = "1"
    merged["L9_GOVERNANCE_SURFACE"] = "cursor"
    merged.update(overrides)
    return merged


def _run(
    args: list[str],
    *,
    stdin_closed: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    python = str(GOV_PY if GOV_PY.is_file() else "python3")
    return subprocess.run(
        [python, str(EXECUTOR), *args],
        cwd=str(ROOT),
        env=env or _env(),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL if stdin_closed else None,
        check=False,
    )


def setup_function() -> None:
    if STATE.exists():
        STATE.unlink()


def teardown_function() -> None:
    if STATE.exists():
        STATE.unlink()


def test_authorized_start_closed_stdin_ready_for_build() -> None:
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--plan",
            "tests/workflows/fixtures/gmp_plan_with_todos.plan.md",
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "READY_FOR_BUILD" in proc.stdout
    assert "Enter CONFIRM or ABORT" not in proc.stdout
    assert STATE.is_file()


def test_authorized_start_empty_plan_is_no_scope() -> None:
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--plan",
            "tests/workflows/fixtures/gmp_plan_empty.plan.md",
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ]
    )
    assert proc.returncode == 2, proc.stderr + proc.stdout
    assert "NO_SCOPE" in proc.stdout


def test_authorized_full_without_task_is_no_task() -> None:
    proc = _run(["--authorized-by", "slash-gmp", "--mode", "full"])
    assert proc.returncode == 2, proc.stderr + proc.stdout
    assert "NO_TASK" in proc.stdout


def test_authorized_finalize_records_make_pr_not_merge() -> None:
    adapter_env = _env(L9_GOVERNANCE_SURFACE="claude-code")
    start = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--plan",
            "tests/workflows/fixtures/gmp_plan_with_todos.plan.md",
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ],
        env=adapter_env,
    )
    assert start.returncode == 0, start.stderr + start.stdout
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--resume",
            "--mode",
            "finalize",
            "--commit-when-done",
        ],
        env=adapter_env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    combined = proc.stdout + proc.stderr
    assert "PR_REMEDIATE=1 make pr" in combined
    assert "gh pr merge" not in combined


def test_authorized_finalize_cursor_stops_without_make_pr() -> None:
    start = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--plan",
            "tests/workflows/fixtures/gmp_plan_with_todos.plan.md",
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ]
    )
    assert start.returncode == 0, start.stderr + start.stdout
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--resume",
            "--mode",
            "finalize",
            "--commit-when-done",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    combined = proc.stdout + proc.stderr
    assert "make precommit-repo" in combined
    assert "Do not make pr" in combined
    assert "PR_REMEDIATE=1 make pr" not in combined
    assert "gh pr merge" not in combined
