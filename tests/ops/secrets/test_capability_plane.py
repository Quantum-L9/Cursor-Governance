"""Zero-static-secret contract tests (contract §22 T1–T14, §23).

These are the regression barrier for the capability architecture. They assert
*negative* security properties — that a secret cannot be obtained.

The capability-broker experiment never shipped. Broker-side tests live with the
archived implementation under ops/secrets/_archived/capability-broker/tests/
and are not collected. Live tests prove the model-facing plane still refuses
secrets and reports UNAVAILABLE.

No network and no real credentials.
"""

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

import capability_client as cc  # noqa: E402
import surface_trust  # noqa: E402
import validate_capability_contract as vcc  # noqa: E402
from capability_registry import load_registry  # noqa: E402

MODEL_SURFACES = ["claude-code", "codex", "gemini", "manus", "cursor", "generic"]
UNKNOWN_SURFACES = ["", "unknown", "brand-new-adapter", "OPERATOR-ish", "trusted"]


# ---------------------------------------------------------------------------
# T3 / R2 — raw export denial
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("surface", MODEL_SURFACES + UNKNOWN_SURFACES)
def test_raw_export_denied_on_every_untrusted_surface(surface: str) -> None:
    """Known model surfaces AND unregistered ids must both be denied.

    The unregistered case is the one that matters most: trust must never be
    inferred from the absence of a known id.
    """
    result = subprocess.run(  # noqa: S603
        [
            "bash",
            str(SECRETS_DIR / "bootstrap_agent_env.sh"),
            "--surface",
            surface,
            "--export",
            "SONAR_TOKEN",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert result.returncode == 3, result.stderr
    assert "DENIED: raw secret export is prohibited" in result.stderr
    assert "export SONAR_TOKEN=" not in result.stdout


def test_operator_claim_from_model_runtime_is_refused() -> None:
    """An LLM can pass --surface operator as easily as a human can."""
    trust = surface_trust.classify("operator", env={"CLAUDECODE": "1"})
    assert trust.trust_class == surface_trust.MODEL_CONTROLLED
    assert not trust.raw_secret_allowed
    assert "claim refused" in trust.reason


def test_operator_trusted_only_in_a_clean_runtime() -> None:
    trust = surface_trust.classify("operator", env={"PATH": "/usr/bin"})
    assert trust.raw_secret_allowed


def test_value_path_is_guarded_against_direct_import() -> None:
    """Bypassing the CLI by importing the provider must not bypass the boundary."""
    import hydrate_infisical as hi

    with pytest.raises(PermissionError, match="DENIED"):
        hi.fetch_values(
            {
                "host": "h",
                "client_id": "c",
                "client_secret": "s",
                "project_id": "p",
                "environment": "prod",
                "secret_path": "/",
            },
            surface="claude-code",
        )


# ---------------------------------------------------------------------------
# S4 / T4 — no raw-secret API anywhere in the plane
# ---------------------------------------------------------------------------


def test_client_exposes_no_secret_returning_api() -> None:
    for forbidden in ("get_secret", "resolve_secret", "export_secret", "secret_value", "hydrate"):
        assert not hasattr(cc, forbidden), f"capability_client exposes {forbidden}"
    assert not hasattr(cc.CapabilityClient, "get_secret")


def test_retired_broker_stub_serves_no_secret_route() -> None:
    """Live capability_broker.py is a refuse stub, not a server."""
    source = (SECRETS_DIR / "capability_broker.py").read_text(encoding="utf-8")
    assert "never shipped" in source
    for route in ("/secret/", "/resolve-secret", "/print-secret", "/export"):
        assert f'self.path == "{route}"' not in source


def test_capability_registry_declares_no_secret_values() -> None:
    registry = load_registry()
    raw = (SECRETS_DIR / "capabilities.yaml").read_text(encoding="utf-8")
    assert registry.secret_refs() <= {
        "SONAR_TOKEN",
        "SEMGREP_APP_TOKEN",
        "GRAPHITI_MCP_TOKEN",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "CONTEXT7_API_KEY",
        "GITGUARDIAN_API_KEY",
    }
    for marker in ("BEGIN PRIVATE KEY", "Bearer ey", "sqp_", "github_pat_"):
        assert marker not in raw


def test_repository_scoped_params_are_not_caller_supplied() -> None:
    """project/organization/group_id must not be caller-supplied."""
    registry = load_registry()
    for capability, protected in (
        ("sonar.read_issues", ("project", "organization")),
        ("graphiti.query", ("group_id",)),
        ("graphiti.write_governed", ("group_id",)),
    ):
        spec = registry.get(capability)
        assert spec is not None
        for name in protected:
            assert name not in spec.caller_params(), f"{capability}.{name} is caller-supplied"


# ---------------------------------------------------------------------------
# §18 — failure semantics: an outage is never a pass
# ---------------------------------------------------------------------------


def test_retired_broker_is_unavailable_and_never_enabled() -> None:
    env = {"L9_GOVERNANCE_SURFACE": "claude-code", "CLAUDECODE": "1"}
    client = cc.CapabilityClient(env=env)
    status = client.status("sonar.read_issues")
    assert status.status == cc.UNAVAILABLE
    assert status.status != cc.ENABLED
    assert "retired" in status.detail


def test_required_capability_check_is_nonzero_when_not_enabled() -> None:
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(SECRETS_DIR / "capability_client.py"),
            "--check",
            "--require",
            "sonar.read_issues",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        env={**os.environ, "L9_CAPABILITY_BROKER_URL": ""},
    )
    assert result.returncode == 1


def test_advisory_and_authority_capabilities_declare_distinct_semantics() -> None:
    registry = load_registry()
    assert registry.get("sonar.read_issues").is_advisory
    assert not registry.get("graphiti.write_governed").is_advisory


# ---------------------------------------------------------------------------
# T1 / T2 / §23 — no credentials in surface environments or examples
# ---------------------------------------------------------------------------


def test_no_adapter_example_carries_a_credential() -> None:
    """T1/§23: no future agent may reintroduce REPLACE_WITH_* secrets."""
    violations = vcc.scan_env_examples(REPO_ROOT)
    assert violations == [], "\n".join(v.render() for v in violations)


def test_no_llm_facing_code_reaches_for_raw_secrets() -> None:
    violations = vcc.scan_code(REPO_ROOT)
    assert violations == [], "\n".join(v.render() for v in violations)


def test_validator_catches_a_reintroduced_secret(tmp_path: Path) -> None:
    """The validator must actually fail on the thing it claims to prevent."""
    example = tmp_path / "environment" / "agents" / "adapters" / "evil"
    example.mkdir(parents=True)
    (example / "environment.env.example").write_text(
        "GRAPHITI_MCP_TOKEN=REPLACE_WITH_GRAPHITI_MCP_BEARER_TOKEN\n"
        "INFISICAL_CLIENT_SECRET=REPLACE_WITH_INFISICAL_UA_CLIENT_SECRET\n"
        "GH_TOKEN=github_pat_realtokenvalue\n"
    )
    violations = vcc.scan_env_examples(tmp_path)
    flagged = {v.line for v in violations}
    assert flagged == {1, 2, 3}, [v.render() for v in violations]


def test_validator_allows_proxy_injected_github(tmp_path: Path) -> None:
    example = tmp_path / "environment" / "agents" / "adapters" / "ok"
    example.mkdir(parents=True)
    (example / "environment.env.example").write_text("GH_TOKEN=proxy-injected\n")
    assert vcc.scan_env_examples(tmp_path) == []


def test_mcp_config_carries_no_bearer() -> None:
    """§12: Claude's MCP wiring must not hold a Graphiti token."""
    raw = (REPO_ROOT / ".mcp.json").read_text(encoding="utf-8")
    config = json.loads(raw)
    server = config["mcpServers"]["graphiti-memory"]
    assert "GRAPHITI_MCP_TOKEN" not in json.dumps(server)
    assert "headers" not in server


def test_no_adapter_mcp_template_carries_a_graphiti_bearer() -> None:
    """Every adapter uses GRAPHITI_MCP_URL with no in-file bearer.

    Scoped to adapter templates. `ops/graphiti/mcp.json.example` is the
    trusted-operator (Cursor SSH tunnel) shape and is deliberately not an
    adapter template — see its own header.
    """
    adapters = REPO_ROOT / "environment" / "agents" / "adapters"
    offenders: list[str] = []
    missing_front_door: list[str] = []
    checked = 0
    for path in sorted(adapters.rglob("*.json")):
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(config, dict):
            continue
        wiring = {k: v for k, v in config.items() if not k.startswith("_")}
        if "mcpServers" not in wiring and "transport" not in wiring:
            continue
        checked += 1
        rendered = json.dumps(wiring)
        rel = str(path.relative_to(REPO_ROOT))
        if "GRAPHITI_MCP_TOKEN" in rendered or "Authorization" in rendered:
            offenders.append(rel)
        if "L9_CAPABILITY_BROKER_URL" in rendered:
            offenders.append(rel)
        if "GRAPHITI_MCP_URL" not in rendered:
            missing_front_door.append(rel)
    assert checked >= 5, f"adapter template discovery found only {checked} configs"
    assert offenders == [], (
        "adapter MCP templates must point at ${GRAPHITI_MCP_URL} "
        f"with no in-file bearer and no broker URL: {offenders}"
    )
    assert missing_front_door == [], (
        f"adapter MCP templates must use ${{GRAPHITI_MCP_URL}}: {missing_front_door}"
    )


# ---------------------------------------------------------------------------
# §13 — Sonar consumer is never env-token on a model surface
# ---------------------------------------------------------------------------


def test_sonar_consumer_ignores_an_env_token_on_a_model_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "skills" / "l9-pr-remediation" / "scripts"))
    import sonar_fetch

    monkeypatch.setenv("SONAR_TOKEN", "CANARY_TOKEN_VALUE")
    monkeypatch.setenv("L9_GOVERNANCE_SURFACE", "claude-code")
    monkeypatch.setenv("CLAUDECODE", "1")
    transport = sonar_fetch.build_transport("https://sonarcloud.io/api")
    assert not transport.authenticated
    assert "CANARY_TOKEN_VALUE" not in json.dumps(vars(transport), default=str)


def test_sonar_direct_transport_refuses_a_token_from_a_model_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "skills" / "l9-pr-remediation" / "scripts"))
    import sonar_fetch

    monkeypatch.setenv("CLAUDECODE", "1")
    with pytest.raises(PermissionError):
        sonar_fetch.DirectTransport("https://sonarcloud.io/api", "tok", surface="operator")
