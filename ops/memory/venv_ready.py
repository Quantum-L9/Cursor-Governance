"""Wait for the locked governance ``.venv`` to finish installing before memory runs.

Claude Code starts every SessionStart hook at once and offers no ordering
(hooks reference: "All matching hooks run in parallel"). One hook installs the
governance environment (``ops/scripts/ensure_uv_environment.sh``: ``uv sync``
and the seal's ``pip install --force-reinstall`` of ``l9_graphite_memory``)
while another hydrates memory through that same environment. Observed
2026-09-24: hydrate spawned ``l9-memory`` at 23:48:55.89Z, the reinstall wrote
``l9_graphite_memory/contracts/review.py`` at 23:48:57.52Z, and the runtime
died with ``ModuleNotFoundError: No module named
'l9_graphite_memory.contracts.review'`` — reported as a canonical
``INVALID_RECEIPT`` although memory itself was never reached.

The writer side holds an exclusive ``flock`` on ``.l9/uv-environment.lock`` for
the whole mutation and leaves ``.l9/uv-environment.installing`` behind only if
the install was interrupted or could not be verified. This module is the reader
side: take the same lock SHARED before a runtime is spawned, hold it for the
call so no sync can start underneath it, and refuse a venv whose install never
completed.

It never creates the lock file: an environment no new-style writer has touched
has nothing to wait for. Waiting is bounded per process and per lock, not per
call, so a hook that makes several memory calls cannot multiply the wait past
its own registration timeout.
"""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

LOCK_REL = Path(".l9/uv-environment.lock")
IN_PROGRESS_REL = Path(".l9/uv-environment.installing")

ENV_WAIT = "L9_VENV_READY_WAIT_S"
#: Seconds. Sized under the memory_prefetch.py SessionStart registration (25 s)
#: with room for the hydrate calls themselves (4-7 s measured).
DEFAULT_WAIT_S = 15.0
_POLL_S = 0.1

#: First-wait deadline per lock path, shared by every later wait in this process
#: while the lock stays held. Cleared once the lock is acquired, and ignored
#: once it is older than _SHARED_DEADLINE_TTL_S past its expiry.
_DEADLINES: dict[Path, float] = {}
_SHARED_DEADLINE_TTL_S = 60.0


@dataclass(frozen=True)
class VenvReadiness:
    ready: bool
    reason: str = ""
    waited_s: float = 0.0


def wait_budget(env: Mapping[str, str] | None = None) -> float:
    raw = str((env if env is not None else os.environ).get(ENV_WAIT, "")).strip()
    try:
        value = float(raw) if raw else DEFAULT_WAIT_S
    except ValueError:
        return DEFAULT_WAIT_S
    return value if value >= 0 else DEFAULT_WAIT_S


def governance_root_for_cli(cli: str | os.PathLike[str] | None) -> Path | None:
    """``<root>/.venv/bin/l9-memory`` -> ``<root>``; ``None`` for any other layout.

    Only a ``.venv`` directly under a root is an environment the locked writer
    manages; a developer's own interpreter has no lock to honour.
    """

    if not cli:
        return None
    path = Path(cli)
    if len(path.parents) < 3 or path.parents[1].name != ".venv":
        return None
    return path.parents[2]


def _interrupted(root: Path) -> VenvReadiness | None:
    marker = root / IN_PROGRESS_REL
    if not marker.exists():
        return None
    return VenvReadiness(
        False,
        f"governance venv install was interrupted before it completed ({marker} present); "
        f"repair: bash {root / 'ops/scripts/ensure_uv_environment.sh'} {root} apply",
    )


@contextmanager
def venv_ready(root: Path, *, timeout: float | None = None) -> Iterator[VenvReadiness]:
    """Yield the environment's readiness, holding the shared lock while ready."""

    lock_path = root / LOCK_REL
    try:
        fd = os.open(lock_path, os.O_RDONLY)
    except FileNotFoundError:
        yield _interrupted(root) or VenvReadiness(True)
        return
    except OSError as exc:
        # An unreadable lock is not proof of a sync in progress; say so and go on.
        yield _interrupted(root) or VenvReadiness(True, f"venv lock unreadable: {exc}")
        return
    try:
        budget = wait_budget() if timeout is None else max(0.0, timeout)
        started = time.monotonic()
        deadline = _DEADLINES.get(lock_path)
        if deadline is None or started > deadline + _SHARED_DEADLINE_TTL_S:
            # A long-lived process (an MCP server, a pytest session) must not
            # carry a give-up from one install into the next, unrelated one.
            deadline = started + budget
            _DEADLINES[lock_path] = deadline
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    yield VenvReadiness(
                        False,
                        "governance venv install still in progress "
                        f"({lock_path} held); waited {time.monotonic() - started:.1f}s",
                        time.monotonic() - started,
                    )
                    return
                time.sleep(_POLL_S)
        _DEADLINES.pop(lock_path, None)
        waited = time.monotonic() - started
        try:
            broken = _interrupted(root)
            yield broken or VenvReadiness(True, waited_s=waited)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
