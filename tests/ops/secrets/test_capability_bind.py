"""capability_bind: Infisical-only in-process use, never export."""

from __future__ import annotations

import json
import os
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


def _env_lacks(name: str) -> bool:
    return not (os.environ.get(name) or "").strip()


def test_bind_uses_already_present_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEMGREP_APP_TOKEN", "CANARY_ENV")
    bound = cb.bind("SEMGREP_APP_TOKEN", infisical_cli=lambda _: None)
    assert bound == "CANARY_ENV"
    status = cb.bind_status("SEMGREP_APP_TOKEN")
    assert status == {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "env"}
    assert "CANARY_ENV" not in json.dumps(status)


def test_bind_uses_infisical_when_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMGREP_APP_TOKEN", raising=False)
    value = cb.bind(
        "SEMGREP_APP_TOKEN",
        infisical_cli=lambda name: "CANARY_CLI" if name == "SEMGREP_APP_TOKEN" else None,
    )
    assert value == "CANARY_CLI"
    assert cb.bind_status("SEMGREP_APP_TOKEN")["source"] == "infisical"
    assert _env_lacks("SEMGREP_APP_TOKEN")


def test_bind_does_not_use_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMGREP_APP_TOKEN", raising=False)
    value = cb.bind("SEMGREP_APP_TOKEN", infisical_cli=lambda _: None)
    assert value is None
    assert cb.bind_status("SEMGREP_APP_TOKEN")["source"] == "unbound"


def test_missing_machine_profile_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMGREP_APP_TOKEN", raising=False)
    monkeypatch.setattr(cb, "_machine_profile", lambda: None)
    assert cb.bind("SEMGREP_APP_TOKEN") is None
    assert cb.bind_status("SEMGREP_APP_TOKEN")["source"] == "infisical-machine-absent"


def test_bind_uses_machine_profile_not_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMGREP_APP_TOKEN", raising=False)
    # A clean runner has no ~/.infisical/l9-machine.json; without a present
    # profile _resolve reports infisical-machine-absent before any fetch runs.
    # Stub the profile too, so the assertion exercises the machine path.
    monkeypatch.setattr(
        cb,
        "_machine_profile",
        lambda: {
            "host": "https://infisical.invalid",
            "project_id": "fixture-project",
            "environment": "fixture",
            "client_id": "fixture-client",
            "client_secret": "fixture-secret",
        },
    )
    monkeypatch.setattr(cb, "_from_machine_profile", lambda _name: "CANARY_MACHINE")
    assert cb.bind("SEMGREP_APP_TOKEN") == "CANARY_MACHINE"
    assert cb.bind_status("SEMGREP_APP_TOKEN")["source"] == "infisical"
    assert "infisical secrets" not in Path(cb.__file__).read_text(encoding="utf-8")


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


AUTH0_NAMES = ("AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET")


def test_operator_only_names_are_gated_inventory_names() -> None:
    operator_only = cb.operator_only_names()
    assert set(AUTH0_NAMES) <= operator_only
    assert operator_only <= cb.allowed_names()


@pytest.mark.parametrize("name", AUTH0_NAMES)
def test_operator_only_name_refused_for_an_environment_identity(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(cb, "_identity_source", lambda: "env")
    assert cb.bind(name, infisical_cli=lambda _: "CANARY_OPERATOR_ONLY") is None
    assert cb.bind_status(name) == {"name": name, "bound": False, "source": "operator-only-refused"}


def test_operator_only_name_refused_on_a_hosted_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "1")
    monkeypatch.setenv("AUTH0_CLIENT_SECRET", "CANARY_HOSTED_ENV")
    monkeypatch.setattr(cb, "_identity_source", lambda: "profile")
    assert cb.bind("AUTH0_CLIENT_SECRET", infisical_cli=lambda _: "CANARY_OPERATOR_ONLY") is None
    assert cb.bind_status("AUTH0_CLIENT_SECRET")["source"] == "operator-only-refused"


def test_operator_only_name_binds_on_the_workstation_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    monkeypatch.delenv("AUTH0_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(cb, "_identity_source", lambda: "profile")
    value = cb.bind("AUTH0_CLIENT_SECRET", infisical_cli=lambda _: "CANARY_OPERATOR_ONLY")
    assert value == "CANARY_OPERATOR_ONLY"
    assert cb.bind_status("AUTH0_CLIENT_SECRET")["source"] == "infisical"
    assert _env_lacks("AUTH0_CLIENT_SECRET")


def test_operator_only_gate_does_not_touch_other_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "1")
    monkeypatch.delenv("SEMGREP_APP_TOKEN", raising=False)
    monkeypatch.setattr(cb, "_identity_source", lambda: "env")
    value = cb.bind("SEMGREP_APP_TOKEN", infisical_cli=lambda _: "CANARY_ORDINARY")
    assert value == "CANARY_ORDINARY"


def test_identity_source_is_read_from_the_machine_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        machine_login, "machine_identity", lambda env=None: ("profile", {"client_id": "x"})
    )
    assert cb._identity_source() == "profile"
    cb.reset_cache()
    monkeypatch.setattr(machine_login, "machine_identity", lambda env=None: ("", None))
    assert cb._identity_source() == ""


def test_bind_never_writes_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SONAR_TOKEN", raising=False)
    cb.bind("SONAR_TOKEN", infisical_cli=lambda _: "CANARY_SONAR")
    assert _env_lacks("SONAR_TOKEN")


def test_bind_first_walks_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SONAR_TOKEN", raising=False)
    monkeypatch.delenv("SONARCLOUD_TOKEN", raising=False)
    monkeypatch.setenv("SONARCLOUD_TOKEN", "CANARY_ALIAS")
    assert (
        cb.bind_first(
            "SONAR_TOKEN",
            "SONARCLOUD_TOKEN",
            infisical_cli=lambda _: None,
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
            **{k: v for k, v in os.environ.items() if k != "SEMGREP_APP_TOKEN"},
            "SEMGREP_APP_TOKEN": "CANARY_MUST_NOT_APPEAR",
        },
    )
    assert "CANARY_MUST_NOT_APPEAR" not in result.stdout
    assert "CANARY_MUST_NOT_APPEAR" not in result.stderr
    assert "SEMGREP_APP_TOKEN:" in result.stdout
    assert "source=" in result.stdout


def test_check_cli_translates_a_legacy_ref_to_its_infisical_name() -> None:
    """ADR-0053: a legacy openclaw-igorbot ref checks its Infisical name, never AWS."""
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(SECRETS_DIR / "capability_bind.py"),
            "--check",
            "openclaw-igorbot/semgrep#token",
            "openclaw-igorbot/nope#nothing",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
        env={
            **{k: v for k, v in os.environ.items() if k != "SEMGREP_APP_TOKEN"},
            "SEMGREP_APP_TOKEN": "CANARY_MUST_NOT_APPEAR",
        },
    )
    assert "CANARY_MUST_NOT_APPEAR" not in result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert lines[0].startswith("SEMGREP_APP_TOKEN: bound source=")
    assert lines[1].startswith("<not-in-inventory>:")
    assert "openclaw-igorbot" not in result.stdout  # the raw argument is never echoed
    assert result.returncode == 1


def test_legacy_ref_map_is_the_port_tools_map() -> None:
    import legacy_refs
    import port_aws_to_infisical

    assert port_aws_to_infisical.ENV_MAP is legacy_refs.ENV_MAP
    assert legacy_refs.infisical_name("openclaw-igorbot/github#token") == "GITHUB_TOKEN"
    assert legacy_refs.infisical_name("openclaw-igorbot/sonarcloud#token") == "SONAR_TOKEN"
    assert legacy_refs.infisical_name("openclaw-igorbot/context7#apikey") == "CONTEXT7_API_KEY"
    assert legacy_refs.infisical_name("GITHUB_TOKEN") is None
    # Refs the port named through its generic fallback translate the same way.
    assert port_aws_to_infisical.env_name is legacy_refs.env_name
    assert (
        legacy_refs.infisical_name("openclaw-igorbot/google-service-account#private_key")
        == "GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY"
    )
    assert "GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY" in cb.allowed_names()
    # Every mapped name an agent binds must pass the bind name gate.
    for name in ("GITHUB_TOKEN", "SONAR_TOKEN", "SEMGREP_APP_TOKEN", "CONTEXT7_API_KEY"):
        assert name in cb.allowed_names()


# --- the machine identity: one non-AWS bootstrap secret ----------------------

import infisical_cli_login as machine_login  # noqa: E402

IDENTITY_ENV = {
    "L9_INFISICAL_CLIENT_ID": "client-id-not-secret",
    "L9_INFISICAL_CLIENT_SECRET": "CANARY_BOOTSTRAP_SECRET_VALUE",
}


def test_env_identity_takes_the_project_from_the_inventory() -> None:
    identity = machine_login.env_identity(IDENTITY_ENV)
    assert identity is not None
    assert identity["client_id"] == "client-id-not-secret"
    assert identity["project_id"] == "9f92179d-3caa-4d7a-90a9-bb896499bfe6"
    assert identity["environment"] == "prod"
    assert identity["host"] == "https://app.infisical.com"


def test_env_identity_needs_both_halves() -> None:
    assert machine_login.env_identity({"L9_INFISICAL_CLIENT_ID": "x"}) is None
    assert machine_login.env_identity({"L9_INFISICAL_CLIENT_SECRET": "x"}) is None
    assert machine_login.env_identity({}) is None


def test_env_identity_refuses_ambient_routing_overrides() -> None:
    """Hosted bootstrap cannot be pointed at another host, project, or environment."""
    route = machine_login.canonical_route()
    assert machine_login.env_identity(IDENTITY_ENV)["host"] == route["host"]
    assert (
        machine_login.env_identity({**IDENTITY_ENV, "L9_INFISICAL_HOST": "https://evil.example"})
        is None
    )
    assert (
        machine_login.env_identity(
            {**IDENTITY_ENV, "L9_INFISICAL_PROJECT_ID": "00000000-0000-0000-0000-000000000000"}
        )
        is None
    )
    assert machine_login.env_identity({**IDENTITY_ENV, "L9_INFISICAL_ENV": "dev"}) is None
    repeated = machine_login.env_identity(
        {
            **IDENTITY_ENV,
            "L9_INFISICAL_HOST": route["host"],
            "L9_INFISICAL_PROJECT_ID": route["project_id"],
            "L9_INFISICAL_ENV": route["environment"],
        }
    )
    assert repeated is not None
    assert repeated["host"] == route["host"]
    assert repeated["project_id"] == route["project_id"]
    assert repeated["environment"] == route["environment"]


def test_infisical_transport_refuses_a_noncanonical_host() -> None:
    import infisical_http

    with pytest.raises(ValueError, match="refusing"):
        infisical_http.infisical_req("https://evil.example", "GET", "/api/v1/workspace")


def test_the_environment_identity_wins_over_the_workstation_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile = tmp_path / "l9-machine.json"
    profile.write_text(
        json.dumps({"client_id": "file", "client_secret": "file-secret", "project_id": "p"})
    )
    monkeypatch.setattr(machine_login, "PROFILE", profile)
    assert machine_login.machine_identity(IDENTITY_ENV)[0] == "env"
    assert machine_login.machine_identity({})[0] == "profile"
    monkeypatch.setattr(machine_login, "PROFILE", tmp_path / "absent.json")
    assert machine_login.machine_identity({}) == ("", None)


def test_ensure_reports_absent_refused_and_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(machine_login, "PROFILE", Path("/nonexistent/l9-machine.json"))
    assert machine_login.ensure_machine_profile({}) == "absent"
    monkeypatch.setattr(machine_login, "universal_auth_login", lambda *a, **k: "")
    assert machine_login.ensure_machine_profile(IDENTITY_ENV) == "failed"
    monkeypatch.setattr(machine_login, "universal_auth_login", lambda *a, **k: "token")
    assert machine_login.ensure_machine_profile(IDENTITY_ENV) == "env"


def test_bind_as_the_env_identity_over_http_never_exports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End to end through capability_bind: env identity -> UA login -> one secret."""
    import infisical_http

    cb.reset_cache()
    for name, value in IDENTITY_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
    calls: list[tuple[str, str]] = []

    def fake_req(host, method, path, token=None, body=None, retries=6):
        calls.append((method, path.split("?")[0]))
        if path == "/api/v1/auth/universal-auth/login":
            assert body == {
                "clientId": "client-id-not-secret",
                "clientSecret": "CANARY_BOOTSTRAP_SECRET_VALUE",
            }
            return 200, {"accessToken": "ua-token"}
        assert token == "ua-token"
        return 200, {"secret": {"secretKey": "CONTEXT7_API_KEY", "secretValue": "ctx7sk-CANARY"}}

    monkeypatch.setattr(infisical_http, "infisical_req", fake_req)
    assert cb.bind("CONTEXT7_API_KEY") == "ctx7sk-CANARY"
    assert cb.bind_status("CONTEXT7_API_KEY")["source"] == "infisical"
    assert "CONTEXT7_API_KEY" not in os.environ
    assert calls == [
        ("POST", "/api/v1/auth/universal-auth/login"),
        ("GET", "/api/v3/secrets/raw/CONTEXT7_API_KEY"),
    ]
    cb.reset_cache()


def test_a_failed_login_is_attempted_once_for_every_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every name binds through one identity; a lost login is lost for all of them."""
    import infisical_http

    for name, value in IDENTITY_ENV.items():
        monkeypatch.setenv(name, value)
    for name in ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "CONTEXT7_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    logins: list[str] = []

    def fake_req(host, method, path, token=None, body=None, retries=6):
        logins.append(path)
        return 403, {"error": "denied"}

    monkeypatch.setattr(infisical_http, "infisical_req", fake_req)
    for name in ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "CONTEXT7_API_KEY"):
        assert cb.bind_status(name)["source"] == "unbound"
    assert logins == ["/api/v1/auth/universal-auth/login"]
    cb.reset_cache()
    assert cb.bind_status("SONAR_TOKEN")["source"] == "unbound"
    assert len(logins) == 2, "reset_cache clears the remembered failure"


def test_a_noted_login_failure_skips_the_login_entirely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import infisical_http

    for name, value in IDENTITY_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("SONAR_TOKEN", raising=False)

    def fake_req(*_a, **_k):
        raise AssertionError("no login after note_login_failed")

    monkeypatch.setattr(infisical_http, "infisical_req", fake_req)
    cb.note_login_failed()
    assert cb.bind_status("SONAR_TOKEN") == {
        "name": "SONAR_TOKEN",
        "bound": False,
        "source": "unbound",
    }


def test_the_bootstrap_secret_itself_is_never_bound() -> None:
    cb.reset_cache()
    assert cb.bind_status("L9_INFISICAL_CLIENT_SECRET")["source"] == "refused"
    cb.reset_cache()


def test_the_aws_seed_is_cursors_path_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Cursor / operator seed the profile from AWS; Claude never calls the seed."""
    import stat

    profile = tmp_path / "l9-machine.json"
    monkeypatch.setattr(machine_login, "PROFILE", profile)
    calls: list[str] = []

    def seed() -> dict[str, str]:
        calls.append("seed")
        return {
            "schema": "1",
            "host": "https://app.infisical.com",
            "project_id": "p",
            "environment": "prod",
            "client_id": "cid",
            "client_secret": "seeded-secret",
        }

    monkeypatch.setattr(machine_login, "_seed_from_aws", seed)
    monkeypatch.setattr(machine_login, "universal_auth_login", lambda *a, **k: "token")
    assert machine_login.ensure_machine_profile({}) == "absent"
    assert calls == [], "no seed without allow_aws_seed (Claude)"
    assert machine_login.ensure_machine_profile({}, allow_aws_seed=True) == "seeded"
    assert calls == ["seed"]
    assert stat.S_IMODE(profile.stat().st_mode) == 0o600
    assert machine_login.ensure_machine_profile({}, allow_aws_seed=True) == "present"
    assert calls == ["seed"], "an existing profile is used as before, never re-seeded"


def test_a_failed_seed_is_failed_not_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(machine_login, "PROFILE", tmp_path / "l9-machine.json")
    monkeypatch.setattr(machine_login, "_seed_from_aws", lambda: None)
    assert machine_login.ensure_machine_profile({}, allow_aws_seed=True) == "failed"
