#!/usr/bin/env python3
"""Prove Claude memory hooks use Cursor Graphiti only — no HTTP side door."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

CLAUDE = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE / "hooks"
MEM = CLAUDE / "memory"
FORBIDDEN_IMPORTS = {"memory_client", "urllib.request", "urllib.error"}
FORBIDDEN_SUBSTRINGS = (
    "L9_MEMORY_HTTP_URL",
    "L9_MEMORY_CLIENT_TOKEN",
    "L9_MEMORY_ENFORCEMENT=off",
    "l9-shared-memory",
    "import memory_client",
    "memory/memory_client.py",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


class FrontDoorTests(unittest.TestCase):
    def test_http_client_deleted(self) -> None:
        self.assertFalse((MEM / "memory_client.py").exists())

    def test_bridge_exists(self) -> None:
        self.assertTrue((MEM / "graphiti_bridge.py").is_file())

    def test_agent_force_lock_interface_absent(self) -> None:
        """E8: no agent-facing Graphiti force-lock interface may exist.

        ``memory_lock.py acquire --force`` used to mint repository-write
        permission out of memory state, and ``--force`` let an agent do it over
        a reported conflict. Both are prohibited by the L9 Multi-Agent
        Main-Bound Execution Contract, so the hook is deleted rather than
        softened.
        """
        self.assertFalse((HOOKS / "memory_lock.py").exists())
        # Prose may *state* the prohibition (the prefetch hook tells agents no
        # phase-lock is accepted). What must not exist is code that acquires,
        # checks, or forces one -- so match invocation forms, not the word.
        forbidden = (
            '"phase-lock"',  # CLI subcommand argument
            "'phase-lock'",
            "gmp:phase_lock",  # satisfied-marker lookup
            "phase_lock_satisfied",
            "gb.phase_lock",
            "write_lock",
            "read_lock",
            "--force",
        )
        for path in HOOKS.glob("*.py"):
            src = path.read_text(encoding="utf-8")
            code = "\n".join(line for line in src.splitlines() if not line.strip().startswith("#"))
            for bad in forbidden:
                self.assertNotIn(bad, code, f"{path.name}: {bad}")

    def test_bridge_exposes_no_phase_lock(self) -> None:
        """E7: the bridge cannot mint repository-write permission."""
        src = (MEM / "graphiti_bridge.py").read_text(encoding="utf-8")
        self.assertNotIn("def phase_lock", src)
        self.assertNotIn("phase_lock_satisfied", src)

    def test_memory_hooks_call_bridge_not_http_client(self) -> None:
        """Hooks that reach the memory store go through the bridge.

        ``memory_gate.py`` is deliberately absent from this list: since the
        phase-lock decoupling it consults local hydration receipts only and
        needs no memory transport at all. It is covered by
        :meth:`test_no_hook_uses_an_http_side_door` below.
        """
        for name in ("memory_prefetch.py", "memory_writeback.py"):
            path = HOOKS / name
            src = path.read_text(encoding="utf-8")
            imports = _imports(path)
            self.assertNotIn("memory_client", imports, name)
            self.assertIn("graphiti_bridge", src, name)
            for bad in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(bad, src, name)

    def test_no_hook_uses_an_http_side_door(self) -> None:
        for path in HOOKS.glob("memory_*.py"):
            src = path.read_text(encoding="utf-8")
            self.assertNotIn("memory_client", _imports(path), path.name)
            for bad in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(bad, src, path.name)

    def test_bridge_targets_graphiti_cli(self) -> None:
        src = (MEM / "graphiti_bridge.py").read_text(encoding="utf-8")
        self.assertIn("ops/graphiti/graphiti_memory_client.py", src)
        self.assertNotIn("L9_MEMORY_HTTP_URL", src)
        self.assertNotIn("L9_MEMORY_CLIENT_TOKEN", src)
        self.assertNotIn("import memory_client", src)
        self.assertNotIn("memory/memory_client.py", src)

    def test_mcp_template_is_graphiti_env_front_door(self) -> None:
        mcp = json.loads((CLAUDE / "mcp.template.json").read_text(encoding="utf-8"))
        servers = mcp.get("mcpServers") or {}
        self.assertNotIn("l9-shared-memory", servers)
        self.assertIn("graphiti-memory", servers)
        url = servers["graphiti-memory"].get("url", "")
        self.assertEqual(url, "${L9_CAPABILITY_BROKER_URL}/mcp/graphiti")

    def test_mcp_template_holds_no_bearer(self) -> None:
        """Contract S3/§12: the functional config carries no Graphiti bearer.

        A prohibition mention in the _comment block documents the contract and
        is expected; the mcpServers config itself must never reference it.
        """
        raw = (CLAUDE / "mcp.template.json").read_text(encoding="utf-8")
        mcp = json.loads(raw)
        self.assertNotIn("GRAPHITI_MCP_TOKEN", json.dumps(mcp["mcpServers"]))
        self.assertNotIn("Bearer", raw)
        mem = mcp["mcpServers"]["graphiti-memory"]
        self.assertFalse(mem.get("headers"), "graphiti-memory must carry no headers")

    def test_environment_template_exports_no_credentials(self) -> None:
        """The cloud variables field is plaintext and model-readable: no
        assignment of any credential name may appear in it."""
        env = (CLAUDE / "web" / "environment.env.example").read_text(encoding="utf-8")
        for token in ("GH_TOKEN", "GRAPHITI_MCP_TOKEN", "INFISICAL_CLIENT_SECRET", "SONAR_TOKEN"):
            self.assertNotRegex(env, rf"^\s*{token}\s*=", f"{token} must not be assigned")


if __name__ == "__main__":
    unittest.main()
