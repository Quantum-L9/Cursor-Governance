"""Tests for ops/secrets/hydrate_infisical.py (read-side secret resolution).

No network and no real credentials: the Infisical fetch is stubbed. What is
asserted here is the contract that matters for safety — bootstrap precedence,
fail-closed behaviour when the provider is unreachable, and above all that
``--check`` never emits a secret value.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import hydrate_infisical as hi  # noqa: E402

INFISICAL_ENV_KEYS = (
    "INFISICAL_CLIENT_ID",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_PROJECT_ID",
    "INFISICAL_ENV",
    "INFISICAL_SITE_URL",
    "INFISICAL_SECRET_PATH",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key in INFISICAL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    # Never let a developer machine's AWS profile turn this into a live call.
    monkeypatch.setattr(hi, "_aws_bootstrap", lambda: None)
    return monkeypatch


def test_env_credentials_take_precedence(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("INFISICAL_CLIENT_ID", "cid")
    clean_env.setenv("INFISICAL_CLIENT_SECRET", "csec")
    clean_env.setenv("INFISICAL_SITE_URL", "https://infisical.example/")
    cfg = hi.bootstrap_config()
    assert cfg is not None
    assert cfg["client_id"] == "cid"
    # Trailing slash stripped so path joins do not produce a double slash.
    assert cfg["host"] == "https://infisical.example"
    # Unset values fall back to the registered project defaults.
    assert cfg["environment"] == hi.DEFAULT_ENV
    assert cfg["secret_path"] == hi.DEFAULT_SECRET_PATH


def test_falls_back_to_aws_bootstrap(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setattr(
        hi,
        "_aws_bootstrap",
        lambda: {
            "client_id": "aws-id",
            "client_secret": "aws-secret",
            "host": "https://aws.example/",
        },
    )
    cfg = hi.bootstrap_config()
    assert cfg is not None
    assert cfg["client_id"] == "aws-id"
    assert cfg["host"] == "https://aws.example"


def test_no_credentials_returns_none(clean_env: pytest.MonkeyPatch) -> None:
    assert hi.bootstrap_config() is None


def test_check_fails_closed_without_provider(
    clean_env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = hi.main(["--check", "--require", "SONAR_TOKEN"])
    assert rc == 1
    assert "SONAR_TOKEN: PROVIDER_UNAVAILABLE" in capsys.readouterr().out


def test_check_reports_missing_names(
    clean_env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    clean_env.setenv("INFISICAL_CLIENT_ID", "cid")
    clean_env.setenv("INFISICAL_CLIENT_SECRET", "csec")
    clean_env.setattr(hi, "_fetch", lambda cfg, *, with_values: {"SONAR_TOKEN": ""})

    rc = hi.main(["--check", "--require", "SONAR_TOKEN,SEMGREP_APP_TOKEN"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "SONAR_TOKEN: available" in out
    assert "SEMGREP_APP_TOKEN: MISSING" in out


def test_check_never_prints_values(
    clean_env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The core safety property: --check must not leak a value."""
    clean_env.setenv("INFISICAL_CLIENT_ID", "cid")
    clean_env.setenv("INFISICAL_CLIENT_SECRET", "csec")
    seen: dict[str, bool] = {}

    def fake_fetch(cfg: dict[str, str], *, with_values: bool) -> dict[str, str]:
        seen["with_values"] = with_values
        return {"SONAR_TOKEN": "super-secret-value"}

    clean_env.setattr(hi, "_fetch", fake_fetch)
    rc = hi.main(["--check", "--require", "SONAR_TOKEN"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "super-secret-value" not in out
    # Values are not merely withheld from stdout — they are never requested.
    assert seen["with_values"] is False


def test_export_emits_quoted_shell_assignment(
    clean_env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    clean_env.setenv("INFISICAL_CLIENT_ID", "cid")
    clean_env.setenv("INFISICAL_CLIENT_SECRET", "csec")
    clean_env.setattr(
        hi, "_fetch", lambda cfg, *, with_values: {"SONAR_TOKEN": "va lue'with$quotes"}
    )
    rc = hi.main(["--export", "SONAR_TOKEN"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out.startswith("export SONAR_TOKEN=")
    # Shell-quoted so spaces/quotes/$ in a value cannot break out of `eval`:
    # the round-trip through the shell lexer must reproduce the value exactly.
    import shlex

    assert shlex.split(out) == ["export", "SONAR_TOKEN=va lue'with$quotes"]


def test_export_fails_when_name_absent(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("INFISICAL_CLIENT_ID", "cid")
    clean_env.setenv("INFISICAL_CLIENT_SECRET", "csec")
    clean_env.setattr(hi, "_fetch", lambda cfg, *, with_values: {})
    assert hi.main(["--export", "SONAR_TOKEN"]) == 1
