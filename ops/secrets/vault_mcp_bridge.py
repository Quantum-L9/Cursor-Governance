#!/usr/bin/env python3
"""stdio MCP bridge to a remote MCP server whose credential lives in Infisical.

A remote MCP server that needs an API key (Context7) used to be declared as an
HTTP server with ``Authorization: Bearer ${KEY}``: Claude Code expands the
variable from its own environment at load, so the key had to be in the
environment — where nothing put it, and where it would be readable anyway. This
bridge is declared instead as a local stdio server. It binds the key from
Infisical in-process (``capability_bind``, as this surface's machine identity),
forwards each JSON-RPC message to the one allow-listed upstream over HTTPS, and
writes the upstream's messages back on stdout. The key never enters the
environment, argv, a file or a log.

Bridges are declared in ``vault-mcp-bridges.json`` (name -> url, secret, header,
format). Only the declared host is contacted, redirects are never followed
(``safe_https``), and an upstream response that echoes the key is withheld.
stdout is the MCP channel: diagnostics go to stderr only.

Usage (from .mcp.json): run_vault_mcp_bridge.sh <name>
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
for _path in (HERE, HERE.parent / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import capability_bind as cb  # noqa: E402
from safe_https import https_exchange  # noqa: E402

REGISTRY = HERE / "vault-mcp-bridges.json"
TIMEOUT = 120.0
UPSTREAM_ERROR = -32000


class BridgeError(RuntimeError):
    """The bridge cannot serve (unknown bridge, unbound key, bad registry)."""


def load_bridge(name: str, registry: Path = REGISTRY) -> dict[str, str]:
    data = json.loads(registry.read_text(encoding="utf-8"))
    entry = (data.get("bridges") or {}).get(name)
    if not isinstance(entry, dict):
        raise BridgeError(f"no bridge named {name!r} in {registry.name}")
    for key in ("url", "secret", "header", "format"):
        if not isinstance(entry.get(key), str) or not entry[key]:
            raise BridgeError(f"bridge {name!r} lacks {key!r}")
    if urlparse(entry["url"]).scheme != "https" or "{value}" not in entry["format"]:
        raise BridgeError(f"bridge {name!r} must be https and format must contain {{value}}")
    return {k: entry[k] for k in ("url", "secret", "header", "format")}


def sse_messages(body: bytes) -> list[str]:
    """JSON-RPC messages from a text/event-stream body (one per event)."""
    messages: list[str] = []
    data: list[str] = []
    for line in body.decode("utf-8", errors="replace").splitlines():
        if line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        elif not line.strip() and data:
            messages.append("\n".join(data))
            data = []
    if data:
        messages.append("\n".join(data))
    return messages


class Bridge:
    def __init__(self, config: dict[str, str], key: str, *, send: Any = None) -> None:
        self.url = config["url"]
        self.host = frozenset({(urlparse(self.url).hostname or "").lower()})
        self.header = config["header"]
        self.header_value = config["format"].replace("{value}", key)
        self._key = key
        self._send = send or https_exchange
        self._session = ""
        self._protocol = ""
        self._out = threading.Lock()

    def emit(self, message: str) -> None:
        with self._out:
            sys.stdout.write(message.strip() + "\n")
            sys.stdout.flush()

    def _error(self, request_id: Any, text: str) -> None:
        if request_id is None:
            return
        error = {"code": UPSTREAM_ERROR, "message": text}
        self.emit(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": error}))

    def forward(self, line: str) -> None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return
        request_id = message.get("id") if isinstance(message, dict) else None
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            self.header: self.header_value,
        }
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        if self._protocol:
            headers["MCP-Protocol-Version"] = self._protocol
        request = urllib.request.Request(
            self.url, data=line.encode("utf-8"), method="POST", headers=headers
        )
        try:
            response = self._send(request, timeout=TIMEOUT, allowed_hosts=self.host, label="bridge")
        except urllib.error.HTTPError as exc:
            self._error(request_id, f"upstream HTTP {exc.code}")
            return
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self._error(request_id, f"upstream unreachable ({type(exc).__name__})")
            return
        session = response.headers.get("Mcp-Session-Id") or ""
        if session:
            self._session = session.strip()
        body = response.read()
        if not body:
            return  # 202 for a notification
        if self._key and self._key.encode() in body:
            self._error(request_id, "upstream response withheld: it contained the credential")
            return
        ctype = (response.headers.get("Content-Type") or "").lower()
        texts = sse_messages(body) if "text/event-stream" in ctype else [body.decode("utf-8")]
        for text in texts:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            result = parsed.get("result") if isinstance(parsed, dict) else None
            if isinstance(result, dict) and isinstance(result.get("protocolVersion"), str):
                self._protocol = result["protocolVersion"]
            self.emit(json.dumps(parsed))

    def serve(self, stream: Any = None) -> None:
        threads: list[threading.Thread] = []
        for raw in stream or sys.stdin:
            line = raw.strip()
            if not line:
                continue
            if '"initialize"' in line and not self._session:
                self.forward(line)  # the session id must exist before anything else
                continue
            thread = threading.Thread(target=self.forward, args=(line,), daemon=True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join(timeout=TIMEOUT)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: vault_mcp_bridge.py <bridge-name>", file=sys.stderr)
        return 2
    try:
        config = load_bridge(args[0])
    except (BridgeError, OSError, json.JSONDecodeError) as exc:
        print(f"vault_mcp_bridge: {exc}", file=sys.stderr)
        return 2
    key = cb.bind(config["secret"])
    if not key:
        source = cb.bind_status(config["secret"])["source"]
        print(
            f"vault_mcp_bridge: {config['secret']} is not bound (source={source}) — the "
            f"{args[0]} MCP server cannot start. It is bound from Infisical as this "
            "surface's machine identity: set L9_INFISICAL_CLIENT_ID and "
            "L9_INFISICAL_CLIENT_SECRET in the environment settings.",
            file=sys.stderr,
        )
        return 1
    Bridge(config, key).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
