from __future__ import annotations

import hashlib
import os
import platform
import shutil
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import structlog

log = structlog.get_logger("peer_execution.subprocess")

_MAX_OUTPUT = 1_000_000
_SECRET_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "KEY", "CREDENTIAL")
_SHA256_PREFIX = "sha256:"


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    executable: str
    exit_code: int
    stdout: str
    stderr: str
    stdout_digest: str
    stderr_digest: str
    duration_seconds: float
    timed_out: bool
    environment_fingerprint: str
    #: `stdout` / `stderr` hold at most `_MAX_OUTPUT` bytes of the tail. When
    #: the process wrote more, the flag says so and `*_bytes` says how much;
    #: the digests are always over the full raw stream, never the tail, so a
    #: truncated capture cannot be mistaken for the complete output.
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    stdout_bytes: int = 0
    stderr_bytes: int = 0

    def to_evidence(self) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "executable": self.executable,
            "exit_code": self.exit_code,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "environment_fingerprint": self.environment_fingerprint,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
        }


def _fingerprint_environment(environment: Mapping[str, str]) -> str:
    visible = {
        key: value
        for key, value in environment.items()
        if not any(marker in key.upper() for marker in _SECRET_MARKERS)
    }
    visible["platform"] = platform.platform()
    visible["python"] = platform.python_version()
    payload = "\n".join(f"{key}={visible[key]}" for key in sorted(visible))
    return _SHA256_PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_argv(argv: Sequence[str]) -> tuple[str, ...]:
    if isinstance(argv, (str, bytes)) or not argv:
        raise ValueError("argv must be a non-empty sequence of strings")
    normalized: list[str] = []
    for index, item in enumerate(argv):
        if not isinstance(item, str):
            raise ValueError(f"argv[{index}] must be a string")
        if index == 0 and not item.strip():
            raise ValueError("argv[0] must name an executable")
        if "\x00" in item:
            raise ValueError(f"argv[{index}] contains a null byte")
        normalized.append(item)
    return tuple(normalized)


def _merge_environment(
    base: Mapping[str, str],
    overrides: Mapping[str, str] | None,
) -> dict[str, str]:
    merged = dict(base)
    if not overrides:
        return merged
    for key, value in overrides.items():
        if not isinstance(key, str) or not key or "=" in key or "\x00" in key:
            raise ValueError(f"environment key is invalid: {key!r}")
        if not isinstance(value, str) or "\x00" in value:
            raise ValueError(f"environment value must be a string for {key!r}")
        merged[key] = value
    return merged


def _bound_stream(raw: bytes | None) -> tuple[str, bool, int]:
    """Decode the tail of a captured stream: (text, truncated, raw byte count).

    Captured as bytes and decoded with replacement so a process that emits
    non-UTF-8 output still yields a result (and a receipt) instead of dying
    in the runner with a `UnicodeDecodeError`. Only the last `_MAX_OUTPUT`
    bytes are kept as text; the caller digests the full raw stream.
    """
    data = raw or b""
    truncated = len(data) > _MAX_OUTPUT
    tail = data[-_MAX_OUTPUT:] if truncated else data
    return tail.decode("utf-8", errors="replace"), truncated, len(data)


def _kill_process_group(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return


def run_argv(
    argv: Sequence[str],
    *,
    cwd: str | Path,
    timeout_seconds: int,
    environment: Mapping[str, str] | None = None,
    stdin: str | None = None,
) -> CommandResult:
    normalized = _normalize_argv(argv)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise ValueError("timeout_seconds must be an integer")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if stdin is not None and not isinstance(stdin, str):
        raise ValueError("stdin must be a string or null")
    executable = shutil.which(normalized[0])
    if executable is None:
        raise FileNotFoundError(normalized[0])
    working_directory = Path(cwd).expanduser().resolve()
    if not working_directory.is_dir():
        raise NotADirectoryError(str(working_directory))
    env = _merge_environment(os.environ, environment)
    stdin_bytes = stdin.encode("utf-8") if stdin is not None else None
    start = time.monotonic()
    process = subprocess.Popen(
        normalized,
        cwd=working_directory,
        env=env,
        stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        start_new_session=True,
    )
    timed_out = False
    try:
        raw_stdout, raw_stderr = process.communicate(input=stdin_bytes, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        log.warning("subprocess_timed_out", timeout_seconds=timeout_seconds)
        timed_out = True
        _kill_process_group(process.pid, signal.SIGTERM)
        try:
            raw_stdout, raw_stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _kill_process_group(process.pid, signal.SIGKILL)
            raw_stdout, raw_stderr = process.communicate()
    duration = time.monotonic() - start
    raw_stdout = raw_stdout or b""
    raw_stderr = raw_stderr or b""
    stdout, stdout_truncated, stdout_bytes = _bound_stream(raw_stdout)
    stderr, stderr_truncated, stderr_bytes = _bound_stream(raw_stderr)
    return CommandResult(
        argv=normalized,
        executable=executable,
        exit_code=process.returncode,
        stdout=stdout,
        stderr=stderr,
        stdout_digest=_SHA256_PREFIX + hashlib.sha256(raw_stdout).hexdigest(),
        stderr_digest=_SHA256_PREFIX + hashlib.sha256(raw_stderr).hexdigest(),
        duration_seconds=round(duration, 6),
        timed_out=timed_out,
        environment_fingerprint=_fingerprint_environment(env),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
    )
