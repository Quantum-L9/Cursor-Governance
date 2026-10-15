"""Consumer interoperability against a real Memory 3.0.0 release candidate (ADR-0053).

Every positive case drives the full consumer path: ``ops/memory/run_memory_mcp.sh``
(host-derived identity, door minted from local maps), then
``ops/memory_remote/bridge.py``, then a real ``l9-graphite-memory`` server process on
loopback in ``signed-agent`` mode. Nothing is mocked on either side of the socket.

Skip condition (rule 95 exception, narrow and external): the candidate runtime is
not the governance venv's pinned 2.6.0, so these cases need an interpreter with the
candidate wheel and its ``[server]`` extra installed, named by
``L9_MEMORY_REMOTE_CANDIDATE_PYTHON``. A fixture cannot stand in, because the point is
the real server's verifier. Removal trigger: when ``ops/config/memory-remote-binding.json``
binds an admitted 3.x release and the governance venv carries it, these run
unconditionally. The PostgreSQL restart and tenant cases additionally need
``L9_MEMORY_REMOTE_CANDIDATE_POSTGRES_DSN`` (a disposable cluster). Unrelated failures
are not hidden: the skips are module- and case-scoped to those two variables only.

Exact bytes. A run qualifies one exact wheel, never "a candidate". With a candidate
interpreter supplied, ``L9_MEMORY_REMOTE_CANDIDATE_WHEEL_SHA256`` must name the wheel's
digest, and ``test_the_installed_candidate_is_the_declared_wheel`` FAILS unless the
installed distribution's PEP 610 record proves it came from exactly those bytes and
reports the binding's candidate version. ``L9_MEMORY_REMOTE_CANDIDATE_SOURCE_SHA`` names
the source revision the wheel was built from. The wheel is reproducible under
``SOURCE_DATE_EPOCH`` (memory ``scripts/validate_release.sh``), so that link is
re-derivable by rebuilding. Results against one revision never qualify another.

This does not certify a hosted deployment, Cursor or Claude Code Mobile UI clients, or
TLS. Those stay deployment-acceptance obligations (ADR-0053).
"""

from __future__ import annotations

import json
import os
import queue
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPO_ROOT / "ops" / "memory" / "run_memory_mcp.sh"
CANDIDATE_PY = os.environ.get("L9_MEMORY_REMOTE_CANDIDATE_PYTHON", "").strip()
POSTGRES_DSN = os.environ.get("L9_MEMORY_REMOTE_CANDIDATE_POSTGRES_DSN", "").strip()
CANDIDATE_WHEEL_SHA256 = os.environ.get("L9_MEMORY_REMOTE_CANDIDATE_WHEEL_SHA256", "").strip()
CANDIDATE_SOURCE_SHA = os.environ.get("L9_MEMORY_REMOTE_CANDIDATE_SOURCE_SHA", "").strip()

pytestmark = pytest.mark.skipif(
    not CANDIDATE_PY or not Path(CANDIDATE_PY).is_file(),
    reason="L9_MEMORY_REMOTE_CANDIDATE_PYTHON names no Memory 3.0.0 candidate interpreter",
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.memory.agent_assertion import (  # noqa: E402
    build_agent_mcp_env,
    identity_assertion_hmac,
    mint_assertion,
    seal_identity_assertion,
)

CLAUDE = "claude-code"
CURSOR = "cursor"
SHARED = "interop-shared"
CLAUDE_HOME = "interop-claude-only"
PROTOCOL = "2025-11-25"
QUALIFICATION = "consumer interop qualification against release candidate #96"
HOST_MARKERS = {
    CLAUDE: {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli"},
    CURSOR: {"CURSOR_AGENT": "1"},
}
GRANTS = {
    CLAUDE: {
        "roles": ["implementer", "memory-client"],
        "read_namespaces": [SHARED, CLAUDE_HOME],
        "write_namespaces": [SHARED, CLAUDE_HOME],
        "promote_namespaces": [],
        "is_admin": False,
    },
    CURSOR: {
        "roles": ["reviewer", "memory-client"],
        "read_namespaces": [SHARED],
        "write_namespaces": [SHARED],
        "promote_namespaces": [],
        "is_admin": False,
    },
}


# ---------------------------------------------------------------------------
# Candidate server
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Server:
    def __init__(self, process: subprocess.Popen[bytes], base: str, log: Path) -> None:
        self.process = process
        self.base = base
        self.log = log

    @property
    def endpoint(self) -> str:
        return f"{self.base}/mcp"

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


def _server_env(
    workdir: Path,
    keys: dict[str, str],
    grants: dict[str, Any],
    *,
    tenant: str,
    dsn: str | None,
) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(workdir / "home"),
        "L9_MEMORY_DATA_DIR": str(workdir / "data"),
        "L9_MEMORY_STATE_DIR": str(workdir / "state"),
        "L9_MEMORY_PROJECTION_BACKEND": "none",
        "L9_MEMORY_JSON_LOGS": "0",
        "L9_MEMORY_HTTP_AUTH_MODE": "signed-agent",
        "L9_MEMORY_LOCAL_TENANT_ID": tenant,
        "L9_MEMORY_AGENT_SIGNING_KEYS_JSON": json.dumps(keys),
        "L9_MEMORY_AGENT_GRANTS_JSON": json.dumps(grants),
        # A human door on the server must still be unreachable over HTTP.
        "L9_MEMORY_HUMAN_DOOR_SECRET": secrets.token_hex(32),
    }
    if dsn:
        env["L9_MEMORY_STORE_BACKEND"] = "postgres"
        env["L9_MEMORY_POSTGRES_DSN"] = dsn
    return env


def start_server(
    tmp_path: Path,
    keys: dict[str, str],
    grants: dict[str, Any] | None = None,
    *,
    tenant: str = "l9",
    dsn: str | None = None,
    wait: bool = True,
) -> Server:
    port = _free_port()
    workdir = tmp_path / f"server-{port}"
    workdir.mkdir(parents=True)
    log = workdir / "server.log"
    process = subprocess.Popen(
        [
            CANDIDATE_PY,
            "-m",
            "l9_graphite_memory.server",
            "--transport",
            "http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=workdir,
        env=_server_env(workdir, keys, grants or GRANTS, tenant=tenant, dsn=dsn),
        stdout=subprocess.DEVNULL,
        stderr=log.open("wb"),
    )
    server = Server(process, f"http://127.0.0.1:{port}", log)
    if not wait:
        return server
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"candidate server exited: {log.read_text()[-2000:]}")
        try:
            with urllib.request.urlopen(f"{server.base}/healthz", timeout=2):  # noqa: S310
                return server
        except urllib.error.HTTPError:
            return server  # 503 is still an answer
        except OSError:
            time.sleep(0.2)
    server.stop()
    raise RuntimeError(f"candidate server never answered: {log.read_text()[-2000:]}")


@pytest.fixture()
def keys() -> dict[str, str]:
    return {CLAUDE: secrets.token_hex(32), CURSOR: secrets.token_hex(32)}


@pytest.fixture()
def server(tmp_path: Path, keys: dict[str, str]) -> Iterator[Server]:
    running = start_server(tmp_path, keys)
    try:
        yield running
    finally:
        running.stop()


# ---------------------------------------------------------------------------
# Consumer: the real wrapper, driven as an MCP host would
# ---------------------------------------------------------------------------


def _agent_home(tmp_path: Path, agent: str, key: str) -> Path:
    home = tmp_path / f"home-{agent}-{secrets.token_hex(4)}"
    config = home / ".config" / "l9-memory"
    config.mkdir(parents=True)
    (config / "agent_tokens.local.json").write_text(
        json.dumps(
            {"agents_door_secret": secrets.token_hex(32), "agent_signing_keys": {agent: key}}
        ),
        encoding="utf-8",
    )
    (config / "agent_grants.json").write_text(json.dumps({agent: GRANTS[agent]}), encoding="utf-8")
    return home


def consumer_env(
    tmp_path: Path, agent: str, key: str, endpoint: str, **extra: str
) -> dict[str, str]:
    home = _agent_home(tmp_path, agent, key)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(home),
        "L9_GOVERNANCE_DIR": str(REPO_ROOT),
        "L9_MEMORY_REMOTE_MCP_ENDPOINT": endpoint,
        "L9_MEMORY_REMOTE_CANDIDATE_QUALIFICATION": QUALIFICATION,
        **HOST_MARKERS[agent],
    }
    env.update(extra)
    return env


class McpHost:
    """A minimal MCP host: one stdio child, JSON-RPC lines, ids matched."""

    def __init__(self, env: dict[str, str]) -> None:
        self.process = subprocess.Popen(
            ["bash", str(WRAPPER), "-m", "l9_graphite_memory.server", "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=env["HOME"],
            text=True,
        )
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._ids = 0
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ids += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": self._ids, "method": method}
        if params is not None:
            message["params"] = params
        self._send(message)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                line = self._lines.get(timeout=1)
            except queue.Empty:
                continue
            if line is None:
                raise AssertionError(f"consumer exited: {self.stderr()}")
            reply = json.loads(line)
            if reply.get("id") == self._ids:
                return reply
        raise AssertionError(f"no reply to {method}: {self.stderr()}")

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def _send(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def initialize(self) -> dict[str, Any]:
        reply = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL,
                "capabilities": {},
                "clientInfo": {"name": "interop-host", "version": "1"},
            },
        )
        self.notify("notifications/initialized")
        return reply

    def tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def stderr(self) -> str:
        if self.process.poll() is None:
            return "<running>"
        assert self.process.stderr is not None
        return self.process.stderr.read()

    def close(self) -> tuple[int, str]:
        if self.process.stdin is not None:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        assert self.process.stderr is not None
        return self.process.returncode, self.process.stderr.read()


def payload(reply: dict[str, Any]) -> dict[str, Any]:
    assert "result" in reply, reply
    return dict(json.loads(reply["result"]["content"][0]["text"]))


def run_refused(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(WRAPPER)],
        input="",
        capture_output=True,
        text=True,
        env=env,
        cwd=env["HOME"],
        check=False,
        timeout=90,
    )


def write(host: McpHost, namespace: str, content: str, agent: str) -> dict[str, Any]:
    return payload(
        host.tool(
            "memory.write_agent",
            {
                "namespace": namespace,
                "content": content,
                "memory_class": "observation",
                "tags": [f"agent:{agent}", "remote-interop"],
                "idempotency_key": f"agent:{namespace}:{secrets.token_hex(8)}",
            },
        )
    )


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------


def test_the_installed_candidate_is_the_declared_wheel() -> None:
    """F3: qualify exact bytes. The PEP 610 record must name the declared digest."""
    assert re.fullmatch(r"[0-9a-f]{64}", CANDIDATE_WHEEL_SHA256), (
        "L9_MEMORY_REMOTE_CANDIDATE_WHEEL_SHA256 must name the exact wheel under test"
    )
    assert re.fullmatch(r"[0-9a-f]{40}", CANDIDATE_SOURCE_SHA), (
        "L9_MEMORY_REMOTE_CANDIDATE_SOURCE_SHA must name the exact source revision"
    )
    probe = (
        "import json, importlib.metadata as md\n"
        "d = md.distribution('l9-graphite-memory')\n"
        "import l9_graphite_memory.version as v\n"
        "print(json.dumps({'version': d.version, 'module_version': v.PACKAGE_VERSION,"
        " 'remote': v.REMOTE_MCP_CONTRACT_VERSION,"
        " 'direct_url': json.loads(d.read_text('direct_url.json') or '{}')}))\n"
    )
    out = subprocess.run(
        [CANDIDATE_PY, "-I", "-c", probe], capture_output=True, text=True, check=True, timeout=60
    )
    installed = json.loads(out.stdout)
    hashes = installed["direct_url"].get("archive_info", {}).get("hashes", {})
    assert hashes.get("sha256") == CANDIDATE_WHEEL_SHA256, installed["direct_url"]
    binding = json.loads(
        (REPO_ROOT / "ops" / "config" / "memory-remote-binding.json").read_text(encoding="utf-8")
    )
    expected_version = binding["candidate"]["version"]
    assert installed["version"] == installed["module_version"] == expected_version
    assert installed["remote"] == "memory-remote-mcp/v1"


def test_both_agents_authenticate_through_the_real_consumer_path(
    tmp_path: Path, server: Server, keys: dict[str, str]
) -> None:
    for agent in (CLAUDE, CURSOR):
        host = McpHost(consumer_env(tmp_path, agent, keys[agent], server.endpoint))
        try:
            init = host.initialize()
            assert init["result"]["protocolVersion"] == PROTOCOL
            assert init["result"]["serverInfo"]["name"] == "l9-graphite-memory"
            tools = {tool["name"] for tool in host.request("tools/list")["result"]["tools"]}
            assert {"memory.write_agent", "memory.phase_lock", "memory.write_governed"} <= tools
            capabilities = payload(host.tool("memory.capabilities", {}))
            assert capabilities["contract_version"] == "memory-control-plane/v1"
            assert capabilities["remote_mcp_contract_version"] == "memory-remote-mcp/v1"
        finally:
            code, stderr = host.close()
        assert code == 0, stderr
        assert f"memory_remote: {agent} -> memory-remote-mcp/v1" in stderr


def test_one_agent_writes_and_the_other_reads_with_authorship_preserved(
    tmp_path: Path, server: Server, keys: dict[str, str]
) -> None:
    writer = McpHost(consumer_env(tmp_path, CLAUDE, keys[CLAUDE], server.endpoint))
    reader = McpHost(consumer_env(tmp_path, CURSOR, keys[CURSOR], server.endpoint))
    try:
        writer.initialize()
        reader.initialize()
        receipt = write(writer, SHARED, "heron fishes the eastern reservoir", CLAUDE)
        assert receipt["status"] == "admitted", receipt
        assert receipt["authorization"]["principal_id"] == CLAUDE
        found = payload(reader.tool("memory.search", {"query": "heron", "namespaces": [SHARED]}))
        assert found["namespaces_authorized"] == [SHARED]
        hits = {item["record"]["record_id"]: item["record"] for item in found["hits"]}
        assert receipt["record_id"] in hits
        stored = payload(reader.tool("memory.get", {"record_id": receipt["record_id"]}))
        assert stored["record"]["provenance"]["source_agent_id"] == CLAUDE
    finally:
        writer.close()
        reader.close()


def test_each_agent_receives_only_its_own_grants(
    tmp_path: Path, server: Server, keys: dict[str, str]
) -> None:
    claude = McpHost(consumer_env(tmp_path, CLAUDE, keys[CLAUDE], server.endpoint))
    cursor = McpHost(consumer_env(tmp_path, CURSOR, keys[CURSOR], server.endpoint))
    try:
        claude.initialize()
        cursor.initialize()
        own = write(claude, CLAUDE_HOME, "claude-only note on the quarry", CLAUDE)
        assert own["status"] == "admitted", own
        refused = write(cursor, CLAUDE_HOME, "cursor must not write here", CURSOR)
        assert refused["status"] == "rejected", refused
        assert refused["authorization"]["allowed"] is False
        unreadable = cursor.tool("memory.search", {"query": "quarry", "namespaces": [CLAUDE_HOME]})
        assert unreadable["error"]["code"] == -32010, unreadable
        assert "not authorized to read" in unreadable["error"]["message"]
    finally:
        claude.close()
        cursor.close()


def test_the_remote_operation_contract_matches_the_candidate_stdio_server(
    tmp_path: Path, server: Server, keys: dict[str, str]
) -> None:
    """Tool definitions and the write receipt shape are transport-invariant."""

    host = McpHost(consumer_env(tmp_path, CLAUDE, keys[CLAUDE], server.endpoint))
    try:
        host.initialize()
        remote_tools = host.request("tools/list")["result"]["tools"]
        remote_receipt = write(host, SHARED, "swift over the lock gates", CLAUDE)
    finally:
        host.close()

    sys.path.insert(0, str(REPO_ROOT))
    from ops.memory.print_agent_assertion_env import build_runtime_identity_assertion

    identity = build_runtime_identity_assertion(HOST_MARKERS[CLAUDE], root=REPO_ROOT)
    door = build_agent_mcp_env(
        agent_id=CLAUDE,
        agents_door_secret=secrets.token_hex(32),
        signing_key=keys[CLAUDE],
        grants=GRANTS,
        identity_assertion=identity,
    )
    workdir = tmp_path / "stdio"
    workdir.mkdir()
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(workdir),
        "L9_MEMORY_DATA_DIR": str(workdir / "data"),
        "L9_MEMORY_STATE_DIR": str(workdir / "state"),
        "L9_MEMORY_PROJECTION_BACKEND": "none",
        **door,
    }
    stdio = subprocess.Popen(
        [CANDIDATE_PY, "-m", "l9_graphite_memory.server", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=workdir,
        text=True,
    )
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "memory.write_agent",
                "arguments": {
                    "namespace": SHARED,
                    "content": "swift over the lock gates",
                    "memory_class": "observation",
                    "tags": [f"agent:{CLAUDE}", "remote-interop"],
                    "idempotency_key": f"agent:{SHARED}:stdio-parity",
                },
            },
        },
    ]
    out, err = stdio.communicate("".join(json.dumps(m) + "\n" for m in messages), timeout=90)
    replies = {reply["id"]: reply for reply in map(json.loads, out.splitlines()) if "id" in reply}
    assert 3 in replies, err[-2000:]
    assert replies[2]["result"]["tools"] == remote_tools
    stdio_receipt = payload(replies[3])
    assert stdio_receipt["status"] == "admitted", stdio_receipt
    assert set(stdio_receipt) == set(remote_receipt)


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------


def _raw_post(endpoint: str, headers: dict[str, str]) -> int:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL,
            **headers,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _identity_headers(agent: str, key: str, *, actor: str | None = None) -> dict[str, str]:
    from ops.memory.print_agent_assertion_env import build_runtime_identity_assertion

    identity = build_runtime_identity_assertion(HOST_MARKERS[actor or agent], root=REPO_ROOT)
    import base64

    sealed = seal_identity_assertion(identity)
    raw = json.dumps(sealed, separators=(",", ":"), ensure_ascii=False).encode()
    return {
        "L9-Identity-Assertion": base64.urlsafe_b64encode(raw).decode().rstrip("="),
        "L9-Identity-Assertion-HMAC": identity_assertion_hmac(str(sealed["assertion_digest"]), key),
    }


def test_missing_credential_is_refused(server: Server) -> None:
    assert _raw_post(server.endpoint, {}) == 401


def test_expired_assertion_is_refused(server: Server, keys: dict[str, str]) -> None:
    token = mint_assertion(CLAUDE, keys[CLAUDE], ttl_seconds=-300)
    headers = {"Authorization": f"Bearer {token}", **_identity_headers(CLAUDE, keys[CLAUDE])}
    assert _raw_post(server.endpoint, headers) == 401
    fresh = mint_assertion(CLAUDE, keys[CLAUDE], ttl_seconds=120)
    headers["Authorization"] = f"Bearer {fresh}"
    assert _raw_post(server.endpoint, headers) == 200


def test_an_identity_assertion_for_another_actor_is_refused(
    server: Server, keys: dict[str, str]
) -> None:
    token = mint_assertion(CURSOR, keys[CURSOR], ttl_seconds=120)
    headers = {
        "Authorization": f"Bearer {token}",
        **_identity_headers(CURSOR, keys[CURSOR], actor=CLAUDE),
    }
    assert _raw_post(server.endpoint, headers) == 401


def test_an_invalid_signature_refuses_to_launch_without_fallback(
    tmp_path: Path, server: Server
) -> None:
    result = run_refused(consumer_env(tmp_path, CLAUDE, secrets.token_hex(32), server.endpoint))
    assert result.returncode == 1
    assert result.stdout == ""
    assert "refused authentication" in result.stderr
    assert "no fallback" in result.stderr


def test_an_unadmitted_release_refuses_to_launch(
    tmp_path: Path, server: Server, keys: dict[str, str]
) -> None:
    env = consumer_env(tmp_path, CLAUDE, keys[CLAUDE], server.endpoint)
    del env["L9_MEMORY_REMOTE_CANDIDATE_QUALIFICATION"]
    result = run_refused(env)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "remote memory transport requested but not admissible" in result.stderr


def test_a_retired_or_non_mcp_endpoint_refuses_to_launch(
    tmp_path: Path, server: Server, keys: dict[str, str]
) -> None:
    for endpoint in (f"{server.base}/memory", "http://127.0.0.1:9002/mcp", server.base):
        result = run_refused(consumer_env(tmp_path, CLAUDE, keys[CLAUDE], endpoint))
        assert result.returncode == 1, endpoint
        assert result.stdout == "", endpoint
    assert _raw_post(f"{server.base}/memory", {}) in {404, 405}


def test_the_human_principal_and_admin_grants_never_cross_http(
    tmp_path: Path, keys: dict[str, str]
) -> None:
    admin = {**GRANTS, CLAUDE: {**GRANTS[CLAUDE], "is_admin": True}}
    refused = start_server(tmp_path, keys, admin, wait=False)
    try:
        assert refused.process.wait(timeout=60) != 0
        assert "administrator authority is not reachable over HTTP" in refused.log.read_text()
    finally:
        refused.stop()
    human_grant = {**GRANTS[CURSOR], "is_admin": False}
    human = start_server(
        tmp_path,
        {**keys, "human": secrets.token_hex(32)},
        {**GRANTS, "human": human_grant},
        wait=False,
    )
    try:
        assert human.process.wait(timeout=60) != 0
        assert "the human door is not reachable over HTTP" in human.log.read_text()
    finally:
        human.stop()
    # The consumer refuses the human principal before any request is minted.
    from ops.memory_remote.bridge import Credentials, RemoteBindingError

    with pytest.raises(RemoteBindingError, match="human principal"):
        Credentials("human", keys[CLAUDE], {}, 120)


def test_a_drifted_service_identity_is_refused(server: Server, keys: dict[str, str]) -> None:
    from ops.memory.print_agent_assertion_env import build_runtime_identity_assertion
    from ops.memory_remote.bridge import Credentials, RemoteBindingError, RemoteBridge

    identity = build_runtime_identity_assertion(HOST_MARKERS[CLAUDE], root=REPO_ROOT)
    bridge = RemoteBridge(
        server.endpoint,
        Credentials(CLAUDE, keys[CLAUDE], identity, 120),
        protocol_versions=[PROTOCOL],
    )
    assert bridge.verify_service("3.0.0")["package_version"] == "3.0.0"
    with pytest.raises(RemoteBindingError, match="not the bound release"):
        bridge.verify_service("3.0.1")


# ---------------------------------------------------------------------------
# PostgreSQL: restart persistence and tenant isolation
# ---------------------------------------------------------------------------

needs_postgres = pytest.mark.skipif(
    not POSTGRES_DSN,
    reason="L9_MEMORY_REMOTE_CANDIDATE_POSTGRES_DSN names no disposable PostgreSQL",
)


def _schema_dsn(schema: str) -> str:
    return f"{POSTGRES_DSN} options=-csearch_path={schema}"


def _fresh_schema() -> str:
    schema = f"interop_{secrets.token_hex(6)}"
    subprocess.run(
        ["psql", POSTGRES_DSN, "-v", "ON_ERROR_STOP=1", "-c", f"CREATE SCHEMA {schema};"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return schema


@needs_postgres
def test_canonical_data_survives_a_service_restart_on_postgres(
    tmp_path: Path, keys: dict[str, str]
) -> None:
    dsn = _schema_dsn(_fresh_schema())
    first = start_server(tmp_path, keys, dsn=dsn)
    try:
        writer = McpHost(consumer_env(tmp_path, CLAUDE, keys[CLAUDE], first.endpoint))
        writer.initialize()
        receipt = write(writer, SHARED, "otter dens under the old mill", CLAUDE)
        writer.close()
        assert receipt["status"] == "admitted", receipt
    finally:
        first.stop()
    second = start_server(tmp_path, keys, dsn=dsn)
    try:
        reader = McpHost(consumer_env(tmp_path, CURSOR, keys[CURSOR], second.endpoint))
        reader.initialize()
        stored = payload(reader.tool("memory.get", {"record_id": receipt["record_id"]}))
        reader.close()
        assert stored["record"]["provenance"]["source_agent_id"] == CLAUDE
        assert stored["record"]["content"] == "otter dens under the old mill"
    finally:
        second.stop()


@needs_postgres
def test_a_wrong_tenant_never_sees_another_tenants_records(
    tmp_path: Path, keys: dict[str, str]
) -> None:
    dsn = _schema_dsn(_fresh_schema())
    home = start_server(tmp_path, keys, tenant="l9", dsn=dsn)
    other = start_server(tmp_path, keys, tenant="other-tenant", dsn=dsn)
    try:
        writer = McpHost(consumer_env(tmp_path, CLAUDE, keys[CLAUDE], home.endpoint))
        writer.initialize()
        receipt = write(writer, SHARED, "kingfisher on the weir", CLAUDE)
        same = payload(
            writer.tool("memory.search", {"query": "kingfisher", "namespaces": [SHARED]})
        )
        writer.close()
        assert receipt["status"] == "admitted", receipt
        # Positive control: the record is findable inside its own tenant.
        assert receipt["record_id"] in {item["record"]["record_id"] for item in same["hits"]}
        stranger = McpHost(consumer_env(tmp_path, CURSOR, keys[CURSOR], other.endpoint))
        stranger.initialize()
        found = payload(
            stranger.tool("memory.search", {"query": "kingfisher", "namespaces": [SHARED]})
        )
        fetched = stranger.tool("memory.get", {"record_id": receipt["record_id"]})
        stranger.close()
        assert receipt["record_id"] not in {item["record"]["record_id"] for item in found["hits"]}
        assert fetched["error"]["code"] == -32010, fetched
        assert "different tenant" in fetched["error"]["message"]
    finally:
        home.stop()
        other.stop()
