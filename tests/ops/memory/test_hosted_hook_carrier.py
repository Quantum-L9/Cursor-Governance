"""Hosted hook carrier (ADR-0055; CANONICAL_LAW §8.11 as amended 2026-11-17).

The hook lane sends ``write`` / ``ingest_candidate`` / ``close`` straight to the
hosted ``MemoryService`` MCP endpoint as the machine hook principal. Every test
here runs against a fake endpoint: no live network, no real credential.

What is proved:

- the carrier decision (bound => hosted, unbound => relay / local, override
  wins, unknown override refused);
- ``OK`` only for a UUID hosted receipt that proves the commit;
- a refusal is ``REJECTED`` and is never parked or rerouted;
- a transport failure parks the record in the relay outbox with its reason;
- the envelope still bounds what may be sent;
- the Stop-hook drain acknowledges or settles owed entries;
- no credential or token reaches any output, outcome, or file.
"""

from __future__ import annotations

import json
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml
from l9_graphite_memory import mcp_tools

from ops.memory import hosted_hook_transport as hht
from ops.memory import relay
from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.hook_carrier import (
    CARRIER_ENV,
    HOOK_CLIENT_ID,
    HOOK_CLIENT_SECRET,
    HOOK_CREDENTIALS,
    CarrierError,
    resolve_carrier,
    store_of,
)
from ops.memory.runtime_binding import RuntimeBinding

ROOT = Path(__file__).resolve().parents[3]
NS = "cursor-governance"
RESOURCE = "https://memory.example.test/mcp"
ISSUER = "https://issuer.example.test/"
TOKEN_ENDPOINT = "https://issuer.example.test/oauth/token"
CLIENT_ID_VALUE = "cid-HOOK-PRINCIPAL-not-a-secret-marker"
CLIENT_SECRET_VALUE = "csec-SHOULD-NEVER-APPEAR-ANYWHERE"
ACCESS_TOKEN = "tok-SHOULD-NEVER-APPEAR-ANYWHERE"
SECRETS = (CLIENT_SECRET_VALUE, ACCESS_TOKEN)

ONBOARDING = {
    "issuer": {"domain": "issuer.example.test", "issuer_url": ISSUER},
    "resource": {"identifier": RESOURCE},
}


@pytest.fixture(autouse=True)
def _repository_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


@pytest.fixture(autouse=True)
def _fresh_caches() -> None:
    hht.reset_caches()
    yield
    hht.reset_caches()


@pytest.fixture
def hosted_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CARRIER_ENV, "hosted")


def _credential(name: str) -> str | None:
    return {HOOK_CLIENT_ID: CLIENT_ID_VALUE, HOOK_CLIENT_SECRET: CLIENT_SECRET_VALUE}.get(name)


class FakeHosted:
    """A Memory MCP endpoint and an Auth0 issuer, in memory."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str], bytes | None]] = []
        self.receipt: dict[str, Any] = {
            "receipt_id": str(uuid.uuid4()),
            "status": "admitted",
            "namespace": NS,
            "record_id": "rec-1",
        }
        self.tool_reply: dict[str, Any] | None = None  # full JSON-RPC message override
        self.mcp_status = 200
        self.token_status = 200
        self.sse = False
        self.network_down = False
        self.tool_calls: list[dict[str, Any]] = []
        self.prm: dict[str, Any] | None = None

    def __call__(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float
    ) -> hht.HttpReply:
        self.calls.append((method, url, dict(headers), body))
        if self.network_down:
            raise hht.HostedUnavailable("URLError reaching memory.example.test")
        if url == f"{ISSUER}.well-known/openid-configuration":
            return self._json(200, {"issuer": ISSUER, "token_endpoint": TOKEN_ENDPOINT})
        if url.startswith("https://memory.example.test/.well-known/oauth-protected-resource"):
            if self.prm is None:
                return hht.HttpReply(404, {}, b"")
            return self._json(200, self.prm)
        if url == TOKEN_ENDPOINT:
            if self.token_status != 200:
                return self._json(self.token_status, {"error": "access_denied"})
            return self._json(200, {"access_token": ACCESS_TOKEN, "expires_in": 3600})
        if url == RESOURCE:
            assert headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"
            return self._mcp(json.loads((body or b"{}").decode("utf-8")), headers)
        return hht.HttpReply(404, {}, b"")

    @staticmethod
    def _json(status: int, payload: Any, headers: dict[str, str] | None = None) -> hht.HttpReply:
        return hht.HttpReply(
            status,
            {"content-type": "application/json", **(headers or {})},
            json.dumps(payload).encode("utf-8"),
        )

    def _mcp(self, message: dict[str, Any], headers: Mapping[str, str]) -> hht.HttpReply:
        method = message.get("method")
        if method == "initialize":
            return self._json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {"protocolVersion": "2025-06-18"},
                },
                {"mcp-session-id": "sess-abc"},
            )
        assert headers.get("Mcp-Session-Id") == "sess-abc"
        if method == "notifications/initialized":
            return hht.HttpReply(202, {}, b"")
        assert method == "tools/call"
        self.tool_calls.append(message["params"])
        if self.mcp_status != 200:
            return self._json(self.mcp_status, {"jsonrpc": "2.0", "error": {"code": -1}})
        reply = self.tool_reply or {
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {
                "content": [{"type": "text", "text": json.dumps(self.receipt)}],
                "structuredContent": self.receipt,
                "isError": False,
            },
        }
        if self.sse:
            body = f"event: message\ndata: {json.dumps(reply)}\n\n".encode()
            return hht.HttpReply(200, {"content-type": "text/event-stream"}, body)
        return self._json(200, reply)

    def count(self, url: str) -> int:
        return sum(1 for _m, u, _h, _b in self.calls if u == url)


@pytest.fixture
def endpoint() -> FakeHosted:
    return FakeHosted()


def _transport(endpoint: FakeHosted, onboarding: Mapping[str, Any] = ONBOARDING):
    return hht.HostedHookTransport(http=endpoint, onboarding=onboarding, credential=_credential)


def _client(bound: RuntimeBinding, fake_cli, endpoint: FakeHosted, surface: str | None = None):
    return MemoryControlPlaneClient(
        bound,
        runner=fake_cli.run,
        session_id="sess-1",
        surface=surface,
        hosted_transport=_transport(endpoint),
    )


def _write(client: MemoryControlPlaneClient, tmp_path: Path, **kw: Any):
    return client.write(
        kw.pop("content", "Hook records reach the hosted store directly."),
        workspace=str(tmp_path),
        namespace=NS,
        memory_class=kw.pop("memory_class", "decision"),
        tags=("topic:memory",),
        idempotency_key="k-1",
        **kw,
    )


# --- carrier decision --------------------------------------------------------


def _bound(_name: str, _env: object) -> bool:
    return True


def _unbound(_name: str, _env: object) -> bool:
    return False


def test_bound_credentials_choose_hosted_on_every_surface() -> None:
    assert resolve_carrier({}, binder=_bound) == "hosted"
    assert resolve_carrier({"CLAUDE_CODE_REMOTE": "true"}, binder=_bound) == "hosted"


def test_unbound_credentials_fall_back_to_relay_remote_and_local_elsewhere() -> None:
    assert resolve_carrier({"CLAUDE_CODE_REMOTE": "true"}, binder=_unbound) == "relay"
    assert resolve_carrier({}, binder=_unbound) == "local"


def test_both_credentials_must_bind() -> None:
    def only_id(name: str, _env: object) -> bool:
        return name == HOOK_CLIENT_ID

    assert resolve_carrier({"CLAUDE_CODE_REMOTE": "true"}, binder=only_id) == "relay"


def test_override_wins_over_bound_credentials() -> None:
    for carrier in ("relay", "local", "hosted"):
        env = {CARRIER_ENV: carrier, "CLAUDE_CODE_REMOTE": "true"}
        assert resolve_carrier(env, binder=_bound) == carrier
    assert resolve_carrier({CARRIER_ENV: "HOSTED"}, binder=_unbound) == "hosted"


def test_unknown_override_is_refused_even_when_bound() -> None:
    with pytest.raises(CarrierError, match="names no hook carrier"):
        resolve_carrier({CARRIER_ENV: "remote"}, binder=_bound)


def test_the_override_is_decided_before_any_credential_is_bound() -> None:
    asked: list[str] = []

    def spy(name: str, _env: object) -> bool:
        asked.append(name)
        return True

    resolve_carrier({CARRIER_ENV: "local"}, binder=spy)
    assert asked == []


def test_hook_credentials_are_listed_and_bind_only_when_their_values_exist() -> None:
    """The committed mirror lists both names (2026-11-20, lane MEM-HOOK).

    Listing makes the names bindable without the live list; the carrier is
    still ``hosted`` only when both values are actually present.
    """
    inventory = yaml.safe_load(
        (ROOT / "ops/secrets/infisical-cursor-governance.yaml").read_text(encoding="utf-8")
    )
    for name in HOOK_CREDENTIALS:
        assert name in inventory["root_env_keys"]
    secrets = str(ROOT / "ops" / "secrets")
    if secrets not in sys.path:
        sys.path.insert(0, secrets)
    import capability_bind as bind

    bind.remember_vault_names(frozenset())
    bind.reset_cache()
    try:
        assert resolve_carrier({}) != "hosted"
        bind.reset_cache()
        env = {HOOK_CLIENT_ID: CLIENT_ID_VALUE, HOOK_CLIENT_SECRET: CLIENT_SECRET_VALUE}
        assert resolve_carrier(env) == "hosted"
    finally:
        bind.remember_vault_names(None)
        bind.reset_cache()


def test_relay_and_hosted_are_the_same_store() -> None:
    assert store_of("relay") == store_of("hosted") == "hosted"
    assert store_of("local") == "local"
    assert store_of(None) is None


# --- the hosted tool map (REMOTE_MCP_CONTRACT §2b) ---------------------------


def test_hosted_map_is_the_hook_principal_map() -> None:
    assert dict(hht.HOSTED_TOOLS) == {
        "write": "memory.ingest",
        "ingest_candidate": "memory.ingest_governed_candidate",
        "close": "memory.close",
    }


def test_hosted_map_never_names_write_agent() -> None:
    assert "memory.write_agent" not in hht.HOSTED_TOOLS.values()
    assert all("write_agent" not in tool for tool in hht.HOSTED_TOOLS.values())


def test_relay_keeps_write_agent_because_the_agent_carries_it() -> None:
    assert relay.CONNECTOR_TOOLS["write"] == "memory.write_agent"
    assert set(relay.CONNECTOR_TOOLS) == set(hht.HOSTED_TOOLS)


def test_write_arguments_fit_memory_ingest() -> None:
    args = {"namespace": NS, "content": "x", "memory_class": "meta", "tags": ["t"]}
    assert hht.hosted_arguments("write", args) == args
    with pytest.raises(hht.HostedUnavailable, match="not declared by memory.ingest"):
        hht.hosted_arguments("write", {**args, "agent": "x"})
    with pytest.raises(hht.HostedUnavailable, match="missing memory.ingest fields"):
        hht.hosted_arguments("write", {"namespace": NS})
    candidate = {"candidate": {"source": {}}}
    assert hht.hosted_arguments("ingest_candidate", candidate) == candidate


def test_ingest_fields_match_the_bound_release_schema() -> None:
    (tool,) = [t for t in mcp_tools.CANONICAL_TOOLS if t["name"] == "memory.ingest"]
    schema = tool["inputSchema"]
    assert set(schema["properties"]) == hht.INGEST_FIELDS
    assert tuple(schema.get("required", ())) == hht.INGEST_REQUIRED


@pytest.mark.usefixtures("hosted_env")
def test_an_undeclared_write_field_is_parked_not_sent(bound, fake_cli, endpoint, tmp_path) -> None:
    transport = _transport(endpoint)
    result = transport.call("write", {"namespace": NS, "content": "x", "agent": "y"})
    assert result.unavailable and "not declared by memory.ingest" in (result.reason or "")
    assert endpoint.calls == []


# --- OK, and only OK with a UUID receipt -------------------------------------


@pytest.mark.usefixtures("hosted_env")
def test_write_is_sent_as_the_hook_principal_and_reports_ok(
    bound, fake_cli, endpoint, tmp_path
) -> None:
    client = _client(bound, fake_cli, endpoint, surface="cursor-session-end")
    outcome = _write(client, tmp_path, source_id="session:sess-1")
    assert outcome.status is OutcomeStatus.OK, outcome.error
    assert outcome.integration_receipt["transport"] == "hosted-mcp"
    assert outcome.integration_receipt["canonical_receipt_id"] == endpoint.receipt["receipt_id"]
    assert fake_cli.calls == [], "the hosted carrier never spawns the local runtime"
    assert not relay.relay_dir(tmp_path).exists()
    (params,) = endpoint.tool_calls
    assert params["name"] == "memory.ingest"
    assert params["arguments"]["tags"] == [
        "topic:memory",
        "carrier:hosted",
        "hook-surface:cursor-session-end",
    ]
    assert params["arguments"]["idempotency_key"] == "k-1"
    # client-credentials grant against the Memory audience, form-encoded
    (token_call,) = [c for c in endpoint.calls if c[1] == TOKEN_ENDPOINT]
    assert b"grant_type=client_credentials" in (token_call[3] or b"")
    assert b"audience=https%3A%2F%2Fmemory.example.test%2Fmcp" in (token_call[3] or b"")


@pytest.mark.usefixtures("hosted_env")
def test_close_and_candidate_use_their_connector_tools(bound, fake_cli, endpoint, tmp_path) -> None:
    client = _client(bound, fake_cli, endpoint)
    endpoint.receipt = {
        "receipt_id": str(uuid.uuid4()),
        "status": "complete",
        "namespace": NS,
        "record_id": "close-1",
        "write_receipt_id": str(uuid.uuid4()),
    }
    closed = client.close(
        workspace=str(tmp_path), namespace=NS, summary="closed", idempotency_key="close:1"
    )
    endpoint.receipt = {
        "status": "admitted",
        "candidate_id": "cand-1",
        "namespace": NS,
        "record_id": "cont-1",
        "write_receipt_id": str(uuid.uuid4()),
        "storage_committed": True,
    }
    candidate = {"source": {"namespace": NS, "repository": "Quantum-L9/X"}, "knowledge": {}}
    admitted = client.ingest_candidate(candidate, workspace=str(tmp_path))
    assert closed.status is OutcomeStatus.OK, closed.error
    assert admitted.status is OutcomeStatus.OK, admitted.error
    assert admitted.receipt.record_id == "cont-1"
    assert [p["name"] for p in endpoint.tool_calls] == [
        "memory.close",
        "memory.ingest_governed_candidate",
    ]
    assert endpoint.tool_calls[1]["arguments"] == {"candidate": candidate}


@pytest.mark.usefixtures("hosted_env")
@pytest.mark.parametrize("bad", ["", "not-a-uuid", None])
def test_ok_requires_a_uuid_receipt_otherwise_the_record_is_parked(
    bound, fake_cli, endpoint, tmp_path, bad
) -> None:
    endpoint.receipt = {**endpoint.receipt, "receipt_id": bad}
    outcome = _write(_client(bound, fake_cli, endpoint), tmp_path)
    assert outcome.status is OutcomeStatus.RELAYED
    (entry,) = relay.pending(tmp_path)
    assert entry["carrier"] == "hosted"
    assert "no UUID receipt id" in entry["reason"]


@pytest.mark.usefixtures("hosted_env")
def test_a_receipt_that_does_not_prove_the_commit_is_parked(
    bound, fake_cli, endpoint, tmp_path
) -> None:
    endpoint.receipt = {**endpoint.receipt, "status": "pending"}
    outcome = _write(_client(bound, fake_cli, endpoint), tmp_path)
    assert outcome.status is OutcomeStatus.RELAYED
    assert "does not prove a commit" in relay.pending(tmp_path)[0]["reason"]


@pytest.mark.usefixtures("hosted_env")
def test_an_sse_reply_is_read_like_a_json_reply(bound, fake_cli, endpoint, tmp_path) -> None:
    endpoint.sse = True
    assert _write(_client(bound, fake_cli, endpoint), tmp_path).status is OutcomeStatus.OK


@pytest.mark.usefixtures("hosted_env")
def test_the_token_is_cached_in_process(bound, fake_cli, endpoint, tmp_path) -> None:
    client = _client(bound, fake_cli, endpoint)
    _write(client, tmp_path, content="one")
    _write(client, tmp_path, content="two")
    assert endpoint.count(TOKEN_ENDPOINT) == 1
    assert endpoint.count(f"{ISSUER}.well-known/openid-configuration") == 1


# --- refusal is the verdict ----------------------------------------------------


def _tool_error(endpoint: FakeHosted) -> None:
    endpoint.tool_reply = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"content": [{"type": "text", "text": "namespace not granted"}], "isError": True},
    }


def _rpc_error(endpoint: FakeHosted) -> None:
    endpoint.tool_reply = {
        "jsonrpc": "2.0",
        "id": 2,
        "error": {"code": -32602, "message": "unknown tool"},
    }


def _forbidden(endpoint: FakeHosted) -> None:
    endpoint.mcp_status = 403


def _quarantined(endpoint: FakeHosted) -> None:
    endpoint.receipt = {**endpoint.receipt, "status": "quarantined", "reason": "pii suspected"}


@pytest.mark.usefixtures("hosted_env")
@pytest.mark.parametrize("refuse", [_tool_error, _rpc_error, _forbidden, _quarantined])
def test_a_hosted_refusal_is_rejected_and_never_parked(
    bound, fake_cli, endpoint, tmp_path, refuse
) -> None:
    refuse(endpoint)
    outcome = _write(_client(bound, fake_cli, endpoint), tmp_path)
    assert outcome.status is OutcomeStatus.REJECTED
    assert (outcome.error or "").startswith("hosted refusal:")
    assert outcome.integration_receipt["transport"] == "hosted-mcp"
    assert not relay.relay_dir(tmp_path).exists(), "a refusal is never rerouted"
    assert fake_cli.calls == []


# --- transport failure is not a verdict: park in the relay outbox -------------


def _down(endpoint: FakeHosted) -> None:
    endpoint.network_down = True


def _server_error(endpoint: FakeHosted) -> None:
    endpoint.mcp_status = 503


def _unauthenticated(endpoint: FakeHosted) -> None:
    endpoint.mcp_status = 401


def _token_refused(endpoint: FakeHosted) -> None:
    endpoint.token_status = 401


def _unreadable(endpoint: FakeHosted) -> None:
    endpoint.tool_reply = {"jsonrpc": "2.0", "id": 2, "result": {"content": []}}


@pytest.mark.usefixtures("hosted_env")
@pytest.mark.parametrize(
    ("fail", "reason"),
    [
        (_down, "URLError"),
        (_server_error, "HTTP 503"),
        (_unauthenticated, "HTTP 401"),
        (_token_refused, "token request refused: HTTP 401"),
        (_unreadable, "no readable receipt"),
    ],
)
def test_a_transport_failure_parks_the_record_with_its_reason(
    bound, fake_cli, endpoint, tmp_path, fail, reason
) -> None:
    fail(endpoint)
    outcome = _write(_client(bound, fake_cli, endpoint), tmp_path)
    assert outcome.status is OutcomeStatus.RELAYED
    assert not outcome.ok
    assert outcome.fault_class == "none"
    (entry,) = relay.pending(tmp_path)
    assert reason in entry["reason"]
    assert entry["carrier"] == "hosted"
    assert entry["tool"] == relay.CONNECTOR_TOOLS["write"]
    assert "carrier:hosted" in entry["arguments"]["tags"], "the retry sends the same record"
    assert fake_cli.calls == []


@pytest.mark.usefixtures("hosted_env")
def test_an_unbound_credential_is_a_transport_failure(bound, fake_cli, endpoint, tmp_path) -> None:
    client = MemoryControlPlaneClient(
        bound,
        runner=fake_cli.run,
        hosted_transport=hht.HostedHookTransport(
            http=endpoint, onboarding=ONBOARDING, credential=lambda _name: None
        ),
    )
    outcome = _write(client, tmp_path)
    assert outcome.status is OutcomeStatus.RELAYED
    assert "hook credential does not bind" in relay.pending(tmp_path)[0]["reason"]
    assert endpoint.calls == []


@pytest.mark.usefixtures("hosted_env")
def test_https_only(bound, fake_cli, endpoint, tmp_path) -> None:
    plain = {**ONBOARDING, "resource": {"identifier": "http://memory.example.test/mcp"}}
    client = MemoryControlPlaneClient(
        bound,
        runner=fake_cli.run,
        hosted_transport=hht.HostedHookTransport(
            http=endpoint, onboarding=plain, credential=_credential
        ),
    )
    assert _write(client, tmp_path).status is OutcomeStatus.RELAYED
    assert "not an https URL" in relay.pending(tmp_path)[0]["reason"]
    assert endpoint.calls == []


def test_issuer_is_discovered_from_protected_resource_metadata_when_unbound(endpoint) -> None:
    endpoint.prm = {"resource": RESOURCE, "authorization_servers": [ISSUER]}
    unbound = {"issuer": {"domain": None, "issuer_url": None}, "resource": {"identifier": RESOURCE}}
    result = _transport(endpoint, unbound).call("write", {"namespace": NS, "content": "c"})
    assert result.ok, result.reason
    assert endpoint.calls[0][1] == (
        "https://memory.example.test/.well-known/oauth-protected-resource/mcp"
    )


def test_a_token_endpoint_off_the_issuer_host_is_refused(endpoint) -> None:
    def elsewhere(method, url, headers, body, timeout):
        if url.endswith("openid-configuration"):
            return FakeHosted._json(
                200, {"issuer": ISSUER, "token_endpoint": "https://attacker.example/token"}
            )
        return endpoint(method, url, headers, body, timeout)

    result = hht.HostedHookTransport(
        http=elsewhere, onboarding=ONBOARDING, credential=_credential
    ).call("write", {"namespace": NS, "content": "x"})
    assert result.unavailable
    assert "not on the issuer's host" in (result.reason or "")
    assert not any(u.startswith("https://attacker") for _m, u, _h, _b in endpoint.calls)


# --- the envelope still admits before sending ----------------------------------


@pytest.mark.usefixtures("hosted_env")
def test_the_envelope_still_bounds_what_may_be_sent(bound, fake_cli, endpoint, tmp_path) -> None:
    client = _client(bound, fake_cli, endpoint, surface="pr-publish")  # episodic only, max 1
    wrong = client.write(
        "x", workspace=str(tmp_path), namespace=NS, memory_class="decision", source_id="PR#1"
    )
    assert wrong.status is OutcomeStatus.REJECTED
    assert endpoint.calls == [], "an envelope violation never reaches the network"
    first = client.write(
        "published", workspace=str(tmp_path), namespace=NS, memory_class="episodic", source_id="P"
    )
    second = client.write(
        "again", workspace=str(tmp_path), namespace=NS, memory_class="episodic", source_id="P"
    )
    assert first.status is OutcomeStatus.OK
    assert second.status is OutcomeStatus.REJECTED, "a hosted commit counts against max_records"
    assert len(endpoint.tool_calls) == 1


@pytest.mark.usefixtures("hosted_env")
def test_dry_run_and_distill_send_nothing(bound, fake_cli, endpoint, tmp_path) -> None:
    client = _client(bound, fake_cli, endpoint)
    dry = client.write(
        "x", workspace=str(tmp_path), namespace=NS, memory_class="decision", dry_run=True
    )
    source = tmp_path / "excerpt.txt"
    source.write_text("redacted\n", encoding="utf-8")
    distilled = client.distill(workspace=str(tmp_path), namespace=NS, source_path=source)
    assert dry.status is OutcomeStatus.NOT_COMMITTED
    assert distilled.status is OutcomeStatus.NOT_COMMITTED
    assert "hosted carrier" in (distilled.error or "")
    assert endpoint.calls == [] and fake_cli.calls == []


# --- Stop-hook drain ----------------------------------------------------------


def _owe(tmp_path: Path, content: str) -> str:
    entry = relay.enqueue(
        tmp_path,
        surface="pr-publish",
        operation="write",
        arguments={"namespace": NS, "content": content},
    )
    return str(entry["id"])


def test_drain_acks_with_the_hosted_receipt(endpoint, tmp_path) -> None:
    first, second = _owe(tmp_path, "a"), _owe(tmp_path, "b")
    report = hht.drain(tmp_path, transport=_transport(endpoint))
    assert report["acked"] == [first, second]
    assert report["remaining"] == 0
    assert relay.acks(tmp_path)[first]["receipt_id"] == endpoint.receipt["receipt_id"]


def test_drain_settles_a_refusal_and_stops_on_a_transport_failure(endpoint, tmp_path) -> None:
    refused = _owe(tmp_path, "a")
    _owe(tmp_path, "b")
    _quarantined(endpoint)
    report = hht.drain(tmp_path, transport=_transport(endpoint), limit=1)
    assert report["rejected"] == [refused]
    assert "quarantined" in relay.rejects(tmp_path)[refused]["refusal"]
    endpoint.network_down = True
    calls_before = len(endpoint.calls)
    _owe(tmp_path, "c")
    report = hht.drain(tmp_path, transport=_transport(endpoint))
    assert report["acked"] == [] and report["rejected"] == []
    assert report["remaining"] == 2
    assert "URLError" in report["stopped"]
    assert len(endpoint.calls) == calls_before + 1, "a failed endpoint is asked once per drain"


def test_drain_sends_relay_entries_to_the_hook_tool_not_write_agent(endpoint, tmp_path) -> None:
    _owe(tmp_path, "a")
    (entry,) = relay.pending(tmp_path)
    assert entry["tool"] == "memory.write_agent", "the outbox still names the agent-carried tool"
    hht.drain(tmp_path, transport=_transport(endpoint))
    assert [p["name"] for p in endpoint.tool_calls] == ["memory.ingest"]


def test_drain_with_an_empty_outbox_sends_nothing(endpoint, tmp_path) -> None:
    report = hht.drain(tmp_path, transport=_transport(endpoint))
    assert report == {"acked": [], "rejected": [], "remaining": 0, "stopped": None}
    assert endpoint.calls == []


# --- no secret anywhere --------------------------------------------------------


@pytest.mark.usefixtures("hosted_env")
def test_no_credential_or_token_reaches_any_output(
    bound, fake_cli, endpoint, tmp_path, capsys, caplog
) -> None:
    client = _client(bound, fake_cli, endpoint)
    outcomes = [_write(client, tmp_path, content="ok")]
    _tool_error(endpoint)
    outcomes.append(_write(client, tmp_path, content="refused"))
    endpoint.tool_reply = None
    endpoint.mcp_status = 503
    outcomes.append(_write(client, tmp_path, content="parked"))
    endpoint.token_status = 401
    hht.reset_caches()
    outcomes.append(_write(client, tmp_path, content="token refused"))
    relay.main(["--workspace", str(tmp_path), "instructions"])
    relay.main(["--workspace", str(tmp_path), "pending"])
    captured = capsys.readouterr()
    haystacks = [
        captured.out,
        captured.err,
        caplog.text,
        *(repr(outcome) for outcome in outcomes),
        *(json.dumps(outcome.integration_receipt, default=str) for outcome in outcomes),
        *(
            path.read_text(encoding="utf-8")
            for path in relay.relay_dir(tmp_path).iterdir()
            if path.is_file()
        ),
    ]
    for secret in SECRETS:
        for text in haystacks:
            assert secret not in text
