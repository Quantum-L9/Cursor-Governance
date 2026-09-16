"""Heal deterministic lock drift in a governance interpreter before binding.

Companion to :mod:`ops.memory.runtime_binding` (INV-11). The binding proves
which ``l9-graphite-memory`` a governance ``.venv`` carries; when that venv
disagrees with the checkout's own ``uv.lock`` — the pin moved on ``main`` and
nothing re-synced the environment — the honest verdict is still *unbound*,
but the cause is the environment, and the repair is mechanical and
idempotent: ``ops/scripts/ensure_uv_environment.sh <root> apply`` runs
``uv sync --locked --no-build`` against the lock that produced the manifest.

This module runs that repair exactly once per binding attempt, and only when
it is deterministic to do so:

- never in unmarked CI (the receipt lives under gitignored ``.l9/``; a CI
  runner has its own install step and a heal there would mask a real defect);
- never when ``L9_MEMORY_ENV_HEAL`` is ``0`` / ``false``;
- never while the repository write lock for that root is held by a live
  process (``ops/scripts/lib/repo_write_lock.sh``) — a concurrent
  ``make pr`` owns the tree;
- never for a development checkout (``L9_MEMORY_DEV_CHECKOUT``): that venv is
  the developer's, not a locked governance environment.

It never installs a version the lock does not name, never touches a provider,
and reports what it did in one word so the binding can carry it verbatim.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from pathlib import Path

ENV_HEAL = "L9_MEMORY_ENV_HEAL"
ENV_HEAL_TIMEOUT = "L9_MEMORY_ENV_HEAL_TIMEOUT"
DEFAULT_HEAL_TIMEOUT = 180.0

HEAL_SCRIPT_REL = Path("ops/scripts/ensure_uv_environment.sh")
FINGERPRINT_REL = Path(".venv/.l9-uv-fingerprint")
HEAL_LOCK_REL = Path(".l9/memory-env-heal.lock")

HEAL_HEALED = "healed"
HEAL_FAILED = "failed"
HEAL_SKIPPED_PREFIX = "skipped:"

_FALSE = {"0", "false", "no", "off"}
_TRUE = {"1", "true", "yes", "on"}

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def heal_disabled(env: Mapping[str, str]) -> bool:
    return str(env.get(ENV_HEAL, "1")).strip().lower() in _FALSE


def running_in_ci(env: Mapping[str, str]) -> bool:
    """Unmarked CI: ``GITHUB_ACTIONS`` or ``CI`` set truthy."""

    if str(env.get("GITHUB_ACTIONS", "")).strip().lower() in _TRUE:
        return True
    return str(env.get("CI", "")).strip().lower() in _TRUE


def repo_write_lock_dir(root: Path, env: Mapping[str, str]) -> Path:
    """Mirror ``repo_write_lock_dir`` from ``ops/scripts/lib/repo_write_lock.sh``."""

    home = env.get("HOME") or str(Path.home())
    lock_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return Path(home) / ".cursor" / f"l9-repo-write.{lock_id}.lock.d"


def repo_write_lock_held(root: Path, env: Mapping[str, str]) -> bool:
    """True when the ledger names a live owner pid for ``root``."""

    owner = repo_write_lock_dir(root, env) / "owner"
    try:
        first = owner.read_text(encoding="utf-8").split()
    except OSError:
        return False
    if not first:
        return False
    try:
        pid = int(first[0])
    except ValueError:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def repo_write_lock_disabled(env: Mapping[str, str]) -> bool:
    return str(env.get("L9_REPO_WRITE_LOCK", "1")).strip().lower() in _FALSE


def repo_write_lock_held_by_me(root: Path, env: Mapping[str, str]) -> bool:
    mine = str(env.get("L9_REPO_WRITE_LOCK_OWNER") or "").strip()
    if not mine:
        return False
    owner = repo_write_lock_dir(root, env) / "owner"
    try:
        first = owner.read_text(encoding="utf-8").split()
    except OSError:
        return False
    return bool(first) and first[0] == mine


def _repo_write_lock_stale_s(env: Mapping[str, str]) -> int:
    raw = str(env.get("L9_REPO_WRITE_LOCK_STALE_S") or "").strip()
    return int(raw) if raw.isdigit() else 300


def _owner_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _break_stale_repo_write_lock(lock_dir: Path, env: Mapping[str, str]) -> bool:
    """Remove a lock whose owner is gone or whose ledger is older than stale age."""

    owner = lock_dir / "owner"
    try:
        parts = owner.read_text(encoding="utf-8").split()
    except OSError:
        parts = []
    pid = 0
    ts = 0
    if parts:
        try:
            pid = int(parts[0])
        except ValueError:
            pid = 0
    if len(parts) > 1:
        try:
            ts = int(parts[1])
        except ValueError:
            ts = 0
    if pid > 0 and not _owner_is_alive(pid):
        shutil.rmtree(lock_dir, ignore_errors=True)
        return True
    now = int(time.time())
    if ts > 0 and now - ts > _repo_write_lock_stale_s(env):
        shutil.rmtree(lock_dir, ignore_errors=True)
        return True
    return False


def acquire_repo_write_lock(
    root: Path, env: Mapping[str, str], *, timeout: float = 0.0
) -> tuple[Path | None, str | None]:
    """Acquire the shared repo-write lock for ``root``.

    Returns ``(lock_dir, skip_reason)``. ``lock_dir`` is set only when this
    process created the directory and must release it. ``skip_reason`` is set
    when another live owner holds the lock. Disabled / already-ours succeed
    with ``(None, None)`` so the caller proceeds without releasing.
    """

    if repo_write_lock_disabled(env):
        return None, None
    if repo_write_lock_held_by_me(root, env):
        return None, None
    lock_dir = repo_write_lock_dir(root, env)
    try:
        lock_dir.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        required = str(env.get("L9_REPO_WRITE_LOCK_REQUIRED", "0")).strip().lower() in _TRUE
        if required:
            return None, "repo-write-lock-held"
        return None, None
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        try:
            lock_dir.mkdir()
        except FileExistsError:
            if _break_stale_repo_write_lock(lock_dir, env):
                continue
            if time.monotonic() >= deadline:
                return None, "repo-write-lock-held"
            time.sleep(0.2)
            continue
        except OSError:
            return None, "repo-write-lock-held"
        try:
            (lock_dir / "owner").write_text(
                f"{os.getpid()} {int(time.time())} {root} memory-env-heal\n",
                encoding="utf-8",
            )
        except OSError:
            shutil.rmtree(lock_dir, ignore_errors=True)
            return None, "repo-write-lock-held"
        return lock_dir, None


def release_repo_write_lock(lock_dir: Path | None) -> None:
    if lock_dir is None:
        return
    shutil.rmtree(lock_dir, ignore_errors=True)


def heal_script(root: Path) -> Path | None:
    script = root / HEAL_SCRIPT_REL
    return script if script.is_file() else None


def heal_timeout(env: Mapping[str, str]) -> float:
    raw = str(env.get(ENV_HEAL_TIMEOUT, "")).strip()
    try:
        value = float(raw) if raw else DEFAULT_HEAL_TIMEOUT
    except ValueError:
        value = DEFAULT_HEAL_TIMEOUT
    return value if value > 0 else DEFAULT_HEAL_TIMEOUT


def _default_runner(
    argv: list[str], *, timeout: float, env: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv list, never a shell string
        argv,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=dict(env),
    )


def heal_environment(
    root: Path,
    *,
    env: Mapping[str, str],
    runner: Runner | None = None,
    timeout: float | None = None,
) -> tuple[str, list[str]]:
    """Run the locked sync for ``root`` once. Returns ``(outcome, reasons)``.

    ``outcome`` is ``healed``, ``failed``, or ``skipped:<why>``. The caller
    re-probes after ``healed``; the other two leave the binding unbound with
    the reasons attached.
    """

    reasons: list[str] = []
    if heal_disabled(env):
        return f"{HEAL_SKIPPED_PREFIX}{ENV_HEAL}=0", reasons
    if running_in_ci(env):
        return f"{HEAL_SKIPPED_PREFIX}ci", reasons
    script = heal_script(root)
    if script is None:
        return f"{HEAL_SKIPPED_PREFIX}no-heal-script", reasons
    budget = timeout if timeout is not None else heal_timeout(env)
    started = time.monotonic()
    repo_lock, skip = acquire_repo_write_lock(root, env, timeout=0.0)
    if skip:
        return f"{HEAL_SKIPPED_PREFIX}{skip}", reasons

    run = runner or _default_runner
    child_env = dict(env)
    if repo_lock is not None:
        child_env["L9_REPO_WRITE_LOCK_OWNER"] = str(os.getpid())
        child_env["L9_REPO_WRITE_LOCK_LABEL"] = "memory-env-heal"
    lock_path = root / HEAL_LOCK_REL
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(lock_path, "a+", encoding="utf-8")  # noqa: SIM115 - held across the sync
    except OSError as exc:
        release_repo_write_lock(repo_lock)
        return f"{HEAL_SKIPPED_PREFIX}lock-unusable", [f"heal lock unusable: {exc}"]
    try:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() - started > budget:
                    return f"{HEAL_SKIPPED_PREFIX}heal-in-progress", [
                        "another process is healing this environment"
                    ]
                time.sleep(0.2)
        # The fingerprint is a cache marker; drift was *proved* by the probe,
        # so the cached "already synced" answer is exactly what must not win.
        fingerprint = root / FINGERPRINT_REL
        try:
            fingerprint.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            reasons.append(f"fingerprint not cleared: {exc}")
        remaining = budget - (time.monotonic() - started)
        if remaining <= 0:
            return HEAL_FAILED, [*reasons, f"environment heal timed out after {budget:.0f}s"]
        try:
            completed = run(
                ["bash", str(script), str(root), "apply"],
                timeout=remaining,
                env=child_env,
            )
        except subprocess.TimeoutExpired:
            return HEAL_FAILED, [*reasons, f"environment heal timed out after {budget:.0f}s"]
        except OSError as exc:
            return HEAL_FAILED, [*reasons, f"environment heal could not run: {exc}"]
        if completed.returncode != 0:
            tail = (completed.stderr or "").strip().splitlines()[-3:]
            return HEAL_FAILED, [
                *reasons,
                f"environment heal exited {completed.returncode}: " + " | ".join(tail),
            ]
        return HEAL_HEALED, reasons
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()
        release_repo_write_lock(repo_lock)
