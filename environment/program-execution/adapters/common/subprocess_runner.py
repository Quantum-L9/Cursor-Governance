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


def run_argv(
    argv: Sequence[str],
    *,
    cwd: str | Path,
    timeout_seconds: int,
    environment: Mapping[str, str] | None = None,
    stdin: str | None = None,
) -> CommandResult:
    if isinstance(argv, (str, bytes)) or not argv:
        raise ValueError("argv must be a non-empty sequence of strings")
    normalized = tuple(str(item) for item in argv)
    executable = shutil.which(normalized[0])
    if executable is None:
        raise FileNotFoundError(normalized[0])
    env = os.environ.copy()
    if environment:
        env.update({str(key): str(value) for key, value in environment.items()})
    start = time.monotonic()
    process = subprocess.Popen(
        normalized,
        cwd=Path(cwd).resolve(),
        env=env,
        stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=stdin, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    duration = time.monotonic() - start
    stdout = stdout[-_MAX_OUTPUT:]
    stderr = stderr[-_MAX_OUTPUT:]
    return CommandResult(
        argv=normalized,
        executable=executable,
        exit_code=process.returncode,
        stdout=stdout,
        stderr=stderr,
        stdout_digest=_SHA256_PREFIX + hashlib.sha256(stdout.encode()).hexdigest(),
        stderr_digest=_SHA256_PREFIX + hashlib.sha256(stderr.encode()).hexdigest(),
        duration_seconds=round(duration, 6),
        timed_out=timed_out,
        environment_fingerprint=_fingerprint_environment(env),
    )
