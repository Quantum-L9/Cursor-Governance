#!/usr/bin/env python3
"""Prove Claude memory hooks use Cursor Graphiti only — no HTTP side door."""

from __future__ import annotations

import ast
import json
import re
import sys
import unittest
from pathlib import Path

CLAUDE = Path(__file__).resolve().parent.parent
REPO = Path(__file__).resolve().parents[5]
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
        self.assertEqual(url, "${GRAPHITI_MCP_URL}")

    def test_mcp_template_holds_no_literal_credential(self) -> None:
        """Contract S3/§12: no credential VALUE, in the template or the render.

        The prohibition is on written-down credential material, not on naming a
        variable. A bearer may now be referenced as ``${GRAPHITI_MCP_TOKEN}`` —
        Claude Code expands it at load from a value the platform proxies, so
        nothing is stored here or in the account variables field. What must never
        appear is a resolved secret: any Bearer whose argument is not a bare
        ``${VAR}`` reference.
        """
        mcp = json.loads((CLAUDE / "mcp.template.json").read_text(encoding="utf-8"))

        def walk(node: object) -> list[str]:
            """Every string leaf, so a Bearer is matched in its own value."""
            if isinstance(node, str):
                return [node]
            if isinstance(node, dict):
                return [leaf for value in node.values() for leaf in walk(value)]
            if isinstance(node, list):
                return [leaf for item in node for leaf in walk(item)]
            return []

        found = 0
        for leaf in walk(mcp["mcpServers"]):
            match = re.fullmatch(r"Bearer\s+(.+)", leaf)
            if not match:
                continue
            found += 1
            self.assertRegex(
                match.group(1),
                r"^\$\{[A-Z0-9_]+\}$",
                f"Bearer must reference a variable, not a literal: {match.group(1)!r}",
            )
        self.assertTrue(found, "expected at least one ${VAR} bearer reference to check")

    def test_graphiti_bearer_is_env_gated_and_absent_when_unproxied(self) -> None:
        """An unproxied session must render exactly the previous wire config.

        The Graphiti front door is unauthenticated today. Emitting an empty or
        literal Authorization header would break the one memory path that works,
        so the header lives under ``_optional_headers`` and only materialises
        when the variable actually carries a proxied value.
        """
        sys.path.insert(0, str(REPO / "ops" / "scripts"))
        import claude_projection as cp

        template = json.loads((CLAUDE / "mcp.template.json").read_text(encoding="utf-8"))

        unproxied = cp.render_mcp(template, None, environ={})["mcpServers"]
        self.assertIn("graphiti-memory", unproxied)
        self.assertFalse(
            unproxied["graphiti-memory"].get("headers"),
            "unproxied graphiti-memory must carry no headers",
        )
        self.assertNotIn("context7", unproxied, "context7 requires a proxied key")
        self.assertNotIn(
            "_optional_headers",
            json.dumps(unproxied),
            "private template directives must never ship",
        )

        proxied = cp.render_mcp(
            template,
            None,
            environ={"GRAPHITI_MCP_TOKEN": "proxied", "CONTEXT7_API_KEY": "proxied"},
        )["mcpServers"]
        self.assertEqual(
            proxied["graphiti-memory"]["headers"]["Authorization"],
            "Bearer ${GRAPHITI_MCP_TOKEN}",
        )
        self.assertEqual(proxied["context7"]["url"], "https://mcp.context7.com/mcp")

    def test_environment_template_exports_no_credentials(self) -> None:
        """The cloud variables field is plaintext and model-readable: no
        assignment of any credential name may appear in it."""
        env = (CLAUDE / "web" / "environment.env.example").read_text(encoding="utf-8")
        for token in ("GH_TOKEN", "GRAPHITI_MCP_TOKEN", "INFISICAL_CLIENT_SECRET", "SONAR_TOKEN"):
            self.assertNotRegex(env, rf"^\s*{token}\s*=", f"{token} must not be assigned")


if __name__ == "__main__":
    unittest.main()
