"""Zero-static-secret contract tests (contract §22 T1–T14, §23).

These are the regression barrier for the capability architecture. They assert
*negative* security properties — that a secret cannot be obtained — which means
most of them are written as "attempt the attack, require the refusal" rather
than "call the API, check the result".

No network and no real credentials. Where a test needs a signed assertion it
mints a throwaway P-256 key and signs one, so signature verification is
exercised for real rather than stubbed.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
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

try:
    import broker_identity  # noqa: E402
    import capability_broker as cb  # noqa: E402
except ImportError as exc:
    # Isolate UV_PROJECT can bind a sibling checkout whose cryptography wheel
    # does not load (macOS ABI). CI and a healthy local .venv still import.
    pytest.skip(
        f"capability broker imports unavailable: {exc}",
        allow_module_level=True,
    )

MODEL_SURFACES = ["claude-code", "codex", "gemini", "manus", "cursor", "generic"]
UNKNOWN_SURFACES = ["", "unknown", "brand-new-adapter", "OPERATOR-ish", "trusted"]

#: Names that must never appear as a real credential in a model-controlled
#: runtime. GH_TOKEN is checked separately because one literal value is allowed.
FORBIDDEN_ENV_NAMES = (
    "GITHUB_TOKEN",
    "GRAPHITI_MCP_TOKEN",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_TOKEN",
    "INFISICAL_PASSWORD",
    "SONAR_TOKEN",
    "SONARCLOUD_TOKEN",
    "SEMGREP_APP_TOKEN",
)


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


def test_broker_serves_no_secret_route() -> None:
    """Every route shaped like a secret read must 404 (T4).

    Asserted against the handler's own dispatch rather than a live socket: the
    property is that no such branch exists, and that is what is checked.
    """
    source = (SECRETS_DIR / "capability_broker.py").read_text(encoding="utf-8")
    for route in ("/secret/", "/resolve-secret", "/print-secret", "/export"):
        assert f'self.path == "{route}"' not in source
    # The only routes the handler dispatches on.
    assert 'self.path == "/healthz"' in source
    assert 'self.path != "/capability"' in source


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
    # A registry is a mapping of names, never a store of values.
    for marker in ("BEGIN PRIVATE KEY", "Bearer ey", "sqp_", "github_pat_"):
        assert marker not in raw


# ---------------------------------------------------------------------------
# §8 — no arbitrary credentialed proxy
# ---------------------------------------------------------------------------


def test_caller_cannot_override_host_or_credential() -> None:
    """The caller may influence only registry-declared params (SSRF defence)."""
    spec = load_registry().get("sonar.read_issues")
    assert spec is not None
    for hostile in (
        {"host": "evil.example"},
        {"Authorization": "Bearer x"},
        {"secret_name": "SONAR_TOKEN"},
        {"organization": "attacker-org"},
    ):
        with pytest.raises(cb.BrokerError) as excinfo:
            cb.validate_params(spec, hostile)
        assert excinfo.value.status == 400


def test_repository_scoped_params_are_not_caller_supplied() -> None:
    """project/organization/group_id must be broker-derived, else sessions cross repos."""
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


def test_caller_params_are_validated() -> None:
    spec = load_registry().get("sonar.read_issues")
    assert spec is not None
    assert cb.validate_params(spec, {"branch": "main", "ps": "100"}) == {
        "branch": "main",
        "ps": "100",
    }
    for bad in ({"ps": "not-a-number"}, {"ps": "99999"}, {"branch": "a b;rm -rf /"}):
        with pytest.raises(cb.BrokerError):
            cb.validate_params(spec, bad)


# ---------------------------------------------------------------------------
# §21 — no same-UID fake isolation
# ---------------------------------------------------------------------------


def test_broker_refuses_to_start_inside_a_model_runtime() -> None:
    posture = cb.boundary_posture({"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "s"})
    assert not posture.isolated
    assert "not a trust boundary" in posture.reason


def test_broker_boundary_ok_outside_model_runtime() -> None:
    assert cb.boundary_posture({"PATH": "/usr/bin"}).isolated


# ---------------------------------------------------------------------------
# T7 / §4 / §20 — broker workload identity, never a static secret
# ---------------------------------------------------------------------------


def test_static_infisical_secret_is_refused_as_broker_identity() -> None:
    identity = cb.workload_identity({"INFISICAL_CLIENT_SECRET": "whatever"})
    assert identity.method == "none"
    assert "REFUSED" in identity.detail


def test_workload_identity_prefers_kubernetes(tmp_path: Path) -> None:
    token = tmp_path / "sa-token"
    token.write_text("projected-jwt")
    identity = cb.workload_identity(
        {"INFISICAL_IDENTITY_ID": "id-1", "INFISICAL_K8S_SA_TOKEN_PATH": str(token)}
    )
    assert identity.method == "kubernetes-auth"
    # The report names the mechanism; it never carries material.
    assert "projected-jwt" not in identity.detail


def test_no_identity_available_is_reported_not_faked() -> None:
    assert cb.workload_identity({}).method == "none"


# ---------------------------------------------------------------------------
# T5 / T6 — session identity verification
# ---------------------------------------------------------------------------


def _sign(claims: dict, *, alg: str = "ES256", kid: str = "k1", key=None) -> tuple[str, object]:
    """Mint a real ES256 assertion so verification is exercised, not stubbed."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    from cryptography.hazmat.primitives.hashes import SHA256

    key = key or ec.generate_private_key(ec.SECP256R1())
    b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()  # noqa: E731
    header = b64(json.dumps({"alg": alg, "typ": "JWT", "kid": kid}).encode())
    payload = b64(json.dumps(claims).encode())
    signed = f"{header}.{payload}".encode()
    r, s = decode_dss_signature(key.sign(signed, ec.ECDSA(SHA256())))
    signature = b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"{header}.{payload}.{signature}", key


class _StubJWKS:
    def __init__(self, key) -> None:
        self._key = key.public_key()

    def get(self, kid: str, *, now=None):
        if kid != "k1":
            raise broker_identity.IdentityError(f"signing key '{kid}' not published")
        return self._key


def _valid_claims(**overrides) -> dict:
    claims = {
        "iss": "ccr",
        "aud": ["ccpool_l9-prod"],
        "ccr:role": "session_worker",
        "ccr:session_id": "sess-1",
        "ccr:org_id": "org-1",
        "ccr:account_id": "acct-1",
        "jti": "jti-1",
        "exp": int(time.time()) + 600,
    }
    claims.update(overrides)
    return claims


def test_valid_session_identity_is_accepted_and_audited() -> None:
    """T6 — accepted, scope assigned, audit recorded, raw JWT never logged."""
    token, key = _sign(_valid_claims())
    claims = broker_identity.verify(
        token, expected_audience="ccpool_l9-prod", expected_org="org-1", jwks=_StubJWKS(key)
    )
    assert claims.session_id == "sess-1"
    record = claims.audit_record()
    assert record["ccr:session_id"] == "sess-1"
    assert record["jti"] == "jti-1"
    assert record["ccr:org_id"] == "org-1"
    # Contract §5: never record the JWT itself.
    assert token not in json.dumps(record)
    assert not any(token in str(v) for v in record.values())


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"iss": "not-ccr"}, "issuer"),
        ({"aud": ["ccpool_someone-else"]}, "audience"),
        ({"ccr:role": "admin"}, "role"),
        ({"exp": int(time.time()) - 3600}, "expired"),
        ({"ccr:session_id": ""}, "session identity"),
    ],
)
def test_bad_claims_are_rejected(overrides: dict, expected: str) -> None:
    """T5 — wrong issuer / wrong pool / wrong role / expired / no session."""
    token, key = _sign(_valid_claims(**overrides))
    with pytest.raises(broker_identity.IdentityError, match=expected):
        broker_identity.verify(token, expected_audience="ccpool_l9-prod", jwks=_StubJWKS(key))


def test_wrong_organization_is_rejected() -> None:
    token, key = _sign(_valid_claims())
    with pytest.raises(broker_identity.IdentityError, match="organization"):
        broker_identity.verify(
            token,
            expected_audience="ccpool_l9-prod",
            expected_org="other-org",
            jwks=_StubJWKS(key),
        )


def test_bad_signature_is_rejected() -> None:
    from cryptography.hazmat.primitives.asymmetric import ec

    token, _ = _sign(_valid_claims())
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(broker_identity.IdentityError, match="signature"):
        broker_identity.verify(token, expected_audience="ccpool_l9-prod", jwks=_StubJWKS(other))


@pytest.mark.parametrize("alg", ["none", "HS256", "RS256"])
def test_algorithm_confusion_is_rejected(alg: str) -> None:
    """`alg: none` and HMAC confusion must fail before any key work."""
    token, key = _sign(_valid_claims(), alg=alg)
    with pytest.raises(broker_identity.IdentityError, match="algorithm"):
        broker_identity.verify(token, expected_audience="ccpool_l9-prod", jwks=_StubJWKS(key))


@pytest.mark.parametrize("token", ["", "not.a.jwt.at.all", "onlyonesegment", "a.b"])
def test_malformed_tokens_are_rejected(token: str) -> None:
    with pytest.raises(broker_identity.IdentityError):
        broker_identity.verify(token, expected_audience="ccpool_l9-prod")


def test_broker_cannot_be_configured_to_accept_any_audience() -> None:
    """There is no wildcard-audience mode to deploy by accident."""
    token, key = _sign(_valid_claims())
    with pytest.raises(broker_identity.IdentityError, match="misconfigured"):
        broker_identity.verify(token, expected_audience="*", jwks=_StubJWKS(key))


# ---------------------------------------------------------------------------
# T13 — cross-session isolation
# ---------------------------------------------------------------------------


def test_session_a_assertion_is_useless_against_another_pool() -> None:
    """Session A's valid assertion must not authorize against pool B."""
    token, key = _sign(_valid_claims(aud=["ccpool_env-a"]))
    assert (
        broker_identity.verify(
            token, expected_audience="ccpool_env-a", jwks=_StubJWKS(key)
        ).session_id
        == "sess-1"
    )
    with pytest.raises(broker_identity.IdentityError, match="audience"):
        broker_identity.verify(token, expected_audience="ccpool_env-b", jwks=_StubJWKS(key))


# ---------------------------------------------------------------------------
# §17 — response sanitization
# ---------------------------------------------------------------------------


def test_sanitizer_returns_structured_subset_only() -> None:
    spec = load_registry().get("sonar.read_issues")
    assert spec is not None
    payload = {
        "total": 1,
        "issues": [{"key": "i1", "rule": "r1", "severity": "MAJOR", "secretField": "leak"}],
        "authorization": "Bearer sqp_deadbeef",
    }
    result = cb.scrub(spec, payload, [])
    serialized = json.dumps(result)
    assert "secretField" not in serialized
    assert "sqp_deadbeef" not in serialized
    assert result["issues"][0]["rule"] == "r1"


def test_response_is_withheld_if_a_credential_survives_sanitizing() -> None:
    """Backstop: a leak means the sanitizer is wrong, so drop the whole response."""
    spec = load_registry().get("sonar.read_issues")
    assert spec is not None
    payload = {"issues": [{"key": "i1", "message": "token is sqp_live_value"}]}
    with pytest.raises(cb.BrokerError, match="withheld"):
        cb.scrub(spec, payload, ["sqp_live_value"])


# ---------------------------------------------------------------------------
# §18 — failure semantics: an outage is never a pass
# ---------------------------------------------------------------------------


def test_missing_broker_degrades_and_fails_the_requirement() -> None:
    env = {"L9_GOVERNANCE_SURFACE": "claude-code", "CLAUDECODE": "1"}
    client = cc.CapabilityClient(env=env)
    status = client.status("sonar.read_issues")
    assert status.status == cc.DEGRADED
    assert status.status != cc.ENABLED


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
# #303 item 2 — declared guards are enforced, not merely parsed
# ---------------------------------------------------------------------------


def _stub_claims() -> broker_identity.SessionClaims:
    return broker_identity.SessionClaims(
        session_id="sess-rate",
        jti="jti-rate",
        org_id="org-1",
        account_id="acct-1",
        audience="ccpool_l9-prod",
        role="session_worker",
        expires_at=int(time.time()) + 600,
    )


def _broker() -> cb.Broker:
    return cb.Broker("ccpool_l9-prod", env={"L9_BROKER_EXPECTED_ORG": "org-1"})


def test_every_declared_requirement_is_one_the_broker_can_evaluate() -> None:
    """A registry precondition no code evaluates is a guard in name only."""
    registry = load_registry()
    undecidable = {
        f"{spec_id}:{req}"
        for spec_id in registry.ids()
        for req in registry.get(spec_id).requires
        if req not in cb.EVALUABLE_REQUIREMENTS
    }
    assert undecidable == set(), (
        "capabilities.yaml declares preconditions the broker cannot evaluate; "
        "either implement them in EVALUABLE_REQUIREMENTS or remove them: "
        f"{sorted(undecidable)}"
    )


def test_unevaluable_precondition_denies_rather_than_passing_silently() -> None:
    """The failure mode #303 names: declared `requires`, executed anyway."""
    broker = _broker()
    spec = broker.registry.get("graphiti.query")
    object.__setattr__(spec, "requires", ("phase_lock_held",))
    with pytest.raises(cb.BrokerError) as excinfo:
        broker.handle(_stub_claims(), {"capability": "graphiti.query", "params": {}})
    assert excinfo.value.status == 403
    assert broker.audit[-1]["decision"] == "DENY"
    assert broker.audit[-1]["detail"] == "unevaluable precondition"


def test_rate_ceiling_is_enforced_per_session_and_capability() -> None:
    limiter = cb.RateLimiter()
    assert all(limiter.check("sess-a", "cap.one", 3, now=1000.0) for _ in range(3))
    # Fourth call inside the window is refused...
    assert not limiter.check("sess-a", "cap.one", 3, now=1000.0)
    # ...but a different capability and a different session keep their own budget.
    assert limiter.check("sess-a", "cap.two", 3, now=1000.0)
    assert limiter.check("sess-b", "cap.one", 3, now=1000.0)
    # ...and the window slides.
    assert limiter.check("sess-a", "cap.one", 3, now=1061.0)


def test_declared_rate_ceiling_denies_the_over_limit_request() -> None:
    broker = _broker()
    spec = broker.registry.get("graphiti.query")
    object.__setattr__(spec, "max_requests_per_minute", 1)
    body = {"capability": "graphiti.query", "params": {"query": "x"}}
    # First request gets past the ceiling and fails later, at the upstream call
    # (no network here) — what matters is that it is not a rate denial.
    with pytest.raises(cb.BrokerError) as first:
        broker.handle(_stub_claims(), body)
    assert first.value.status != 429
    with pytest.raises(cb.BrokerError) as second:
        broker.handle(_stub_claims(), body)
    assert second.value.status == 429
    assert broker.audit[-1]["detail"] == "rate ceiling exceeded"


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


def test_master_mcp_does_not_route_through_retired_broker() -> None:
    """Cursor master MCP must not send GitHub/Context7/etc through the dead broker."""
    raw = (REPO_ROOT / "environment" / "mcp" / "master.mcp.json").read_text(encoding="utf-8")
    config = json.loads(raw)
    wiring = {k: v for k, v in config.items() if not str(k).startswith("_")}
    assert "L9_CAPABILITY_BROKER_URL" not in json.dumps(wiring)


def test_no_adapter_mcp_template_carries_a_graphiti_bearer() -> None:
    """#303 item 3: adapter MCP templates use GRAPHITI_MCP_URL with no bearer.

    Scoped to adapter templates. `ops/graphiti/mcp.json.example` is the
    trusted-operator (Cursor SSH tunnel) shape and is deliberately not an
    adapter template — see its own header.
    """
    adapters = REPO_ROOT / "environment" / "agents" / "adapters"
    offenders: list[str] = []
    checked = 0
    for path in sorted(adapters.rglob("*.json")):
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(config, dict):
            continue
        # `_comment` / `_l9_meta` carry prose that names the token precisely to
        # forbid it. Configuration is everything else.
        wiring = {k: v for k, v in config.items() if not k.startswith("_")}
        if "mcpServers" not in wiring and "transport" not in wiring:
            continue
        checked += 1
        rendered = json.dumps(wiring)
        if "GRAPHITI_MCP_TOKEN" in rendered or "Authorization" in rendered:
            offenders.append(str(path.relative_to(REPO_ROOT)))
        if "L9_CAPABILITY_BROKER_URL" in rendered:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert checked >= 5, f"adapter template discovery found only {checked} configs"
    assert offenders == [], (
        f"adapter MCP templates must use ${{GRAPHITI_MCP_URL}} with no in-file bearer: {offenders}"
    )


# ---------------------------------------------------------------------------
# §13 — Sonar consumer is brokered, never env-token on a model surface
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
