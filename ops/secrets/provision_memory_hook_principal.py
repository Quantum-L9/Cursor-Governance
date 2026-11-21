#!/usr/bin/env python3
"""Provision the hosted Memory hook principal ``l9-memory-hooks`` (operator step).

ADR-0055 / l9-graphiti-memory REMOTE_MCP_CONTRACT §2b. Idempotent, and a DRY
RUN unless ``--apply`` is given:

1. Auth0 (Management API, credentials ``AUTH0_CLIENT_DOMAIN`` /
   ``AUTH0_CLIENT_ID`` / ``AUTH0_CLIENT_SECRET`` bound through
   ``capability_bind``): the ``non_interactive`` client-credentials app
   ``l9-memory-hooks`` (reused when one exists by that name) and its grant on
   the Memory API audience (``resource.identifier`` of
   ``ops/config/memory-auth0-onboarding.yaml``) with ``scope: []``.
2. Infisical, as this machine's identity: ``L9_MEMORY_HOOK_CLIENT_ID`` and
   ``L9_MEMORY_HOOK_CLIENT_SECRET`` in project ``cursor-governance`` (prod,
   ``/``), and ``L9_MEMORY_HOOK_PRINCIPALS_JSON`` (the §2b envelope keyed by
   the client id) in project ``l9-graphite-memory`` (prod, ``/``).
3. Verification: a client-credentials token for the hook app against the
   Memory audience (HTTP status only). The memory server is never called.

It never rotates: an existing app whose secret is not stored, or a stored
value that differs from what would be written, STOPS (exit 3) for an operator
decision. A 403 from Infisical stops (exit 4) naming the project and env.
Output is names, HTTP statuses and the last four characters of a client id —
never a secret, token or envelope value.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO / "ops" / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

APP_NAME = "l9-memory-hooks"
#: Inventory names, never values (see infisical-cursor-governance.yaml).
HOOK_NAMES = ("L9_MEMORY_HOOK_CLIENT_ID", "L9_MEMORY_HOOK_CLIENT_SECRET")
PRINCIPALS_NAME = "L9_MEMORY_HOOK_PRINCIPALS_JSON"
MANAGEMENT_NAMES = ("AUTH0_CLIENT_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET")
ENVIRONMENT = "prod"
SECRET_PATH = "/"
#: The hook principal envelope (REMOTE_MCP_CONTRACT §2b), keyed by client id.
ENVELOPE: dict[str, Any] = {
    "surface": "claude-code",
    "operations": ["write", "ingest_candidate", "close"],
    "record_classes": ["meta", "semantic", "episodic", "observation"],
    "max_records": 1,
    "max_bytes": 65536,
    "provenance_required": True,
    "read_namespaces": [],
    "write_namespaces": ["@l9-repositories"],
}

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_STOP = 3
EXIT_FORBIDDEN = 4

#: ``(method, url, headers, body) -> (status, json)``; never raises for HTTP errors.
Http = Callable[[str, str, Mapping[str, str], bytes | None], tuple[int, Any]]
#: ``(method, path, body) -> (status, json)`` against the Infisical API as this identity.
Infisical = Callable[[str, str, dict[str, Any] | None], tuple[int, Any]]


class Stop(Exception):
    """An operator decision is needed; the message names what, never a value."""

    def __init__(self, message: str, code: int = EXIT_STOP) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Targets:
    audience: str
    cg_project: str
    memory_project: str


def load_targets(repo: Path = REPO) -> Targets:
    import yaml  # noqa: PLC0415

    onboarding = yaml.safe_load(
        (repo / "ops/config/memory-auth0-onboarding.yaml").read_text(encoding="utf-8")
    )
    inventory = yaml.safe_load(
        (repo / "ops/secrets/infisical-cursor-governance.yaml").read_text(encoding="utf-8")
    )
    return Targets(
        audience=str(onboarding["resource"]["identifier"]),
        cg_project=str(inventory["project"]["id"]),
        memory_project=str(inventory["memory_prod_secret_refs"]["project"]["id"]),
    )


def last4(client_id: str) -> str:
    return f"…{client_id[-4:]}" if client_id else "(none)"


def principals_json(client_id: str) -> str:
    return json.dumps({client_id: ENVELOPE}, separators=(",", ":"), sort_keys=True)


@dataclass
class Provisioner:
    targets: Targets
    domain: str
    management_id: str
    management_secret: str
    http: Http
    infisical: Infisical
    apply: bool
    log: Callable[[str], None] = print
    #: Steps that would change something (dry run) or did (apply).
    changes: list[str] = field(default_factory=list)

    # -- Auth0 ---------------------------------------------------------------
    @property
    def base(self) -> str:
        return f"https://{self.domain}"

    def _form(self, fields: Mapping[str, str]) -> bytes:
        return urllib.parse.urlencode(dict(fields)).encode("ascii")

    def management_token(self) -> str:
        status, body = self.http(
            "POST",
            f"{self.base}/oauth/token",
            {"Content-Type": "application/x-www-form-urlencoded"},
            self._form(
                {
                    "grant_type": "client_credentials",
                    "client_id": self.management_id,
                    "client_secret": self.management_secret,
                    "audience": f"{self.base}/api/v2/",
                }
            ),
        )
        self.log(f"auth0 management token: HTTP {status}")
        token = body.get("access_token") if isinstance(body, dict) else None
        if status != 200 or not isinstance(token, str):
            raise Stop(f"Auth0 management token refused (HTTP {status})", EXIT_FAILED)
        return token

    def _api(self, token: str, method: str, path: str, payload: Any = None) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        return self.http(method, f"{self.base}{path}", headers, data)

    def find_app(self, token: str) -> str | None:
        page = 0
        while True:
            query = urllib.parse.urlencode(
                {
                    "fields": "client_id,name",
                    "include_fields": "true",
                    "per_page": "100",
                    "page": str(page),
                }
            )
            status, body = self._api(token, "GET", f"/api/v2/clients?{query}")
            if status != 200 or not isinstance(body, list):
                raise Stop(f"Auth0 client listing failed (HTTP {status})", EXIT_FAILED)
            for client in body:
                if isinstance(client, dict) and client.get("name") == APP_NAME:
                    return str(client.get("client_id") or "") or None
            if len(body) < 100:
                return None
            page += 1

    def create_app(self, token: str) -> tuple[str, str]:
        status, body = self._api(
            token,
            "POST",
            "/api/v2/clients",
            {
                "name": APP_NAME,
                "app_type": "non_interactive",
                "grant_types": ["client_credentials"],
                "token_endpoint_auth_method": "client_secret_post",
            },
        )
        self.log(f"auth0 create app {APP_NAME}: HTTP {status}")
        if status not in (200, 201) or not isinstance(body, dict):
            raise Stop(f"Auth0 refused to create {APP_NAME} (HTTP {status})", EXIT_FAILED)
        return str(body["client_id"]), str(body["client_secret"])

    def ensure_grant(self, token: str, client_id: str) -> None:
        query = urllib.parse.urlencode({"client_id": client_id, "audience": self.targets.audience})
        status, body = self._api(token, "GET", f"/api/v2/client-grants?{query}")
        if status != 200 or not isinstance(body, list):
            raise Stop(f"Auth0 client-grant listing failed (HTTP {status})", EXIT_FAILED)
        if any(isinstance(g, dict) and g.get("audience") == self.targets.audience for g in body):
            self.log("auth0 grant on the Memory API: present")
            return
        self.changes.append("auth0 grant")
        if not self.apply:
            self.log("auth0 grant on the Memory API: absent — would create (scope [])")
            return
        status, _ = self._api(
            token,
            "POST",
            "/api/v2/client-grants",
            {"client_id": client_id, "audience": self.targets.audience, "scope": []},
        )
        self.log(f"auth0 create grant (scope []): HTTP {status}")
        if status not in (200, 201):
            raise Stop(f"Auth0 refused the grant (HTTP {status})", EXIT_FAILED)

    def verify_token(self, client_id: str, client_secret: str) -> int:
        status, _ = self.http(
            "POST",
            f"{self.base}/oauth/token",
            {"Content-Type": "application/x-www-form-urlencoded"},
            self._form(
                {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "audience": self.targets.audience,
                }
            ),
        )
        self.log(f"hook app client-credentials token (Memory audience): HTTP {status}")
        return status

    # -- Infisical -----------------------------------------------------------
    def stored(self, project: str, label: str, name: str) -> str | None:
        query = urllib.parse.urlencode(
            {
                "workspaceId": project,
                "environment": ENVIRONMENT,
                "secretPath": SECRET_PATH,
                "viewSecretValue": "true",
                "include_imports": "false",
            }
        )
        status, body = self.infisical("GET", f"/api/v3/secrets/raw/{name}?{query}", None)
        if status == 403:
            raise Stop(f"Infisical 403 reading {name} in {label}/{ENVIRONMENT}", EXIT_FORBIDDEN)
        if status != 200:
            return None
        secret = body.get("secret") if isinstance(body, dict) else None
        value = secret.get("secretValue") if isinstance(secret, dict) else None
        return str(value) if value else None

    def ensure_secret(self, project: str, label: str, name: str, value: str | None) -> None:
        where = f"{label}/{ENVIRONMENT}{SECRET_PATH}"
        current = self.stored(project, label, name)
        if current is not None:
            if value is not None and current.strip() != value.strip():
                raise Stop(f"{where} {name} exists with a different value — not overwritten")
            self.log(f"infisical {where} {name}: present")
            return
        self.changes.append(name)
        if not self.apply or value is None:
            self.log(f"infisical {where} {name}: absent — would create")
            return
        status, body = self.infisical(
            "POST",
            f"/api/v3/secrets/raw/{name}",
            {
                "workspaceId": project,
                "environment": ENVIRONMENT,
                "secretPath": SECRET_PATH,
                "secretValue": value,
                "type": "shared",
            },
        )
        if status == 403:
            raise Stop(f"Infisical 403 writing {name} in {label}/{ENVIRONMENT}", EXIT_FORBIDDEN)
        if status == 200 and isinstance(body, dict) and "approval" in body:
            raise Stop(f"{where} {name}: a secret approval was requested; not present yet")
        self.log(f"infisical {where} {name}: create HTTP {status}")
        if status != 200:
            raise Stop(f"Infisical refused {name} (HTTP {status})", EXIT_FAILED)

    # -- the run ------------------------------------------------------------
    def run(self) -> int:
        mode = "APPLY" if self.apply else "DRY RUN (no change; --apply to provision)"
        self.log(f"provision {APP_NAME}: {mode}")
        token = self.management_token()
        client_id = self.find_app(token)
        client_secret: str | None = None
        if client_id:
            self.log(f"auth0 app {APP_NAME}: present, client_id {last4(client_id)}")
            client_secret = self.stored(self.targets.cg_project, "cursor-governance", HOOK_NAMES[1])
            if client_secret is None:
                raise Stop(
                    f"{APP_NAME} exists but cursor-governance/{ENVIRONMENT} holds no "
                    f"{HOOK_NAMES[1]}: rotating its secret is an operator decision"
                )
        elif self.apply:
            client_id, client_secret = self.create_app(token)
            self.changes.append("auth0 app")
            self.log(f"auth0 app {APP_NAME}: created, client_id {last4(client_id)}")
        else:
            self.changes.append("auth0 app")
            self.log(f"auth0 app {APP_NAME}: absent — would create")
        if client_id:
            self.ensure_grant(token, client_id)
        else:
            self.changes.append("auth0 grant")
            self.log("auth0 grant on the Memory API: would create with the new app (scope [])")
        self.ensure_secret(self.targets.cg_project, "cursor-governance", HOOK_NAMES[0], client_id)
        self.ensure_secret(
            self.targets.cg_project, "cursor-governance", HOOK_NAMES[1], client_secret
        )
        self.ensure_secret(
            self.targets.memory_project,
            "l9-graphite-memory",
            PRINCIPALS_NAME,
            principals_json(client_id) if client_id else None,
        )
        if client_id and client_secret:
            if self.verify_token(client_id, client_secret) != 200:
                raise Stop("hook app token request did not return 200", EXIT_FAILED)
        self.log(
            f"done: {'applied' if self.apply else 'would change'} "
            f"{', '.join(self.changes) or 'nothing (already provisioned)'}"
        )
        return EXIT_OK


# --- real transports ---------------------------------------------------------


def https_json(allowed_host: str) -> Http:
    """HTTPS to one host only (``ops/lib/safe_https.py``); JSON in, JSON out."""
    import safe_https  # noqa: PLC0415 - ops/lib is not a package

    def call(
        method: str, url: str, headers: Mapping[str, str], body: bytes | None
    ) -> tuple[int, Any]:
        request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
        try:
            response = safe_https.https_exchange(
                request, timeout=20.0, allowed_hosts=frozenset({allowed_host}), label="auth0"
            )
            status, raw = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read() or b""
        try:
            return status, json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, ValueError):
            return status, {}

    return call


def infisical_as_this_identity() -> Infisical:
    import capability_bind as cb  # noqa: PLC0415
    from infisical_http import infisical_req  # noqa: PLC0415

    profile = cb._machine_profile()  # noqa: SLF001 - the owner's identity resolution
    if profile is None:
        raise Stop("no Infisical machine identity on this surface", EXIT_FAILED)
    token = cb._ua_token(profile)  # noqa: SLF001
    if not token:
        raise Stop("Infisical machine identity login refused", EXIT_FAILED)
    host = profile["host"]

    def call(method: str, path: str, body: dict[str, Any] | None) -> tuple[int, Any]:
        return infisical_req(host, method, path, token, body=body, retries=2)

    return call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="make the changes (default: dry run)")
    args = parser.parse_args(argv)
    try:
        import capability_bind as cb  # noqa: PLC0415

        domain, mgmt_id, mgmt_secret = (cb.bind(name) for name in MANAGEMENT_NAMES)
        if not (domain and mgmt_id and mgmt_secret):
            missing = [n for n in MANAGEMENT_NAMES if not cb.bind_status(n).get("bound")]
            raise Stop(f"Auth0 management credentials do not bind: {missing}", EXIT_FAILED)
        domain = domain.strip().removeprefix("https://").rstrip("/")
        provisioner = Provisioner(
            targets=load_targets(),
            domain=domain,
            management_id=mgmt_id,
            management_secret=mgmt_secret,
            http=https_json(domain),
            infisical=infisical_as_this_identity(),
            apply=args.apply,
        )
        return provisioner.run()
    except Stop as stop:
        print(f"STOP: {stop}", file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    raise SystemExit(main())
