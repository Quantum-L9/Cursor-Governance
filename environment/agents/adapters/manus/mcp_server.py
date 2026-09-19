#!/usr/bin/env python3
"""Streamable-HTTP MCP server for the thin Manus governance adapter.

This service exposes a deliberately narrow control plane over the checked-out
L9 governance repository. It does not expose a shell, raw credentials, a
memory provider, or repository-writing tools. Manus continues to edit an
already-authorized workspace through its normal coding environment; this MCP
server makes the shared governance contract discoverable and invokes only the
existing shared bootstrap in an explicit diagnostic or apply mode.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import subprocess
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SERVER_NAME = "l9-governance"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_REQUEST_BYTES = 1_000_000
MAX_TOOL_OUTPUT_CHARS = 16_000
MAX_DOCUMENT_BYTES = 512_000
MAX_READ_LINES = 500
MAX_SEARCH_RESULTS = 50

ROOT_DOCUMENTS = {
    "AGENTS.md",
    "ARCHITECTURE.md",
    "CANONICAL_LAW.md",
    "INVARIANTS.md",
    "ORG_INVARIANTS.yaml",
    "README.md",
}
READABLE_PREFIXES = (
    "commands/",
    "docs/",
    "environment/agents/",
    "environment/contracts/",
    "environment/program-execution/",
    "governance/",
    "kernels/",
    "ops/autonomy/",
    "ops/config/",
    "rules/",
    "skills/",
)
DENIED_PARTS = {".git", ".venv", "__pycache__", "WIP", "ops/secrets", "ops/vendor"}
READABLE_SUFFIXES = {".json", ".md", ".mdc", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml"}


class ToolInputError(ValueError):
    """A caller supplied invalid tool input."""


def _truncate(text: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n… output truncated after {limit} characters"


def _text_content(value: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    serialized = json.dumps(value, indent=2, sort_keys=True)
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": _truncate(serialized)}],
        "structuredContent": value,
    }
    if is_error:
        result["isError"] = True
    return result


def _run(command: list[str], *, cwd: Path, timeout: int = 120) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"command": command, "status": "timed_out", "timeout_seconds": timeout}
    except OSError as exc:
        return {"command": command, "status": "execution_error", "error": str(exc)}
    return {
        "command": command,
        "status": "completed",
        "exit_code": completed.returncode,
        "stdout": _truncate(completed.stdout),
        "stderr": _truncate(completed.stderr),
    }


class GovernanceMcpService:
    """Implements the tool layer independently of the HTTP transport."""

    def __init__(
        self,
        governance_root: Path,
        *,
        bootstrap_enabled: bool = False,
        bootstrap_apply_enabled: bool = False,
    ) -> None:
        self.governance_root = governance_root.resolve()
        if not (self.governance_root / "CANONICAL_LAW.md").is_file():
            raise ValueError(f"not a Cursor-Governance checkout: {self.governance_root}")
        self.adapter_root = self.governance_root / "environment/agents/adapters/manus"
        self.bootstrap_enabled = bootstrap_enabled
        self.bootstrap_apply_enabled = bootstrap_apply_enabled

    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "governance_status",
                "description": (
                    "Read the L9 governance checkout status, Manus adapter contract status, and an "
                    "optional workspace Git summary. This tool never changes files."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": (
                                "Optional absolute path to a local Git workspace for a read-only "
                                "status summary."
                            ),
                        }
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "governance_validate",
                "description": (
                    "Run existing L9 structural validators for the Manus adapter. Mode 'full' also "
                    "validates the agent registry and Program Execution provider descriptor. "
                    "Validators are read-only."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["manus", "full"],
                            "description": "Validation scope. Defaults to manus.",
                        }
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "governance_bootstrap",
                "description": (
                    "Delegate an existing Git workspace to the shared L9 Manus bootstrap. "
                    "This tool requires a bearer-protected deployment because even diagnostic runs "
                    "write local readiness metadata. Apply mode also requires "
                    "--allow-bootstrap-apply and never installs credentials or changes remote "
                    "services."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Absolute path to the Git workspace to bootstrap.",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["check", "apply"],
                            "description": (
                                "Use check for diagnostic mode or apply to run the shared "
                                "bootstrap. "
                                "Defaults to check."
                            ),
                        },
                    },
                    "required": ["workspace"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "governance_read",
                "description": (
                    "Read a bounded text range from a governance policy, rule, skill, command, "
                    "adapter, or Program Execution file. Secret, vendor, Git, virtual-environment, "
                    "and WIP paths are blocked."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Repository-relative path to an allowed text file.",
                        },
                        "start_line": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "First line to return. Defaults to 1.",
                        },
                        "end_line": {
                            "type": "integer",
                            "minimum": 1,
                            "description": (
                                "Last line to return. Defaults to at most 500 lines after "
                                "start_line."
                            ),
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "governance_search",
                "description": (
                    "Search allowed governance text for a literal, case-insensitive query. "
                    "Returns bounded path, line, and excerpt results; it never searches secret "
                    "or Git paths."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "minLength": 2,
                            "maxLength": 160,
                            "description": "Literal text to search for.",
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Maximum number of matching lines. Defaults to 20.",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "governance_list_skills",
                "description": (
                    "List the active L9 skill packs and their short descriptions from the shared "
                    "governance checkout."
                ),
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        ]

    def _resolve_workspace(self, raw: Any) -> Path:
        if not isinstance(raw, str) or not raw.strip():
            raise ToolInputError("workspace must be a non-empty absolute path")
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ToolInputError("workspace must be an absolute path")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise ToolInputError(f"workspace is not accessible: {exc}") from exc
        if resolved == Path.home().resolve():
            raise ToolInputError("workspace must be a Git repository, not the home directory")
        if not (resolved / ".git").exists():
            probe = _run(
                ["git", "-C", str(resolved), "rev-parse", "--is-inside-work-tree"],
                cwd=self.governance_root,
            )
            if probe.get("exit_code") != 0:
                raise ToolInputError("workspace is not a Git work tree")
        return resolved

    def _allowed_path(self, raw: Any) -> Path:
        if not isinstance(raw, str) or not raw.strip():
            raise ToolInputError("path must be a non-empty repository-relative path")
        candidate = Path(raw)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ToolInputError("path must be repository-relative and may not traverse upward")
        relative = candidate.as_posix()
        if relative in ROOT_DOCUMENTS:
            allowed = True
        else:
            allowed = any(relative.startswith(prefix) for prefix in READABLE_PREFIXES)
        if not allowed:
            raise ToolInputError("path is outside the governance MCP read allowlist")
        if any(part in DENIED_PARTS for part in candidate.parts):
            raise ToolInputError("path is blocked by the governance MCP safety boundary")
        if candidate.suffix.lower() not in READABLE_SUFFIXES:
            raise ToolInputError("path is not an allowed text artifact")
        resolved = (self.governance_root / candidate).resolve()
        if self.governance_root not in resolved.parents or not resolved.is_file():
            raise ToolInputError(
                "path does not resolve to a readable file in the governance checkout"
            )
        if resolved.stat().st_size > MAX_DOCUMENT_BYTES:
            raise ToolInputError("file exceeds the governance MCP read limit")
        return resolved

    def _iter_searchable_files(self) -> list[Path]:
        files: list[Path] = []
        for root_document in ROOT_DOCUMENTS:
            candidate = self.governance_root / root_document
            if candidate.is_file():
                files.append(candidate)
        for prefix in READABLE_PREFIXES:
            base = self.governance_root / prefix.rstrip("/")
            if not base.is_dir():
                continue
            for candidate in base.rglob("*"):
                if not candidate.is_file() or candidate.suffix.lower() not in READABLE_SUFFIXES:
                    continue
                relative = candidate.relative_to(self.governance_root)
                if any(part in DENIED_PARTS for part in relative.parts):
                    continue
                if candidate.stat().st_size <= MAX_DOCUMENT_BYTES:
                    files.append(candidate)
        return sorted(set(files))

    def _adapter_contract_errors(self) -> list[str]:
        sys.path.insert(0, str(self.adapter_root))
        try:
            import validate_manus_adapter  # type: ignore[import-not-found]

            return validate_manus_adapter.validate(self.governance_root)
        finally:
            try:
                sys.path.remove(str(self.adapter_root))
            except ValueError:
                pass

    def status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        git_head = _run(["git", "rev-parse", "--short", "HEAD"], cwd=self.governance_root)
        git_branch = _run(["git", "status", "--porcelain=v1", "--branch"], cwd=self.governance_root)
        adapter_errors = self._adapter_contract_errors()
        result: dict[str, Any] = {
            "governance_root": str(self.governance_root),
            "governance_git_head": git_head.get("stdout", "").strip(),
            "governance_git_status": git_branch.get("stdout", "").strip(),
            "manus_adapter": {
                "status": "ready" if not adapter_errors else "invalid",
                "contract_errors": adapter_errors,
                "mcp_server": {"transport": "streamable-http", "endpoint": "/mcp"},
                "memory": "not exposed by this adapter",
                "bootstrap_enabled": self.bootstrap_enabled,
                "bootstrap_apply_enabled": self.bootstrap_apply_enabled,
            },
        }
        if "workspace" in arguments:
            if not self.bootstrap_enabled:
                raise ToolInputError("workspace status requires a bearer-protected MCP deployment")
            workspace = self._resolve_workspace(arguments["workspace"])
            workspace_status = _run(["git", "status", "--porcelain=v1", "--branch"], cwd=workspace)
            workspace_head = _run(["git", "rev-parse", "--short", "HEAD"], cwd=workspace)
            result["workspace"] = {
                "path": str(workspace),
                "git_head": workspace_head.get("stdout", "").strip(),
                "git_status": workspace_status.get("stdout", "").strip(),
            }
        return result

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        mode = arguments.get("mode", "manus")
        if mode not in {"manus", "full"}:
            raise ToolInputError("mode must be manus or full")
        commands = [
            [
                sys.executable,
                str(self.adapter_root / "validate_manus_adapter.py"),
                "--repo-root",
                str(self.governance_root),
            ]
        ]
        if mode == "full":
            commands.extend(
                [
                    [
                        sys.executable,
                        str(self.governance_root / "environment/agents/tools/validate_agents.py"),
                    ],
                    [
                        sys.executable,
                        str(
                            self.governance_root
                            / "environment/program-execution/scripts/validate_execution_adapters.py"
                        ),
                    ],
                ]
            )
        results = [_run(command, cwd=self.governance_root) for command in commands]
        passed = all(item.get("exit_code") == 0 for item in results)
        return {"mode": mode, "status": "passed" if passed else "failed", "checks": results}

    def bootstrap(self, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = self._resolve_workspace(arguments.get("workspace"))
        mode = arguments.get("mode", "check")
        if mode not in {"check", "apply"}:
            raise ToolInputError("mode must be check or apply")
        if not self.bootstrap_enabled:
            raise ToolInputError("governance bootstrap requires a bearer-protected MCP deployment")
        if mode == "apply" and not self.bootstrap_apply_enabled:
            raise ToolInputError(
                "bootstrap apply requires a bearer-protected MCP deployment with "
                "--allow-bootstrap-apply"
            )
        command = [
            "bash",
            str(self.adapter_root / "install.sh"),
            "--governance",
            str(self.governance_root),
            "--workspace",
            str(workspace),
            "--quiet",
        ]
        if mode == "check":
            command.append("--check")
        result = _run(command, cwd=self.governance_root, timeout=300)
        exit_code = result.get("exit_code")
        if exit_code == 0:
            status = "ready"
        elif exit_code == 6:
            status = "degraded"
        else:
            status = "blocked"
        return {"mode": mode, "workspace": str(workspace), "status": status, "bootstrap": result}

    def read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._allowed_path(arguments.get("path"))
        start_line = arguments.get("start_line", 1)
        end_line = arguments.get("end_line")
        if not isinstance(start_line, int) or start_line < 1:
            raise ToolInputError("start_line must be a positive integer")
        if end_line is not None and (not isinstance(end_line, int) or end_line < start_line):
            raise ToolInputError("end_line must be an integer greater than or equal to start_line")
        if end_line is None:
            end_line = start_line + MAX_READ_LINES - 1
        end_line = min(end_line, start_line + MAX_READ_LINES - 1)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = [
            f"{line_number}: {line}"
            for line_number, line in enumerate(lines[start_line - 1 : end_line], start=start_line)
        ]
        return {
            "path": path.relative_to(self.governance_root).as_posix(),
            "start_line": start_line,
            "end_line": min(end_line, len(lines)),
            "total_lines": len(lines),
            "content": "\n".join(selected),
        }

    def search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query")
        if not isinstance(query, str) or not 2 <= len(query.strip()) <= 160:
            raise ToolInputError("query must contain 2 to 160 characters")
        max_results = arguments.get("max_results", 20)
        if not isinstance(max_results, int) or not 1 <= max_results <= MAX_SEARCH_RESULTS:
            raise ToolInputError("max_results must be an integer between 1 and 50")
        needle = query.casefold()
        matches: list[dict[str, Any]] = []
        for path in self._iter_searchable_files():
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if needle in line.casefold():
                    matches.append(
                        {
                            "path": path.relative_to(self.governance_root).as_posix(),
                            "line": line_number,
                            "excerpt": line[:400],
                        }
                    )
                    if len(matches) >= max_results:
                        return {"query": query, "matches": matches, "truncated": True}
        return {"query": query, "matches": matches, "truncated": False}

    def list_skills(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        skills_root = self.governance_root / "skills"
        skills: list[dict[str, str]] = []
        for manifest in sorted(skills_root.glob("*/SKILL.md")):
            if manifest.parent.name.startswith("_"):
                continue
            description = ""
            for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines()[:30]:
                if line.startswith("description:"):
                    description = line.partition(":")[2].strip()
                    break
            skills.append({"name": manifest.parent.name, "description": description})
        return {"skills": skills, "count": len(skills)}

    def call_tool(self, name: str, arguments: Any) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            return _text_content({"error": "tool arguments must be an object"}, is_error=True)
        try:
            if name == "governance_status":
                return _text_content(self.status(arguments))
            if name == "governance_validate":
                return _text_content(self.validate(arguments))
            if name == "governance_bootstrap":
                return _text_content(self.bootstrap(arguments))
            if name == "governance_read":
                return _text_content(self.read(arguments))
            if name == "governance_search":
                return _text_content(self.search(arguments))
            if name == "governance_list_skills":
                return _text_content(self.list_skills(arguments))
            return _text_content({"error": f"unknown tool: {name}"}, is_error=True)
        except (OSError, ToolInputError, ValueError) as exc:
            return _text_content({"error": str(exc)}, is_error=True)

    def handle_rpc(self, payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return self._error(None, -32600, "request must be a JSON object")
        request_id = payload.get("id")
        if payload.get("jsonrpc") != "2.0" or not isinstance(payload.get("method"), str):
            return self._error(request_id, -32600, "invalid JSON-RPC request")
        method = payload["method"]
        params = payload.get("params", {})
        if not isinstance(params, dict):
            return self._error(request_id, -32602, "params must be an object")
        if method == "initialize":
            requested = params.get("protocolVersion")
            version = (
                requested
                if requested in SUPPORTED_PROTOCOL_VERSIONS
                else SUPPORTED_PROTOCOL_VERSIONS[0]
            )
            result: dict[str, Any] = {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Use this MCP server to inspect the shared L9 governance contract and run the "
                    "existing Manus bootstrap. It intentionally provides no memory provider, "
                    "credentials, shell, arbitrary file access, or repository-writing tool."
                ),
            }
            return self._result(request_id, result)
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return self._result(request_id, {"tools": self.tools()})
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                return self._error(request_id, -32602, "tools/call requires a string name")
            return self._result(request_id, self.call_tool(name, params.get("arguments", {})))
        return self._error(request_id, -32601, f"method not found: {method}")

    @staticmethod
    def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class GovernanceMcpRequestHandler(BaseHTTPRequestHandler):
    server: GovernanceMcpHttpServer

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers", "Authorization, Content-Type, MCP-Session-Id"
        )
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            self._send_json(
                HTTPStatus.OK, {"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION}
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/mcp":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "missing or invalid bearer token"})
            return
        content_length = self.headers.get("Content-Length")
        try:
            size = int(content_length or "0")
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid Content-Length"})
            return
        if size <= 0 or size > MAX_REQUEST_BYTES:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "request size is invalid or exceeds the limit"},
            )
            return
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "request body must be UTF-8 JSON"})
            return
        response = self.server.service.handle_rpc(payload)
        if response is None:
            self.send_response(HTTPStatus.ACCEPTED)
            self.send_header("MCP-Session-Id", self.server.session_id)
            self.end_headers()
            return
        self._send_json(HTTPStatus.OK, response)

    def _authorized(self) -> bool:
        expected = self.server.bearer_token
        if not expected:
            return True
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, f"Bearer {expected}")

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("MCP-Session-Id", self.server.session_id)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        del fmt, args
        return


class GovernanceMcpHttpServer(ThreadingHTTPServer):
    def __init__(
        self, server_address: tuple[str, int], service: GovernanceMcpService, bearer_token: str
    ) -> None:
        super().__init__(server_address, GovernanceMcpRequestHandler)
        self.service = service
        self.bearer_token = bearer_token
        self.session_id = str(uuid.uuid4())


def _load_token(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"could not read auth token file: {exc}") from exc
    if not token:
        raise ValueError("auth token file is empty")
    return token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--governance-root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="Cursor-Governance repository root",
    )
    parser.add_argument("--host", default=os.environ.get("L9_MANUS_MCP_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("L9_MANUS_MCP_PORT", "8787"))
    )
    parser.add_argument(
        "--auth-token-file",
        type=Path,
        help=(
            "Optional file containing the bearer token required on POST /mcp; the token is never "
            "logged."
        ),
    )
    parser.add_argument(
        "--allow-bootstrap-apply",
        action="store_true",
        help="Enable the mutating bootstrap apply mode; requires --auth-token-file.",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        bearer_token = _load_token(args.auth_token_file)
    except ValueError as exc:
        parser.error(str(exc))
    if args.allow_bootstrap_apply and not bearer_token:
        parser.error("--allow-bootstrap-apply requires --auth-token-file")
    try:
        service = GovernanceMcpService(
            args.governance_root,
            bootstrap_enabled=bool(bearer_token),
            bootstrap_apply_enabled=args.allow_bootstrap_apply,
        )
    except ValueError as exc:
        parser.error(str(exc))
    server = GovernanceMcpHttpServer((args.host, args.port), service, bearer_token)
    auth_mode = "bearer" if bearer_token else "none"
    print(
        f"{SERVER_NAME} listening on http://{args.host}:{args.port}/mcp "
        f"(auth={auth_mode}; health=/health)",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
