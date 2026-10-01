"""Environment heal: one deterministic locked sync, skipped where it is not safe."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

from ops.memory import environment_heal as eh


def _governance_root(tmp_path: Path) -> Path:
    root = tmp_path / "gov"
    (root / "ops" / "scripts").mkdir(parents=True)
    (root / eh.HEAL_SCRIPT_REL).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (root / ".venv").mkdir()
    (root / eh.FINGERPRINT_REL).write_text("stale-fingerprint\n", encoding="utf-8")
    return root


class Recorder:
    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.calls: list[list[str]] = []
        self.returncode = returncode
        self.stderr = stderr
        self.fingerprint_present_at_call: bool | None = None

    def __call__(
        self, argv: list[str], *, timeout: float, env: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        root = Path(argv[2])
        self.fingerprint_present_at_call = (root / eh.FINGERPRINT_REL).exists()
        return subprocess.CompletedProcess(argv, self.returncode, "", self.stderr)


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return {"HOME": str(home), **extra}


def test_heal_runs_the_locked_sync_once_with_the_fingerprint_cleared(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    run = Recorder()
    outcome, reasons = eh.heal_environment(root, env=_env(tmp_path), runner=run)
    assert outcome == eh.HEAL_HEALED
    assert reasons == []
    assert run.calls == [["bash", str(root / eh.HEAL_SCRIPT_REL), str(root), "apply"]]
    # The cached "already synced" marker must not be allowed to win when
    # drift was proved by the probe.
    assert run.fingerprint_present_at_call is False


def test_heal_reports_a_failed_sync(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    run = Recorder(returncode=2, stderr="error: lock out of date\n")
    outcome, reasons = eh.heal_environment(root, env=_env(tmp_path), runner=run)
    assert outcome == eh.HEAL_FAILED
    assert any("exited 2" in reason and "lock out of date" in reason for reason in reasons)


def test_heal_is_skipped_by_the_kill_switch(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    run = Recorder()
    outcome, _ = eh.heal_environment(root, env=_env(tmp_path, L9_MEMORY_ENV_HEAL="0"), runner=run)
    assert outcome == f"{eh.HEAL_SKIPPED_PREFIX}{eh.ENV_HEAL}=0"
    assert run.calls == []


def test_heal_is_skipped_in_unmarked_ci(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    run = Recorder()
    assert eh.heal_environment(root, env=_env(tmp_path, CI="true"), runner=run)[0] == "skipped:ci"
    assert (
        eh.heal_environment(root, env=_env(tmp_path, GITHUB_ACTIONS="true"), runner=run)[0]
        == "skipped:ci"
    )
    assert run.calls == []


def test_heal_is_skipped_without_the_governance_script(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    run = Recorder()
    outcome, _ = eh.heal_environment(root, env=_env(tmp_path), runner=run)
    assert outcome == "skipped:no-heal-script"
    assert run.calls == []


def test_heal_is_skipped_while_the_repo_write_lock_is_held(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    env = _env(tmp_path)
    lock_dir = eh.repo_write_lock_dir(root, env)
    lock_dir.mkdir(parents=True)
    (lock_dir / "owner").write_text(f"{os.getpid()} 0 {root} make-pr\n", encoding="utf-8")
    run = Recorder()
    outcome, _ = eh.heal_environment(root, env=env, runner=run)
    assert outcome == "skipped:repo-write-lock-held"
    assert run.calls == []


def test_a_dead_lock_owner_does_not_block_the_heal(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    env = _env(tmp_path)
    lock_dir = eh.repo_write_lock_dir(root, env)
    lock_dir.mkdir(parents=True)
    # A pid that cannot be alive: max pid + 1 on every supported platform.
    (lock_dir / "owner").write_text("4194305 0 x y\n", encoding="utf-8")
    run = Recorder()
    outcome, _ = eh.heal_environment(root, env=env, runner=run)
    assert outcome == eh.HEAL_HEALED
    assert len(run.calls) == 1


def test_lock_dir_mirrors_the_shell_library(tmp_path: Path) -> None:
    """``repo_write_lock_dir`` must agree byte-for-byte with repo_write_lock.sh."""

    root = tmp_path / "ws"
    env = _env(tmp_path)
    expected = subprocess.run(  # noqa: S603 - fixed argv
        [
            "bash",
            "-c",
            'source "$1/ops/scripts/lib/repo_write_lock.sh" && repo_write_lock_dir "$2"',
            "_",
            str(Path(eh.__file__).resolve().parents[2]),
            str(root),
        ],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "HOME": env["HOME"]},
    ).stdout.strip()
    assert str(eh.repo_write_lock_dir(root, env)) == expected


def test_heal_timeout_defaults_and_rejects_nonsense() -> None:
    assert eh.heal_timeout({}) == eh.DEFAULT_HEAL_TIMEOUT
    assert eh.heal_timeout({eh.ENV_HEAL_TIMEOUT: "45"}) == 45.0
    assert eh.heal_timeout({eh.ENV_HEAL_TIMEOUT: "zero"}) == eh.DEFAULT_HEAL_TIMEOUT
    assert eh.heal_timeout({eh.ENV_HEAL_TIMEOUT: "-3"}) == eh.DEFAULT_HEAL_TIMEOUT


def test_heal_does_not_floor_remaining_budget_to_one_second(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    seen: list[float] = []

    def run(
        argv: list[str], *, timeout: float, env: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        seen.append(timeout)
        return subprocess.CompletedProcess(argv, 0, "", "")

    outcome, _ = eh.heal_environment(root, env=_env(tmp_path), runner=run, timeout=0.4)
    assert outcome == eh.HEAL_HEALED
    assert seen and 0 < seen[0] <= 0.4


def test_heal_holds_the_repo_write_lock_during_the_sync(tmp_path: Path) -> None:
    root = _governance_root(tmp_path)
    env = _env(tmp_path)
    seen: dict[str, object] = {}

    def run(
        argv: list[str], *, timeout: float, env: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        lock_dir = eh.repo_write_lock_dir(root, env)
        owner = lock_dir / "owner"
        seen["exists"] = lock_dir.is_dir()
        seen["owner"] = owner.read_text(encoding="utf-8") if owner.is_file() else ""
        seen["child_owner"] = env.get("L9_REPO_WRITE_LOCK_OWNER")
        return subprocess.CompletedProcess(argv, 0, "", "")

    outcome, _ = eh.heal_environment(root, env=env, runner=run)
    assert outcome == eh.HEAL_HEALED
    assert seen["exists"] is True
    assert str(os.getpid()) in str(seen["owner"])
    assert seen["child_owner"] == str(os.getpid())
    assert not eh.repo_write_lock_dir(root, env).exists()


def test_heal_is_skipped_while_an_install_holds_the_environment_lock(tmp_path: Path) -> None:
    """Drift seen during an install is the install; healing would queue a resync."""
    import fcntl
    import os

    root = tmp_path / "gov"
    (root / "ops" / "scripts").mkdir(parents=True)
    (root / "ops" / "scripts" / "ensure_uv_environment.sh").write_text("#!/bin/sh\nexit 0\n")
    (root / ".l9").mkdir()
    fd = os.open(root / ".l9" / "uv-environment.lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    calls: list[object] = []
    try:
        outcome, reasons = eh.heal_environment(
            root, env={"HOME": str(tmp_path)}, runner=lambda *a, **k: calls.append(a)
        )
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert outcome == "skipped:install-in-progress"
    assert calls == []
    assert reasons and "held by a running install" in reasons[0]
    assert not eh.install_in_progress(root)
