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
        "install.sh",
        "mcp-connector.json",
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
    if connector.get("status") != "retired-pending-memory-remote-transport":
        errors.append("MCP carrier must state the remote memory transport is not provisioned")
    if connector.get("transport") != "none":
        errors.append("MCP carrier must not invent a Manus memory transport")
    if "mcpServers" in connector or _contains_forbidden_key(connector):
        errors.append("MCP carrier must not contain a URL, headers, environment, or server entry")

    bootstrap = (adapter / "session_bootstrap.md").read_text(encoding="utf-8")
    for marker in REQUIRED_BOOTSTRAP_TEXT:
        if marker not in bootstrap:
            errors.append(f"session bootstrap is missing required authority marker: {marker}")
    for forbidden in ("Authorization:", "Bearer ", "GRAPHITI_MCP_URL", "https://memory."):
        if forbidden in bootstrap:
            errors.append(f"session bootstrap contains retired provider material: {forbidden}")

    installer = (adapter / "install.sh").read_text(encoding="utf-8")
    for marker in ("bootstrap_agent_environment.sh", "--surface manus", "--workspace"):
        if marker not in installer:
            errors.append(f"installer is missing shared-bootstrap marker: {marker}")
    for forbidden in ("git clone", "curl ", "INFISICAL_", "GRAPHITI_MCP_"):
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
