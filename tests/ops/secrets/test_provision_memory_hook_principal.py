"""The l9-memory-hooks provisioning script: dry run by default, idempotent, no values out."""

from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import provision_memory_hook_principal as prov  # noqa: E402

DOMAIN = "tenant.example.test"
AUDIENCE = "https://memory.example.test/mcp"
CG, MEM = "cg-project", "mem-project"
NEW_ID = "hookclientid0000WXYZ"
NEW_SECRET = "hook-SECRET-sentinel-never-printed"
MGMT_SECRET = "mgmt-SECRET-sentinel-never-printed"
TARGETS = prov.Targets(audience=AUDIENCE, cg_project=CG, memory_project=MEM)


class FakeAuth0:
    def __init__(self, *, app: bool = False, grant: bool = False, token_status: int = 200) -> None:
        self.app = app
        self.grant = grant
        self.token_status = token_status
        self.calls: list[tuple[str, str, Any]] = []

    def __call__(self, method: str, url: str, headers: Any, body: bytes | None) -> tuple[int, Any]:
        parsed = urllib.parse.urlparse(url)
        assert parsed.scheme == "https" and parsed.hostname == DOMAIN
        payload: Any = None
        if body and headers.get("Content-Type") == "application/json":
            payload = json.loads(body)
        elif body:
            payload = dict(urllib.parse.parse_qsl(body.decode()))
        self.calls.append((method, parsed.path, payload))
        if parsed.path == "/oauth/token":
            if payload["client_id"] == "mgmt-id":
                return 200, {"access_token": "mgmt-token"}
            assert payload["audience"] == AUDIENCE and payload["client_secret"] == NEW_SECRET
            return self.token_status, {"access_token": "hook-token"}
        if method == "GET" and parsed.path == "/api/v2/clients":
            return 200, [{"client_id": "other", "name": "x"}] + (
                [{"client_id": NEW_ID, "name": prov.APP_NAME}] if self.app else []
            )
        if method == "POST" and parsed.path == "/api/v2/clients":
            self.app = True
            return 201, {"client_id": NEW_ID, "client_secret": NEW_SECRET}
        if method == "GET" and parsed.path == "/api/v2/client-grants":
            return 200, [{"audience": AUDIENCE}] if self.grant else []
        if method == "POST" and parsed.path == "/api/v2/client-grants":
            assert payload == {"client_id": NEW_ID, "audience": AUDIENCE, "scope": []}
            self.grant = True
            return 201, {}
        raise AssertionError(f"unexpected {method} {parsed.path}")

    def writes(self) -> list[tuple[str, str]]:
        return [(m, p) for m, p, _ in self.calls if m == "POST" and p != "/oauth/token"]


class FakeInfisical:
    def __init__(self, store: dict[tuple[str, str], str] | None = None, forbid: str = "") -> None:
        self.store = dict(store or {})
        self.forbid = forbid
        self.writes: list[tuple[str, str]] = []

    def __call__(self, method: str, path: str, body: dict[str, Any] | None) -> tuple[int, Any]:
        name = path.split("/api/v3/secrets/raw/")[1].split("?")[0]
        if method == "GET":
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(path).query))
            assert query["environment"] == "prod" and query["secretPath"] == "/"
            value = self.store.get((query["workspaceId"], name))
            return (200, {"secret": {"secretValue": value}}) if value else (404, {})
        assert body is not None and body["environment"] == "prod" and body["secretPath"] == "/"
        if self.forbid and body["workspaceId"] == self.forbid:
            return 403, {}
        self.store[(body["workspaceId"], name)] = body["secretValue"]
        self.writes.append((body["workspaceId"], name))
        return 200, {"secret": {}}


def _run(auth0: FakeAuth0, infisical: FakeInfisical, *, apply: bool) -> tuple[int, str]:
    lines: list[str] = []
    provisioner = prov.Provisioner(
        targets=TARGETS,
        domain=DOMAIN,
        management_id="mgmt-id",
        management_secret=MGMT_SECRET,
        http=auth0,
        infisical=infisical,
        apply=apply,
        log=lines.append,
    )
    try:
        code = provisioner.run()
    except prov.Stop as stop:
        lines.append(f"STOP: {stop}")
        code = stop.code
    return code, "\n".join(lines)


def _assert_no_values(out: str) -> None:
    for value in (NEW_SECRET, MGMT_SECRET, "mgmt-token", "hook-token", NEW_ID, '"surface"'):
        assert value not in out


def test_dry_run_changes_nothing_and_says_what_it_would_do() -> None:
    auth0, infisical = FakeAuth0(), FakeInfisical()
    code, out = _run(auth0, infisical, apply=False)
    assert code == prov.EXIT_OK
    assert auth0.writes() == [] and infisical.writes == []
    assert "DRY RUN" in out and "would create" in out
    assert "auth0 app" in out and "L9_MEMORY_HOOK_PRINCIPALS_JSON" in out
    _assert_no_values(out)


def test_apply_creates_app_grant_three_names_and_verifies_the_token() -> None:
    auth0, infisical = FakeAuth0(), FakeInfisical()
    code, out = _run(auth0, infisical, apply=True)
    assert code == prov.EXIT_OK
    assert auth0.writes() == [("POST", "/api/v2/clients"), ("POST", "/api/v2/client-grants")]
    assert infisical.store[(CG, "L9_MEMORY_HOOK_CLIENT_ID")] == NEW_ID
    assert infisical.store[(CG, "L9_MEMORY_HOOK_CLIENT_SECRET")] == NEW_SECRET
    envelope = json.loads(infisical.store[(MEM, "L9_MEMORY_HOOK_PRINCIPALS_JSON")])
    assert envelope == {NEW_ID: prov.ENVELOPE}
    assert envelope[NEW_ID]["write_namespaces"] == ["@l9-repositories"]
    assert "HTTP 200" in out and f"…{NEW_ID[-4:]}" in out
    _assert_no_values(out)


def test_a_second_apply_is_a_no_op() -> None:
    auth0, infisical = FakeAuth0(), FakeInfisical()
    _run(auth0, infisical, apply=True)
    before = (list(auth0.writes()), list(infisical.writes))
    code, out = _run(auth0, infisical, apply=True)
    assert code == prov.EXIT_OK
    assert (auth0.writes(), infisical.writes) == before
    assert "nothing (already provisioned)" in out


def test_an_existing_app_without_a_stored_secret_stops_instead_of_rotating() -> None:
    auth0 = FakeAuth0(app=True, grant=True)
    code, out = _run(auth0, FakeInfisical(), apply=True)
    assert code == prov.EXIT_STOP
    assert "operator decision" in out and auth0.writes() == []


def test_a_stored_value_that_differs_is_never_overwritten() -> None:
    auth0 = FakeAuth0(app=True, grant=True)
    infisical = FakeInfisical(
        {
            (CG, "L9_MEMORY_HOOK_CLIENT_SECRET"): NEW_SECRET,
            (CG, "L9_MEMORY_HOOK_CLIENT_ID"): "some-other-client",
        }
    )
    code, out = _run(auth0, infisical, apply=True)
    assert code == prov.EXIT_STOP
    assert "different value" in out and infisical.writes == []
    _assert_no_values(out)


def test_an_infisical_403_stops_naming_project_and_env() -> None:
    code, out = _run(FakeAuth0(), FakeInfisical(forbid=MEM), apply=True)
    assert code == prov.EXIT_FORBIDDEN
    assert "Infisical 403" in out and "l9-graphite-memory/prod" in out


def test_a_hook_token_that_is_not_200_fails() -> None:
    code, out = _run(FakeAuth0(token_status=401), FakeInfisical(), apply=True)
    assert code == prov.EXIT_FAILED and "HTTP 401" in out


def test_targets_come_from_the_repository_files() -> None:
    targets = prov.load_targets()
    assert targets.audience.startswith("https://") and targets.audience.endswith("/mcp")
    assert targets.cg_project != targets.memory_project
