"""capability_bind: in-process use, never export. No network, no real credentials."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import capability_bind as cb  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_bind_cache() -> None:
    cb.reset_cache()
    yield
    cb.reset_cache()


def test_bind_uses_already_present_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEMGREP_APP_TOKEN", "CANARY_ENV")
    bound = cb.bind(
        "SEMGREP_APP_TOKEN",
        infisical_cli=lambda _: None,
        aws=lambda _: None,
    )
    assert bound == "CANARY_ENV"
    status = cb.bind_status("SEMGREP_APP_TOKEN")
    assert status == {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "env"}
    assert "CANARY_ENV" not in json.dumps(status)


def test_bind_uses_infisical_cli_profile_when_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMGREP_APP_TOKEN", raising=False)
    value = cb.bind(
        "SEMGREP_APP_TOKEN",
        infisical_cli=lambda name: "CANARY_CLI" if name == "SEMGREP_APP_TOKEN" else None,
        aws=lambda _: "SHOULD_NOT_RUN",
    )
    assert value == "CANARY_CLI"
    assert cb.bind_status("SEMGREP_APP_TOKEN")["source"] == "infisical-cli"
    assert os_environ_lacks(monkeypatch, "SEMGREP_APP_TOKEN")


def test_bind_falls_back_to_aws_when_cli_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMGREP_APP_TOKEN", raising=False)
    value = cb.bind(
        "SEMGREP_APP_TOKEN",
        infisical_cli=lambda _: None,
        aws=lambda name: "CANARY_AWS" if name == "SEMGREP_APP_TOKEN" else None,
    )
    assert value == "CANARY_AWS"
    assert cb.bind_status("SEMGREP_APP_TOKEN")["source"] == "aws"


def test_bind_refuses_bootstrap_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "CANARY_UA")
    assert cb.bind("INFISICAL_CLIENT_SECRET") is None
    assert cb.bind_status("INFISICAL_CLIENT_SECRET")["source"] == "refused"


def test_bind_rejects_unknown_name() -> None:
    assert cb.bind("NOT_A_REAL_SECRET_NAME") is None
    assert cb.bind_status("NOT_A_REAL_SECRET_NAME") == {
        "name": "NOT_A_REAL_SECRET_NAME",
        "bound": False,
        "source": "unbound",
    }


def test_bind_never_writes_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SONAR_TOKEN", raising=False)
    cb.bind("SONAR_TOKEN", infisical_cli=lambda _: "CANARY_SONAR", aws=lambda _: None)
    assert os_environ_lacks(monkeypatch, "SONAR_TOKEN")


def test_bind_first_walks_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SONAR_TOKEN", raising=False)
    monkeypatch.delenv("SONARCLOUD_TOKEN", raising=False)
    monkeypatch.setenv("SONARCLOUD_TOKEN", "CANARY_ALIAS")
    assert (
        cb.bind_first(
            "SONAR_TOKEN",
            "SONARCLOUD_TOKEN",
            infisical_cli=lambda _: None,
            aws=lambda _: None,
        )
        == "CANARY_ALIAS"
    )


def test_check_cli_prints_source_never_value() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SECRETS_DIR / "capability_bind.py"), "--check", "SEMGREP_APP_TOKEN"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
        env={
            **{k: v for k, v in __import__("os").environ.items() if k != "SEMGREP_APP_TOKEN"},
            "SEMGREP_APP_TOKEN": "CANARY_MUST_NOT_APPEAR",
        },
    )
    assert "CANARY_MUST_NOT_APPEAR" not in result.stdout
    assert "CANARY_MUST_NOT_APPEAR" not in result.stderr
    assert "SEMGREP_APP_TOKEN:" in result.stdout
    assert "source=" in result.stdout


def test_aws_ref_map_covers_semgrep_and_sonar() -> None:
    refs = cb._aws_refs()
    assert refs["SEMGREP_APP_TOKEN"] == "openclaw-igorbot/semgrep#token"
    assert refs["SONAR_TOKEN"] == "openclaw-igorbot/sonarcloud#token"
    assert refs["GH_TOKEN"] == "openclaw-igorbot/github#token"


def os_environ_lacks(monkeypatch: pytest.MonkeyPatch, name: str) -> bool:
    import os

    return not (os.environ.get(name) or "").strip()
