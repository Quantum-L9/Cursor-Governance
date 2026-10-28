"""Auth0 native OAuth consumer: onboarding, install refusal, and identity."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ops.memory import agent_identity as ai
from ops.memory import auth0_native_oauth as oauth
from ops.memory import mcp_instantiation as inst
from ops.memory.runtime_binding import RuntimeBinding

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "environment/agents/adapters/claude-code/mcp.template.json"
BOOTSTRAP = ROOT / "environment/agents/adapters/claude-code/web/setup.bootstrap.sh"
POLICY = ROOT / "environment/agents/adapters/claude-code/web/network-policy.md"
RESOURCE = "https://memory.example.invalid/mcp"
PUBLISHED_RESOURCE = "https://memory.quantumaipartners.com/mcp"
CURSOR_CLIENT = "synthetic-cursor-public"
CLAUDE_CLIENT = "synthetic-claude-public"


def _bound() -> dict[str, Any]:
    document = oauth.load_onboarding()
    document["issuer"]["domain"] = "tenant.example.invalid"
    document["issuer"]["issuer_url"] = "https://tenant.example.invalid/"
    document["resource"]["identifier"] = RESOURCE
    document["clients"]["cursor-native"]["client_id"] = CURSOR_CLIENT
    document["clients"]["claude-account-connector"]["client_id"] = CLAUDE_CLIENT
    return document


def _entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "type": "streamable-http",
        "url": RESOURCE,
        "auth": {"CLIENT_ID": CURSOR_CLIENT, "scopes": ["memory.read", "memory.write"]},
    }
    entry.update(overrides)
    return entry


def test_shipped_onboarding_is_structural_and_unbound() -> None:
    document = oauth.load_onboarding()
    verdict = oauth.validate_onboarding(document)
    assert verdict["status"] == "unbound"
    assert verdict["errors"] == []
    assert "issuer.domain" in verdict["binding_gaps"]
    assert "clients.cursor-native.client_id" in verdict["binding_gaps"]
    assert "clients.claude-account-connector.client_id" in verdict["binding_gaps"]
    assert "resource.identifier" not in verdict["binding_gaps"]
    assert document["issuer"]["domain"] is None
    assert document["resource"]["identifier"] == PUBLISHED_RESOURCE
    assert document["clients"]["cursor-native"]["client_id"] is None
    assert document["pkce"] == {"required": True, "method": "S256", "plain_forbidden": True}
    assert document["scopes"] == ["memory.read", "memory.write"]
    assert oauth.contains_secret(document) is False
    assert verdict["wrote"] is False
    host_only = oauth.authorize_cursor_package_entry(
        _entry(url="https://memory.quantumaipartners.com"), document
    )
    graphiti = oauth.authorize_cursor_package_entry(
        _entry(url="https://memory.quantumaipartners.com/graphiti/mcp"), document
    )
    matching = oauth.authorize_cursor_package_entry(_entry(url=PUBLISHED_RESOURCE), document)
    assert host_only["status"] == "audience_mismatch"
    assert graphiti["status"] == "audience_mismatch"
    assert matching["status"] == "unbound_client"
    assert matching["install"] is False


def test_bound_fixture_authorizes_only_the_approved_cursor_client() -> None:
    document = _bound()
    assert oauth.validate_onboarding(document)["status"] == "bound"
    allowed = oauth.authorize_cursor_package_entry(_entry(), document)
    assert allowed["status"] == "authorized"
    assert allowed["install"] is True
    assert allowed["wrote"] is False
    denied = oauth.authorize_cursor_package_entry(
        _entry(auth={"CLIENT_ID": "other-client", "scopes": ["memory.read", "memory.write"]}),
        document,
    )
    assert denied["status"] == "unauthorized_client"
    assert denied["install"] is False


def test_resource_and_client_without_a_bound_issuer_do_not_authorize() -> None:
    document = _bound()
    document["issuer"]["domain"] = None
    document["issuer"]["issuer_url"] = None
    missing = oauth.authorize_cursor_package_entry(_entry(), document)
    assert missing["status"] == "unbound_issuer"
    assert missing["install"] is False

    inconsistent = _bound()
    inconsistent["clients"]["claude-account-connector"]["client_id"] = None
    inconsistent["issuer"]["issuer_url"] = "https://other.example.invalid/"
    mismatched = oauth.authorize_cursor_package_entry(_entry(), inconsistent)
    assert mismatched["status"] == "malformed"
    assert mismatched["install"] is False


def test_malformed_onboarding_and_package_entry_fail_closed() -> None:
    document = _bound()
    document["pkce"]["method"] = "plain"
    assert oauth.validate_onboarding(document)["status"] == "malformed"
    document = _bound()
    document["clients"]["cursor-native"]["redirect_uris"] = ["https://evil.example/callback"]
    assert "cursor-native.redirect_uris" in oauth.structural_errors(document)
    document = _bound()
    entry = _entry(auth={"CLIENT_ID": CURSOR_CLIENT, "scopes": ["memory.read"]})
    assert oauth.authorize_cursor_package_entry(entry, document)["status"] == "malformed"


def test_audience_mismatch_and_stale_transport_do_not_install() -> None:
    document = _bound()
    mismatch = oauth.authorize_cursor_package_entry(
        _entry(url="https://other.example.invalid/mcp"), document
    )
    assert mismatch["status"] == "audience_mismatch"
    assert oauth.audience_matches(["https://other.example.invalid/mcp"], RESOURCE) is False
    assert oauth.audience_matches(RESOURCE, RESOURCE) is True
    stale = oauth.authorize_cursor_package_entry(_entry(protocolVersion="2024-11-05"), document)
    assert stale["status"] == "stale_transport"
    hmac = oauth.authorize_cursor_package_entry(
        _entry(headers={"L9-Identity-Assertion-HMAC": "forged"}), document
    )
    assert hmac["status"] == "stale_transport"
    stdio = oauth.authorize_cursor_package_entry(
        {"command": "/usr/bin/python", "args": ["--transport", "stdio"]}, document
    )
    assert stdio["status"] == "upstream_blocked"
    assert stdio["install"] is False


def test_secret_material_is_rejected_and_not_stored_in_source() -> None:
    document = _bound()
    secret = oauth.authorize_cursor_package_entry(
        _entry(
            auth={
                "CLIENT_ID": CURSOR_CLIENT,
                "CLIENT_SECRET": "synthetic-secret",
                "scopes": ["memory.read", "memory.write"],
            }
        ),
        document,
    )
    assert secret["status"] == "secret_rejected"
    assert secret["wrote"] is False
    connector = oauth.claude_account_connector()
    assert connector["project_mcp_entry"] is False
    assert connector["hosted_credential_injection"] is False
    assert connector["redirect_uris"] == [oauth.CLAUDE_ACCOUNT_REDIRECT_URI]
    assert connector["client_id"] is None
    assert connector["resource_identifier"] == PUBLISHED_RESOURCE
    assert oauth.contains_secret(connector) is False
    onboarding_text = oauth.ONBOARDING_PATH.read_text(encoding="utf-8")
    connector_text = oauth.CONNECTOR_PATH.read_text(encoding="utf-8")
    assert PUBLISHED_RESOURCE in onboarding_text
    assert PUBLISHED_RESOURCE in connector_text
    assert "synthetic-secret" not in onboarding_text
    assert "synthetic-secret" not in connector_text
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    for name in oauth.HOSTED_OAUTH_SECRET_ENV:
        assert f"unset {name}" in bootstrap or name in bootstrap.split("unset ", 1)[-1]


def test_forged_oauth_claims_do_not_set_identity_coordinates() -> None:
    claims = {
        "sub": "claude-code",
        "client_id": CURSOR_CLIENT,
        "aud": RESOURCE,
        "release_identity": "l9.release/forged",
        "runtime_identity": "l9.runtime/forged",
    }
    cursor = ai.resolve_identity_coordinates({"CURSOR_AGENT": "1"}, claims)
    assert cursor["actor_identity"] == "cursor"
    assert cursor["surface_identity"] == "cursor-ide"
    assert cursor["release_identity"] == "unknown"
    assert cursor["runtime_identity"] == "unknown"
    assert cursor["oauth_subject_used"] is False
    assert cursor["oauth_client_id_used"] is False
    assert "sub" in cursor["ignored_oauth_claims"]
    forged_only = ai.resolve_identity_coordinates({}, claims)
    assert forged_only["actor_identity"] == "unknown"
    assert forged_only["surface_identity"] == "unknown"
    assert forged_only["release_identity"] == "unknown"
    assert forged_only["runtime_identity"] == "unknown"


def test_claude_template_has_no_project_memory_entry() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert "l9-graphite-memory" not in template["mcpServers"]
    assert "l9-graphite-memory" in template["_retired_servers"]
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "CLIENT_SECRET" not in text
    assert "https://" not in template["mcpServers"]["context7"].get("args", [])


def test_network_allowlist_does_not_gain_an_unverified_memory_host() -> None:
    text = POLICY.read_text(encoding="utf-8")
    fence = text.split("```", 2)[1]
    assert "auth0.com" not in fence
    assert "memory.quantumaipartners.com" not in fence
    assert "UPSTREAM_BLOCKED" in text
    assert "Auth0" in text


def test_unbound_native_package_is_not_installed(tmp_path: Path) -> None:
    venv = tmp_path / "venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text("", encoding="utf-8")
    (venv / "l9-memory").write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if "-c" in argv:
            payload = json.dumps(_entry(url=PUBLISHED_RESOURCE))
            return subprocess.CompletedProcess(argv, 0, payload, "")
        raise AssertionError(argv)

    binding = RuntimeBinding(
        status="exact",
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version="2.6.0",
        expected_contract_version="memory-control-plane/v1",
        manifest_path=str(tmp_path / "memory-binding.json"),
        interpreter=str(venv / "python"),
        memory_cli=str(venv / "l9-memory"),
        reasons=(),
    )
    receipt = inst.memory_entry(
        config_path=tmp_path / "mcp.json",
        binding=binding,
        interpreter=None,
        check=False,
        verify=False,
        runner=runner,
    )
    assert receipt["status"] == "unbound_client"
    assert all("cursor" not in " ".join(call) or "-c" in call for call in calls)
    assert inst.exit_code({"status": "written", "memory": receipt}) == 1
