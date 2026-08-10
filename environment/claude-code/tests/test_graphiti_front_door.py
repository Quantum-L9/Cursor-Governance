#!/usr/bin/env python3
"""Prove Claude memory hooks use Cursor Graphiti only — no HTTP side door."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

CLAUDE = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE / "hooks"
MEM = CLAUDE / "memory"
FORBIDDEN_IMPORTS = {"memory_client", "urllib.request", "urllib.error"}
FORBIDDEN_SUBSTRINGS = (
    "L9_MEMORY_HTTP_URL",
    "L9_MEMORY_CLIENT_TOKEN",
    "memory.quantumaipartners.com",
    "L9_MEMORY_ENFORCEMENT=off",
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

    def test_hooks_call_bridge_not_http_client(self) -> None:
        for name in (
            "memory_prefetch.py",
            "memory_lock.py",
            "memory_writeback.py",
            "memory_gate.py",
        ):
            path = HOOKS / name
            src = path.read_text(encoding="utf-8")
            imports = _imports(path)
            self.assertNotIn("memory_client", imports, name)
            self.assertIn("graphiti_bridge", src, name)
            for bad in FORBIDDEN_SUBSTRINGS:
                # gate/prefetch may mention BREAKGLASS; only forbid =off and HTTP URL/token
                if bad == "L9_MEMORY_ENFORCEMENT=off":
                    self.assertNotIn(bad, src, name)
                elif "HTTP" in bad or "TOKEN" in bad or "quantum" in bad:
                    self.assertNotIn(bad, src, name)

    def test_bridge_targets_graphiti_cli(self) -> None:
        src = (MEM / "graphiti_bridge.py").read_text(encoding="utf-8")
        self.assertIn("ops/graphiti/graphiti_memory_client.py", src)
        self.assertNotIn("L9_MEMORY_HTTP_URL", src)
        self.assertNotIn("memory.quantumaipartners.com", src)

    def test_mcp_template_is_graphiti_front_door(self) -> None:
        mcp = json_load(CLAUDE / "mcp.template.json")
        servers = mcp.get("mcpServers") or {}
        self.assertNotIn("l9-shared-memory", servers)
        self.assertIn("graphiti-memory", servers)
        url = servers["graphiti-memory"].get("url", "")
        self.assertIn("127.0.0.1:8100", url)
        self.assertNotIn("quantumaipartners", url)


def json_load(path: Path):
    import json

    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
