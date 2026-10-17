"""Authorized non-interactive GMP executor (slash-gmp)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = ROOT / "workflows" / "gmp_executor.py"
GOV_PY = ROOT / ".venv" / "bin" / "python"
STATE = ROOT / ".l9" / "gmp" / "executor-state.json"

pytestmark = pytest.mark.xdist_group("gmp_executor_authorized")


FIXTURE_PLAN = ROOT / "tests" / "workflows" / "fixtures" / "gmp_plan_with_todos.plan.md"
CONSUMER_ORIGIN = "https://github.com/Example-Org/consumer.git"


def _env(**overrides: str) -> dict[str, str]:
    merged = os.environ.copy()
    # `make pr` exports WS into the gate; an inherited WS must not pick the clone.
    merged.pop("WS", None)
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
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    python = str(GOV_PY if GOV_PY.is_file() else "python3")
    return subprocess.run(
        [python, str(EXECUTOR), *args],
        cwd=str(cwd),
        env=env or _env(),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL if stdin_closed else None,
        check=False,
    )


def _temp_repo(tmp_path: Path, *, origin: bool = True) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    if origin:
        subprocess.run(
            ["git", "-C", str(repo), "remote", "add", "origin", CONSUMER_ORIGIN], check=True
        )
    return repo.resolve()


def _start(workspace: Path, plan: Path | str = FIXTURE_PLAN, **env: str):
    return _run(
        [
            "--workspace",
            str(workspace),
            "--authorized-by",
            "slash-gmp",
            "--plan",
            str(plan),
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ],
        env=_env(**env),
    )


def _finalize(workspace: Path, **env: str):
    return _run(
        ["--workspace", str(workspace), "--resume", "--mode", "finalize", "--commit-when-done"],
        env=_env(**env),
    )


def _write_plan(path: Path, todo_file: str) -> Path:
    path.write_text(
        "---\nname: t\ntodos:\n"
        f"  - id: T1\n    file: {todo_file}\n    content: escape\n    status: pending\n"
        "---\n\n# t\n",
        encoding="utf-8",
    )
    return path


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
    assert "PR_REMEDIATE=1" in combined
    assert "make -C" in combined
    assert " pr " in combined
    assert "WS=" in combined
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
    assert f"make -C {ROOT} precommit-repo WS={ROOT}" in combined
    assert "Do not make pr" in combined
    assert "PR_REMEDIATE=1" not in combined
    assert "gh pr merge" not in combined


def test_workspace_flag_locks_other_clone(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    proc = _start(repo, L9_L4_LOCAL_AUTONOMY="1")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "READY_FOR_BUILD" in proc.stdout
    assert f"Workspace: {repo}" in proc.stdout
    assert "Identity: Example-Org/consumer" in proc.stdout
    state_file = repo / ".l9" / "gmp" / "executor-state.json"
    assert json.loads(state_file.read_text(encoding="utf-8"))["work_root"] == str(repo)
    assert not STATE.exists()
    l4_lines = [
        line
        for line in proc.stdout.splitlines()
        if line.startswith("SUBPROCESS:") and "l4_local.py" in line
    ]
    assert l4_lines, proc.stdout
    assert all(f"--workspace {repo} begin" in line for line in l4_lines), l4_lines


def test_consumer_finalize_targets_work_root(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    assert _start(repo).returncode == 0
    proc = _finalize(repo)
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined
    assert f"SUBPROCESS: make -C {ROOT} precommit-repo WS={repo}" in combined
    memory_lines = [line for line in combined.splitlines() if "ops.memory.cli write" in line]
    assert memory_lines and all(f"--workspace {repo}" in line for line in memory_lines)
    assert "Do not make pr" in combined
    assert not (repo / ".l9" / "gmp" / "executor-state.json").exists()
    assert not STATE.exists()


def test_consumer_adapter_publish_targets_work_root(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    surface = {"L9_GOVERNANCE_SURFACE": "claude-code", "L9_L4_LOCAL_AUTONOMY": "1"}
    assert _start(repo, **surface).returncode == 0
    proc = _finalize(repo, **surface)
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined
    assert f"PR_REMEDIATE=1 make -C {ROOT} pr WS={repo}" in combined
    assert f"--workspace {repo} authorize-release" in combined
    assert "gh pr merge" not in combined


def test_relative_plan_resolves_under_work_root_only(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    (repo / "plans").mkdir()
    _write_plan(repo / "plans" / "local.plan.md", "README.md")
    hit = _start(repo, "plans/local.plan.md")
    assert hit.returncode == 0, hit.stderr + hit.stdout
    assert "READY_FOR_BUILD" in hit.stdout
    _finalize(repo)

    empty_home = tmp_path / "home"
    empty_home.mkdir()
    miss = _start(
        repo, "tests/workflows/fixtures/gmp_plan_with_todos.plan.md", HOME=str(empty_home)
    )
    assert miss.returncode == 2, miss.stderr + miss.stdout
    assert "NO_PLAN" in miss.stdout
    assert "NO_SCOPE" not in miss.stdout
    assert not (repo / ".l9" / "gmp" / "executor-state.json").exists()
    assert not STATE.exists()


def test_workspace_subdir_normalizes_to_toplevel(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    sub = repo / "sub" / "dir"
    sub.mkdir(parents=True)
    proc = _start(sub)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (repo / ".l9" / "gmp" / "executor-state.json").is_file()
    assert not (sub / ".l9").exists()


def test_repo_without_origin_still_locks(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path, origin=False)
    proc = _start(repo)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "READY_FOR_BUILD" in proc.stdout
    assert "Identity: unknown" in proc.stdout


def test_no_git_toplevel_is_no_workspace(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    proc = _start(plain)
    assert proc.returncode == 2, proc.stderr + proc.stdout
    assert "NO_WORKSPACE" in proc.stdout
    assert not (plain / ".l9").exists()
    assert not STATE.exists()


@pytest.mark.parametrize("todo_file", ["../escape.py", "/etc/hosts"])
def test_todo_path_outside_work_root(tmp_path: Path, todo_file: str) -> None:
    repo = _temp_repo(tmp_path)
    plan = _write_plan(tmp_path / "escape.plan.md", todo_file)
    proc = _start(repo, plan, L9_L4_LOCAL_AUTONOMY="1")
    assert proc.returncode == 2, proc.stderr + proc.stdout
    assert "OUT_OF_WORKSPACE" in proc.stdout
    assert "READY_FOR_BUILD" not in proc.stdout
    assert "l4_local.py" not in proc.stdout
    assert not (repo / ".l9" / "gmp" / "executor-state.json").exists()


def test_memory_argv_targets_work_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("gmp_executor_under_test", EXECUTOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve string annotations through sys.modules.
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)

    repo = _temp_repo(tmp_path)
    executor = module.GMPExecutor(repo, "Example-Org/consumer")
    argv = executor._memory_argv("search", "q")
    assert argv[-2:] == ["--workspace", str(repo)]

    calls: list[tuple[list[str], Path]] = []

    def fake_run(argv: list[str], *, cwd: Path, **_: object) -> subprocess.CompletedProcess[str]:
        calls.append((argv, cwd))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.delenv("L9_GMP_DRY_RUN", raising=False)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    executor._init_state("memory probe", "RUNTIME")
    executor._step_memory_read()
    assert calls
    for call_argv, cwd in calls:
        assert cwd == module.GOV_ROOT
        assert call_argv[-2:] == ["--workspace", str(repo)]
