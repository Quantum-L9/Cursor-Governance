#!/usr/bin/env python3
"""Infisical IAM for ``operator_only_keys``: hosted identities cannot read them.

``capability_bind`` refuses operator-only names off the operator workstation,
but a hosted process controls both inputs to that check. The boundary is here:
every project identity named in ``operator_only_iam.hosted_identity_names``
keeps its built-in role and holds one identity-specific privilege that forbids
every secret action on the operator-only names.

Usage:
  operator_only_iam.py --check   # exit 1 if any hosted identity lacks the forbid privilege
  operator_only_iam.py --apply   # create or update the privilege on every hosted identity
  operator_only_iam.py --probe   # log in as each hosted identity once; prove deny and allow
  operator_only_iam.py --self-probe  # this surface's own identity: HTTP status per name

``--probe`` exits 1 on any unexpected read and 2 when an identity could not be
probed from this surface. ``--self-probe`` needs no admin rights; on a hosted
surface it exits 0 only when every operator-only name is refused. The other modes
run as this surface's machine identity, which must administer the project.
Prints names, IDs and HTTP statuses, never a secret value.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import urllib.parse
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import capability_bind  # noqa: E402

SECRET_ACTIONS = ("describeSecret", "readValue", "edit", "create", "delete")
LEGACY_READ = "read"
PRIVILEGE_PATH = "/api/v2/identity-project-additional-privilege"
Request = Callable[..., tuple[int, dict[str, Any]]]
"""``(method, path, body, token=None)``; ``token`` defaults to this surface's identity."""


class IamError(RuntimeError):
    pass


def policy() -> tuple[list[str], list[str], str]:
    """Operator-only names, hosted identity names and the privilege slug."""
    block = capability_bind._inventory().get("operator_only_iam") or {}
    names = sorted(capability_bind.operator_only_names())
    hosted = [str(name) for name in block.get("hosted_identity_names") or []]
    slug = str(block.get("privilege_slug") or "")
    if not names or not hosted or not slug:
        raise IamError(
            "inventory lacks operator_only_keys or operator_only_iam "
            "(hosted_identity_names, privilege_slug)"
        )
    return names, hosted, slug


def deny_rules(names: Iterable[str]) -> list[dict[str, Any]]:
    """Forbid every secret action on ``names``.

    Infisical's read check also accepts the legacy ``read`` action, which built-in
    roles such as ``member`` grant, and a rule may not combine ``read`` with
    ``describeSecret``/``readValue``; so ``read`` gets a forbid rule of its own.
    """
    conditions = {"secretName": {"$in": sorted(names)}}
    return [
        {"subject": "secrets", "action": [LEGACY_READ], "inverted": True, "conditions": conditions},
        {
            "subject": "secrets",
            "action": list(SECRET_ACTIONS),
            "inverted": True,
            "conditions": copy.deepcopy(conditions),
        },
    ]


def _canonical(rules: list[dict[str, Any]]) -> str:
    def norm(rule: dict[str, Any]) -> dict[str, Any]:
        out = {key: value for key, value in rule.items() if value is not None}
        out["inverted"] = bool(rule.get("inverted"))
        if isinstance(out.get("action"), list):
            out["action"] = sorted(out["action"])
        return out

    return json.dumps([norm(rule) for rule in rules], sort_keys=True)


class Project:
    def __init__(self, request: Request, project_id: str) -> None:
        self._request = request
        self.project_id = project_id

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        status, payload = self._request(method, path, body)
        if status >= 400:
            message = (payload or {}).get("message") or (payload or {}).get("error") or ""
            raise IamError(f"{method} {path.split('?')[0]}: HTTP {status} {str(message)[:200]}")
        return payload or {}

    def memberships(self) -> list[dict[str, Any]]:
        path = f"/api/v2/workspace/{self.project_id}/identity-memberships"
        return self.call("GET", path)["identityMemberships"]

    def privileges(self, identity_id: str) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"identityId": identity_id, "projectId": self.project_id})
        return self.call("GET", f"{PRIVILEGE_PATH}?{query}").get("privileges") or []

    def privilege(self, privilege_id: str) -> dict[str, Any]:
        """One privilege with its rules; the list endpoint omits them."""
        return self.call("GET", f"{PRIVILEGE_PATH}/{privilege_id}").get("privilege") or {}

    def create_privilege(self, identity_id: str, slug: str, rules: list[dict[str, Any]]) -> None:
        body = {
            "identityId": identity_id,
            "projectId": self.project_id,
            "slug": slug,
            "permissions": rules,
            "type": {"isTemporary": False},
        }
        self.call("POST", PRIVILEGE_PATH, body)

    def update_privilege(self, privilege_id: str, slug: str, rules: list[dict[str, Any]]) -> None:
        body = {"slug": slug, "permissions": rules, "type": {"isTemporary": False}}
        self.call("PATCH", f"{PRIVILEGE_PATH}/{privilege_id}", body)


def hosted_memberships(project: Project, hosted: list[str]) -> list[dict[str, Any]]:
    return [m for m in project.memberships() if m["identity"].get("name") in hosted]


def plan(project: Project, names: list[str], hosted: list[str], slug: str) -> list[dict[str, Any]]:
    """Actions that give every hosted identity the forbid privilege. Reads only."""
    rules = deny_rules(names)
    actions: list[dict[str, Any]] = []
    for membership in hosted_memberships(project, hosted):
        identity = membership["identity"]
        found = [p for p in project.privileges(identity["id"]) if p.get("slug") == slug]
        base = {"identity": identity["name"], "identity_id": identity["id"], "rules": rules}
        if not found:
            actions.append({"op": "create", **base})
            continue
        stored = project.privilege(found[0]["id"]).get("permissions") or []
        if _canonical(stored) != _canonical(rules):
            actions.append({"op": "update", "privilege_id": found[0]["id"], **base})
    return actions


def apply(project: Project, actions: list[dict[str, Any]], slug: str) -> None:
    for action in actions:
        if action["op"] == "create":
            project.create_privilege(action["identity_id"], slug, action["rules"])
        else:
            project.update_privilege(action["privilege_id"], slug, action["rules"])


def describe(action: dict[str, Any], slug: str) -> str:
    return f"{action['op']} privilege {slug} on {action['identity']} ({action['identity_id']})"


def probe(
    request: Request,
    login: Callable[[str, str], str],
    project: Project,
    names: list[str],
    hosted: list[str],
    environment: str,
) -> tuple[list[str], list[str]]:
    """Log in as each hosted identity with a one-use secret; read denied and allowed names.

    Returns (unexpected reads, identities this surface could not probe).
    """
    failures: list[str] = []
    unprobed: list[str] = []
    allowed = sorted(set(capability_bind.allowed_names()) - set(names))
    base_query = {"workspaceId": project.project_id, "environment": environment, "secretPath": "/"}
    listing = urllib.parse.urlencode({**base_query, "viewSecretValue": "false"})
    status, payload = request("GET", f"/api/v3/secrets/raw?{listing}", None)
    present = {item.get("secretKey") for item in (payload or {}).get("secrets", [])}
    control = next((name for name in allowed if name in present), None)
    if status != 200 or control is None:
        raise IamError("no readable control secret for the probe")
    read = urllib.parse.urlencode({**base_query, "viewSecretValue": "true"})
    targets = hosted_memberships(project, hosted)
    if not targets:
        raise IamError("no hosted membership to probe")
    for membership in targets:
        identity_id = membership["identity"]["id"]
        label = f"{membership['identity']['name']} ({identity_id})"
        ua_path = f"/api/v1/auth/universal-auth/identities/{identity_id}"
        try:
            client_id = project.call("GET", ua_path)["identityUniversalAuth"]["clientId"]
            created = project.call(
                "POST",
                f"{ua_path}/client-secrets",
                {"description": "operator-only IAM probe (one use)", "ttl": 300, "numUsesLimit": 1},
            )
        except IamError as error:
            unprobed.append(f"{label}: {error}")
            print(f"probe {label}: NOT PROBED ({error})")
            continue
        secret_id = (created.get("clientSecretData") or {}).get("id")
        try:
            token = login(client_id, created["clientSecret"])
            if not token:
                unprobed.append(f"{label}: probe login failed")
                continue
            for name, expect_ok in [(control, True), *[(n, False) for n in names]]:
                path = f"/api/v3/secrets/raw/{urllib.parse.quote(name, safe='')}?{read}"
                got, _ = request("GET", path, None, token)
                ok = (got == 200) == expect_ok
                verdict = "expected" if ok else "UNEXPECTED"
                print(f"probe {label}: {name} -> HTTP {got} ({verdict})")
                if not ok:
                    failures.append(f"{label} {name} HTTP {got}")
        finally:
            if secret_id:
                project.call("POST", f"{ua_path}/client-secrets/{secret_id}/revoke")
                print(f"probe {label}: one-use client secret revoked")
            else:
                failures.append(f"{label}: probe secret id missing; revoke it in the dashboard")
    return failures, unprobed


def self_probe(request: Request, project_id: str, names: list[str], environment: str) -> int:
    """Read each operator-only name as this surface's own identity; report statuses."""
    query = urllib.parse.urlencode(
        {
            "workspaceId": project_id,
            "environment": environment,
            "secretPath": "/",
            "viewSecretValue": "true",
        }
    )
    readable = []
    for name in names:
        status, _ = request(
            "GET", f"/api/v3/secrets/raw/{urllib.parse.quote(name, safe='')}?{query}", None
        )
        print(f"self-probe: {name} -> HTTP {status}")
        if status == 200:
            readable.append(name)
    if readable:
        print(f"this identity can read {len(readable)} operator-only name(s)")
        return 1
    print("PASS: this identity is refused every operator-only name")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--self-probe", action="store_true")
    args = parser.parse_args(argv)

    from infisical_http import infisical_req, universal_auth_login

    try:
        names, hosted, slug = policy()
        profile = capability_bind._machine_profile()
        if profile is None:
            raise IamError("no machine identity on this surface")
        admin_token = capability_bind._ua_token(profile)
        if not admin_token:
            raise IamError("machine identity login failed")
        host = profile["host"]

        def request(method: str, path: str, body: dict[str, Any] | None, token: str | None = None):
            return infisical_req(host, method, path, token or admin_token, body=body, retries=2)

        project = Project(request, profile["project_id"])
        if args.self_probe:
            return self_probe(request, project.project_id, names, profile["environment"])
        if args.probe:
            failures, unprobed = probe(
                request,
                lambda cid, secret: universal_auth_login(host, cid, secret),
                project,
                names,
                hosted,
                profile["environment"],
            )
            if failures:
                print("FAIL: " + "; ".join(failures), file=sys.stderr)
                return 1
            if unprobed:
                print(f"PARTIAL: {len(unprobed)} identity(ies) not probed from this surface")
                return 2
            print("PASS: hosted identities are denied operator-only names and read the control")
            return 0

        actions = plan(project, names, hosted, slug)
        for action in actions:
            print(("apply: " if args.apply else "drift: ") + describe(action, slug))
        if args.check:
            print("PASS" if not actions else "FAIL: hosted identities can read operator-only names")
            return 0 if not actions else 1
        apply(project, actions, slug)
        remaining = plan(project, names, hosted, slug)
        if remaining:
            raise IamError(
                "read-back still differs: " + "; ".join(describe(a, slug) for a in remaining)
            )
        print(f"PASS: {len(actions)} change(s); every hosted identity holds {slug}")
        return 0
    except IamError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
