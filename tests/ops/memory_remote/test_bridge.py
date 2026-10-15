"""Network-free contract for the remote Memory consumer bridge (ADR-0053, §8.10).

Every refusal named in the ADR is exercised here against a fake transport, so the
fail-closed behavior is merge-blocking even where no candidate runtime exists.
``test_candidate_interop.py`` proves the same paths against a real server.
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.memory.agent_assertion import seal_identity_assertion  # noqa: E402
from ops.memory_remote import bridge as b  # noqa: E402

AGENT = "claude-code"
KEY = "k" * 64
SIDE_DOORS = b.forbidden_side_doors()


def identity(agent: str = AGENT) -> dict[str, Any]:
    actor = f"{b.ACTOR_PREFIX}{agent}"
    return seal_identity_assertion(
        {
            "schema": "l9.identity-assertion/v1",
            "subject_ref": actor,
            "resolved_dimensions": {"actor_identity": actor},
            "result": "resolved",
        }
    )


# --- endpoint ---------------------------------------------------------------


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://memory.example.org/mcp",
        "https://memory.example.org:8443/mcp/",
        "http://127.0.0.1:8200/mcp",
    ],
)
def test_admissible_endpoints(endpoint: str) -> None:
    assert b.validate_endpoint(endpoint, side_doors=SIDE_DOORS) == endpoint


@pytest.mark.parametrize(
    ("endpoint", "reason"),
    [
        ("http://memory.example.org/mcp", "https off loopback"),
        ("ftp://memory.example.org/mcp", "not https"),
        ("https://user:pw@memory.example.org/mcp", "userinfo"),
        ("https://memory.example.org/mcp?token=x", "query"),
        ("https://memory.example.org/mcp#frag", "fragment"),
        ("https://memory.example.org/memory", "is not the memory-remote-mcp/v1 route"),
        ("https://memory.example.org/", "is not the memory-remote-mcp/v1 route"),
        ("https://memory.example.org:9002/mcp", "retired memory endpoint"),
        ("http://127.0.0.1:8100/mcp", "retired memory endpoint"),
    ],
)
def test_refused_endpoints(endpoint: str, reason: str) -> None:
    with pytest.raises(b.RemoteBindingError, match=reason):
        b.validate_endpoint(endpoint, side_doors=SIDE_DOORS)


def test_every_retired_host_in_the_contract_is_refused() -> None:
    hosts = [door for door in SIDE_DOORS if "." in door and "/" not in door.split("://")[-1]]
    assert hosts, "the contract names the retired memory hosts"
    for host in hosts:
        bare = host.split("://")[-1].split("@")[-1]
        with pytest.raises(b.RemoteBindingError, match="retired memory side door"):
            b.validate_endpoint(f"https://{bare}/mcp", side_doors=SIDE_DOORS)


def test_no_endpoint_means_local(tmp_path: Path) -> None:
    assert b.requested_endpoint({"HOME": str(tmp_path)}) is None
    assert b.resolve({"HOME": str(tmp_path)}) is None


def test_environment_wins_over_the_address_file(tmp_path: Path) -> None:
    config = tmp_path / ".config" / "l9-memory"
    config.mkdir(parents=True)
    (config / "remote-endpoint.json").write_text(
        json.dumps({"endpoint": "https://file.example/mcp"}), encoding="utf-8"
    )
    env = {"HOME": str(tmp_path)}
    assert b.requested_endpoint(env) == "https://file.example/mcp"
    env[b.ENV_ENDPOINT] = "https://env.example/mcp"
    assert b.requested_endpoint(env) == "https://env.example/mcp"


@pytest.mark.parametrize(
    "content",
    [
        {"endpoint": "https://m.example/mcp", "token": "x"},
        {"url": "https://m.example/mcp"},
        {"endpoint": ""},
    ],
)
def test_the_address_file_holds_an_address_only(tmp_path: Path, content: dict[str, str]) -> None:
    path = tmp_path / "remote.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(b.RemoteBindingError):
        b.requested_endpoint({b.ENV_CONFIG: str(path)})


# --- release binding --------------------------------------------------------


def test_the_checked_in_binding_is_pending_and_refuses_hosted_endpoints() -> None:
    binding = b.load_binding()
    assert binding["release"]["admission"] == "pending"
    with pytest.raises(b.RemoteBindingError, match="unadmitted Memory release binding"):
        b.bound_release(binding, "https://memory.example.org/mcp", {})
    reason = {b.ENV_CANDIDATE: "consumer qualification"}
    with pytest.raises(b.RemoteBindingError, match="loopback-only"):
        b.bound_release(binding, "https://memory.example.org/mcp", reason)


def test_a_candidate_is_reachable_on_loopback_with_a_reason_only() -> None:
    binding = b.load_binding()
    loopback = "http://127.0.0.1:8200/mcp"
    for bare in ("", "1", "true", "yes"):
        with pytest.raises(b.RemoteBindingError):
            b.bound_release(binding, loopback, {b.ENV_CANDIDATE: bare})
    release = b.bound_release(binding, loopback, {b.ENV_CANDIDATE: "consumer qualification"})
    assert release == {"mode": "candidate_qualification", "version": "3.0.0"}


def test_admission_requires_every_evidence_field() -> None:
    binding = b.load_binding()
    binding["release"] = {"admission": "admitted", "version": "3.0.0"}
    with pytest.raises(b.RemoteBindingError, match="without evidence"):
        b.bound_release(binding, "https://memory.example.org/mcp", {})
    binding["release"].update(
        source_sha="a" * 40,
        tag="v3.0.0",
        wheel_sha256="b" * 64,
        admission_receipt="docs/receipts/l9-memory-release-3.0.0.md",
    )
    release = b.bound_release(binding, "https://memory.example.org/mcp", {})
    assert release == {"mode": "admitted", "version": "3.0.0"}


def test_a_foreign_binding_schema_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "binding.json"
    path.write_text(json.dumps({"schema": "other"}), encoding="utf-8")
    with pytest.raises(b.RemoteBindingError, match="is not l9.memory-remote-binding.v1"):
        b.load_binding(path)


# --- credentials ------------------------------------------------------------


def _door(**overrides: str) -> dict[str, str]:
    env = {
        b.ENV_AGENT_ID: AGENT,
        b.ENV_SIGNING_KEYS: json.dumps({AGENT: KEY}),
        b.ENV_IDENTITY: json.dumps(identity()),
        "L9_MEMORY_AGENTS_DOOR_SECRET": "door",
        "L9_MEMORY_AGENT_GRANTS_JSON": "{}",
        "L9_MEMORY_HUMAN_DOOR_SECRET": "human",
    }
    env.update(overrides)
    return env


def test_the_bridge_keeps_only_its_own_material() -> None:
    env = _door()
    creds = b.credentials_from_env(env, 300)
    assert creds.agent_id == AGENT
    for gone in (b.ENV_SIGNING_KEYS, b.ENV_IDENTITY, *b.SERVER_SIDE_ENV):
        assert gone not in env, gone
    headers = creds.headers()
    assert set(headers) == {"Authorization", "L9-Identity-Assertion", "L9-Identity-Assertion-HMAC"}
    token = headers["Authorization"].removeprefix("Bearer ")
    assert token.split(".")[0] == AGENT
    assert KEY not in json.dumps(headers)
    assert headers["Authorization"] != creds.headers()["Authorization"], "fresh token per request"


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({b.ENV_SIGNING_KEYS: json.dumps({AGENT: KEY, "cursor": KEY})}, "exactly the signing key"),
        ({b.ENV_SIGNING_KEYS: json.dumps({"cursor": KEY})}, "exactly the signing key"),
        ({b.ENV_SIGNING_KEYS: json.dumps({AGENT: "short"})}, "too short"),
        ({b.ENV_IDENTITY: "{}"}, "no sealed identity"),
        ({b.ENV_IDENTITY: json.dumps(identity("cursor"))}, "not the authenticated agent"),
        ({b.ENV_SIGNING_KEYS: "not json"}, "malformed"),
    ],
)
def test_bad_door_material_is_refused(overrides: dict[str, str], reason: str) -> None:
    with pytest.raises(b.RemoteBindingError, match=reason):
        b.credentials_from_env(_door(**overrides), 300)


def test_an_unsealed_identity_is_refused() -> None:
    unsealed = {**identity(), "assertion_digest": "sha256:" + "0" * 64}
    with pytest.raises(b.RemoteBindingError, match="not sealed"):
        b.Credentials(AGENT, KEY, unsealed, 300)


def test_the_human_principal_is_refused() -> None:
    with pytest.raises(b.RemoteBindingError, match="human principal"):
        b.Credentials("human", KEY, identity("human"), 300)


# --- relay ------------------------------------------------------------------


class Reply:
    def __init__(self, status: int, body: bytes, ctype: str = "application/json") -> None:
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = ctype
        self._body = body

    def read(self) -> bytes:
        return self._body


class FakeSend:
    """Scripted transport: a list of replies or HTTP status codes."""

    def __init__(self, *script: Any) -> None:
        self.script = list(script)
        self.requests: list[Any] = []
        self.kwargs: list[dict[str, Any]] = []

    def __call__(self, request: Any, **kwargs: Any) -> Reply:
        self.requests.append(request)
        self.kwargs.append(kwargs)
        step = self.script.pop(0)
        if isinstance(step, int):
            headers = Message()
            headers["Content-Type"] = "application/json"
            body = json.dumps({"jsonrpc": "2.0", "error": {"code": -32001, "message": "no"}})
            raise urllib.error.HTTPError(
                request.full_url, step, "refused", headers, io.BytesIO(body.encode())
            )
        return step


def _bridge(
    send: FakeSend, endpoint: str = "https://memory.example.org/mcp"
) -> tuple[b.RemoteBridge, io.StringIO]:
    out = io.StringIO()
    bridge = b.RemoteBridge(
        endpoint,
        b.Credentials(AGENT, KEY, identity(), 300),
        protocol_versions=["2025-11-25", "2025-06-18"],
        send=send,
        out=out,
    )
    return bridge, out


def _ok(result: Any, request_id: Any = 1) -> Reply:
    return Reply(200, json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}).encode())


def _capabilities(**overrides: str) -> Reply:
    caps = {
        "package_version": "3.0.0",
        "contract_version": "memory-control-plane/v1",
        "remote_mcp_contract_version": "memory-remote-mcp/v1",
        **overrides,
    }
    return _ok({"content": [{"type": "text", "text": json.dumps(caps)}]}, "l9-bridge-capabilities")


def test_every_request_is_signed_and_pinned_to_one_host() -> None:
    send = FakeSend(_ok({"protocolVersion": "2025-11-25"}), _ok({"tools": []}, 2))
    bridge, out = _bridge(send)
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
    first, second = (dict(request.header_items()) for request in send.requests)
    for headers in (first, second):
        assert headers["Authorization"].startswith(f"Bearer {AGENT}.")
        assert "L9-identity-assertion" in headers
        assert not any("grant" in key.lower() or "door" in key.lower() for key in headers)
    assert "Mcp-protocol-version" not in first
    assert second["Mcp-protocol-version"] == "2025-11-25"
    assert first["Authorization"] != second["Authorization"]
    assert {kw["allowed_https_hosts"] for kw in send.kwargs} == {frozenset({"memory.example.org"})}
    assert all(kw["allow_loopback_http"] is False for kw in send.kwargs)
    assert len(out.getvalue().splitlines()) == 2


def test_a_401_is_reminted_once_then_reported_without_fallback() -> None:
    send = FakeSend(401, _ok({"tools": []}, 7))
    bridge, out = _bridge(send)
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/list"}))
    assert json.loads(out.getvalue())["result"] == {"tools": []}

    send = FakeSend(401, 401)
    bridge, out = _bridge(send)
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 8, "method": "tools/list"}))
    reply = json.loads(out.getvalue())
    assert reply["id"] == 8
    assert reply["error"]["code"] == b.AUTH_REFUSED
    assert "no fallback backend" in reply["error"]["message"]
    assert len(send.requests) == 2


def test_an_idless_refusal_answers_the_callers_id() -> None:
    body = json.dumps({"jsonrpc": "2.0", "error": {"code": -32600, "message": "bad"}}).encode()
    bridge, out = _bridge(FakeSend(Reply(400, body)))
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": "x", "method": "tools/list"}))
    assert json.loads(out.getvalue()) == {
        "jsonrpc": "2.0",
        "error": {"code": -32600, "message": "bad"},
        "id": "x",
    }


def test_a_response_echoing_the_key_is_withheld() -> None:
    leak = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"echo": KEY}}).encode()
    bridge, out = _bridge(FakeSend(Reply(200, leak)))
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}))
    reply = json.loads(out.getvalue())
    assert KEY not in out.getvalue()
    assert reply["error"]["code"] == b.UNAVAILABLE


def test_an_unreachable_service_is_an_error_not_a_fallback() -> None:
    class Down:
        def __call__(self, *_a: Any, **_k: Any) -> Any:
            raise urllib.error.URLError("connection refused")

    bridge, out = _bridge(Down())  # type: ignore[arg-type]
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}))
    reply = json.loads(out.getvalue())
    assert reply["id"] == 3
    assert "no fallback backend" in reply["error"]["message"]


def test_notifications_and_sse_are_relayed() -> None:
    sse = b'event: message\ndata: {"jsonrpc":"2.0","id":4,"result":{}}\n\n'
    bridge, out = _bridge(FakeSend(Reply(202, b""), Reply(200, sse, "text/event-stream")))
    bridge.forward(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
    assert out.getvalue() == ""
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 4, "method": "ping"}))
    assert json.loads(out.getvalue()) == {"jsonrpc": "2.0", "id": 4, "result": {}}


def test_the_service_must_prove_the_bound_release() -> None:
    bridge, _ = _bridge(
        FakeSend(
            _ok({"protocolVersion": "2025-11-25"}, "l9-bridge-init"),
            Reply(202, b""),
            _capabilities(),
        )
    )
    assert bridge.verify_service("3.0.0")["package_version"] == "3.0.0"
    for drift in (
        {"package_version": "3.0.1"},
        {"contract_version": "memory-control-plane/v2"},
        {"remote_mcp_contract_version": "memory-remote-mcp/v2"},
    ):
        bridge, _ = _bridge(
            FakeSend(
                _ok({"protocolVersion": "2025-11-25"}, "l9-bridge-init"),
                Reply(202, b""),
                _capabilities(**drift),
            )
        )
        with pytest.raises(b.RemoteBindingError, match="not the bound release"):
            bridge.verify_service("3.0.0")


def test_an_unsupported_protocol_revision_is_refused() -> None:
    bridge, _ = _bridge(FakeSend(_ok({"protocolVersion": "2024-11-05"}, "l9-bridge-init")))
    with pytest.raises(b.RemoteBindingError, match="negotiated MCP revision"):
        bridge.verify_service("3.0.0")


def test_refused_authentication_at_start_raises() -> None:
    bridge, _ = _bridge(FakeSend(401, 401))
    with pytest.raises(b.AuthenticationRefused):
        bridge.verify_service("3.0.0")


def test_check_mode_reports_local_without_an_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(b.ENV_ENDPOINT, raising=False)
    monkeypatch.delenv(b.ENV_CONFIG, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert b.main(["--check"]) == 0
    assert capsys.readouterr().out.strip() == "local"


def test_check_mode_refuses_an_unadmitted_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(b.ENV_CANDIDATE, raising=False)
    monkeypatch.setenv(b.ENV_ENDPOINT, "https://memory.example.org/mcp")
    assert b.main(["--check"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no fallback backend" in captured.err


def test_the_bridge_imports_no_provider_or_third_party_transport() -> None:
    source = (REPO_ROOT / "ops" / "memory_remote" / "bridge.py").read_text(encoding="utf-8")
    for forbidden in ("graphiti_core", "neo4j", "requests", "httpx", "aiohttp", "import mcp"):
        assert forbidden not in source, forbidden


@pytest.mark.parametrize(
    "reply",
    [
        Reply(200, b"not json"),
        Reply(200, b"[1, 2]"),
        Reply(200, b""),
        Reply(200, b"event: message\n\n", "text/event-stream"),
    ],
)
def test_a_request_never_goes_unanswered(reply: Reply) -> None:
    """A malformed or empty 2xx still answers the caller's id (no host-side timeout)."""
    bridge, out = _bridge(FakeSend(reply))
    bridge.forward(json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list"}))
    answer = json.loads(out.getvalue())
    assert answer["id"] == 9
    assert answer["error"]["code"] == b.UNAVAILABLE
    assert "no fallback backend" in answer["error"]["message"]


def test_startup_completes_the_mcp_lifecycle_before_any_request() -> None:
    send = FakeSend(
        _ok({"protocolVersion": "2025-11-25"}, "l9-bridge-init"),
        Reply(202, b""),
        _capabilities(),
    )
    bridge, _ = _bridge(send)
    bridge.verify_service("3.0.0")
    methods = [json.loads(request.data)["method"] for request in send.requests]
    assert methods == ["initialize", "notifications/initialized", "tools/call"]
