# L9_META:
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: secrets
#   owner: platform
#   status: active
#   created: 2026-07-05
#   contract: infisical-config (Python port of @quantum-l9/infisical-config)
"""
Infisical Universal Auth secrets adapter for L9-Graphite-Memory.

Port of the TypeScript ``@quantum-l9/infisical-config`` package contract.
Hydrates ``os.environ`` from Infisical via machine identity (Universal Auth)
so that downstream modules (graphiti_memory_client, zep_transport, etc.) can
read secrets from the environment without knowing where they came from.

Design principles:
  - OPTIONAL: no-op when client id / secret / project id are all absent.
  - NON-DESTRUCTIVE: never overwrites an already-set var (unless ``overwrite``).
  - FAIL-SOFT by default; ``required`` raises on missing config or fetch failure.
  - infisical-python is imported lazily, only when Infisical is configured.
  - Rotation-aware: SIGHUP handler + interval refresh for long-running servers.

Boot env vars (the only 3 you ever need):
  INFISICAL_CLIENT_ID
  INFISICAL_CLIENT_SECRET
  INFISICAL_PROJECT_ID

Optional env vars:
  INFISICAL_ENV           (default: "prod")
  INFISICAL_SECRET_PATH   (default: "/")
  INFISICAL_SITE_URL      (default: Infisical Cloud)
  INFISICAL_RECURSIVE     (default: "0")
  INFISICAL_REQUIRED      (default: "0")
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

__all__ = [
    "LoadSecretsResult",
    "RefreshSecretsResult",
    "load_secrets",
    "load_secrets_sync",
    "refresh_secrets",
    "install_sighup_reload",
    "start_refresh_interval",
    "env_flag",
]

log = logging.getLogger("l9.secrets")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadSecretsResult:
    """Outcome of a load_secrets() call."""

    loaded: bool
    injected: int
    source: Literal["infisical", "environ"]


@dataclass(frozen=True)
class RefreshSecretsResult(LoadSecretsResult):
    """Outcome of a refresh_secrets() call."""

    refreshed_at: str = field(default="")  # ISO 8601


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def env_flag(value: str | None) -> bool:
    """Parse a loose boolean env var ('1' / 'true', case-insensitive)."""
    if value is None:
        return False
    return value.strip() == "1" or value.strip().lower() == "true"


def _get_config(
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    project_id: str | None = None,
    environment: str | None = None,
    secret_path: str | None = None,
    site_url: str | None = None,
    recursive: bool | None = None,
    required: bool | None = None,
) -> dict[str, Any]:
    """Resolve configuration from explicit args → env vars → defaults."""
    return {
        "client_id": client_id or os.environ.get("INFISICAL_CLIENT_ID", ""),
        "client_secret": client_secret or os.environ.get("INFISICAL_CLIENT_SECRET", ""),
        "project_id": project_id or os.environ.get("INFISICAL_PROJECT_ID", ""),
        "environment": environment or os.environ.get("INFISICAL_ENV", "prod"),
        "secret_path": secret_path or os.environ.get("INFISICAL_SECRET_PATH", "/"),
        "site_url": site_url or os.environ.get("INFISICAL_SITE_URL", ""),
        "recursive": recursive if recursive is not None else env_flag(os.environ.get("INFISICAL_RECURSIVE")),
        "required": required if required is not None else env_flag(os.environ.get("INFISICAL_REQUIRED")),
    }


# ---------------------------------------------------------------------------
# Core: load_secrets
# ---------------------------------------------------------------------------


async def load_secrets(
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    project_id: str | None = None,
    environment: str | None = None,
    secret_path: str | None = None,
    site_url: str | None = None,
    recursive: bool | None = None,
    required: bool | None = None,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> LoadSecretsResult:
    """
    Hydrate ``os.environ`` from Infisical via Universal Auth machine identity.

    Async wrapper around the synchronous SDK call. Safe to call from both
    sync and async contexts (use ``load_secrets_sync`` for pure sync).
    """
    return load_secrets_sync(
        client_id=client_id,
        client_secret=client_secret,
        project_id=project_id,
        environment=environment,
        secret_path=secret_path,
        site_url=site_url,
        recursive=recursive,
        required=required,
        overwrite=overwrite,
        logger=logger,
    )


def load_secrets_sync(
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    project_id: str | None = None,
    environment: str | None = None,
    secret_path: str | None = None,
    site_url: str | None = None,
    recursive: bool | None = None,
    required: bool | None = None,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> LoadSecretsResult:
    """
    Synchronous version of load_secrets.

    The infisical-python SDK is synchronous, so this is the true implementation.
    """
    _log = logger or log
    cfg = _get_config(
        client_id=client_id,
        client_secret=client_secret,
        project_id=project_id,
        environment=environment,
        secret_path=secret_path,
        site_url=site_url,
        recursive=recursive,
        required=required,
    )

    cid = cfg["client_id"]
    csecret = cfg["client_secret"]
    pid = cfg["project_id"]
    is_required = cfg["required"]

    # --- Guard: not configured ---
    if not cid or not csecret or not pid:
        if is_required:
            raise RuntimeError(
                "INFISICAL_REQUIRED is set but client id, client secret, "
                "and project id are not all provided."
            )
        if cid or csecret or pid:
            _log.warning(
                "Infisical partially configured — need client id, client secret, "
                "and project id; skipping Infisical"
            )
        else:
            _log.debug("Infisical not configured — using os.environ only")
        return LoadSecretsResult(loaded=False, injected=0, source="environ")

    # --- Lazy import ---
    try:
        from infisical_client import (  # type: ignore[import-untyped]
            AuthenticationOptions,
            ClientSettings,
            InfisicalClient,
            ListSecretsOptions,
            UniversalAuthMethod,
        )
    except ImportError as exc:
        if is_required:
            raise RuntimeError(
                "infisical-python is not installed. "
                "Install with: pip install infisical-python"
            ) from exc
        _log.warning("infisical-python not installed — using os.environ only")
        return LoadSecretsResult(loaded=False, injected=0, source="environ")

    # --- Build client ---
    try:
        settings_kwargs: dict[str, Any] = {
            "auth": AuthenticationOptions(
                universal_auth=UniversalAuthMethod(
                    client_id=cid,
                    client_secret=csecret,
                )
            ),
        }
        if cfg["site_url"]:
            settings_kwargs["site_url"] = cfg["site_url"]

        client = InfisicalClient(settings=ClientSettings(**settings_kwargs))

        # --- Fetch secrets ---
        secrets = client.listSecrets(
            options=ListSecretsOptions(
                environment=cfg["environment"],
                project_id=pid,
                path=cfg["secret_path"],
                recursive=cfg["recursive"],
                expand_secret_references=True,
                include_imports=True,
                attach_to_process_env=False,
            )
        )

        # --- Inject into os.environ ---
        injected = 0
        for secret in secrets:
            secret_dict = secret.to_dict()
            key = secret_dict.get("secretKey", "") or secret_dict.get("secret_key", "")
            value = secret_dict.get("secretValue", "") or secret_dict.get("secret_value", "")
            if not key:
                continue
            if overwrite or os.environ.get(key) is None:
                os.environ[key] = value
                injected += 1

        _log.info(
            "Loaded secrets from Infisical: environment=%s, path=%s, fetched=%d, injected=%d",
            cfg["environment"],
            cfg["secret_path"],
            len(secrets),
            injected,
        )
        return LoadSecretsResult(loaded=True, injected=injected, source="infisical")

    except Exception as exc:
        message = str(exc)
        if is_required:
            raise RuntimeError(f"Infisical secret load failed (required): {message}") from exc
        _log.warning("Infisical secret load failed (non-required): %s — using os.environ", message)
        return LoadSecretsResult(loaded=False, injected=0, source="environ")


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


async def refresh_secrets(
    *,
    logger: logging.Logger | None = None,
    on_refresh: Callable[[RefreshSecretsResult], None] | None = None,
    **kwargs: Any,
) -> RefreshSecretsResult:
    """
    Re-fetch secrets with ``overwrite=True``. Returns refreshed_at ISO timestamp.

    Intended for rotation scenarios where Infisical has rotated a credential
    and the running process needs to pick up the new value.
    """
    _log = logger or log
    _log.info("Refreshing secrets from Infisical (overwrite=True)")

    base_result = load_secrets_sync(overwrite=True, logger=logger, **kwargs)
    result = RefreshSecretsResult(
        loaded=base_result.loaded,
        injected=base_result.injected,
        source=base_result.source,
        refreshed_at=datetime.now(timezone.utc).isoformat(),
    )

    if on_refresh:
        on_refresh(result)

    return result


# ---------------------------------------------------------------------------
# SIGHUP reload
# ---------------------------------------------------------------------------


def install_sighup_reload(
    *,
    logger: logging.Logger | None = None,
    on_refresh: Callable[[RefreshSecretsResult], None] | None = None,
    **kwargs: Any,
) -> Callable[[], None]:
    """
    Register a SIGHUP handler that refreshes secrets from Infisical.

    Returns an uninstall function that removes the handler.

    On Windows (where SIGHUP is not available), this is a no-op that logs
    a warning and returns a no-op uninstall function.
    """
    _log = logger or log

    if sys.platform == "win32":
        _log.warning("SIGHUP not available on Windows — reload handler not installed")
        return lambda: None

    def _handler(signum: int, frame: Any) -> None:
        _log.info("SIGHUP received — refreshing secrets from Infisical")
        # Run refresh synchronously in signal handler context
        try:
            base_result = load_secrets_sync(overwrite=True, logger=logger, **kwargs)
            result = RefreshSecretsResult(
                loaded=base_result.loaded,
                injected=base_result.injected,
                source=base_result.source,
                refreshed_at=datetime.now(timezone.utc).isoformat(),
            )
            if on_refresh:
                on_refresh(result)
        except Exception as exc:
            _log.warning("refreshSecrets on SIGHUP failed: %s", exc)

    old_handler = signal.signal(signal.SIGHUP, _handler)
    _log.debug("SIGHUP reload handler installed")

    def _uninstall() -> None:
        signal.signal(signal.SIGHUP, old_handler)
        _log.debug("SIGHUP reload handler removed")

    return _uninstall


# ---------------------------------------------------------------------------
# Interval refresh
# ---------------------------------------------------------------------------


def start_refresh_interval(
    interval_seconds: int = 900,
    *,
    logger: logging.Logger | None = None,
    on_refresh: Callable[[RefreshSecretsResult], None] | None = None,
    **kwargs: Any,
) -> asyncio.Task[None]:
    """
    Start an interval-based secret refresh loop as an asyncio Task.

    Fires immediately on first call, then repeats every ``interval_seconds``.
    Use as a belt-and-suspenders complement to SIGHUP reload — the interval
    ensures stale secrets are caught even without an explicit reload signal.

    Keep ``interval_seconds`` shorter than the Infisical rotation overlap
    window to guarantee every instance re-fetches before the old credential
    is revoked.

    Returns a cancellable ``asyncio.Task``. Call ``task.cancel()`` to stop.
    """
    _log = logger or log
    _log.info("Starting Infisical secret refresh interval: %ds", interval_seconds)

    async def _loop() -> None:
        while True:
            try:
                await refresh_secrets(logger=logger, on_refresh=on_refresh, **kwargs)
            except Exception as exc:
                _log.warning("Interval refresh failed: %s", exc)
            await asyncio.sleep(interval_seconds)

    loop = asyncio.get_event_loop()
    return loop.create_task(_loop(), name="infisical-refresh-interval")
