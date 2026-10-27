#!/usr/bin/env python3
"""POSIX lock and session adapter for ensure_uv_environment.sh.

Process safety only. The shell script remains the only uv sync owner. This
module acquires the existing ``.l9/uv-environment.lock`` with ``fcntl.flock``
and runs that script in a new session so a SIGTERM to the caller does not
kill the mutation or drop the lock early.

The lock is taken on fd 8 before the child is spawned and inherited across
``start_new_session``. It is never unlocked explicitly: on this platform
``LOCK_UN`` releases the open-file-description lock the child is holding.

``wait-shared`` and ``exec-shared`` are the reader side of the same lock.
They do not create the lock file. ``exec-shared`` keeps the shared lock open
across the replacement image so a writer cannot enter between the check and
the exec. Its failure codes are 80, 81, and 82 so a hook's own 0 or 2 is
never read as "did not run".
"""

from __future__ import annotations

import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

LOCK_FD = 8
_POLL_S = 0.05
_LOG_PREFIX = "uv-environment."
_LOG_SUFFIX = ".log"
# exec-shared did not replace the process. Outside the hook contract
# (0 proceed, 2 block) so a completed hook is never classified as a probe.
EXEC_BUSY = 80
EXEC_INTERRUPTED = 81
EXEC_PROBE = 82


def _fail(message: str, code: int) -> int:
    print(message, file=sys.stderr)
    return code


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _sweep_dead_logs(log_dir: Path) -> None:
    if not log_dir.is_dir():
        return
    for old in log_dir.glob(f"{_LOG_PREFIX}*{_LOG_SUFFIX}"):
        middle = old.name[len(_LOG_PREFIX) : -len(_LOG_SUFFIX)]
        if not middle.isdigit():
            continue
        if not _alive(int(middle)):
            old.unlink(missing_ok=True)


def _acquire(wait_s: int, lock_path: Path) -> int:
    """Block until fd 8 holds an exclusive flock, or return 75 on timeout."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    source = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    if source != LOCK_FD:
        os.dup2(source, LOCK_FD)
        os.close(source)
    os.set_inheritable(LOCK_FD, True)
    deadline = time.monotonic() + wait_s
    while True:
        try:
            fcntl.flock(LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return 0
        except InterruptedError:
            continue
        except BlockingIOError:
            if time.monotonic() >= deadline:
                return _fail(
                    f"UV: {lock_path} still held after {wait_s}s; "
                    "another sync owns this environment",
                    75,
                )
            time.sleep(min(_POLL_S, max(0.0, deadline - time.monotonic())))


def _classify_shared(lock_path: Path, wait_s: int, marker: Path | None) -> tuple[int, int | None]:
    """Return ``(code, fd)``.

    ``fd`` is open and holds ``LOCK_SH`` only when ``code`` is 0 and the lock
    file already existed. The file is never created. Codes: 0 ready, 1 the
    exclusive writer is still alive after the wait, 2 a marker with no writer,
    3 the probe itself failed.
    """
    if wait_s < 0:
        return 3, None
    try:
        fd = os.open(lock_path, os.O_RDONLY)
    except FileNotFoundError:
        if marker is not None and marker.exists():
            return 2, None
        return 0, None
    except OSError:
        return 3, None
    deadline = time.monotonic() + wait_s
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except InterruptedError:
            continue
        except BlockingIOError:
            if time.monotonic() >= deadline:
                os.close(fd)
                return 1, None
            time.sleep(min(_POLL_S, max(0.0, deadline - time.monotonic())))
            continue
        except OSError:
            os.close(fd)
            return 3, None
        break
    if marker is not None and marker.exists():
        os.close(fd)
        return 2, None
    return 0, fd


def wait_shared(lock_path: Path, wait_s: int, marker: Path | None) -> int:
    """Block for a shared lock, then release it. See ``_classify_shared``."""
    code, fd = _classify_shared(lock_path, wait_s, marker)
    if fd is not None:
        os.close(fd)
    return code


def exec_shared(lock_path: Path, wait_s: int, marker: Path | None, command: list[str]) -> int:
    """Replace this process only while the shared lock is held, or the lock is absent.

    Failure returns ``EXEC_BUSY``, ``EXEC_INTERRUPTED``, or ``EXEC_PROBE``
    and does not execute ``command``.
    """
    if not command or not command[0]:
        return EXEC_PROBE
    code, fd = _classify_shared(lock_path, wait_s, marker)
    if code == 1:
        return EXEC_BUSY
    if code == 2:
        return EXEC_INTERRUPTED
    if code != 0:
        return EXEC_PROBE
    if fd is not None:
        try:
            os.set_inheritable(fd, True)
        except OSError:
            os.close(fd)
            return EXEC_PROBE
    try:
        os.execv(command[0], command)
    except OSError:
        if fd is not None:
            os.close(fd)
        return EXEC_PROBE


def probe_shared(lock_path: Path) -> int:
    """Return 0 when a shared lock is free, 1 when a writer holds it, 2 on error."""
    try:
        fd = os.open(lock_path, os.O_RDONLY)
    except FileNotFoundError:
        return 0
    except OSError as exc:
        return _fail(f"UV: cannot probe {lock_path}: {exc}", 2)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except InterruptedError:
            return _fail(f"UV: cannot probe {lock_path}: interrupted", 2)
        except BlockingIOError:
            return 1
    finally:
        os.close(fd)
    return 0


def _replay(log_path: Path) -> None:
    try:
        data = log_path.read_bytes()
    except OSError:
        return
    if data:
        sys.stderr.buffer.write(data)
        sys.stderr.buffer.flush()


def launch(lock_path: Path, wait_s: int, log_dir: Path, command: list[str]) -> int:
    if wait_s < 0:
        return _fail("UV: lock wait must be a non-negative integer", 2)
    if not command:
        return _fail("UV: locked sync command is missing", 2)
    acquired = _acquire(wait_s, lock_path)
    if acquired != 0:
        return acquired
    log_dir.mkdir(parents=True, exist_ok=True)
    _sweep_dead_logs(log_dir)
    log_path = log_dir / f"{_LOG_PREFIX}{os.getpid()}{_LOG_SUFFIX}"
    env = os.environ.copy()
    env["_L9_UV_ENV_LOCKED"] = "1"
    with log_path.open("wb") as log_handle:
        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                pass_fds=(LOCK_FD,),
                env=env,
                close_fds=True,
            )
        except OSError as exc:
            log_path.unlink(missing_ok=True)
            return _fail(f"UV: failed to start locked sync: {exc}", 2)
    returncode = proc.wait()
    _replay(log_path)
    log_path.unlink(missing_ok=True)
    if returncode < 0:
        return 128 + (-returncode)
    return returncode


def _option(args: list[str], name: str) -> str | None:
    if name not in args:
        return None
    index = args.index(name)
    if index + 1 >= len(args):
        return None
    return args[index + 1]


def _probe_main(args: list[str]) -> int:
    raw = _option(args, "--lock")
    if raw is None:
        return _fail("UV: probe-shared requires --lock PATH", 2)
    return probe_shared(Path(raw))


def _launch_main(args: list[str]) -> int:
    if "--" not in args:
        return _fail("UV: launch requires -- before the sync command", 2)
    split = args.index("--")
    options, command = args[:split], args[split + 1 :]
    raw_lock = _option(options, "--lock")
    raw_wait = _option(options, "--wait")
    raw_log_dir = _option(options, "--log-dir")
    if raw_lock is None or raw_wait is None or raw_log_dir is None:
        return _fail("UV: launch requires --lock, --wait, and --log-dir", 2)
    if not raw_wait.isdigit():
        return _fail("UV: lock wait must be a non-negative integer", 2)
    return launch(Path(raw_lock), int(raw_wait), Path(raw_log_dir), command)


def _reader_main(args: list[str], *, replace: bool) -> int:
    if replace and "--" not in args:
        return EXEC_PROBE
    if replace:
        split = args.index("--")
        options, command = args[:split], args[split + 1 :]
    else:
        options, command = args, []
    raw_lock = _option(options, "--lock")
    raw_wait = _option(options, "--wait")
    raw_marker = _option(options, "--marker")
    if raw_lock is None or raw_wait is None or not raw_wait.isdigit():
        return EXEC_PROBE if replace else 3
    marker = Path(raw_marker) if raw_marker else None
    if replace:
        return exec_shared(Path(raw_lock), int(raw_wait), marker, command)
    return wait_shared(Path(raw_lock), int(raw_wait), marker)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in {"probe-shared", "launch", "wait-shared", "exec-shared"}:
        return _fail(
            "usage: uv_environment_lock.py probe-shared --lock PATH"
            " | wait-shared --lock PATH --wait SECONDS [--marker PATH]"
            " | exec-shared --lock PATH --wait SECONDS [--marker PATH] -- COMMAND..."
            " | launch --lock PATH --wait SECONDS --log-dir DIR -- COMMAND...",
            2,
        )
    if args[0] == "probe-shared":
        return _probe_main(args[1:])
    if args[0] == "wait-shared":
        return _reader_main(args[1:], replace=False)
    if args[0] == "exec-shared":
        return _reader_main(args[1:], replace=True)
    return _launch_main(args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
