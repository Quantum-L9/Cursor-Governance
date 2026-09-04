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


def test_resume_finalize_without_flag_stays_authorized() -> None:
    """The documented finalize call carries no --authorized-by (commands/gmp.md).

    Observed 2026-09-04 on GMP-133: an unauthorized resume fell into the
    interactive DAG, where a closed stdin read as "No TODOs defined" and then
    "User aborted" — the human never aborted anything. Authorization is
    stamped into the state file at start and must survive resume.
    """
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
    proc = _run(["--resume", "--mode", "finalize", "--commit-when-done"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    combined = proc.stdout + proc.stderr
    assert "Enter CONFIRM or ABORT" not in combined
    assert "No TODOs defined" not in combined
    assert "User aborted" not in combined


def test_partial_authorized_state_does_not_restore_for_finalize() -> None:
    """Ctrl-C after _init_state must not unlock finalize."""
    import json

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {
                "gmp_id": "GMP-999",
                "tier": "RUNTIME",
                "task": "partial",
                "started_at": "2026-09-04T00:00:00",
                "current_step": "memory_read",
                "completed_steps": [],
                "todo_plan": [],
                "changes_made": [],
                "validations": [],
                "authorized_by": "slash-gmp",
            }
        ),
        encoding="utf-8",
    )
    proc = _run(["--resume", "--mode", "finalize", "--commit-when-done"])
    combined = proc.stdout + proc.stderr
    assert (
        "start ceremony incomplete" in combined
        or "Enter CONFIRM or ABORT" in combined
        or proc.returncode != 0
    )
    assert "COMPLETE GMP-999" not in combined


def test_legacy_state_without_authorized_by_finalizes() -> None:
    """Pre-stamp state that already locked scope still finalizes without the flag."""
    import json

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {
                "gmp_id": "GMP-998",
                "tier": "RUNTIME",
                "task": "legacy",
                "started_at": "2026-09-04T00:00:00",
                "current_step": "baseline",
                "completed_steps": ["memory_read", "scope_lock", "user_gate"],
                "todo_plan": [
                    {
                        "id": "T1",
                        "file": "workflows/gmp_executor.py",
                        "lines": "1-1",
                        "action": "REPLACE",
                        "description": "x",
                    }
                ],
                "changes_made": [],
                "validations": [],
            }
        ),
        encoding="utf-8",
    )
    proc = _run(["--resume", "--mode", "finalize", "--commit-when-done"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Enter CONFIRM or ABORT" not in (proc.stdout + proc.stderr)


def test_l4_argv_puts_workspace_before_subcommand() -> None:
    """l4_local.py declares --workspace on the top-level parser; placed after
    the subcommand it is an unrecognized argument and L4 begin silently fails."""
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
        ],
        env=_env(L9_L4_LOCAL_AUTONOMY="1"),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    l4_lines = [
        line
        for line in proc.stdout.splitlines()
        if line.startswith("SUBPROCESS:") and "l4_local.py" in line
    ]
    assert l4_lines, proc.stdout
    for line in l4_lines:
        assert "--workspace" in line, line
        assert line.index("--workspace") < line.index(" begin"), line


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
