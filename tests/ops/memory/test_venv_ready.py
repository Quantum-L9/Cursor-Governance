"""Readers wait for the locked governance venv; writers hold it for the whole install.

Regression: 2026-09-24 SessionStart. Claude Code runs every SessionStart hook in
parallel; hydrate spawned ``l9-memory`` while ``ensure_uv_environment.sh`` was
force-reinstalling ``l9_graphite_memory``, and the runtime died with
``ModuleNotFoundError`` — reported as a canonical ``INVALID_RECEIPT``.
"""

from __future__ import annotations

import contextlib
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


@contextlib.contextmanager
def _held_exclusive(root: Path):
    """Hold the install lock and always close the descriptor."""
    fd = os.open(root / vr.LOCK_REL, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield fd
    finally:
        os.close(fd)


def _unlock(fd: int) -> None:
    """Drop the lock only. ``_held_exclusive`` closes the descriptor."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        # The context manager already closed the descriptor.
        return


# --- reader: ops/memory/venv_ready.py --------------------------------------


def test_cli_root_is_only_a_governed_venv() -> None:
    assert vr.governance_root_for_cli("/g/.venv/bin/l9-memory") == Path("/g")
    assert vr.governance_root_for_cli("/g/bin/l9-memory") is None
    assert vr.governance_root_for_cli(None) is None


def test_a_first_reader_creates_the_lock_so_a_later_writer_waits(tmp_path: Path) -> None:
    """No lock file yet (first install after merge, a directory swap) is no gap."""
    root = _gov(tmp_path)
    with vr.venv_ready(root, timeout=0) as ready:
        assert ready.ready
        assert (root / vr.LOCK_REL).exists()
        probe = os.open(root / vr.LOCK_REL, os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(probe)


def test_an_unwritable_root_does_not_block_the_reader(tmp_path: Path) -> None:
    root = tmp_path / "gov"
    (root / ".venv").mkdir(parents=True)
    (root / ".l9").write_text("not a directory\n", encoding="utf-8")
    with vr.venv_ready(root, timeout=0) as ready:
        assert ready.ready
        assert "venv lock unreadable" in ready.reason


def test_reader_waits_for_the_writer_then_proceeds(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    with _held_exclusive(root) as fd:
        timer = threading.Timer(0.5, _unlock, args=(fd,))
        timer.start()
        try:
            started = time.monotonic()
            with vr.venv_ready(root, timeout=10) as ready:
                assert ready.ready, ready.reason
            assert time.monotonic() - started >= 0.4
        finally:
            timer.cancel()
            timer.join(timeout=2)


def test_reader_gives_up_with_a_named_reason(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    with _held_exclusive(root):
        with vr.venv_ready(root, timeout=0.3) as ready:
            assert not ready.ready
            assert "install still in progress" in ready.reason


def test_the_wait_is_bounded_per_process_not_per_call(tmp_path: Path) -> None:
    """A hook making several memory calls must not multiply the wait."""
    root = _gov(tmp_path)
    with _held_exclusive(root):
        started = time.monotonic()
        for _ in range(4):
            with vr.venv_ready(root, timeout=0.5) as ready:
                assert not ready.ready
        assert time.monotonic() - started < 1.5


def test_a_give_up_does_not_poison_the_next_install(tmp_path: Path) -> None:
    """A long-lived process waits afresh for a new, unrelated install.

    The give-up is keyed to the install it waited on (the writer's marker), so
    a second install starting moments later is waited for, not refused.
    """
    root = _gov(tmp_path)
    marker = root / vr.IN_PROGRESS_REL
    marker.write_text("111 2026-09-25T00:00:00Z\n", encoding="utf-8")
    with _held_exclusive(root):
        with vr.venv_ready(root, timeout=0.2) as ready:
            assert not ready.ready
        marker.unlink()
    time.sleep(0.3)
    marker.write_text("222 2026-09-25T00:00:01Z\n", encoding="utf-8")

    def _finish() -> None:
        marker.unlink(missing_ok=True)
        _unlock(fd)

    with _held_exclusive(root) as fd:
        timer = threading.Timer(0.5, _finish)
        timer.start()
        try:
            with vr.venv_ready(root, timeout=5) as ready:
                assert ready.ready, ready.reason
                assert ready.waited_s >= 0.4
        finally:
            timer.cancel()
            timer.join(timeout=2)
            marker.unlink(missing_ok=True)


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
    with _held_exclusive(root):
        outcome = MemoryControlPlaneClient(_venv_bound(bound, root), runner=fake_cli.run).hydrate(
            "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
        )
    assert outcome.status is OutcomeStatus.BINDING_FAILED
    assert outcome.integration_receipt["fault_class"] == FAULT_ENVIRONMENT
    assert "install still in progress" in (outcome.error or "")
    assert not [c for c in fake_cli.calls if "hydrate" in c[0]], "runtime must not be spawned"


def test_client_spawns_once_the_install_completes(
    tmp_path: Path, bound: RuntimeBinding, fake_cli: FakeMemoryCli
) -> None:
    root = _gov(tmp_path)
    fake_cli.reply("hydrate", 0, hydration_payload("r1"))
    with _held_exclusive(root) as fd:
        timer = threading.Timer(0.3, _unlock, args=(fd,))
        timer.start()
        try:
            outcome = MemoryControlPlaneClient(
                _venv_bound(bound, root), runner=fake_cli.run
            ).hydrate("t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",))
            assert outcome.status is OutcomeStatus.OK
        finally:
            timer.cancel()
            timer.join(timeout=2)


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
        # Real uv lists its flags; the script feature-probes for
        # --managed-python rather than assuming the floor pin carries it.
        '  case " $* " in\n'
        '    *" --help "*)\n'
        '      if [ -z "${UV_TEST_NO_MANAGED_FLAG:-}" ]; then\n'
        '        echo "      --managed-python  Require use of uv-managed Python"\n'
        "      fi\n"
        "      exit 0\n"
        "      ;;\n"
        "  esac\n"
        '  printf \'%s\\n\' "$*" >> "$UV_TEST_ARGV"\n'
        '  if [ -n "${UV_TEST_TIMELINE:-}" ]; then\n'
        '    python3 "$UV_TEST_TIMELINE_PY" start $$\n'
        "  fi\n"
        f"  sleep {sync_sleep}\n"
        '  python3 "$UV_TEST_LOCK_PROBE" > "$UV_TEST_PROBE"\n'
        '  if [ -n "${UV_TEST_TIMELINE:-}" ]; then\n'
        '    python3 "$UV_TEST_TIMELINE_PY" end $$\n'
        "  fi\n"
        '  synced="$(pwd)"\n'
        '  marker="$synced/.l9/uv-environment.installing"\n'
        '  [ -e "$marker" ] && echo marked >> "$UV_TEST_PROBE"\n'
        '  mkdir -p "$synced/.venv/bin"\n'
        "  printf '%s\\n' '#!/usr/bin/env bash' "
        # UV_TEST_BROKEN_IMPORT: the venv carries a half-installed memory package.
        '\'case "$*" in *"import l9_graphite_memory"*) '
        '[ -n "${UV_TEST_BROKEN_IMPORT:-}" ] && exit 1;; esac\' '
        # UV_TEST_FAKE_MACHINE: the venv was built for another architecture.
        '\'case "$*" in *"platform.machine"*) '
        '[ -n "${UV_TEST_FAKE_MACHINE:-}" ] && { echo "$UV_TEST_FAKE_MACHINE"; exit 0; };; esac\' '
        "'exec python3 \"$@\"' "
        '> "$synced/.venv/bin/python3"\n'
        '  chmod +x "$synced/.venv/bin/python3"\n'
        "  exit 0\nfi\nexit 2\n",
        encoding="utf-8",
    )
    (binary / "uv").chmod(0o755)
    lock_probe = binary / "lock_probe.py"
    lock_probe.write_text(
        "import fcntl, os\n"
        "path = os.getcwd() + '/.l9/uv-environment.lock'\n"
        "fd = os.open(path, os.O_RDWR)\n"
        "try:\n"
        "    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
        "except BlockingIOError:\n"
        "    print('held')\n"
        "else:\n"
        "    print('free')\n"
        "    fcntl.flock(fd, fcntl.LOCK_UN)\n"
        "finally:\n"
        "    os.close(fd)\n",
        encoding="utf-8",
    )
    timeline_py = binary / "timeline.py"
    timeline_py.write_text(
        "import os, sys, time\n"
        "kind, pid = sys.argv[1], sys.argv[2]\n"
        "with open(os.environ['UV_TEST_TIMELINE'], 'a', encoding='utf-8') as handle:\n"
        "    handle.write(f'{kind} {time.time():.6f} {pid}\\n')\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "PATH": f"{binary}:{os.environ.get('PATH', '')}",
        "UV_TEST_ROOT": str(root),
        "UV_TEST_PROBE": str(probe),
        "UV_TEST_ARGV": str(tmp_path / "uv-argv"),
        "UV_TEST_LOCK_PROBE": str(lock_probe),
        "UV_TEST_TIMELINE_PY": str(timeline_py),
    }
    env.pop("GITHUB_ACTIONS", None)
    env.pop("CI", None)
    return root, env


def _sync_argv(tmp_path: Path) -> list[str]:
    """Every `uv sync` argument list the script issued, newest last."""
    recorded = tmp_path / "uv-argv"
    if not recorded.is_file():
        return []
    return [line for line in recorded.read_text(encoding="utf-8").splitlines() if line]


needs_util_linux = pytest.mark.skipif(
    shutil.which("flock") is None,
    reason="the shell venv reader calls the util-linux flock binary, which is not installed here",
)


def test_the_sync_runs_under_the_exclusive_lock_and_marker(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "lock-held-during-sync").read_text().split() == ["held", "marked"]
    assert not (root / ".l9" / "uv-environment.installing").exists(), "verified: marker cleared"
    assert done.stdout == ""


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


def test_an_unverifiable_venv_keeps_the_marker(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    (root / "uv.lock").write_text('version = 1\n\n[[package]]\nname = "l9-graphite-memory"\n')
    # The venv itself is broken — not the caller's import path, which the
    # verification ignores (python -I).
    env["UV_TEST_BROKEN_IMPORT"] = "1"
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 1
    assert "environment verification failed (import l9_graphite_memory)" in done.stderr
    assert (root / ".l9" / "uv-environment.installing").exists()


def test_a_held_lock_times_out_with_exit_75_and_a_reason(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    (root / ".l9").mkdir()
    with _held_exclusive(root):
        done = subprocess.run(
            ["bash", str(ENSURE), str(root)],
            env={**env, "L9_UV_ENV_LOCK_WAIT_S": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert done.returncode == 75
    assert "still held after 1s" in done.stderr
    assert done.stdout == ""


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


def test_check_during_a_live_install_says_in_progress(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    (root / ".l9").mkdir()
    (root / ".l9" / "uv-environment.installing").write_text("1 now\n", encoding="utf-8")
    with _held_exclusive(root):
        check = subprocess.run(
            ["bash", str(ENSURE), str(root), "check"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert check.returncode == 1
    assert "install in progress" in check.stderr
    assert "synchronization required" in check.stderr  # still classified DEGRADED


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


def _without_util_linux(env: dict[str, str], tmp_path: Path) -> dict[str, str]:
    """PATH with no flock or setsid binary, so the POSIX adapter is the writer."""
    mirror = tmp_path / "tools"
    mirror.mkdir()
    keep = []
    for raw in env["PATH"].split(os.pathsep):
        if not raw:
            continue
        directory = Path(raw)
        has_util_linux = any((directory / tool).exists() for tool in ("flock", "setsid"))
        if not directory.is_dir() or not has_util_linux:
            keep.append(raw)
            continue
        for tool in directory.iterdir():
            if tool.name not in ("flock", "setsid") and not (mirror / tool.name).exists():
                (mirror / tool.name).symlink_to(tool)
    keep.append(str(mirror))
    return {**env, "PATH": os.pathsep.join(keep)}


def _exclusive_available(root: Path) -> bool:
    fd = os.open(root / ".l9" / "uv-environment.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    finally:
        os.close(fd)


def _wait_for(predicate, seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_without_flock_or_setsid_the_sync_holds_the_lock(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    hidden = _without_util_linux(env, tmp_path)
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)],
        env=hidden,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert "without the environment lock" not in done.stderr
    assert "flock/setsid unavailable" not in done.stderr
    assert (tmp_path / "lock-held-during-sync").read_text().split() == ["held", "marked"]
    assert (root / ".venv" / ".l9-uv-fingerprint").is_file()
    assert not (root / ".l9" / "uv-environment.installing").exists()
    assert _exclusive_available(root)


def test_posix_fallback_callers_do_not_overlap_their_mutation(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path, sync_sleep=0.6)
    (root / ".l9").mkdir()
    other = tmp_path / "gov-other"
    shutil.copytree(root, other)
    shutil.rmtree(other / ".l9")
    (other / ".l9").symlink_to(root / ".l9", target_is_directory=True)
    (other / "uv.lock").write_text("version = 2\n", encoding="utf-8")
    hidden = _without_util_linux(env, tmp_path)
    timeline = tmp_path / "timeline"
    hidden["UV_TEST_TIMELINE"] = str(timeline)
    first = subprocess.Popen(
        ["bash", str(ENSURE), str(root)],
        env=hidden,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    second = subprocess.Popen(
        ["bash", str(ENSURE), str(other)],
        env=hidden,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    done = [proc.communicate(timeout=60) for proc in (first, second)]
    assert first.returncode == 0, done[0][1]
    assert second.returncode == 0, done[1][1]
    assert "without the environment lock" not in done[0][1] + done[1][1]
    text = timeline.read_text(encoding="utf-8")
    events: dict[str, dict[str, float]] = {}
    for line in text.splitlines():
        kind, stamp, pid = line.split()
        events.setdefault(pid, {})[kind] = float(stamp)
    assert all("start" in item and "end" in item for item in events.values()), text
    intervals = sorted((item["start"], item["end"]) for item in events.values())
    assert len(intervals) == 2, timeline.read_text(encoding="utf-8")
    assert intervals[0][1] <= intervals[1][0]


def test_posix_fallback_lock_timeout_fails_closed(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    hidden = _without_util_linux(env, tmp_path)
    hidden["L9_UV_ENV_LOCK_WAIT_S"] = "1"
    (root / ".l9").mkdir()
    with _held_exclusive(root):
        done = subprocess.run(
            ["bash", str(ENSURE), str(root)],
            env=hidden,
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert done.returncode == 75, done.stderr
    assert "still held after 1s" in done.stderr
    assert "without the environment lock" not in done.stderr
    assert not (root / ".venv" / ".l9-uv-fingerprint").exists()
    assert _sync_argv(tmp_path) == []


def test_posix_fallback_sigterm_leaves_the_detached_worker(tmp_path: Path) -> None:
    """SIGTERM to the initiating session must not abort the locked sync."""
    root, env = _writer_root(tmp_path, sync_sleep=2.0)
    hidden = _without_util_linux(env, tmp_path)
    caller = subprocess.Popen(
        ["bash", str(ENSURE), str(root)],
        env=hidden,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    assert _wait_for(lambda: (root / ".l9" / "uv-environment.installing").exists())
    os.killpg(caller.pid, signal.SIGTERM)
    caller.wait(timeout=10)
    assert not _exclusive_available(root), "the detached worker must still hold the lock"
    assert _wait_for(lambda: (root / ".venv" / ".l9-uv-fingerprint").is_file(), seconds=20)
    assert _wait_for(lambda: not (root / ".l9" / "uv-environment.installing").exists())
    assert _wait_for(lambda: _exclusive_available(root))
    logs = list((root / ".l9").glob("uv-environment.*.log"))
    assert logs, "the detached worker must keep a log after the caller dies"
    assert "synchronized locked environment" in logs[0].read_text(encoding="utf-8")


def test_posix_fallback_killed_while_waiting_does_not_sync_later(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    hidden = _without_util_linux(env, tmp_path)
    hidden["L9_UV_ENV_LOCK_WAIT_S"] = "30"
    (root / ".l9").mkdir()
    with _held_exclusive(root):
        caller = subprocess.Popen(
            ["bash", str(ENSURE), str(root)],
            env=hidden,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(0.4)
        os.killpg(caller.pid, signal.SIGTERM)
        caller.wait(timeout=10)
    time.sleep(0.8)
    assert _sync_argv(tmp_path) == []
    assert not (root / ".venv" / ".l9-uv-fingerprint").exists()


def test_posix_fallback_failed_verify_keeps_the_marker(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    hidden = _without_util_linux(env, tmp_path)
    hidden["UV_TEST_BROKEN_IMPORT"] = "1"
    (root / "uv.lock").write_text('version = 1\n\n[[package]]\nname = "l9-graphite-memory"\n')
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)],
        env=hidden,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 1, done.stderr
    assert "environment verification failed" in done.stderr
    assert (root / ".l9" / "uv-environment.installing").exists()
    assert _exclusive_available(root)


def test_posix_fallback_check_never_mutates(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    hidden = _without_util_linux(env, tmp_path)
    done = subprocess.run(
        ["bash", str(ENSURE), str(root), "check"],
        env=hidden,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 1, done.stderr
    assert "synchronization required" in done.stderr
    assert _sync_argv(tmp_path) == []
    assert not (root / ".l9" / "uv-environment.installing").exists()
    assert not (root / ".venv").exists()


def test_posix_fallback_check_during_a_live_install(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    hidden = _without_util_linux(env, tmp_path)
    (root / ".l9").mkdir()
    (root / ".l9" / "uv-environment.installing").write_text("9 now\n", encoding="utf-8")
    with _held_exclusive(root):
        check = subprocess.run(
            ["bash", str(ENSURE), str(root), "check"],
            env=hidden,
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert check.returncode == 1, check.stderr
    assert "install in progress" in check.stderr
    assert _sync_argv(tmp_path) == []


def test_posix_fallback_blocks_the_memory_reader(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path, sync_sleep=1.2)
    hidden = _without_util_linux(env, tmp_path)
    caller = subprocess.Popen(
        ["bash", str(ENSURE), str(root)],
        env=hidden,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert _wait_for(lambda: (root / ".l9" / "uv-environment.installing").exists())
    with vr.venv_ready(root, timeout=0.3) as blocked:
        assert blocked.ready is False
        assert "still in progress" in blocked.reason
    assert caller.wait(timeout=30) == 0
    stderr = caller.stderr.read() if caller.stderr is not None else ""
    assert "without the environment lock" not in stderr
    with vr.venv_ready(root, timeout=2) as ready:
        assert ready.ready is True
    assert not (root / ".l9" / "uv-environment.installing").exists()


def test_a_caller_killed_while_waiting_leaves_no_orphan_sync(tmp_path: Path) -> None:
    """The lock is waited for by the caller, not by a detached orphan.

    Waiting inside the detached child let a caller killed mid-wait (a hook
    deadline, the environment heal's timeout) leave a process that synced the
    venv minutes later, at no one's request.
    """
    root, env = _writer_root(tmp_path)
    (root / ".l9").mkdir()
    with _held_exclusive(root):
        caller = subprocess.Popen(
            ["bash", str(ENSURE), str(root)],
            env={**env, "L9_UV_ENV_LOCK_WAIT_S": "30"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(0.5)
        os.killpg(caller.pid, signal.SIGKILL)
        caller.wait(timeout=10)
    time.sleep(1.5)
    assert not (tmp_path / "lock-held-during-sync").exists(), "an orphan ran uv sync"
    assert not (root / ".venv" / ".l9-uv-fingerprint").exists()


# --- shell reader: ops/scripts/lib/venv_ready.sh (MCP launcher, python hooks) --

SHELL_READER = ROOT / "ops" / "scripts" / "lib" / "venv_ready.sh"


def _shell_wait(
    root: Path, seconds: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'. "{SHELL_READER}"; venv_ready_wait "$1" "$2"', "_", str(root), seconds],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def _posix_reader_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    """PATH with neither flock nor setsid, so the shell reader uses fcntl."""
    env = _without_util_linux(dict(os.environ), tmp_path)
    env.pop("GITHUB_ACTIONS", None)
    env.pop("CI", None)
    env.update(extra)
    return env


def _executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def test_shell_reader_is_ready_without_a_lock_and_writes_nothing(tmp_path: Path) -> None:
    root = tmp_path / "gov"
    root.mkdir()
    assert _shell_wait(root, "0").returncode == 0
    assert not (root / ".l9").exists()


@needs_util_linux
def test_shell_reader_waits_then_reports_an_install_in_progress(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    with _held_exclusive(root):
        started = time.monotonic()
        held = _shell_wait(root, "1")
    assert held.returncode == 1
    assert time.monotonic() - started >= 0.9
    assert "still in progress" in held.stderr
    assert _shell_wait(root, "1").returncode == 0


def test_shell_reader_refuses_an_interrupted_install(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    (root / vr.IN_PROGRESS_REL).write_text("1 then\n", encoding="utf-8")
    broken = _shell_wait(root, "0")
    assert broken.returncode == 2
    assert "interrupted" in broken.stderr


def test_shell_reader_without_flock_blocks_on_a_live_writer(tmp_path: Path) -> None:
    """No util-linux flock or setsid: the shell reader still waits on fcntl."""
    root = _gov(tmp_path)
    env = _posix_reader_env(tmp_path)
    with _held_exclusive(root):
        started = time.monotonic()
        held = _shell_wait(root, "1", env)
    assert held.returncode == 1
    assert time.monotonic() - started >= 0.9
    assert "still in progress" in held.stderr
    assert "interrupted" not in held.stderr
    assert _shell_wait(root, "1", env).returncode == 0


def test_shell_reader_without_flock_classifies_a_live_writer_not_the_marker(
    tmp_path: Path,
) -> None:
    """A held lock is installing, before the marker exists and after it appears."""
    root = _gov(tmp_path)
    env = _posix_reader_env(tmp_path)
    with _held_exclusive(root):
        before = _shell_wait(root, "1", env)
        (root / vr.IN_PROGRESS_REL).write_text("9 now\n", encoding="utf-8")
        after = _shell_wait(root, "1", env)
    assert before.returncode == 1
    assert "still in progress" in before.stderr
    assert "interrupted" not in before.stderr
    assert after.returncode == 1
    assert "still in progress" in after.stderr
    assert "interrupted" not in after.stderr
    stale = _shell_wait(root, "1", env)
    assert stale.returncode == 2
    assert "interrupted" in stale.stderr


def test_shell_reader_without_flock_times_out_and_a_stale_marker_is_interrupted(
    tmp_path: Path,
) -> None:
    root = _gov(tmp_path)
    env = _posix_reader_env(tmp_path)
    with _held_exclusive(root):
        started = time.monotonic()
        timed_out = _shell_wait(root, "1", env)
    assert timed_out.returncode == 1
    assert time.monotonic() - started >= 0.9
    assert "still in progress" in timed_out.stderr
    (root / vr.IN_PROGRESS_REL).write_text("dead\n", encoding="utf-8")
    started = time.monotonic()
    stale = _shell_wait(root, "5", env)
    assert stale.returncode == 2
    assert time.monotonic() - started < 2
    assert "interrupted" in stale.stderr


def test_shell_reader_without_flock_is_ready_and_writes_nothing(tmp_path: Path) -> None:
    root = tmp_path / "gov"
    root.mkdir()
    env = _posix_reader_env(tmp_path)
    ready = _shell_wait(root, "0", env)
    assert ready.returncode == 0, ready.stderr
    assert not (root / ".l9").exists()
    assert list(root.iterdir()) == []


def test_shell_reader_probe_failure_is_not_ready(tmp_path: Path) -> None:
    root = _gov(tmp_path)
    (root / vr.LOCK_REL).write_bytes(b"")
    empty = tmp_path / "empty-path"
    empty.mkdir()
    (empty / "bash").symlink_to("/bin/bash")
    env = dict(os.environ)
    env["PATH"] = str(empty)
    failed = _shell_wait(root, "1", env)
    assert failed.returncode == 3
    assert "lock probe failed" in failed.stderr
    assert "still in progress" not in failed.stderr


def test_shell_reader_keeps_the_util_linux_flock_path(tmp_path: Path) -> None:
    """Simulated util-linux flock: the shell must call it and not the fcntl helper."""
    root = _gov(tmp_path)
    calls = tmp_path / "calls"
    hold = tmp_path / "hold"
    tools = tmp_path / "stub-tools"
    _executable(
        tools / "flock",
        "#!/bin/bash\n"
        'if [ "${1:-}" = "--version" ]; then echo "flock from util-linux 2.39.2"; exit 0; fi\n'
        'printf "flock %s\\n" "$*" >> "$CALLS"\n'
        'if [ -f "$HOLD" ]; then sleep "$3"; exit 1; fi\n'
        "exit 0\n",
    )
    _executable(
        tools / "python3",
        '#!/bin/bash\nprintf "python3 %s\\n" "$*" >> "$CALLS"\nexit 99\n',
    )
    env = _posix_reader_env(tmp_path, CALLS=str(calls), HOLD=str(hold))
    env["PATH"] = str(tools) + os.pathsep + env["PATH"]
    (root / vr.LOCK_REL).write_bytes(b"")
    ready = _shell_wait(root, "1", env)
    assert ready.returncode == 0, ready.stderr
    recorded = calls.read_text(encoding="utf-8")
    assert "flock -s -w 1 " in recorded
    assert "python3" not in recorded
    calls.write_text("", encoding="utf-8")
    hold.write_text("held\n", encoding="utf-8")
    started = time.monotonic()
    busy = _shell_wait(root, "1", env)
    assert busy.returncode == 1
    assert time.monotonic() - started >= 0.9
    assert "still in progress" in busy.stderr
    assert "python3" not in calls.read_text(encoding="utf-8")


def test_exec_does_not_run_a_partial_interpreter_while_the_writer_holds_the_lock(
    tmp_path: Path,
) -> None:
    root = _gov(tmp_path)
    flag = tmp_path / "flag"
    stamp = tmp_path / "stamp"
    flag.write_text("PARTIAL\n", encoding="utf-8")
    program = tmp_path / "python-under-test"
    _executable(
        program,
        '#!/bin/bash\ncat "$FLAG" >> "$STAMP"\nexit 0\n',
    )
    script = tmp_path / "hook.py"
    script.write_text("# dispatched as an argument\n", encoding="utf-8")
    env = _posix_reader_env(tmp_path, FLAG=str(flag), STAMP=str(stamp))
    with _held_exclusive(root):
        started = subprocess.Popen(
            [
                "bash",
                "-c",
                f'. "{SHELL_READER}"; venv_ready_exec "$1" "$2" "$3" "$4"',
                "_",
                str(root),
                str(program),
                str(script),
                "5",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert _wait_for(lambda: started.poll() is None)
        time.sleep(0.4)
        assert started.poll() is None, "the reader executed while the writer held the lock"
        assert not stamp.exists()
        flag.write_text("COMPLETE\n", encoding="utf-8")
    stdout, stderr = started.communicate(timeout=15)
    assert started.returncode == 0, stderr
    assert stamp.read_text(encoding="utf-8") == "COMPLETE\n"
    assert "PARTIAL" not in stamp.read_text(encoding="utf-8")
    assert stdout == ""


def _hook_fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    """A HOME whose governance tree is only the readiness seam under test."""
    home = tmp_path / "home"
    gov = home / ".cursor-governance"
    lib = gov / "ops" / "scripts" / "lib"
    lib.mkdir(parents=True)
    (gov / "ops" / "scripts" / "uv_environment_lock.py").symlink_to(
        ROOT / "ops" / "scripts" / "uv_environment_lock.py"
    )
    (lib / "venv_ready.sh").symlink_to(SHELL_READER)
    (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
    hook_dir = gov / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
    hook_dir.mkdir(parents=True)
    (hook_dir / "reader_probe.py").write_text("print('should-not-run')\n", encoding="utf-8")
    stamp = tmp_path / "hook-stamp"
    program = gov / ".venv" / "bin" / "python3"
    _executable(program, '#!/bin/bash\nprintf "ran %s\\n" "$1" >> "$STAMP"\nexit 0\n')
    skip_log = tmp_path / "hook-skips.log"
    env = _posix_reader_env(
        tmp_path,
        HOME=str(home),
        STAMP=str(stamp),
        L9_SURFACE_GUARD="0",
        L9_VENV_READY_WAIT_S="1",
        L9_HOOK_SKIP_LOG=str(skip_log),
    )
    env.pop("CLAUDE_CODE_REMOTE", None)
    env.pop("L9_GOVERNANCE_DIR", None)
    return gov, stamp, skip_log, env


def _run_hook(
    tmp_path: Path, hook_class: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    launcher = (
        ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
    )
    return subprocess.run(
        ["bash", str(launcher), "--class", hook_class, "reader_probe.py"],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
        cwd=str(tmp_path),
    )


def test_hook_executes_when_no_install_is_in_progress(tmp_path: Path) -> None:
    _gov_unused, stamp, _skip_log, env = _hook_fixture(tmp_path)
    ran = _run_hook(tmp_path, "gate", env)
    assert ran.returncode == 0, ran.stderr
    assert "BLOCKING" not in ran.stderr
    assert "ran " in stamp.read_text(encoding="utf-8")


def test_gate_fails_closed_and_observer_records_a_skip_when_the_venv_is_busy(
    tmp_path: Path,
) -> None:
    gov, stamp, skip_log, env = _hook_fixture(tmp_path)
    (gov / ".l9").mkdir()
    with _held_exclusive(gov):
        gate = _run_hook(tmp_path, "gate", env)
        observer = _run_hook(tmp_path, "observer", env)
    assert gate.returncode == 2, gate.stderr
    assert "BLOCKING" in gate.stderr
    assert "cannot evaluate" in gate.stderr
    assert not stamp.exists()
    assert observer.returncode == 0, observer.stderr
    assert "did NOT run" in observer.stderr
    assert skip_log.is_file()
    assert "not safe to execute" in skip_log.read_text(encoding="utf-8")
    assert not stamp.exists()


def test_a_missing_readiness_probe_does_not_authorize_a_gate(tmp_path: Path) -> None:
    gov, stamp, skip_log, env = _hook_fixture(tmp_path)
    (gov / "ops" / "scripts" / "lib" / "venv_ready.sh").unlink()
    gate = _run_hook(tmp_path, "gate", env)
    observer = _run_hook(tmp_path, "observer", env)
    assert gate.returncode == 2, gate.stderr
    assert "probe missing" in gate.stderr
    assert observer.returncode == 0, observer.stderr
    assert "probe missing" in skip_log.read_text(encoding="utf-8")
    assert not stamp.exists()


def test_memory_launcher_refuses_a_live_or_interrupted_install(tmp_path: Path) -> None:
    gov = tmp_path / "gov"
    lib = gov / "ops" / "scripts" / "lib"
    lib.mkdir(parents=True)
    (gov / "ops" / "scripts" / "uv_environment_lock.py").symlink_to(
        ROOT / "ops" / "scripts" / "uv_environment_lock.py"
    )
    (lib / "venv_ready.sh").symlink_to(SHELL_READER)
    (lib / "bind_memory_interpreter.sh").write_text(
        "# not sourced when readiness fails\n", encoding="utf-8"
    )
    (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
    (gov / ".l9").mkdir()
    launcher = ROOT / "ops" / "memory" / "run_memory_mcp.sh"
    env = dict(os.environ)
    env.update(
        {
            "L9_GOVERNANCE_DIR": str(gov),
            "L9_VENV_READY_WAIT_S": "1",
        }
    )
    env.pop("CLAUDE_CODE_REMOTE", None)
    with _held_exclusive(gov):
        live = subprocess.run(
            ["bash", str(launcher)],
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
    assert live.returncode == 1, live.stderr
    assert "not ready" in live.stderr
    assert "still in progress" in live.stderr
    assert "agent identity" not in live.stderr
    (gov / vr.LOCK_REL).unlink()
    (gov / vr.IN_PROGRESS_REL).write_text("dead\n", encoding="utf-8")
    stale = subprocess.run(
        ["bash", str(launcher)],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    assert stale.returncode == 1, stale.stderr
    assert "interrupted" in stale.stderr
    assert not (gov / vr.LOCK_REL).exists()


# --- writer: the interpreter the locked environment is built for ------------
#
# uv resolves an interpreter before it resolves wheels, and it prefers an
# already-active environment. On this fleet that is an x86_64 conda base, so a
# fresh worktree on Apple silicon got a Rosetta .venv; uv.lock has no x86_64
# macOS cryptography wheel, so the wheels-only sync failed with "no binary
# distribution" and the whole worktree had no usable environment. `make venv`
# ran `uv sync` WITHOUT --no-build and papered over the same mismatch by
# compiling the sdist, which is why it looked like a lockfile defect.


def test_the_local_sync_requests_a_host_native_interpreter(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 0, done.stderr
    argv = _sync_argv(tmp_path)
    assert argv, "uv sync must have run"
    assert "--managed-python" in argv[-1], argv
    assert "--no-build" in argv[-1], "wheels-only is unchanged"


def test_ci_keeps_its_provisioned_interpreter(tmp_path: Path) -> None:
    """Workflows provision Python with actions/setup-python; uv must use it."""
    for marker in ("GITHUB_ACTIONS", "CI"):
        root, env = _writer_root(tmp_path / marker)
        env[marker] = "true"
        done = subprocess.run(
            ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
        )
        assert done.returncode == 0, done.stderr
        argv = _sync_argv(tmp_path / marker)
        assert argv, marker
        assert "--managed-python" not in argv[-1], marker


def test_a_uv_without_the_flag_is_not_given_it(tmp_path: Path) -> None:
    """Floor pin is uv >= 0.8.0; the flag is probed, never assumed."""
    root, env = _writer_root(tmp_path)
    env["UV_TEST_NO_MANAGED_FLAG"] = "1"
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 0, done.stderr
    argv = _sync_argv(tmp_path)
    assert argv and "--managed-python" not in argv[-1], argv


def test_a_foreign_architecture_venv_is_resynchronized(tmp_path: Path) -> None:
    """An emulated .venv is not this host's environment, however complete."""
    root, env = _writer_root(tmp_path)
    first = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert first.returncode == 0, first.stderr
    assert (root / ".venv" / ".l9-uv-fingerprint").is_file()

    foreign = {**env, "UV_TEST_FAKE_MACHINE": "sparc64"}
    check = subprocess.run(
        ["bash", str(ENSURE), str(root), "check"],
        env=foreign,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert check.returncode == 1
    assert "on a" in check.stderr and "host; re-synchronizing" in check.stderr
    assert "sparc64" in check.stderr

    before = len(_sync_argv(tmp_path))
    again = subprocess.run(
        ["bash", str(ENSURE), str(root)],
        env=foreign,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert again.returncode == 0, again.stderr
    assert len(_sync_argv(tmp_path)) == before + 1, "the mismatch must force a real sync"


def test_a_matching_architecture_venv_stays_cached(tmp_path: Path) -> None:
    """The guard must not re-sync a healthy environment on every call."""
    root, env = _writer_root(tmp_path)
    assert (
        subprocess.run(
            ["bash", str(ENSURE), str(root)], env=env, capture_output=True, timeout=120
        ).returncode
        == 0
    )
    before = len(_sync_argv(tmp_path))
    again = subprocess.run(
        ["bash", str(ENSURE), str(root), "check"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert again.returncode == 0, again.stderr
    assert "cached locked environment" in again.stderr
    assert len(_sync_argv(tmp_path)) == before, "no sync for a healthy environment"


def test_a_second_apply_on_unchanged_inputs_does_not_resync(tmp_path: Path) -> None:
    """APPLY mode, twice, same inputs: one sync, one fingerprint, no second sync.

    Regression (PR #696 CI): the Test Suite built ``.venv`` with a raw
    ``uv sync`` that wrote no fingerprint, so the first repository test to
    reach ``run_pr_gate.sh`` → ``ensure_gov_python.sh`` (APPLY, not check)
    re-entered ``uv sync`` under live xdist workers. Once the owner has run
    APPLY once, a later APPLY on unchanged pyproject/uv.lock/interpreter must
    be a cached no-op: the fingerprint stays valid and the sync count does
    not move. ``check`` mode is covered above; this pins the mode the gate
    actually calls.
    """
    root, env = _writer_root(tmp_path)
    fingerprint = root / ".venv" / ".l9-uv-fingerprint"
    first = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert first.returncode == 0, first.stderr
    assert "synchronized locked environment" in first.stderr
    assert len(_sync_argv(tmp_path)) == 1, "the first apply syncs exactly once"
    assert fingerprint.is_file()
    recorded = fingerprint.read_text(encoding="utf-8")
    assert recorded.strip()
    assert (root / ".venv" / "bin" / "python3").is_file()

    second = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert second.returncode == 0, second.stderr
    assert "cached locked environment" in second.stderr
    assert "synchronized locked environment" not in second.stderr
    assert len(_sync_argv(tmp_path)) == 1, "a second apply on unchanged inputs must not sync"
    assert fingerprint.read_text(encoding="utf-8") == recorded, "fingerprint stays valid"
    assert (root / ".venv" / "bin" / "python3").is_file(), "python3 survives the second apply"
    assert not (root / ".l9" / "uv-environment.installing").exists()


# --- protected root: the checkout a test suite executes from -----------------
#
# Regression (PR #696 / main d864e21 CI): tests ran the real installer,
# SessionStart hook and ensure_gov_python.sh against this checkout, each
# reaching `apply` on the .venv the other xdist workers were executing from.
# Lock + marker made memory readers refuse the venv; a sync that asked for a
# different interpreter rebuilt it out from under them. The root conftest now
# registers each controller pid under .l9/uv-environment.protected.d/.


def _protect(root: Path, pid: int) -> None:
    registry = root / ".l9" / "uv-environment.protected.d"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / str(pid)).touch()


def _dead_pid() -> int:
    child = subprocess.Popen(["true"])
    child.wait()
    return child.pid


def test_the_running_session_protects_this_checkout() -> None:
    registry = ROOT / ".l9" / "uv-environment.protected.d"
    live = []
    for entry in registry.iterdir() if registry.is_dir() else ():
        try:
            os.kill(int(entry.name), 0)
        except (OSError, ValueError):
            continue
        live.append(entry.name)
    assert live, "root conftest did not register this session's controller"


def test_one_live_session_keeps_the_root_protected_after_another_ends(tmp_path: Path) -> None:
    """Codex P2 on #702: overlapping controllers must not lift each other's protection."""
    root, env = _writer_root(tmp_path)
    _protect(root, _dead_pid())  # the session that already finished
    _protect(root, os.getpid())  # the one still running
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 1, done.stderr
    assert "protected by a running test session" in done.stderr
    assert _sync_argv(tmp_path) == []


def test_a_protected_root_is_never_synced(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    _protect(root, os.getpid())
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 1, done.stderr
    assert "protected by a running test session" in done.stderr
    assert "synchronization required" in done.stderr
    assert _sync_argv(tmp_path) == [], "a protected root is verified, never synced"
    assert not (root / ".venv").exists()
    assert not (root / ".l9" / "uv-environment.installing").exists()


def test_a_protected_root_reached_through_a_symlink_is_still_protected(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    _protect(root, os.getpid())
    linked = tmp_path / "home" / ".cursor-governance"
    linked.parent.mkdir()
    linked.symlink_to(root, target_is_directory=True)
    done = subprocess.run(
        ["bash", str(ENSURE), str(linked)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 1, done.stderr
    assert _sync_argv(tmp_path) == []


def test_a_cached_protected_root_verifies_without_a_lock_or_marker(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    first = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert first.returncode == 0, first.stderr
    (root / ".l9" / "uv-environment.lock").unlink(missing_ok=True)

    _protect(root, os.getpid())
    second = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert second.returncode == 0, second.stderr
    assert "cached locked environment" in second.stderr
    assert len(_sync_argv(tmp_path)) == 1, "the protected apply did not sync"
    assert not (root / ".l9" / "uv-environment.lock").exists(), "no lock was taken"
    assert not (root / ".l9" / "uv-environment.installing").exists()


def test_a_stale_protection_no_longer_blocks_apply(tmp_path: Path) -> None:
    root, env = _writer_root(tmp_path)
    _protect(root, _dead_pid())
    done = subprocess.run(
        ["bash", str(ENSURE), str(root)], env=env, capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 0, done.stderr
    assert "protected" not in done.stderr
    assert len(_sync_argv(tmp_path)) == 1
