"""Manus shared-session identity is distinct from its encrypted MCP connector."""

from __future__ import annotations

import importlib
import json
import os
import sys
import urllib.parse
from pathlib import Path
from unittest import mock

import pytest

SECRETS = Path(__file__).resolve().parents[3] / "ops" / "secrets"
if str(SECRETS) not in sys.path:
    sys.path.insert(0, str(SECRETS))

login = importlib.import_module("infisical_cli_login")
plane = importlib.import_module("session_start_secrets")
cb = plane.cb
http = importlib.import_module("infisical_http")

MANUS = {"L9_GOVERNANCE_SURFACE": "manus"}
CANARY = "CANARY_MACHINE_SECRET_DO_NOT_EMIT"


@pytest.fixture(autouse=True)
def _clear_binder():
    cb.reset_cache()
    yield
    cb.reset_cache()


def _forbidden(*args, **kwargs):
    raise AssertionError("operator/AWS path reached from Manus")


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"L9_INFISICAL_CLIENT_ID": "fixture-client"},
        {
            "L9_MANUS_INFISICAL_CLIENT_ID": "connector-id",
            "L9_MANUS_INFISICAL_CLIENT_SECRET": CANARY,
        },
        {
            "L9_INFISICAL_CLIENT_ID": "fixture-client",
            "L9_INFISICAL_CLIENT_SECRET": CANARY,
            "L9_INFISICAL_PROJECT_ID": "wrong-project",
        },
    ],
)
def test_manus_absent_partial_connector_or_redirected_identity_never_borrows_profile(
    monkeypatch, extra
):
    env = {**MANUS, **extra}
    monkeypatch.setattr(login, "file_identity", _forbidden)
    monkeypatch.setattr(login, "_seed_from_aws", _forbidden)
    monkeypatch.setattr(login, "universal_auth_login", _forbidden)
    assert login.machine_identity(env) == ("", None)
    assert login.ensure_machine_profile(env, allow_aws_seed=True) == "absent"
    assert plane.surface_class(env) == plane.MODEL_CONTROLLED


@pytest.mark.parametrize("token,expected", [("fixture-access-token", "env"), ("", "failed")])
def test_manus_env_login_uses_only_canonical_route_and_keeps_values_internal(
    monkeypatch, token, expected
):
    env = {
        **MANUS,
        "L9_INFISICAL_CLIENT_ID": "fixture-client",
        "L9_INFISICAL_CLIENT_SECRET": CANARY,
    }
    monkeypatch.setattr(login, "file_identity", _forbidden)
    monkeypatch.setattr(login, "_seed_from_aws", _forbidden)
    calls = []
    monkeypatch.setattr(login, "universal_auth_login", lambda *args: calls.append(args) or token)
    assert login.ensure_machine_profile(env, allow_aws_seed=True) == expected
    assert calls == [(login.canonical_route()["host"], "fixture-client", CANARY)]
    assert CANARY not in json.dumps(plane.identity_status(expected, "env"))


@pytest.mark.parametrize("state", ["absent", "failed", "env"])
def test_plane_manus_never_calls_aws_and_does_not_claim_connector_readiness(monkeypatch, state):
    monkeypatch.setattr(plane, "_aws_probe", _forbidden)
    monkeypatch.setattr(login, "file_identity", _forbidden)
    monkeypatch.setattr(login, "_seed_from_aws", _forbidden)
    calls = []
    monkeypatch.setattr(login, "ensure_machine_profile", lambda env: calls.append(env) or state)
    monkeypatch.setattr(plane.cb, "note_login_failed", lambda env=None: None)
    monkeypatch.setattr(
        plane.cb, "bind_status", lambda name, *, env=None: {"bound": False, "source": "unbound"}
    )
    env = {**MANUS, "L9_MANUS_INFISICAL_CLIENT_SECRET": CANARY}
    result = plane.run_plane(env)
    assert calls == [env]
    assert result["surface_class"] == plane.MODEL_CONTROLLED
    assert "aws" not in result
    assert result["plane_ok"] is (state == "env")
    assert CANARY not in json.dumps(plane.receipt_payload(result))


def test_explicit_manus_wins_over_inherited_claude_pool(monkeypatch):
    env = {**MANUS, "CLAUDE_CODE_REMOTE_ENVIRONMENT_ID": "ccpool_stale"}
    assert plane.surface_class(env) == plane.MODEL_CONTROLLED
    assert (
        plane.surface_class({"CLAUDE_CODE_REMOTE_ENVIRONMENT_ID": "ccpool_real"})
        == plane.SELF_HOSTED
    )


def test_cursor_and_operator_keep_existing_profile_and_seed_behavior(monkeypatch):
    profile = {"client_id": "operator-id"}
    monkeypatch.setattr(login, "file_identity", lambda: profile)
    assert login.machine_identity({"L9_GOVERNANCE_SURFACE": "cursor"}) == ("profile", profile)
    assert login.machine_identity({}) == ("profile", profile)
    assert (
        login.ensure_machine_profile({"L9_GOVERNANCE_SURFACE": "cursor"}, allow_aws_seed=True)
        == "present"
    )


OPERATOR_ONLY = ("AUTH0_CLIENT_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET")
OPERATOR_ENV = {
    "L9_GOVERNANCE_SURFACE": "cursor",
    "GITHUB_TOKEN": "CANARY_OPERATOR_IMPORTED",
    **{name: "CANARY_OPERATOR_ONLY_IMPORTED" for name in OPERATOR_ONLY},
}
MANUS_IDENTITY = {
    "L9_INFISICAL_CLIENT_ID": "fixture-manus-client",
    "L9_INFISICAL_CLIENT_SECRET": CANARY,
}
INVALID_MANUS_CONTEXTS = [
    {},
    {"L9_INFISICAL_CLIENT_ID": "fixture-manus-client"},
    {"L9_INFISICAL_CLIENT_SECRET": CANARY},
    {"L9_MANUS_INFISICAL_CLIENT_ID": "connector-id", "L9_MANUS_INFISICAL_CLIENT_SECRET": CANARY},
    {**MANUS_IDENTITY, "L9_INFISICAL_PROJECT_ID": "wrong-project"},
    {**MANUS_IDENTITY, "L9_INFISICAL_ENV": "wrong-env"},
    {**MANUS_IDENTITY, "L9_INFISICAL_HOST": "https://wrong.invalid"},
    MANUS_IDENTITY,
]


@pytest.fixture
def primed_operator_binder(monkeypatch):
    """Real binder/profile/token/value caches; HTTP and profile bytes are fixtures only."""
    counts = {"profile": 0, "operator_login": 0, "manus_login": 0, "get": 0}
    phase = {"manus": False}
    profile = {
        **login.canonical_route(),
        "client_id": "fixture-operator-client",
        "client_secret": "CANARY_OPERATOR_MACHINE_SECRET",
    }

    def file_identity():
        if phase["manus"]:
            _forbidden()
        counts["profile"] += 1
        return profile

    def fake_req(host, method, path, token=None, body=None, retries=6):
        assert host == login.canonical_route()["host"]
        if method == "POST":
            assert path == "/api/v1/auth/universal-auth/login"
            if phase["manus"]:
                assert body == {
                    "clientId": "fixture-manus-client",
                    "clientSecret": CANARY,
                }
                counts["manus_login"] += 1
                return 403, {"error": "fixture-refused"}
            assert body == {
                "clientId": profile["client_id"],
                "clientSecret": profile["client_secret"],
            }
            counts["operator_login"] += 1
            return 200, {"accessToken": "CANARY_OPERATOR_ACCESS_TOKEN"}
        assert not phase["manus"], "Manus must not fetch with a cached operator token"
        assert method == "GET"
        assert token == "CANARY_OPERATOR_ACCESS_TOKEN"
        counts["get"] += 1
        name = urllib.parse.unquote(path.split("?")[0].rsplit("/", 1)[-1])
        return 200, {"secret": {"secretKey": name, "secretValue": "CANARY_OPERATOR_BOUND"}}

    monkeypatch.setattr(login, "file_identity", file_identity)
    monkeypatch.setattr(login, "_seed_from_aws", _forbidden)
    monkeypatch.setattr(login, "_write_profile", _forbidden)
    monkeypatch.setattr(plane, "_aws_probe", _forbidden)
    monkeypatch.setattr(http, "infisical_req", fake_req)
    with mock.patch.dict(os.environ, OPERATOR_ENV, clear=True):
        for name in (*plane.BIND_NAMES, *OPERATOR_ONLY):
            assert cb.bind(name)
            assert cb.bind_status(name)["bound"]
        assert cb._PROFILE_SOURCE == "profile"
        assert cb._PROFILE == profile
        assert cb._UA_TOKEN == "CANARY_OPERATOR_ACCESS_TOKEN"
        assert set(cb._VALUES) == {*plane.BIND_NAMES, *OPERATOR_ONLY}
        assert counts == {"profile": 1, "operator_login": 1, "manus_login": 0, "get": 3}
        phase["manus"] = True
        yield counts


@pytest.mark.parametrize("explicit", [True, False], ids=["explicit-mapping", "ambient-transition"])
@pytest.mark.parametrize(
    "extra",
    INVALID_MANUS_CONTEXTS,
    ids=["absent", "id-only", "secret-only", "connector-only", "project", "env", "host", "refused"],
)
def test_real_binder_plane_cannot_reuse_operator_context(
    monkeypatch, primed_operator_binder, extra, explicit, capsys
):
    env = {**MANUS, **extra}
    if not explicit:
        # Change the real process mapping, not an explicit bind argument. The
        # fixture restores every ambient entry when the test leaves its scope.
        # Operator-only imports remain present: even these must be refused.
        inherited = {name: OPERATOR_ENV[name] for name in OPERATOR_ONLY}
        with mock.patch.dict(os.environ, {**inherited, **env}, clear=True):
            _assert_failed_manus_context(plane.run_plane(), None, env, primed_operator_binder)
            assert dict(os.environ) == {**inherited, **env}
    else:
        ambient_before = dict(os.environ)
        _assert_failed_manus_context(plane.run_plane(env), env, env, primed_operator_binder)
        assert dict(os.environ) == ambient_before
    assert capsys.readouterr() == ("", "")


def _assert_failed_manus_context(result, bind_env, expected_env, counts):
    expected_login = "failed" if expected_env == {**MANUS, **MANUS_IDENTITY} else "absent"
    expected_source = (
        cb.SOURCE_UNBOUND if expected_login == "failed" else cb.SOURCE_INFISICAL_ABSENT
    )
    assert result["surface_class"] == plane.MODEL_CONTROLLED
    assert result["login"] == expected_login
    assert result["state"] == plane.STATE_FAILED
    assert not result["plane_ok"]
    assert "aws" not in result
    assert all(not row["bound"] and row["source"] == expected_source for row in result["binds"])
    for name in OPERATOR_ONLY:
        assert cb.bind(name, env=bind_env) is None
        assert cb.bind_status(name, env=bind_env) == {
            "name": name,
            "bound": False,
            "source": cb.SOURCE_OPERATOR_ONLY_REFUSED,
        }
    for name in plane.BIND_NAMES:
        assert cb.bind(name, env=bind_env) is None
    assert cb._PROFILE_SOURCE != "profile"
    assert cb._UA_TOKEN is None
    assert not cb._VALUES
    assert counts == {
        "profile": 1,
        "operator_login": 1,
        "manus_login": int(expected_login == "failed"),
        "get": 3,
    }
    blob = json.dumps(plane.receipt_payload(result))
    assert "CANARY" not in blob
    assert "fingerprint" not in blob.lower()
    assert "fixture-manus-client" not in blob


@pytest.mark.parametrize("entry", ["bind", "bind_first", "bind_status", "profile", "operator"])
def test_each_binder_entry_invalidates_before_a_cached_operator_hit(primed_operator_binder, entry):
    env = dict(MANUS)
    if entry == "bind":
        assert cb.bind("AUTH0_CLIENT_SECRET", env=env) is None
    elif entry == "bind_first":
        assert cb.bind_first("GITHUB_TOKEN", "SONAR_TOKEN", env=env) is None
    elif entry == "bind_status":
        assert not cb.bind_status("GITHUB_TOKEN", env=env)["bound"]
    elif entry == "profile":
        assert cb._machine_profile(env) is None
    else:
        assert not cb._operator_surface(env)
    assert cb._UA_TOKEN is None
    assert not cb._VALUES
    assert cb._PROFILE_SOURCE != "profile"
    assert primed_operator_binder["profile"] == 1
    assert primed_operator_binder["get"] == 3


def test_explicit_operator_context_does_not_inherit_an_ambient_manus_marker(monkeypatch):
    profile = {**login.canonical_route(), "client_id": "operator-id", "client_secret": CANARY}
    monkeypatch.setattr(login, "file_identity", lambda: profile)
    monkeypatch.setattr(login, "_seed_from_aws", _forbidden)
    monkeypatch.setattr(http, "infisical_req", _forbidden)
    monkeypatch.setattr(plane, "_aws_probe", lambda: {"ok": True})
    env = {
        "L9_GOVERNANCE_SURFACE": "cursor",
        **{name: "CANARY_EXPLICIT_OPERATOR_VALUE" for name in plane.BIND_NAMES},
        "AUTH0_CLIENT_SECRET": "CANARY_EXPLICIT_OPERATOR_VALUE",
    }
    with mock.patch.dict(os.environ, MANUS, clear=True):
        before = dict(os.environ)
        result = plane.run_plane(env)
        assert result["state"] == plane.STATE_OK
        assert result["surface_class"] == plane.OPERATOR
        assert result["identity"]["source"] == "profile"
        assert all(row["source"] == cb.SOURCE_ENV for row in result["binds"])
        assert cb.bind("AUTH0_CLIENT_SECRET", env=env) == "CANARY_EXPLICIT_OPERATOR_VALUE"
        assert dict(os.environ) == before


def test_explicit_context_is_monotonic_for_equal_mappings_and_name_only_callbacks() -> None:
    env = {"L9_GOVERNANCE_SURFACE": "manus"}
    calls = []

    def fetch(name):
        calls.append(name)
        return "CANARY_FIRST_BOUND_VALUE"

    assert cb.bind("SONAR_TOKEN", env=env, infisical_cli=fetch) == "CANARY_FIRST_BOUND_VALUE"
    assert cb.bind_status("SONAR_TOKEN", env=dict(env))["source"] == "infisical"
    assert (
        cb.bind_first("SONAR_TOKEN", "SONARCLOUD_TOKEN", env=dict(env), infisical_cli=fetch)
        == "CANARY_FIRST_BOUND_VALUE"
    )
    assert calls == ["SONAR_TOKEN"]
    assert env == {"L9_GOVERNANCE_SURFACE": "manus"}


@pytest.mark.parametrize(
    "changed",
    [
        {"L9_GOVERNANCE_SURFACE": "cursor"},
        {"CLAUDE_CODE_REMOTE": "true"},
        {"L9_INFISICAL_CLIENT_ID": "different-id"},
        {"L9_INFISICAL_CLIENT_SECRET": "CANARY_DIFFERENT_SECRET"},
        {"L9_INFISICAL_HOST": "https://different.invalid"},
        {"UNRELATED_CONTEXT_MARKER": "changed"},
    ],
)
def test_complete_context_changes_invalidate_value_and_source_before_a_hit(changed) -> None:
    env = {"L9_GOVERNANCE_SURFACE": "manus"}
    assert cb.bind("GITHUB_TOKEN", env=env, infisical_cli=lambda _: "CANARY_OLD") == "CANARY_OLD"
    assert cb.bind_status("GITHUB_TOKEN", env=env)["bound"]
    changed_env = {**env, **changed}
    assert cb.bind("GITHUB_TOKEN", env=changed_env, infisical_cli=lambda _: None) is None
    assert cb.bind_status("GITHUB_TOKEN", env=changed_env) == {
        "name": "GITHUB_TOKEN",
        "bound": False,
        "source": "unbound",
    }


def test_status_and_aliases_read_only_the_supplied_environment(monkeypatch) -> None:
    monkeypatch.setenv("SONAR_TOKEN", "CANARY_AMBIENT")
    env = {"L9_GOVERNANCE_SURFACE": "manus", "SONARCLOUD_TOKEN": "CANARY_EXPLICIT_ALIAS"}
    before = dict(os.environ)
    assert cb.bind_status("SONAR_TOKEN", env=env)["source"] == "infisical-machine-absent"
    assert cb.bind_first("SONAR_TOKEN", "SONARCLOUD_TOKEN", env=env) == "CANARY_EXPLICIT_ALIAS"
    assert cb.bind_status("SONARCLOUD_TOKEN", env=env)["source"] == "env"
    assert dict(os.environ) == before
    assert env == {"L9_GOVERNANCE_SURFACE": "manus", "SONARCLOUD_TOKEN": "CANARY_EXPLICIT_ALIAS"}


def test_failed_login_is_local_to_its_context_and_changed_secret_reauthenticates(monkeypatch):
    import infisical_http

    env = {"L9_GOVERNANCE_SURFACE": "manus", **MANUS_IDENTITY}
    next_env = {**env, "L9_INFISICAL_CLIENT_SECRET": "CANARY_REPLACEMENT_SECRET"}
    calls = []

    def fake_req(host, method, path, token=None, body=None, retries=6):
        calls.append(method)
        if method == "POST":
            assert body == {
                "clientId": next_env["L9_INFISICAL_CLIENT_ID"],
                "clientSecret": next_env["L9_INFISICAL_CLIENT_SECRET"],
            }
            return 200, {"accessToken": "CANARY_REPLACEMENT_ACCESS_TOKEN"}
        assert token == "CANARY_REPLACEMENT_ACCESS_TOKEN"
        return 200, {"secret": {"secretKey": "SONAR_TOKEN", "secretValue": "CANARY_REPLACEMENT"}}

    monkeypatch.setattr(infisical_http, "infisical_req", fake_req)
    cb.note_login_failed(env)
    assert cb.bind_status("SONAR_TOKEN", env=env)["source"] == "unbound"
    assert cb.bind("GITHUB_TOKEN", env=env) is None
    assert calls == []
    assert cb.bind("SONAR_TOKEN", env=next_env) == "CANARY_REPLACEMENT"
    assert cb.bind_status("SONAR_TOKEN", env=dict(next_env))["source"] == "infisical"
    assert cb.bind("SONAR_TOKEN", env=next_env) == "CANARY_REPLACEMENT"
    assert calls == ["POST", "GET"]
    assert cb._PROFILE["client_secret"] == next_env["L9_INFISICAL_CLIENT_SECRET"]
    assert cb._PROFILE_SOURCE == "env"
    assert not cb._LOGIN_STATE["failed"]
    cb.reset_cache()
    assert not cb._VALUES and not cb._SOURCES
    assert cb._PROFILE is None and cb._UA_TOKEN is None
    assert cb._CONTEXT_FINGERPRINT is None
    assert not cb._LOGIN_STATE["failed"]
