"""Hard secret isolation (stage C9): no provider transport reaches any runtime path.

Negative tests that name the forbidden tokens as fixtures. They assert that
the production hooks, bootstraps, MCP inventories and the memory boundary
neither load, export, nor forward a provider URL or bearer, and that the
control-plane client strips such variables before spawning the memory CLI.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from memory_boundary_fixtures import FakeMemoryCli

from ops.memory.control_plane_client import MemoryControlPlaneClient

ROOT = Path(__file__).resolve().parents[3]

PROVIDER_URL = "GRAPHITI_MCP_" + "URL"
PROVIDER_TOKEN = "GRAPHITI_MCP_" + "TOKEN"

#: Runtime paths that execute on every session start, close, or install.
RUNTIME_SCRIPTS = (
    "ops/hooks/graphiti_common.sh",
    "ops/hooks/graphiti-prefetch.sh",
    "ops/hooks/graphiti-session-end.sh",
    "ops/hooks/graphiti-mark-ok.sh",
    "ops/hooks/graphiti-reset-generation.sh",
    "ops/hooks/graphiti_gate_runner.sh",
    "ops/hooks/session_start_memory_orchestrator.sh",
    "ops/hooks/session_start_bootstrap.sh",
    "ops/scripts/bootstrap_agent_environment.sh",
    "environment/agents/adapters/claude-code/web/setup.bootstrap.sh",
    "environment/agents/adapters/claude-code/web/setup.sh",
    "environment/agents/adapters/claude-code/install.sh",
    "environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh",
)

MCP_INVENTORIES = (
    "environment/mcp/master.mcp.json",
    ".mcp.json",
    "environment/agents/adapters/claude-code/mcp.template.json",
    "environment/agents/adapters/cursor/mcp.template.json",
    "environment/agents/adapters/generic/mcp.template.json",
    "environment/agents/adapters/codex/mcp.template.json",
    "environment/agents/adapters/gemini/settings.template.json",
    "environment/agents/adapters/manus/mcp-connector.json",
    "ops/config/memory-binding.json",
    "ops/config/memory-canonical-epoch.json",
)

_ASSIGN = re.compile(
    rf"^\s*(export\s+)?(?::\s*\"\$\{{)?({PROVIDER_URL}|{PROVIDER_TOKEN})[:=]", re.M
)
_KEYCHAIN = re.compile(r"security\s+find-generic-password\s+-s\s+graphiti")
_SECRET_SOURCE = re.compile(r"source\s+\"?\$HOME/\.cursor/secrets/graphiti\.env")
_FUNCTIONAL_JSON_TOKEN = re.compile(rf"\$\{{({PROVIDER_URL}|{PROVIDER_TOKEN})\}}")


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_runtime_scripts_neither_assign_nor_load_a_provider_transport() -> None:
    offenders: list[str] = []
    for rel in RUNTIME_SCRIPTS:
        text = _text(rel)
        if _ASSIGN.search(text):
            offenders.append(f"{rel}: assigns/exports a provider transport")
        if _KEYCHAIN.search(text):
            offenders.append(f"{rel}: reads the provider bearer from the keychain")
        if _SECRET_SOURCE.search(text):
            offenders.append(f"{rel}: sources the provider secrets overlay")
    assert offenders == [], offenders


def test_mcp_inventories_carry_no_provider_transport() -> None:
    offenders: list[str] = []
    for rel in MCP_INVENTORIES:
        data = json.loads(_text(rel))
        functional = {k: v for k, v in data.items() if not str(k).startswith("_")}
        rendered = json.dumps(functional)
        # The retired server is a JSON *key*; the memory package's repository
        # name (l9-graphiti-memory) legitimately appears as a value.
        if _FUNCTIONAL_JSON_TOKEN.search(rendered) or '"graphiti-memory":' in rendered:
            offenders.append(rel)
    assert offenders == [], offenders


def test_memory_boundary_holds_no_provider_vocabulary() -> None:
    forbidden = (PROVIDER_URL, PROVIDER_TOKEN, "search_memory_facts", "add_memory", "add_episode")
    offenders: list[str] = []
    for path in sorted((ROOT / "ops" / "memory").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            # The client strips the provider names from the child environment;
            # that one deliberate mention is assembled from parts, never literal.
            if token in text:
                offenders.append(f"{path.name}: {token}")
    assert offenders == [], offenders


def test_control_plane_client_strips_provider_transport_from_the_child_env(bound) -> None:
    seen: dict[str, object] = {}

    def runner(argv, *, cwd=None, input_text=None, timeout=30.0, env=None):
        seen["env"] = dict(env or {})
        fake = FakeMemoryCli()
        fake.reply("resolve", 0, {"group_id": "cursor-governance", "method": "registry"})
        return fake.run(argv, cwd=cwd, input_text=input_text, timeout=timeout)

    env = {
        "PATH": "/usr/bin",
        PROVIDER_URL: "https://provider.invalid/mcp",
        PROVIDER_TOKEN: "not-a-real-token",
        "GRAPHITI_SSH_HOST": "203.0.113.1",
        "L9_MEMORY_INTERPRETER": "/venv/bin/python",
    }
    client = MemoryControlPlaneClient(bound, runner=runner, env=env)
    client.resolve(workspace=str(ROOT))
    child = seen["env"]
    assert isinstance(child, dict)
    assert PROVIDER_URL not in child and PROVIDER_TOKEN not in child
    assert "GRAPHITI_SSH_HOST" not in child
    assert child["L9_MEMORY_INTERPRETER"] == "/venv/bin/python"
    assert child["PATH"] == "/usr/bin"


def test_adapter_env_examples_assign_no_provider_transport() -> None:
    adapters = ROOT / "environment" / "agents" / "adapters"
    offenders = [
        str(path.relative_to(ROOT))
        for path in sorted(adapters.rglob("environment.env.example"))
        if _ASSIGN.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], offenders


def test_agent_registry_memory_contract_names_no_transport_credential() -> None:
    import yaml

    registry = yaml.safe_load(_text("environment/agents/agent_registry.yaml"))
    memory = registry["memory"]
    assert memory["control_plane"] == "l9-graphite-memory"
    assert memory["transport"] == "stdio"
    for retired in ("url_env", "token_env", "production_url", "mcp_path"):
        assert retired not in memory
    for agent in registry["agents"].values():
        assert "legacy_token_env" not in agent


def test_capability_registry_has_no_memory_capability() -> None:
    import yaml

    registry = yaml.safe_load(_text("ops/secrets/capabilities.yaml"))
    ids = {entry["id"] for entry in registry["capabilities"]}
    assert not any(cid.startswith("graphiti.") for cid in ids)
    assert PROVIDER_TOKEN not in json.dumps(registry["capabilities"])
