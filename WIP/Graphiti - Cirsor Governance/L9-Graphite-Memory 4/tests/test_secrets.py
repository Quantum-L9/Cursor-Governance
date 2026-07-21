# L9_META:
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: tests
#   owner: platform
#   status: active
#   created: 2026-07-05
"""
Unit tests for l9_graphite_memory.secrets — Infisical Universal Auth adapter.

Tests verify behavior contracts without requiring a live Infisical connection.
All Infisical SDK calls are mocked.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from l9_graphite_memory.secrets import (
    LoadSecretsResult,
    RefreshSecretsResult,
    env_flag,
    install_sighup_reload,
    load_secrets,
    load_secrets_sync,
    refresh_secrets,
    start_refresh_interval,
)


# ---------------------------------------------------------------------------
# env_flag tests
# ---------------------------------------------------------------------------


class TestEnvFlag:
    def test_none_returns_false(self) -> None:
        assert env_flag(None) is False

    def test_empty_returns_false(self) -> None:
        assert env_flag("") is False

    def test_zero_returns_false(self) -> None:
        assert env_flag("0") is False

    def test_one_returns_true(self) -> None:
        assert env_flag("1") is True

    def test_true_lowercase_returns_true(self) -> None:
        assert env_flag("true") is True

    def test_true_uppercase_returns_true(self) -> None:
        assert env_flag("TRUE") is True

    def test_true_mixed_case_returns_true(self) -> None:
        assert env_flag("True") is True

    def test_whitespace_one_returns_true(self) -> None:
        assert env_flag(" 1 ") is True

    def test_random_string_returns_false(self) -> None:
        assert env_flag("yes") is False


# ---------------------------------------------------------------------------
# load_secrets_sync tests
# ---------------------------------------------------------------------------


class TestLoadSecretsSync:
    """Test the synchronous load_secrets_sync function."""

    def test_no_config_returns_environ_source(self) -> None:
        """When no Infisical env vars are set, returns fail-soft result."""
        env = {
            "INFISICAL_CLIENT_ID": "",
            "INFISICAL_CLIENT_SECRET": "",
            "INFISICAL_PROJECT_ID": "",
        }
        with patch.dict(os.environ, env, clear=False):
            # Remove the keys entirely
            os.environ.pop("INFISICAL_CLIENT_ID", None)
            os.environ.pop("INFISICAL_CLIENT_SECRET", None)
            os.environ.pop("INFISICAL_PROJECT_ID", None)

            result = load_secrets_sync()

        assert result == LoadSecretsResult(loaded=False, injected=0, source="environ")

    def test_partial_config_warns_and_returns_environ(self) -> None:
        """When only some Infisical vars are set, warns and returns environ."""
        env = {
            "INFISICAL_CLIENT_ID": "some-id",
            "INFISICAL_CLIENT_SECRET": "",
            "INFISICAL_PROJECT_ID": "",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("INFISICAL_CLIENT_SECRET", None)
            os.environ.pop("INFISICAL_PROJECT_ID", None)

            logger = MagicMock(spec=logging.Logger)
            result = load_secrets_sync(logger=logger)

        assert result.loaded is False
        assert result.source == "environ"
        logger.warning.assert_called_once()

    def test_required_raises_when_not_configured(self) -> None:
        """When INFISICAL_REQUIRED=1 and not configured, raises RuntimeError."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("INFISICAL_CLIENT_ID", None)
            os.environ.pop("INFISICAL_CLIENT_SECRET", None)
            os.environ.pop("INFISICAL_PROJECT_ID", None)

            with pytest.raises(RuntimeError, match="INFISICAL_REQUIRED"):
                load_secrets_sync(required=True)

    def test_missing_sdk_returns_environ(self) -> None:
        """When infisical-python is not importable, returns environ."""
        env = {
            "INFISICAL_CLIENT_ID": "cid",
            "INFISICAL_CLIENT_SECRET": "csecret",
            "INFISICAL_PROJECT_ID": "pid",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch.dict("sys.modules", {"infisical_client": None}):
                # Force ImportError
                with patch(
                    "l9_graphite_memory.secrets.load_secrets_sync.__module__",
                    create=True,
                ):
                    # Simpler: mock the import inside the function
                    import builtins

                    original_import = builtins.__import__

                    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
                        if name == "infisical_client":
                            raise ImportError("mocked")
                        return original_import(name, *args, **kwargs)

                    with patch("builtins.__import__", side_effect=mock_import):
                        result = load_secrets_sync()

        assert result.loaded is False
        assert result.source == "environ"

    def test_missing_sdk_required_raises(self) -> None:
        """When infisical-python missing and required=True, raises."""
        env = {
            "INFISICAL_CLIENT_ID": "cid",
            "INFISICAL_CLIENT_SECRET": "csecret",
            "INFISICAL_PROJECT_ID": "pid",
        }
        with patch.dict(os.environ, env, clear=False):
            import builtins

            original_import = builtins.__import__

            def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
                if name == "infisical_client":
                    raise ImportError("mocked")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(RuntimeError, match="infisical-python is not installed"):
                    load_secrets_sync(required=True)

    def test_successful_load_injects_secrets(self) -> None:
        """When Infisical is configured and reachable, injects secrets."""
        env = {
            "INFISICAL_CLIENT_ID": "cid",
            "INFISICAL_CLIENT_SECRET": "csecret",
            "INFISICAL_PROJECT_ID": "pid",
        }

        # Mock the infisical_client module
        mock_secret_1 = MagicMock()
        mock_secret_1.to_dict.return_value = {"secretKey": "ZEP_API_KEY", "secretValue": "z_test123"}
        mock_secret_2 = MagicMock()
        mock_secret_2.to_dict.return_value = {"secretKey": "OPENAI_API_KEY", "secretValue": "sk-test456"}

        mock_client = MagicMock()
        mock_client.listSecrets.return_value = [mock_secret_1, mock_secret_2]

        mock_infisical_client = MagicMock()
        mock_infisical_client.InfisicalClient.return_value = mock_client
        mock_infisical_client.AuthenticationOptions = MagicMock()
        mock_infisical_client.ClientSettings = MagicMock()
        mock_infisical_client.ListSecretsOptions = MagicMock()
        mock_infisical_client.UniversalAuthMethod = MagicMock()

        with patch.dict(os.environ, env, clear=False):
            # Remove any pre-existing keys
            os.environ.pop("ZEP_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)

            with patch.dict("sys.modules", {"infisical_client": mock_infisical_client}):
                result = load_secrets_sync()

            assert result == LoadSecretsResult(loaded=True, injected=2, source="infisical")
            assert os.environ.get("ZEP_API_KEY") == "z_test123"
            assert os.environ.get("OPENAI_API_KEY") == "sk-test456"

    def test_no_overwrite_preserves_existing(self) -> None:
        """When overwrite=False (default), existing env vars are not overwritten."""
        env = {
            "INFISICAL_CLIENT_ID": "cid",
            "INFISICAL_CLIENT_SECRET": "csecret",
            "INFISICAL_PROJECT_ID": "pid",
            "ZEP_API_KEY": "existing_value",
        }

        mock_secret = MagicMock()
        mock_secret.to_dict.return_value = {"secretKey": "ZEP_API_KEY", "secretValue": "new_value"}

        mock_client = MagicMock()
        mock_client.listSecrets.return_value = [mock_secret]

        mock_infisical_client = MagicMock()
        mock_infisical_client.InfisicalClient.return_value = mock_client
        mock_infisical_client.AuthenticationOptions = MagicMock()
        mock_infisical_client.ClientSettings = MagicMock()
        mock_infisical_client.ListSecretsOptions = MagicMock()
        mock_infisical_client.UniversalAuthMethod = MagicMock()

        with patch.dict(os.environ, env, clear=False):
            with patch.dict("sys.modules", {"infisical_client": mock_infisical_client}):
                result = load_secrets_sync(overwrite=False)

            assert result.injected == 0
            assert os.environ.get("ZEP_API_KEY") == "existing_value"

    def test_overwrite_replaces_existing(self) -> None:
        """When overwrite=True, existing env vars are overwritten."""
        env = {
            "INFISICAL_CLIENT_ID": "cid",
            "INFISICAL_CLIENT_SECRET": "csecret",
            "INFISICAL_PROJECT_ID": "pid",
            "ZEP_API_KEY": "old_value",
        }

        mock_secret = MagicMock()
        mock_secret.to_dict.return_value = {"secretKey": "ZEP_API_KEY", "secretValue": "new_value"}

        mock_client = MagicMock()
        mock_client.listSecrets.return_value = [mock_secret]

        mock_infisical_client = MagicMock()
        mock_infisical_client.InfisicalClient.return_value = mock_client
        mock_infisical_client.AuthenticationOptions = MagicMock()
        mock_infisical_client.ClientSettings = MagicMock()
        mock_infisical_client.ListSecretsOptions = MagicMock()
        mock_infisical_client.UniversalAuthMethod = MagicMock()

        with patch.dict(os.environ, env, clear=False):
            with patch.dict("sys.modules", {"infisical_client": mock_infisical_client}):
                result = load_secrets_sync(overwrite=True)

            assert result.injected == 1
            assert os.environ.get("ZEP_API_KEY") == "new_value"

    def test_api_failure_failsoft(self) -> None:
        """When Infisical API fails and required=False, returns environ."""
        env = {
            "INFISICAL_CLIENT_ID": "cid",
            "INFISICAL_CLIENT_SECRET": "csecret",
            "INFISICAL_PROJECT_ID": "pid",
        }

        mock_infisical_client = MagicMock()
        mock_infisical_client.InfisicalClient.side_effect = Exception("connection refused")
        mock_infisical_client.AuthenticationOptions = MagicMock()
        mock_infisical_client.ClientSettings = MagicMock()
        mock_infisical_client.ListSecretsOptions = MagicMock()
        mock_infisical_client.UniversalAuthMethod = MagicMock()

        with patch.dict(os.environ, env, clear=False):
            with patch.dict("sys.modules", {"infisical_client": mock_infisical_client}):
                result = load_secrets_sync()

        assert result.loaded is False
        assert result.source == "environ"

    def test_api_failure_required_raises(self) -> None:
        """When Infisical API fails and required=True, raises RuntimeError."""
        env = {
            "INFISICAL_CLIENT_ID": "cid",
            "INFISICAL_CLIENT_SECRET": "csecret",
            "INFISICAL_PROJECT_ID": "pid",
        }

        mock_infisical_client = MagicMock()
        mock_infisical_client.InfisicalClient.side_effect = Exception("connection refused")
        mock_infisical_client.AuthenticationOptions = MagicMock()
        mock_infisical_client.ClientSettings = MagicMock()
        mock_infisical_client.ListSecretsOptions = MagicMock()
        mock_infisical_client.UniversalAuthMethod = MagicMock()

        with patch.dict(os.environ, env, clear=False):
            with patch.dict("sys.modules", {"infisical_client": mock_infisical_client}):
                with pytest.raises(RuntimeError, match="Infisical secret load failed"):
                    load_secrets_sync(required=True)


# ---------------------------------------------------------------------------
# load_secrets (async) tests
# ---------------------------------------------------------------------------


class TestLoadSecretsAsync:
    """Test the async load_secrets wrapper."""

    @pytest.mark.asyncio
    async def test_async_delegates_to_sync(self) -> None:
        """Async version returns same result as sync."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("INFISICAL_CLIENT_ID", None)
            os.environ.pop("INFISICAL_CLIENT_SECRET", None)
            os.environ.pop("INFISICAL_PROJECT_ID", None)

            result = await load_secrets()

        assert result == LoadSecretsResult(loaded=False, injected=0, source="environ")


# ---------------------------------------------------------------------------
# refresh_secrets tests
# ---------------------------------------------------------------------------


class TestRefreshSecrets:
    """Test the refresh_secrets function."""

    @pytest.mark.asyncio
    async def test_refresh_calls_with_overwrite(self) -> None:
        """refresh_secrets calls load_secrets_sync with overwrite=True."""
        with patch(
            "l9_graphite_memory.secrets.load_secrets_sync",
            return_value=LoadSecretsResult(loaded=True, injected=3, source="infisical"),
        ) as mock_load:
            result = await refresh_secrets()

        mock_load.assert_called_once()
        call_kwargs = mock_load.call_args[1]
        assert call_kwargs["overwrite"] is True
        assert isinstance(result, RefreshSecretsResult)
        assert result.loaded is True
        assert result.refreshed_at != ""

    @pytest.mark.asyncio
    async def test_refresh_calls_on_refresh_callback(self) -> None:
        """refresh_secrets calls on_refresh callback with result."""
        callback = MagicMock()
        with patch(
            "l9_graphite_memory.secrets.load_secrets_sync",
            return_value=LoadSecretsResult(loaded=True, injected=1, source="infisical"),
        ):
            await refresh_secrets(on_refresh=callback)

        callback.assert_called_once()
        arg = callback.call_args[0][0]
        assert isinstance(arg, RefreshSecretsResult)


# ---------------------------------------------------------------------------
# install_sighup_reload tests
# ---------------------------------------------------------------------------


class TestInstallSighupReload:
    """Test SIGHUP handler installation."""

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGHUP not available on Windows")
    def test_installs_and_uninstalls_handler(self) -> None:
        """install_sighup_reload registers and unregisters a SIGHUP handler."""
        original_handler = signal.getsignal(signal.SIGHUP)

        uninstall = install_sighup_reload()

        # Handler should be changed
        current_handler = signal.getsignal(signal.SIGHUP)
        assert current_handler != original_handler

        # Uninstall should restore
        uninstall()
        restored_handler = signal.getsignal(signal.SIGHUP)
        assert restored_handler == original_handler

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_windows_noop(self) -> None:
        """On Windows, returns no-op uninstall function."""
        uninstall = install_sighup_reload()
        # Should not raise
        uninstall()


# ---------------------------------------------------------------------------
# start_refresh_interval tests
# ---------------------------------------------------------------------------


class TestStartRefreshInterval:
    """Test interval-based refresh."""

    @pytest.mark.asyncio
    async def test_creates_cancellable_task(self) -> None:
        """start_refresh_interval returns a cancellable asyncio.Task."""
        with patch(
            "l9_graphite_memory.secrets.load_secrets_sync",
            return_value=LoadSecretsResult(loaded=False, injected=0, source="environ"),
        ):
            task = start_refresh_interval(interval_seconds=1)

        assert isinstance(task, asyncio.Task)
        assert not task.done()

        # Cancel and wait for cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert task.cancelled()
