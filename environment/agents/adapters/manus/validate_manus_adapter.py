#!/usr/bin/env python3
"""Validate the Manus adapter's thin, provider-neutral surface contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ADAPTER_RELATIVE = Path("environment/agents/adapters/manus")
REQUIRED_ENV = {
    "L9_GOVERNANCE_REPO": "Quantum-L9/Cursor-Governance",
    "L9_GOVERNANCE_SURFACE": "manus",
    "USER_ID": "manus_agent",
    "L9_MEMORY_AGENT_ID": "manus",
    "L9_MEMORY_SOURCE": "manus",
    "L9_AGENT_ROLE": "researcher-builder",
    "L9_AUTONOMY_ENABLED": "true",
    "L9_L4_LOCAL_AUTONOMY": "1",
    "L9_WORKTREE_ISOLATION": "1",
}
FORBIDDEN_ENV = {
    "GRAPHITI_MCP_URL",
    "GRAPHITI_MCP_TOKEN",
    "L9_MEMORY_HTTP_URL",
    "L9_MEMORY_CLIENT_TOKEN",
    "L9_CAPABILITY_BROKER_URL",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_TOKEN",
    "SONAR_TOKEN",
    "SEMGREP_APP_TOKEN",
    "L9_MERGE_AUTHORIZED",
    "L9_PUBLISH_PATH_OVERRIDE",
}
REQUIRED_BOOTSTRAP_TEXT = (
    "L9_GOVERNANCE_SURFACE=manus",
    "CANONICAL_LAW.md",
    "AGENTS.md",
    "ops/autonomy/surface_profile.yaml",
    "PR_REMEDIATE=0 make pr",
)
# Repository authority chain (CLAUDE.md / rules 01-authority-chain), highest
# first. The bootstrap must state these rungs in exactly this order inside its
# "Apply authority in this order:" sentence; marker presence alone is not enough.
AUTHORITY_SENTENCE_PREFIX = "Apply authority in this order:"
AUTHORITY_ORDER = (
    "CANONICAL_LAW.md",
    "ops/autonomy/surface_profile.yaml",
    "AGENTS.md",
    "SKILL.md",
)


def authority_order_errors(bootstrap: str) -> list[str]:
    """Return violations of the declared authority order in ``bootstrap``.

    The check is order-sensitive: every rung of ``AUTHORITY_ORDER`` must appear
    in the authority sentence, and each must appear after the previous one.
    """
    start = bootstrap.find(AUTHORITY_SENTENCE_PREFIX)
    if start < 0:
        return [f"session bootstrap has no {AUTHORITY_SENTENCE_PREFIX!r} sentence"]
    end = bootstrap.find("\n\n", start)
    sentence = bootstrap[start:] if end < 0 else bootstrap[start:end]
    expected = " -> ".join(AUTHORITY_ORDER)
    positions: list[int] = []
    for rung in AUTHORITY_ORDER:
        index = sentence.find(rung)
        if index < 0:
            return [f"session bootstrap authority sentence omits {rung}; expected {expected}"]
        positions.append(index)
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        return [f"session bootstrap authority order is wrong; expected {expected}"]
    return []


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML object required: {path}")
    return data


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key:
            raise ValueError(f"invalid environment assignment in {path.name}: {raw!r}")
        values[key] = value
    return values


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in {"env", "headers", "url"}:
                return True
            if _contains_forbidden_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def validate(repo_root: Path) -> list[str]:
    errors: list[str] = []
    adapter = repo_root / ADAPTER_RELATIVE
    required_files = {
        "README.md",
        "environment.env.example",
        "infisical-mcp-connector.json",
        "infisical_capabilities.json",
        "infisical_mcp_server.py",
        "install.sh",
        "mcp-connector.json",
        "mcp_server.py",
        "memory-mcp-connector.json",
        "memory_lifecycle.py",
        "materialize_memory_authority.py",
        "render_infisical_mcp_connector.py",
        "render_mcp_connector.py",
        "render_memory_mcp_connector.py",
        "serve_infisical_mcp.sh",
        "serve_mcp.sh",
        "serve_memory_mcp.sh",
        "session_bootstrap.md",
        "setup.md",
    }
    for filename in sorted(required_files):
        if not (adapter / filename).is_file():
            errors.append(f"missing adapter file: {filename}")
    if errors:
        return errors

    registry = _load_yaml(repo_root / "environment/agents/agent_registry.yaml")
    manus = (registry.get("agents") or {}).get("manus")
    if not isinstance(manus, dict):
        return ["agent registry has no manus entry"]

    env = _load_env(adapter / "environment.env.example")
    expected_from_registry = {
        "USER_ID": manus.get("user_id"),
        "L9_MEMORY_AGENT_ID": manus.get("agent_id"),
        "L9_MEMORY_SOURCE": manus.get("source"),
        "L9_AGENT_ROLE": manus.get("role"),
    }
    for key, expected in {**REQUIRED_ENV, **expected_from_registry}.items():
        if env.get(key) != expected:
            errors.append(f"environment {key}={env.get(key)!r}, expected {expected!r}")
    for key in sorted(FORBIDDEN_ENV & env.keys()):
        errors.append(f"environment must not declare {key}")
    if "L9_GOVERNANCE_DIR" in env:
        errors.append("environment must not declare L9_GOVERNANCE_DIR with a literal hosted path")

    connector = json.loads((adapter / "mcp-connector.json").read_text(encoding="utf-8"))
    if connector.get("transport") != "streamable-http":
        errors.append("MCP carrier must declare the streamable HTTP governance transport")
    if connector.get("endpoint_path") != "/mcp" or connector.get("health_path") != "/health":
        errors.append("MCP carrier must declare /mcp and /health endpoints")
    if connector.get("memory") != {
        "agent_lane": "package-owned-l9-graphite-memory-mcp-or-cli",
        "lifecycle": "bearer-protected-canonical-hydrate-and-close-only",
        "fallback": "fail-closed-no-local-operator-identity",
    }:
        errors.append("MCP carrier must declare the bounded Manus memory lifecycle boundary")
    if connector.get("safety") != {
        "no_shell": True,
        "no_credentials": True,
        "no_arbitrary_file_access": True,
        "no_repository_write_tools": True,
    }:
        errors.append("MCP carrier must preserve the governance MCP safety boundary")
    authentication = connector.get("authentication")
    if (
        not isinstance(authentication, dict)
        or authentication.get("bootstrap_requires") != "bearer-token-file"
    ):
        errors.append("MCP carrier must require bearer protection before bootstrap access")
    elif authentication.get("apply_bootstrap_requires") != (
        "bearer-token-file plus --allow-bootstrap-apply"
    ):
        errors.append("MCP carrier must require an explicit apply authorization flag")
    if "mcpServers" in connector or _contains_forbidden_key(connector):
        errors.append(
            "MCP carrier must not contain a deployment URL, headers, environment, or server entry"
        )

    memory_connector = json.loads(
        (adapter / "memory-mcp-connector.json").read_text(encoding="utf-8")
    )
    if memory_connector.get("transport") != "stdio":
        errors.append("memory MCP carrier must use the package-owned stdio transport")
    if memory_connector.get("command") != "rendered-locally":
        errors.append("memory MCP carrier must require a locally rendered absolute command")
    if memory_connector.get("authentication") != {
        "mode": "inherited-signed-agent-assertion",
        "agent_id": "manus",
        "human_door": "forbidden",
        "local_operator_fallback": "forbidden",
    }:
        errors.append("memory MCP carrier must require the signed Manus agent door")
    if memory_connector.get("authority_delivery") != {
        "mode": "encrypted-connector-environment",
        "payload": "manus-scoped-agent-door-and-signing-key-only",
        "grant": "derived-from-canonical-agent-registry",
        "materialization": "per-process-0600-runtime-files-removed-on-exit",
    }:
        errors.append("memory MCP carrier must preserve scoped durable authority delivery")
    if memory_connector.get("package") != {
        "distribution": "l9-graphite-memory",
        "entrypoint": "l9-memory-server --transport stdio",
        "tool_authority": "package-owned-mcp-tools",
    }:
        errors.append("memory MCP carrier must retain package-owned tool authority")
    if memory_connector.get("scope") != {
        "ordinary_agent_reads": True,
        "cold_safe_agent_writes": True,
        "governed_writes_and_phase_locks": True,
        "lifecycle_start_close": False,
        "provider_transport": False,
        "generic_shell": False,
    }:
        errors.append("memory MCP carrier scope must separate agent tools from lifecycle")
    if "mcpServers" in memory_connector or _contains_forbidden_key(memory_connector):
        errors.append(
            "memory MCP carrier must not contain a deployment URL, headers, "
            "environment, or server entry"
        )

    infisical_connector = json.loads(
        (adapter / "infisical-mcp-connector.json").read_text(encoding="utf-8")
    )
    expected_connector = {
        "name": "l9-manus-infisical",
        "transport": "stdio",
        "status": "native-connector-template-requires-machine-identity",
        "launcher": "serve_infisical_mcp.sh",
        "renderer": "render_infisical_mcp_connector.py",
        "capability_manifest": "infisical_capabilities.json",
        "secret_delivery": "encrypted-connector-env",
        "secret_exposure": "forbidden",
    }
    for key, expected in expected_connector.items():
        if infisical_connector.get(key) != expected:
            errors.append(
                f"Infisical connector {key}={infisical_connector.get(key)!r}, expected {expected!r}"
            )
    if "mcpServers" in infisical_connector or _contains_forbidden_key(infisical_connector):
        errors.append(
            "Infisical connector carrier must not contain a URL, headers, environment, "
            "or server entry"
        )

    try:
        capabilities = json.loads(
            (adapter / "infisical_capabilities.json").read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        errors.append(f"Infisical capability manifest is invalid JSON: {exc}")
        capabilities = {}
    if capabilities.get("schema") != "l9.manus.infisical-capabilities.v1":
        errors.append("Infisical capability manifest has the wrong schema")
    github = (capabilities.get("capabilities") or {}).get("github.get_repository")
    if not isinstance(github, dict):
        errors.append("Infisical capability manifest must declare github.get_repository")
    else:
        if github.get("secret_key") != "GITHUB_TOKEN":
            errors.append("github.get_repository must use the GITHUB_TOKEN inventory key")
        if github.get("origin") != "https://api.github.com" or github.get("method") != "GET":
            errors.append("github.get_repository must be a fixed GitHub HTTPS GET capability")

    server = (adapter / "infisical_mcp_server.py").read_text(encoding="utf-8")
    for marker in (
        "infisical_status",
        "infisical_list_secret_metadata",
        "infisical_invoke",
        '"viewSecretValue": "false"',
        "response was withheld",
    ):
        if marker not in server:
            errors.append(f"Infisical MCP server is missing safety marker: {marker}")
    for forbidden in ("os.environ[", "subprocess.", "shell=True", "GET /secret"):
        if forbidden in server:
            errors.append(
                f"Infisical MCP server contains a forbidden secret-exposure pattern: {forbidden}"
            )

    bootstrap = (adapter / "session_bootstrap.md").read_text(encoding="utf-8")
    for marker in REQUIRED_BOOTSTRAP_TEXT:
        if marker not in bootstrap:
            errors.append(f"session bootstrap is missing required authority marker: {marker}")
    errors.extend(authority_order_errors(bootstrap))
    for forbidden in ("Authorization:", "Bearer ", "GRAPHITI_MCP_URL", "https://memory."):
        if forbidden in bootstrap:
            errors.append(f"session bootstrap contains retired provider material: {forbidden}")

    server = (adapter / "mcp_server.py").read_text(encoding="utf-8")
    for marker in (
        "governance_status",
        "governance_validate",
        "governance_bootstrap",
        "memory_lifecycle_start",
        "memory_lifecycle_close",
        "--enable-memory-lifecycle",
        "streamable-http",
    ):
        if marker not in server:
            errors.append(f"MCP server is missing required governance tool marker: {marker}")
    for forbidden in ("shell=True", "os.system(", "GRAPHITI_MCP_URL", "L9_MEMORY_HTTP_URL"):
        if forbidden in server:
            errors.append(f"MCP server contains prohibited surface behavior: {forbidden}")

    lifecycle = (adapter / "memory_lifecycle.py").read_text(encoding="utf-8")
    for marker in (
        "canonical_hydrate",
        "close_session",
        "manus-session-start",
        "manus-session-end",
        "require_signed_agent_door",
    ):
        if marker not in lifecycle:
            errors.append(f"Manus memory lifecycle is missing canonical marker: {marker}")
    for forbidden in (
        "from l9_graphite_memory import",
        "GRAPHITI_MCP_URL",
        "L9_MEMORY_HTTP_URL",
    ):
        if forbidden in lifecycle:
            errors.append(
                f"Manus memory lifecycle contains prohibited transport material: {forbidden}"
            )

    launcher = (adapter / "serve_mcp.sh").read_text(encoding="utf-8")
    for marker in (".venv/bin/python", "mcp_server.py", "--governance-root"):
        if marker not in launcher:
            errors.append(f"MCP launcher is missing required marker: {marker}")

    memory_launcher = (adapter / "serve_memory_mcp.sh").read_text(encoding="utf-8")
    for marker in (
        "export_agent_assertion_env.sh",
        "L9_MEMORY_AGENT_ID=manus",
        "L9_MANUS_MEMORY_AUTHORITY_JSON",
        "materialize_memory_authority.py",
        "mktemp -d",
        "trap cleanup EXIT HUP INT TERM",
        "l9-memory-server",
        "--transport stdio",
        "local-operator compatibility principal",
    ):
        if marker not in memory_launcher:
            errors.append(f"memory MCP launcher is missing required marker: {marker}")
    for forbidden in ("GRAPHITI_MCP_URL", "L9_MEMORY_HTTP_URL", "http://", "https://"):
        if forbidden in memory_launcher:
            errors.append(
                f"memory MCP launcher contains prohibited transport material: {forbidden}"
            )

    installer = (adapter / "install.sh").read_text(encoding="utf-8")
    for marker in (
        "validate_manus_adapter.py",
        "--repo-root",
        "--workspace",
        "bootstrap_agent_environment.sh",
        "--surface manus",
    ):
        if marker not in installer:
            errors.append(f"installer is missing native-connector validation marker: {marker}")
    for forbidden in ("git clone", "curl ", "GRAPHITI_MCP_"):
        if forbidden in installer:
            errors.append(f"installer contains out-of-scope implementation: {forbidden}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="repository root containing environment/agents",
    )
    args = parser.parse_args(argv)
    try:
        errors = validate(args.repo_root.resolve())
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        errors = [str(exc)]
    if errors:
        print("FAIL — Manus adapter contract violations:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("PASS — Manus adapter is thin, identity-bound, and provider-neutral", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
