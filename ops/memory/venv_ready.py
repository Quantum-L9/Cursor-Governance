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

It creates the lock file when absent, so a reader that arrives first also makes
a later writer wait. Waiting is bounded per install, not per call, so a hook
that makes several memory calls cannot multiply the wait past its own
registration timeout.
"""

from __future__ import annotations

import fcntl
import math
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

#: Give-up deadline per lock path, keyed to the install it was waiting on (the
#: writer's ``.l9/uv-environment.installing`` text: pid + start time). Every
#: later wait on the SAME install shares it, so several calls cannot multiply
#: the wait; a different install — a long-lived MCP server or pytest session
#: meeting the next, unrelated sync — gets a fresh budget. Cleared once the
#: lock is acquired.
_DEADLINES: dict[Path, tuple[str, float]] = {}


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
    # Finite and non-negative only: `inf` would wait past every hook timeout.
    return value if math.isfinite(value) and value >= 0 else DEFAULT_WAIT_S


def _install_token(root: Path) -> str:
    try:
        return (root / IN_PROGRESS_REL).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


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
        # Created, not merely opened: with no lock file a reader would skip the
        # wait entirely, and the first install after this contract lands (or
        # after a governance directory swap) would race exactly as before.
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(lock_path, os.O_RDONLY | os.O_CREAT, 0o600)
    except OSError as exc:
        # An unreadable lock is not proof of a sync in progress; say so and go on.
        yield _interrupted(root) or VenvReadiness(True, f"venv lock unreadable: {exc}")
        return
    try:
        budget = wait_budget() if timeout is None else timeout
        if not math.isfinite(budget) or budget < 0:
            budget = DEFAULT_WAIT_S
        started = time.monotonic()
        call_deadline = started + budget
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                now = time.monotonic()
                token = _install_token(root)
                shared = _DEADLINES.get(lock_path)
                if shared is None or shared[0] != token:
                    shared = (token, now + budget)
                    _DEADLINES[lock_path] = shared
                if now >= min(shared[1], call_deadline):
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
