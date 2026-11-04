"""operator_only_iam: hosted identities hold a forbid privilege on operator-only names."""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import capability_bind as cb  # noqa: E402
import operator_only_iam as iam  # noqa: E402

PROJECT = "test-project"
HOSTED_A = "test-hosted-a"
HOSTED_B = "test-hosted-b"
OPERATOR = "test-operator"
NAMES = ["AUTH0_CLIENT_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET"]
SLUG = "deny-operator-only-keys"


class FakeInfisical:
    """Identity memberships, identity privileges, universal auth and secret reads."""

    def __init__(self, *, readable_by_hosted: set[str] = frozenset(), mintable: bool = True):
        self.privileges: dict[str, dict[str, Any]] = {}
        self.readable_by_hosted = set(readable_by_hosted)
        self.mintable = mintable
        self.revoked: list[str] = []
        self.writes: list[str] = []

    def __call__(self, method: str, path: str, body: Any, token: str | None = None):
        parts = urllib.parse.urlsplit(path)
        query = dict(urllib.parse.parse_qsl(parts.query))
        route = parts.path
        if method != "GET":
            self.writes.append(f"{method} {route}")
        if route == f"/api/v2/workspace/{PROJECT}/identity-memberships":
            return 200, {
                "identityMemberships": [
                    {
                        "identity": {"id": HOSTED_A, "name": "claude-code"},
                        "roles": [{"role": "viewer"}],
                    },
                    {
                        "identity": {"id": HOSTED_B, "name": "claude-code"},
                        "roles": [{"role": "member"}],
                    },
                    {"identity": {"id": OPERATOR, "name": "Cursor"}, "roles": [{"role": "admin"}]},
                ]
            }
        if route == iam.PRIVILEGE_PATH and method == "GET":
            found = [p for p in self.privileges.values() if p["identityId"] == query["identityId"]]
            return 200, {"privileges": [{"id": p["id"], "slug": p["slug"]} for p in found]}
        if route == iam.PRIVILEGE_PATH and method == "POST":
            privilege = {**body, "id": f"priv-{body['identityId']}"}
            self.privileges[privilege["id"]] = privilege
            return 200, {"privilege": privilege}
        if route.startswith(iam.PRIVILEGE_PATH + "/"):
            privilege_id = route.rsplit("/", 1)[1]
            if method == "PATCH":
                self.privileges[privilege_id].update(body)
            return 200, {"privilege": self.privileges[privilege_id]}
        if route.startswith("/api/v1/auth/universal-auth/identities/"):
            identity = route.split("/")[6]
            if route.endswith("/revoke"):
                self.revoked.append(identity)
                return 200, {}
            if route.endswith("/client-secrets"):
                if not self.mintable:
                    return 403, {"message": "You are not allowed to create-token on identity"}
                return 200, {
                    "clientSecret": f"test-one-use-{identity}",
                    "clientSecretData": {"id": "s1"},
                }
            return 200, {"identityUniversalAuth": {"clientId": f"test-client-{identity}"}}
        if route == "/api/v3/secrets/raw":
            return 200, {"secrets": [{"secretKey": "SONAR_TOKEN"}]}
        if route.startswith("/api/v3/secrets/raw/"):
            name = urllib.parse.unquote(route.rsplit("/", 1)[1])
            hosted = token is not None and token.startswith("test-token-")
            if hosted and name in NAMES and name not in self.readable_by_hosted:
                return 403, {"message": "PermissionDenied"}
            return 200, {"secret": {"secretKey": name}}
        raise AssertionError(f"unrouted {method} {route}")


def _project(fake: FakeInfisical) -> iam.Project:
    return iam.Project(fake, PROJECT)


def test_policy_comes_from_the_inventory() -> None:
    names, hosted, slug = iam.policy()
    assert names == sorted(cb.operator_only_names())
    assert set(NAMES) <= set(names)
    assert "claude-code" in hosted
    assert slug == SLUG


def test_deny_rules_cover_legacy_read_separately() -> None:
    rules = iam.deny_rules(NAMES)
    assert [rule["action"] for rule in rules] == [["read"], list(iam.SECRET_ACTIONS)]
    assert "read" not in iam.SECRET_ACTIONS
    for rule in rules:
        assert rule["subject"] == "secrets"
        assert rule["inverted"] is True
        assert rule["conditions"] == {"secretName": {"$in": sorted(NAMES)}}


def test_plan_creates_for_hosted_identities_only_then_converges() -> None:
    fake = FakeInfisical()
    project = _project(fake)
    actions = iam.plan(project, NAMES, ["claude-code"], SLUG)
    assert [(a["op"], a["identity_id"]) for a in actions] == [
        ("create", HOSTED_A),
        ("create", HOSTED_B),
    ]
    iam.apply(project, actions, SLUG)
    assert {p["identityId"] for p in fake.privileges.values()} == {HOSTED_A, HOSTED_B}
    assert all(p["slug"] == SLUG for p in fake.privileges.values())
    assert iam.plan(project, NAMES, ["claude-code"], SLUG) == []


def test_plan_updates_a_stale_privilege() -> None:
    fake = FakeInfisical()
    project = _project(fake)
    iam.apply(project, iam.plan(project, NAMES, ["claude-code"], SLUG), SLUG)
    stale = fake.privileges[f"priv-{HOSTED_A}"]
    stale["permissions"] = iam.deny_rules(NAMES[:1])
    actions = iam.plan(project, NAMES, ["claude-code"], SLUG)
    assert [(a["op"], a["identity_id"]) for a in actions] == [("update", HOSTED_A)]
    iam.apply(project, actions, SLUG)
    assert fake.privileges[f"priv-{HOSTED_A}"]["slug"] == SLUG
    assert iam.plan(project, NAMES, ["claude-code"], SLUG) == []


def _login(client_id: str, secret: str) -> str:
    assert secret.startswith("test-one-use-")
    return "test-token-" + client_id


def test_probe_passes_when_hosted_reads_are_refused_and_revokes_each_secret() -> None:
    fake = FakeInfisical()
    failures, unprobed = iam.probe(fake, _login, _project(fake), NAMES, ["claude-code"], "prod")
    assert failures == [] and unprobed == []
    assert fake.revoked == [HOSTED_A, HOSTED_B]


def test_probe_reports_a_readable_operator_only_name() -> None:
    fake = FakeInfisical(readable_by_hosted={"AUTH0_CLIENT_SECRET"})
    failures, _ = iam.probe(fake, _login, _project(fake), NAMES, ["claude-code"], "prod")
    assert len(failures) == 2
    assert all("AUTH0_CLIENT_SECRET HTTP 200" in failure for failure in failures)
    assert fake.revoked == [HOSTED_A, HOSTED_B]


def test_probe_reports_unprobed_identities_without_passing_them() -> None:
    fake = FakeInfisical(mintable=False)
    failures, unprobed = iam.probe(fake, _login, _project(fake), NAMES, ["claude-code"], "prod")
    assert failures == []
    assert len(unprobed) == 2


@pytest.mark.parametrize(("readable", "expected"), [(set(), 0), ({"AUTH0_CLIENT_ID"}, 1)])
def test_self_probe(readable: set[str], expected: int, capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeInfisical(readable_by_hosted=readable)

    def as_hosted(method: str, path: str, body: Any, token: str | None = None):
        return fake(method, path, body, "test-token-self")

    assert iam.self_probe(as_hosted, PROJECT, NAMES, "prod") == expected
    out = capsys.readouterr().out
    assert "test-one-use-" not in out
