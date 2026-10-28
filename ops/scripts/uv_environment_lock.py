#!/usr/bin/env python3
"""POSIX lock and session adapter for ensure_uv_environment.sh.

Process safety only. The shell script remains the only uv sync owner. This
module acquires the existing ``.l9/uv-environment.lock`` with ``fcntl.flock``
and runs that script in a new session so a SIGTERM to the caller does not
kill the mutation or drop the lock early.

The lock is taken on fd 8 before the child is spawned and inherited across
``start_new_session``. It is never unlocked explicitly: on this platform
``LOCK_UN`` releases the open-file-description lock the child is holding.
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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in {"probe-shared", "launch"}:
        return _fail(
            "usage: uv_environment_lock.py probe-shared --lock PATH"
            " | launch --lock PATH --wait SECONDS --log-dir DIR -- COMMAND...",
            2,
        )
    if args[0] == "probe-shared":
        return _probe_main(args[1:])
    return _launch_main(args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
