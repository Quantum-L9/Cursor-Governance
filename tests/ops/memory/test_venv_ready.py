"""Readers wait for the locked governance venv; writers hold it for the whole install.

Regression: 2026-09-24 SessionStart. Claude Code runs every SessionStart hook in
parallel; hydrate spawned ``l9-memory`` while ``ensure_uv_environment.sh`` was
force-reinstalling ``l9_graphite_memory``, and the runtime died with
``ModuleNotFoundError`` — reported as a canonical ``INVALID_RECEIPT``.
"""

from __future__ import annotations

import dataclasses
import fcntl
import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

import pytest
from memory_boundary_fixtures import FakeMemoryCli, hydration_payload

from ops.memory import venv_ready as vr
from ops.memory.control_plane_client import (
    FAULT_ENVIRONMENT,
    MemoryControlPlaneClient,
    OutcomeStatus,
)
from ops.memory.runtime_binding import RuntimeBinding

ROOT = Path(__file__).resolve().parents[3]
ENSURE = ROOT / "ops" / "scripts" / "ensure_uv_environment.sh"
WS = "/tmp/workspace"


@pytest.fixture(autouse=True)
def _fresh_deadlines():
    vr._DEADLINES.clear()
    yield
    vr._DEADLINES.clear()


def _gov(tmp_path: Path) -> Path:
    root = tmp_path / "gov"
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".l9").mkdir()
    return root


def _hold_exclusive(root: Path) -> int:
    fd = os.open(root / vr.LOCK_REL, os.O_RDWR | os.O_CREAT, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _release(fd: int) -> None:
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


# --- reader: ops/memory/venv_ready.py --------------------------------------


def test_cli_root_is_only_a_governed_venv() -> None:
    assert vr.governance_root_for_cli("/g/.venv/bin/l9-memory") == Path("/g")
    assert vr.governance_root_for_cli("/g/bin/l9-memory") is None
    assert vr.governance_root_for_cli(None) is None


def test_no_lock_file_is_ready_and_creates_nothing(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    with vr.venv_ready(root, timeout=0) as ready:
        assert ready.ready
    assert not (root / vr.LOCK_REL).exists()


def test_reader_waits_for_the_writer_then_proceeds(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    fd = _hold_exclusive(root)
    threading.Timer(0.5, _release, args=(fd,)).start()
    started = time.monotonic()
    with vr.venv_ready(root, timeout=10) as ready:
        assert ready.ready, ready.reason
    assert time.monotonic() - started >= 0.4


def test_reader_gives_up_with_a_named_reason(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    fd = _hold_exclusive(root)
    try:
        with vr.venv_ready(root, timeout=0.3) as ready:
            assert not ready.ready
            assert "install still in progress" in ready.reason
    finally:
        _release(fd)


def test_the_wait_is_bounded_per_process_not_per_call(tmp_path: Path) -> None:
    """A hook making several memory calls must not multiply the wait."""
    root = _gov(tmp_path)
    fd = _hold_exclusive(root)
    try:
        started = time.monotonic()
        for _ in range(4):
            with vr.venv_ready(root, timeout=0.5) as ready:
                assert not ready.ready
        assert time.monotonic() - started < 1.5
    finally:
        _release(fd)


def test_a_give_up_does_not_poison_the_next_install(tmp_path: Path) -> None:
    """A long-lived process waits afresh for a new, unrelated install.

    The give-up is keyed to the install it waited on (the writer's marker), so
    a second install starting moments later is waited for, not refused.
    """
    root = _gov(tmp_path)
    marker = root / vr.IN_PROGRESS_REL
    marker.write_text("111 2026-09-25T00:00:00Z\n", encoding="utf-8")
    fd = _hold_exclusive(root)
    try:
        with vr.venv_ready(root, timeout=0.2) as ready:
            assert not ready.ready
    finally:
        marker.unlink()
        _release(fd)
    time.sleep(0.3)
    marker.write_text("222 2026-09-25T00:00:01Z\n", encoding="utf-8")
    fd = _hold_exclusive(root)

    def _finish() -> None:
        marker.unlink()
        _release(fd)

    threading.Timer(0.5, _finish).start()
    with vr.venv_ready(root, timeout=5) as ready:
        assert ready.ready, ready.reason
        assert ready.waited_s >= 0.4


def test_an_unbounded_wait_budget_is_refused(monkeypatch) -> None:
    monkeypatch.setenv(vr.ENV_WAIT, "inf")
    assert vr.wait_budget() == vr.DEFAULT_WAIT_S
    monkeypatch.setenv(vr.ENV_WAIT, "abc")
    assert vr.wait_budget() == vr.DEFAULT_WAIT_S


def test_an_interrupted_install_is_refused(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    (root / vr.LOCK_REL).touch()
    (root / vr.IN_PROGRESS_REL).write_text("123 2026-09-24T23:48:57Z\n", encoding="utf-8")
    with vr.venv_ready(root, timeout=0) as ready:
        assert not ready.ready
        assert "interrupted" in ready.reason
        assert "ensure_uv_environment.sh" in ready.reason


def test_the_shared_lock_is_held_for_the_call(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    (root / vr.LOCK_REL).touch()
    with vr.venv_ready(root, timeout=0) as ready:
        assert ready.ready
        probe = os.open(root / vr.LOCK_REL, os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(probe)


# --- client: an environment that is not ready is an environment fault -------


def _venv_bound(bound: RuntimeBinding, root: Path) -> RuntimeBinding:
    cli = root / ".venv" / "bin" / "l9-memory"
    shutil.copy(bound.memory_cli, cli)
    return dataclasses.replace(bound, memory_cli=str(cli))


def test_client_does_not_spawn_into_an_installing_venv(
    tmp_path: Path, bound: RuntimeBinding, fake_cli: FakeMemoryCli, monkeypatch
) -> None:
    monkeypatch.setenv(vr.ENV_WAIT, "0.2")
    root = _gov(tmp_path)
    fake_cli.reply("hydrate", 0, hydration_payload("r1"))
    fd = _hold_exclusive(root)
    try:
        outcome = MemoryControlPlaneClient(_venv_bound(bound, root), runner=fake_cli.run).hydrate(
            "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
        )
    finally:
        _release(fd)
    assert outcome.status is OutcomeStatus.BINDING_FAILED
    assert outcome.integration_receipt["fault_class"] == FAULT_ENVIRONMENT
    assert "install still in progress" in (outcome.error or "")
    assert not [c for c in fake_cli.calls if "hydrate" in c[0]], "runtime must not be spawned"


def test_client_spawns_once_the_install_completes(
    tmp_path: Path, bound: RuntimeBinding, fake_cli: FakeMemoryCli
) -> None:
    root = _gov(tmp_path)
    fake_cli.reply("hydrate", 0, hydration_payload("r1"))
    fd = _hold_exclusive(root)
    threading.Timer(0.3, _release, args=(fd,)).start()
    outcome = MemoryControlPlaneClient(_venv_bound(bound, root), runner=fake_cli.run).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.OK


def test_a_runtime_that_cannot_import_itself_is_an_environment_fault(
    bound: RuntimeBinding, fake_cli: FakeMemoryCli
) -> None:
    """The exact 2026-09-24 traceback: no receipt, because nothing ran."""
    traceback = (
        "Traceback (most recent call last):\n"
        '  File "/g/.venv/bin/l9-memory", line 3, in <module>\n'
        '  File "/g/.venv/lib/python3.12/site-packages/l9_graphite_memory/__init__.py", '
        "line 13, in <module>\n"
        "ModuleNotFoundError: No module named 'l9_graphite_memory.contracts.review'\n"
    )
    fake_cli.reply("hydrate", 1, None, traceback)
    outcome = MemoryControlPlaneClient(bound, runner=fake_cli.run).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.BINDING_FAILED
    assert outcome.integration_receipt["fault_class"] == FAULT_ENVIRONMENT
    assert "ModuleNotFoundError" in (outcome.error or "")


@pytest.mark.parametrize(
    "trailer",
    [
        "Exception ignored in: <function _shutdown at 0x7f>\n",
        "/usr/lib/python3.12/warnings.py:1: RuntimeWarning: coroutine never awaited\n",
    ],
)
def test_an_import_failure_followed_by_shutdown_noise_is_still_an_environment_fault(
    bound: RuntimeBinding, fake_cli: FakeMemoryCli, trailer: str
) -> None:
    stderr = (
        "Traceback (most recent call last):\n"
        "ModuleNotFoundError: No module named 'l9_graphite_memory.contracts.review'\n" + trailer
    )
    fake_cli.reply("hydrate", 1, None, stderr)
    outcome = MemoryControlPlaneClient(bound, runner=fake_cli.run).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.BINDING_FAILED


def test_a_non_import_crash_is_still_an_invalid_receipt(
    bound: RuntimeBinding, fake_cli: FakeMemoryCli
) -> None:
    fake_cli.reply("hydrate", 1, None, "Traceback (most recent call last):\nValueError: boom\n")
    outcome = MemoryControlPlaneClient(bound, runner=fake_cli.run).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT


# --- writer: ops/scripts/ensure_uv_environment.sh ---------------------------


def _writer_root(tmp_path: Path, *, sync_sleep: float = 0.0) -> tuple[Path, dict[str, str]]:
    """A governance root with a fake ``uv`` whose sync records who held the lock."""
    root = tmp_path / "gov"
    binary = tmp_path / "bin"
    (root / "ops" / "memory").mkdir(parents=True)
    binary.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="fixture"\n', encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    probe = tmp_path / "lock-held-during-sync"
    (binary / "uv").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'if [ "${1:-}" = "--version" ]; then echo "uv 9.9.9-fixture"; exit 0; fi\n'
        'if [ "${1:-}" = "sync" ]; then\n'
        f"  sleep {sync_sleep}\n"
        '  if flock -n "$UV_TEST_ROOT/.l9/uv-environment.lock" true; then echo free; '
        'else echo held; fi > "$UV_TEST_PROBE"\n'
        '  marker="$UV_TEST_ROOT/.l9/uv-environment.installing"\n'
        '  [ -e "$marker" ] && echo marked >> "$UV_TEST_PROBE"\n'
        '  mkdir -p "$UV_TEST_ROOT/.venv/bin"\n'
        "  printf '%s\\n' '#!/usr/bin/env bash' 'exec python3 \"$@\"' "
        '> "$UV_TEST_ROOT/.venv/bin/python3"\n'
        '  chmod +x "$UV_TEST_ROOT/.venv/bin/python3"\n'
        "  exit 0\nfi\nexit 2\n",
        encoding="utf-8",
    )
    (binary / "uv").chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{binary}:{os.environ.get('PATH', '')}",
        "UV_TEST_ROOT": str(root),
        "UV_TEST_PROBE": str(probe),
    }
    return root, env


needs_util_linux = pytest.mark.skipif(
    shutil.which("flock") is None or shutil.which("setsid") is None,
    reason="flock/setsid (util-linux) not installed; the script falls back to an unlocked sync",
)


@needs_util_linux
def test_the_sync_runs_under_the_exclusive_lock_and_marker(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "lock-held-during-sync").read_text().split() == ["held", "marked"]
    assert not (root / ".l9" / "uv-environment.installing").exists(), "verified: marker cleared"
    assert done.stdout == ""


@needs_util_linux
def test_killing_the_caller_does_not_kill_the_install(tmp_path: Path) -> None:
    """A hook deadline tears down the caller's process group; the sync survives."""
    root, env = _writer_root(tmp_path, sync_sleep=1.5)
    caller = subprocess.Popen(
        ["bash", str(ENSURE), str(root)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(0.5)
    os.killpg(caller.pid, signal.SIGKILL)
    caller.wait(timeout=10)
    fingerprint = root / ".venv" / ".l9-uv-fingerprint"
    deadline = time.monotonic() + 20
    while not fingerprint.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert fingerprint.exists(), "the detached sync must run to completion"
    deadline = time.monotonic() + 10
    while (root / ".l9" / "uv-environment.installing").exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not (root / ".l9" / "uv-environment.installing").exists()


@needs_util_linux
def test_an_interrupted_install_forces_a_resync(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    run = ["bash", str(ENSURE), str(root)]
    assert subprocess.run(run, env=env, capture_output=True, timeout=60).returncode == 0
    (tmp_path / "lock-held-during-sync").unlink()
    (root / ".l9" / "uv-environment.installing").write_text("1 then\n", encoding="utf-8")
    check = subprocess.run([*run, "check"], env=env, capture_output=True, text=True, timeout=60)
    assert check.returncode == 1
    assert "did not complete" in check.stderr
    again = subprocess.run(run, env=env, capture_output=True, text=True, timeout=60)
    assert again.returncode == 0, again.stderr
    assert "re-synchronizing" in again.stderr
    assert (tmp_path / "lock-held-during-sync").exists(), "uv sync ran again"
    assert not (root / ".l9" / "uv-environment.installing").exists()


@needs_util_linux
def test_an_unverifiable_venv_keeps_the_marker(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    (root / "uv.lock").write_text('version = 1\n\n[[package]]\nname = "l9-graphite-memory"\n')
    # Deterministic regardless of which python3 the shim resolves: a package
    # that is present but half-installed, first on the import path.
    broken = tmp_path / "broken" / "l9_graphite_memory"
    broken.mkdir(parents=True)
    (broken / "__init__.py").write_text("raise ImportError('half-installed')\n")
    env["PYTHONPATH"] = str(broken.parent)
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 1
    assert "environment verification failed (import l9_graphite_memory)" in done.stderr
    assert (root / ".l9" / "uv-environment.installing").exists()


@needs_util_linux
def test_a_held_lock_times_out_with_exit_75_and_a_reason(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    (root / ".l9").mkdir()
    fd = _hold_exclusive(root)
    try:
        done = subprocess.run(
            ["bash", str(ENSURE), str(root)],
            env={**env, "L9_UV_ENV_LOCK_WAIT_S": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        _release(fd)
    assert done.returncode == 75
    assert "still held after 1s" in done.stderr
    assert done.stdout == ""


@needs_util_linux
def test_a_non_numeric_lock_wait_falls_back_instead_of_failing(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)],
        env={**env, "L9_UV_ENV_LOCK_WAIT_S": "abc"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr


@needs_util_linux
def test_check_during_a_live_install_says_in_progress(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    (root / ".l9").mkdir()
    (root / ".l9" / "uv-environment.installing").write_text("1 now\n", encoding="utf-8")
    fd = _hold_exclusive(root)
    try:
        check = subprocess.run(
            ["bash", str(ENSURE), str(root), "check"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        _release(fd)
    assert check.returncode == 1
    assert "install in progress" in check.stderr
    assert "synchronization required" in check.stderr  # still classified DEGRADED


@needs_util_linux
def test_logs_of_dead_callers_are_swept(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    (root / ".l9").mkdir()
    dead = subprocess.Popen(["true"])
    dead.wait()
    stale = root / ".l9" / f"uv-environment.{dead.pid}.log"
    stale.write_text("old\n", encoding="utf-8")
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert not stale.exists()
    assert not list((root / ".l9").glob("uv-environment.*.log"))


def test_without_flock_or_setsid_the_sync_runs_unlocked_and_says_so(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    # `command -v` must not find them: every PATH dir that holds flock/setsid is
    # replaced by a mirror of its other tools.
    mirror = tmp_path / "tools"
    mirror.mkdir()
    keep = []
    for d in env["PATH"].split(os.pathsep):
        if not d:
            continue
        if not any((Path(d) / t).exists() for t in ("flock", "setsid")):
            keep.append(d)
            continue
        for tool in Path(d).iterdir():
            if tool.name not in ("flock", "setsid") and not (mirror / tool.name).exists():
                (mirror / tool.name).symlink_to(tool)
    keep.append(str(mirror))
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)],
        env={**env, "PATH": os.pathsep.join(keep)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert "flock/setsid unavailable" in done.stderr
    assert (root / ".venv" / ".l9-uv-fingerprint").exists()
