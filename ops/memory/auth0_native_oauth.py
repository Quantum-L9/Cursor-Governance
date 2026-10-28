"""Auth0 onboarding for the Memory 3.0 native OAuth consumer.

Auth0 is the only authorization server. Memory owns the MCP resource server,
JWT verification, namespace authorization, and storage. This module owns the
consumer requirements: resource and audience equality, scopes, the two
approved public-client registrations, PKCE, and redirect URIs.

The resource identifier is the value Memory published. Tenant domain and
client ids stay unbound until they are registered. This module does not
invent those values, write a secret, or substitute a stdio package for
native OAuth.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "l9.memory-auth0-onboarding/v1"
CONNECTOR_SCHEMA = "l9.claude-account-memory-connector/v1"
ISSUER = "auth0"
PKCE_METHOD = "S256"
SCOPES = ("memory.read", "memory.write")
HTTP_PROTOCOLS = frozenset({"2025-11-25", "2025-06-18"})
STALE_PROTOCOLS = frozenset({"2024-11-05"})
CURSOR_REDIRECT_URIS = (
    "https://www.cursor.com/agents/mcp/oauth/callback",
    "http://localhost:8787/callback",
    "cursor://anysphere.cursor-mcp/oauth/callback",
)
CLAUDE_ACCOUNT_REDIRECT_URI = "https://claude.ai/api/mcp/auth_callback"
REGISTRATIONS = ("cursor-native", "claude-account-connector")
SECRET_FIELDS = frozenset(
    {
        "CLIENT_SECRET",
        "client_secret",
        "access_token",
        "refresh_token",
        "id_token",
        "Authorization",
        "L9-Identity-Assertion",
        "L9-Identity-Assertion-HMAC",
    }
)
HOSTED_OAUTH_SECRET_ENV = (
    "AUTH0_CLIENT_SECRET",
    "L9_MEMORY_OAUTH_CLIENT_SECRET",
    "L9_MEMORY_OAUTH_ACCESS_TOKEN",
    "L9_MEMORY_OAUTH_REFRESH_TOKEN",
)
INSTALL_FAILURE_STATUSES = frozenset(
    {
        "blocked",
        "upstream_blocked",
        "unbound_resource",
        "unbound_issuer",
        "unbound_client",
        "unauthorized_client",
        "audience_mismatch",
        "malformed",
        "stale_transport",
        "secret_rejected",
    }
)
_REPO_ROOT = Path(__file__).resolve().parents[2]
ONBOARDING_PATH = _REPO_ROOT / "ops" / "config" / "memory-auth0-onboarding.yaml"
CONNECTOR_PATH = (
    _REPO_ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "account"
    / "memory-oauth-connector.yaml"
)


def load_onboarding(path: Path | None = None) -> dict[str, Any]:
    target = ONBOARDING_PATH if path is None else path
    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("onboarding document is not a mapping")
    return loaded


def _blank(value: object) -> bool:
    return value is None or value == "" or value == []


def structural_errors(document: Mapping[str, Any]) -> list[str]:
    """Requirements that do not depend on a live tenant."""

    errors: list[str] = []
    if document.get("schema") != SCHEMA:
        errors.append("schema")
    issuer = document.get("issuer")
    issuer_ok = (
        isinstance(issuer, dict) and issuer.get("vendor") == ISSUER and issuer.get("sole") is True
    )
    if not issuer_ok:
        errors.append("issuer")
    if isinstance(issuer, dict) and issuer.get("forbidden"):
        forbidden = issuer.get("forbidden")
        required = {
            "second_authorization_server",
            "oauth_proxy",
            "static_bearer",
            "hmac",
            "stdio",
            "sqlite_fallback",
        }
        if not isinstance(forbidden, list) or required - set(forbidden):
            errors.append("issuer.forbidden")
    pkce = document.get("pkce")
    pkce_ok = (
        isinstance(pkce, dict)
        and pkce.get("required") is True
        and pkce.get("method") == PKCE_METHOD
    )
    if not pkce_ok:
        errors.append("pkce")
    if isinstance(pkce, dict) and pkce.get("plain_forbidden") is not True:
        errors.append("pkce.plain")
    if tuple(document.get("scopes") or ()) != SCOPES:
        errors.append("scopes")
    resource = document.get("resource")
    if not isinstance(resource, dict) or resource.get("audience_equals_resource") is not True:
        errors.append("resource.audience")
    if isinstance(resource, dict) and resource.get("owner") != "Quantum-L9/l9-graphiti-memory":
        errors.append("resource.owner")
    clients = document.get("clients")
    if not isinstance(clients, dict):
        errors.append("clients")
        return errors
    cursor = clients.get("cursor-native")
    claude = clients.get("claude-account-connector")
    if not isinstance(cursor, dict) or not isinstance(claude, dict):
        errors.append("clients.registrations")
        return errors
    errors.extend(_client_shape("cursor-native", cursor, CURSOR_REDIRECT_URIS))
    errors.extend(_client_shape("claude-account-connector", claude, (CLAUDE_ACCOUNT_REDIRECT_URI,)))
    if claude.get("project_mcp_entry") is not False:
        errors.append("claude.project_mcp_entry")
    if claude.get("hosted_credential_injection") is not False:
        errors.append("claude.hosted_credential_injection")
    return errors


def _client_shape(name: str, client: Mapping[str, Any], redirects: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    if client.get("client_type") != "public":
        errors.append(f"{name}.client_type")
    if client.get("token_endpoint_auth_method") != "none":
        errors.append(f"{name}.token_endpoint_auth_method")
    if client.get("pkce") != PKCE_METHOD:
        errors.append(f"{name}.pkce")
    if client.get("client_secret") != "forbidden":
        errors.append(f"{name}.client_secret")
    if tuple(client.get("grant_types") or ()) != ("authorization_code", "refresh_token"):
        errors.append(f"{name}.grant_types")
    if tuple(client.get("redirect_uris") or ()) != redirects:
        errors.append(f"{name}.redirect_uris")
    return errors


def binding_gaps(document: Mapping[str, Any]) -> list[str]:
    """Tenant facts this repository must not invent."""

    gaps: list[str] = []
    issuer = document.get("issuer") if isinstance(document.get("issuer"), dict) else {}
    resource = document.get("resource") if isinstance(document.get("resource"), dict) else {}
    clients = document.get("clients") if isinstance(document.get("clients"), dict) else {}
    if _blank(issuer.get("domain")):
        gaps.append("issuer.domain")
    if _blank(resource.get("identifier")):
        gaps.append("resource.identifier")
    for name in REGISTRATIONS:
        client = clients.get(name) if isinstance(clients.get(name), dict) else {}
        if _blank(client.get("client_id")):
            gaps.append(f"clients.{name}.client_id")
    return gaps


def validate_onboarding(document: Mapping[str, Any]) -> dict[str, Any]:
    errors = structural_errors(document)
    gaps = [] if errors else binding_gaps(document)
    if errors:
        status = "malformed"
    elif gaps:
        status = "unbound"
    else:
        status = _bound_consistency(document)
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": errors,
        "binding_gaps": gaps,
        "wrote": False,
    }


def _bound_consistency(document: Mapping[str, Any]) -> str:
    issuer = document["issuer"]
    domain = str(issuer["domain"])
    expected = f"https://{domain}/"
    if issuer.get("issuer_url") != expected:
        return "malformed"
    identifier = str(document["resource"]["identifier"])
    if not _canonical_resource(identifier):
        return "malformed"
    return "bound"


def _canonical_resource(identifier: str) -> bool:
    if not identifier.startswith("https://") or any(part in identifier for part in ("?", "#", "@")):
        return False
    rest = identifier[len("https://") :]
    host, _, path = rest.partition("/")
    return bool(host) and host == host.lower() and bool(path)


def contains_secret(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in SECRET_FIELDS and item not in (None, "", "forbidden"):
                return True
            if contains_secret(item):
                return True
        return False
    if isinstance(value, list):
        return any(contains_secret(item) for item in value)
    return False


def entry_verdict(config: Mapping[str, Any]) -> str:
    """Classify one package-owned Cursor entry against the native OAuth rules."""

    protocol = str(config.get("protocol") or config.get("protocolVersion") or "")
    if protocol in STALE_PROTOCOLS:
        return "stale_transport"
    headers = config.get("headers")
    if isinstance(headers, dict) and headers:
        return "stale_transport"
    if contains_secret(config):
        return "secret_rejected"
    auth = config.get("auth")
    if isinstance(auth, dict) and any(str(key) in SECRET_FIELDS for key in auth):
        return "secret_rejected"
    args = [str(item) for item in (config.get("args") or [])]
    transport = ""
    if "--transport" in args:
        index = args.index("--transport")
        if index + 1 < len(args):
            transport = args[index + 1].lower()
    declared = str(config.get("type") or config.get("transport") or transport).lower()
    stdio = declared == "stdio" or transport == "stdio" or bool(config.get("command"))
    if stdio:
        return "upstream_blocked"
    if declared == "sse":
        return "stale_transport"
    if declared not in {"http", "streamable-http", "streamable_http"} or not config.get("url"):
        return "malformed"
    return "native_oauth"


def authorize_cursor_package_entry(
    config: Mapping[str, Any],
    document: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide whether the package entry may be installed. Never writes a file."""

    onboarding = load_onboarding() if document is None else document
    shape = validate_onboarding(onboarding)
    if shape["status"] == "malformed":
        return {**shape, "install": False}
    verdict = entry_verdict(config)
    if verdict != "native_oauth":
        reason = {
            "upstream_blocked": (
                "UPSTREAM_BLOCKED: stdio-only Memory package is not a native OAuth client"
            ),
            "stale_transport": "stale transport is not native Auth0 OAuth",
            "secret_rejected": "package entry carries a secret or static credential",
            "malformed": "package entry is not a native OAuth HTTP client",
        }[verdict]
        return {"status": verdict, "reason": reason, "wrote": False, "install": False}
    if "resource.identifier" in shape["binding_gaps"]:
        return {
            "status": "unbound_resource",
            "reason": "Memory has not published the resource identifier",
            "wrote": False,
            "install": False,
        }
    resource = str(onboarding["resource"]["identifier"])
    if str(config.get("url")) != resource:
        return {
            "status": "audience_mismatch",
            "reason": "package URL is not the Memory resource audience",
            "wrote": False,
            "install": False,
        }
    auth = config.get("auth") if isinstance(config.get("auth"), dict) else {}
    if tuple(auth.get("scopes") or ()) != SCOPES:
        return {
            "status": "malformed",
            "reason": "Cursor auth.scopes must be the exact Memory scope set",
            "wrote": False,
            "install": False,
        }
    if "clients.cursor-native.client_id" in shape["binding_gaps"]:
        return {
            "status": "unbound_client",
            "reason": "cursor-native client id is unbound",
            "wrote": False,
            "install": False,
        }
    client_id = str(auth.get("CLIENT_ID") or "")
    approved = str(onboarding["clients"]["cursor-native"]["client_id"])
    if client_id != approved:
        return {
            "status": "unauthorized_client",
            "reason": "CLIENT_ID is not the approved cursor-native registration",
            "wrote": False,
            "install": False,
        }
    issuer_block = _issuer_install_block(onboarding, list(shape["binding_gaps"]))
    if issuer_block is not None:
        return issuer_block
    return {
        "status": "authorized",
        "reason": "package entry matches the bound Auth0 onboarding contract",
        "wrote": False,
        "install": True,
    }


def _issuer_install_block(onboarding: Mapping[str, Any], gaps: list[str]) -> dict[str, Any] | None:
    """A resource and client id do not prove the Auth0 tenant."""

    issuer = onboarding.get("issuer") if isinstance(onboarding.get("issuer"), dict) else {}
    if "issuer.domain" in gaps or _blank(issuer.get("domain")):
        return {
            "status": "unbound_issuer",
            "reason": "Auth0 issuer domain is unbound",
            "wrote": False,
            "install": False,
        }
    expected = f"https://{issuer['domain']}/"
    if issuer.get("issuer_url") != expected:
        return {
            "status": "malformed",
            "reason": "issuer_url does not match the Auth0 domain",
            "wrote": False,
            "install": False,
        }
    return None


def audience_matches(audience: object, resource: str) -> bool:
    if isinstance(audience, str):
        return audience == resource
    if isinstance(audience, list):
        return audience == [resource]
    return False


def claude_account_connector(document: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Account-connector descriptor. It is not a project MCP entry."""

    onboarding = load_onboarding() if document is None else document
    client = onboarding["clients"]["claude-account-connector"]
    descriptor = {
        "schema": CONNECTOR_SCHEMA,
        "placement": "claude_account_connectors",
        "project_mcp_entry": False,
        "hosted_credential_injection": False,
        "issuer_vendor": ISSUER,
        "registration": "claude-account-connector",
        "client_type": "public",
        "pkce": PKCE_METHOD,
        "redirect_uris": list(client["redirect_uris"]),
        "scopes": list(SCOPES),
        "client_id": client.get("client_id"),
        "resource_identifier": onboarding["resource"].get("identifier"),
        "secret_fields": [],
    }
    if contains_secret(descriptor):
        raise ValueError("connector descriptor carried a secret")
    return descriptor


def persisted_secret_hits(text: str) -> list[str]:
    hits = [name for name in HOSTED_OAUTH_SECRET_ENV if f"{name}=" in text or f'"{name}":' in text]
    for marker in ("CLIENT_SECRET", "client_secret", "access_token", "refresh_token"):
        if marker in text and "forbidden" not in text:
            hits.append(marker)
    return hits


def onboarding_json(document: Mapping[str, Any] | None = None) -> str:
    onboarding = load_onboarding() if document is None else document
    verdict = validate_onboarding(onboarding)
    return json.dumps({"onboarding": verdict, "connector": claude_account_connector(onboarding)})
