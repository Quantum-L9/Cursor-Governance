#!/usr/bin/env python3
"""Prove Claude memory hooks use the canonical memory control plane only.

Stage C8 of the realignment: no HTTP side door, no provider client, no
provider URL or bearer anywhere on the surface. The single front door is
``ops/memory`` through ``memory/memory_bridge.py``; the only MCP memory server
is the package-owned ``l9-graphite-memory`` stdio entry.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

CLAUDE = Path(__file__).resolve().parent.parent
REPO = Path(__file__).resolve().parents[5]
HOOKS = CLAUDE / "hooks"
MEM = CLAUDE / "memory"
FORBIDDEN_IMPORTS = {"memory_client", "urllib.request", "urllib.error", "graphiti_bridge"}
FORBIDDEN_SUBSTRINGS = (
    "L9_MEMORY_HTTP_URL",
    "L9_MEMORY_CLIENT_TOKEN",
    "L9_MEMORY_ENFORCEMENT=off",
    "l9-shared-memory",
    "import memory_client",
    "memory/memory_client.py",
    "graphiti_bridge",
    "graphiti_memory_client",
    "GRAPHITI_MCP_URL",
    "GRAPHITI_MCP_TOKEN",
)
MEMORY_ARGS = ["-m", "l9_graphite_memory.server", "--transport", "stdio"]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _template() -> dict:
    return json.loads((CLAUDE / "mcp.template.json").read_text(encoding="utf-8"))


class FrontDoorTests(unittest.TestCase):
    def test_http_client_and_legacy_bridge_deleted(self) -> None:
        self.assertFalse((MEM / "memory_client.py").exists())
        self.assertFalse((MEM / "graphiti_bridge.py").exists())

    def test_bridge_exists(self) -> None:
        self.assertTrue((MEM / "memory_bridge.py").is_file())

    def test_agent_force_lock_interface_absent(self) -> None:
        """E8: no agent-facing force-lock interface may exist.

        ``memory_lock.py acquire --force`` used to mint repository-write
        permission out of memory state. Prose may *state* the prohibition;
        what must not exist is code that acquires, checks, or forces one.
        """
        self.assertFalse((HOOKS / "memory_lock.py").exists())
        forbidden = (
            '"phase-lock"',
            "'phase-lock'",
            "gmp:phase_lock",
            "phase_lock_satisfied",
            "mb.phase_lock",
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
        src = (MEM / "memory_bridge.py").read_text(encoding="utf-8")
        self.assertNotIn("def phase_lock", src)
        self.assertNotIn("phase_lock_satisfied", src)

    def test_memory_hooks_call_bridge_not_a_provider(self) -> None:
        """Hooks that reach memory go through the bridge into ops/memory.

        ``memory_gate.py`` consults local hydration receipts only and needs no
        memory transport at all; it is covered by the side-door test below.
        """
        for name in ("memory_prefetch.py", "memory_writeback.py"):
            path = HOOKS / name
            src = path.read_text(encoding="utf-8")
            imports = _imports(path)
            self.assertFalse(imports & FORBIDDEN_IMPORTS, f"{name}: {imports & FORBIDDEN_IMPORTS}")
            self.assertIn("memory_bridge", imports, name)
            for bad in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(bad, src, name)

    def test_no_hook_uses_a_side_door(self) -> None:
        for path in HOOKS.glob("memory_*.py"):
            src = path.read_text(encoding="utf-8")
            self.assertFalse(_imports(path) & FORBIDDEN_IMPORTS, path.name)
            for bad in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(bad, src, path.name)

    def test_bridge_targets_the_memory_boundary(self) -> None:
        src = (MEM / "memory_bridge.py").read_text(encoding="utf-8")
        self.assertIn("ops/memory/control_plane_client.py", src)
        self.assertIn("MemoryControlPlaneClient", src)
        for bad in FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(bad, src)

    def test_contract_names_the_canonical_front_door(self) -> None:
        contract = json.loads(
            (MEM / "memory-enforcement.contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["memory"]["front_door"], "ops/memory/control_plane_client.py")
        self.assertTrue(contract["memory"]["bridge"].endswith("memory/memory_bridge.py"))
        doors = contract["memory"]["forbidden_side_doors"]
        self.assertIn("ops/graphiti/graphiti_memory_client.py", doors)
        self.assertTrue(any(d.endswith("graphiti_bridge.py") for d in doors))

    # -- interactive write contract (ADR-0030 items 7-9) ----------------------

    @staticmethod
    def _contract() -> dict:
        return json.loads((MEM / "memory-enforcement.contract.json").read_text(encoding="utf-8"))

    @staticmethod
    def _schema() -> dict:
        return json.loads((MEM / "memory-enforcement.schema.json").read_text(encoding="utf-8"))

    @staticmethod
    def _validator():
        sys.path.insert(0, str(CLAUDE))
        import validate_memory_enforcement as vme

        return vme

    def test_contract_states_the_governed_interactive_write(self) -> None:
        """Positive: the model's durable write is phase_lock -> write_governed."""
        imw = self._contract()["interactive_memory_write"]
        self.assertEqual(imw["canonical_mcp_server"], "l9-graphite-memory")
        self.assertEqual(imw["prerequisite"], "memory.phase_lock")
        self.assertEqual(imw["write_operation"], "memory.write_governed")
        self.assertIs(imw["repository_authority"], False)
        self.assertEqual(imw["provider_direct"], "forbidden")
        self.assertEqual(imw["generic_ingest_as_model_write"], "forbidden")
        self.assertEqual(imw["cli_adapter"], "python -m ops.memory.cli")
        self.assertNotIn("ingest", imw["deterministic_adapter_operations"])
        self.assertNotIn("write_governed", imw["deterministic_adapter_operations"])

    def test_schema_requires_the_interactive_write_block(self) -> None:
        schema = self._schema()
        self.assertIn("interactive_memory_write", schema["required"])
        props = schema["properties"]["interactive_memory_write"]["properties"]
        self.assertEqual(props["prerequisite"]["const"], "memory.phase_lock")
        self.assertEqual(props["write_operation"]["const"], "memory.write_governed")
        self.assertIs(props["repository_authority"]["const"], False)
        self.assertEqual(props["provider_direct"]["const"], "forbidden")
        self.assertEqual(props["generic_ingest_as_model_write"]["const"], "forbidden")
        # Retired provider properties are not legal on the memory block any more.
        memory_props = schema["properties"]["memory"]["properties"]
        for retired in ("url_env", "token_env", "mcp_path"):
            self.assertNotIn(retired, memory_props)
        self.assertIs(schema["properties"]["memory"]["additionalProperties"], False)

    def test_contract_validates_against_its_schema(self) -> None:
        try:
            import jsonschema  # type: ignore[import-not-found]
        except ImportError:  # pragma: no cover - the validator has a fallback
            self.skipTest("jsonschema not installed")
        jsonschema.validate(self._contract(), self._schema())

    def test_validator_accepts_the_current_contract(self) -> None:
        vme = self._validator()
        failures: list[str] = []
        vme.doctrine_check(self._contract(), failures)
        self.assertEqual(failures, [])

    def test_validator_rejects_generic_ingest_as_the_model_write(self) -> None:
        vme = self._validator()
        planted = self._contract()
        planted["interactive_memory_write"]["generic_ingest_as_model_write"] = "allowed"
        failures: list[str] = []
        vme.doctrine_check(planted, failures)
        self.assertTrue([f for f in failures if "generic_ingest_as_model_write" in f], failures)

    def test_validator_rejects_a_provider_direct_write(self) -> None:
        vme = self._validator()
        planted = self._contract()
        planted["interactive_memory_write"]["provider_direct"] = "allowed"
        failures: list[str] = []
        vme.doctrine_check(planted, failures)
        self.assertTrue([f for f in failures if "provider_direct" in f], failures)

    def test_validator_rejects_phase_lock_as_repository_authority(self) -> None:
        vme = self._validator()
        planted = self._contract()
        planted["interactive_memory_write"]["repository_authority"] = True
        planted["governed_writes"][0]["requires"] = ["session_prefetch", "phase_lock"]
        failures: list[str] = []
        vme.doctrine_check(planted, failures)
        self.assertTrue([f for f in failures if "repository_authority" in f], failures)
        self.assertTrue([f for f in failures if "E7" in f], failures)

    def test_validator_rejects_a_missing_interactive_write_block(self) -> None:
        vme = self._validator()
        planted = self._contract()
        del planted["interactive_memory_write"]
        failures: list[str] = []
        vme.doctrine_check(planted, failures)
        self.assertTrue(
            [f for f in failures if "interactive_memory_write block missing" in f], failures
        )

    def test_validator_rejects_a_provider_url_or_token_env_on_the_surface(self) -> None:
        vme = self._validator()
        planted = self._contract()
        planted["memory"]["url_env"] = "GRAPHITI_MCP_" + "URL"
        planted["memory"]["token_env"] = "GRAPHITI_MCP_" + "TOKEN"
        failures: list[str] = []
        vme.doctrine_check(planted, failures)
        self.assertTrue([f for f in failures if "memory.url_env" in f], failures)
        self.assertTrue([f for f in failures if "memory.token_env" in f], failures)
        self.assertTrue([f for f in failures if "retired provider transport" in f], failures)

    def test_validator_rejects_a_write_operation_other_than_write_governed(self) -> None:
        vme = self._validator()
        planted = self._contract()
        planted["interactive_memory_write"]["write_operation"] = "memory.ingest"
        failures: list[str] = []
        vme.doctrine_check(planted, failures)
        self.assertTrue([f for f in failures if "write_operation" in f], failures)

    def test_validator_rejects_a_retired_front_door(self) -> None:
        vme = self._validator()
        planted = self._contract()
        planted["memory"]["front_door"] = "ops/graphiti/graphiti_memory_client.py"
        failures: list[str] = []
        vme.doctrine_check(planted, failures)
        self.assertTrue([f for f in failures if "memory.front_door" in f], failures)

    # -- MCP template ---------------------------------------------------------

    def test_mcp_template_declares_only_the_canonical_memory_server(self) -> None:
        servers = _template().get("mcpServers") or {}
        self.assertNotIn("l9-shared-memory", servers)
        self.assertNotIn("graphiti-memory", servers)
        memory = servers["l9-graphite-memory"]
        self.assertEqual(memory["type"], "stdio")
        self.assertEqual(memory["command"], "${L9_MEMORY_INTERPRETER}")
        self.assertEqual(memory["args"], MEMORY_ARGS)
        self.assertIn("L9_MEMORY_INTERPRETER", memory["_requires_env"])
        for forbidden in ("env", "url", "headers"):
            self.assertNotIn(forbidden, memory)
        self.assertIn("graphiti-memory", _template().get("_retired_servers") or [])

    def test_mcp_template_holds_no_literal_credential(self) -> None:
        """Contract S3/§12: no credential VALUE, in the template or the render.

        A bearer may be referenced as ``${VAR}`` (Context7). What must never
        appear is a resolved secret: any Bearer whose argument is not a bare
        ``${VAR}`` reference.
        """

        def walk(node: object) -> list[str]:
            if isinstance(node, str):
                return [node]
            if isinstance(node, dict):
                return [leaf for value in node.values() for leaf in walk(value)]
            if isinstance(node, list):
                return [leaf for item in node for leaf in walk(item)]
            return []

        found = 0
        for leaf in walk(_template()["mcpServers"]):
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

    def test_render_is_gated_on_the_interpreter_and_retires_the_legacy_key(self) -> None:
        """An unbound session renders no memory server; a bound one renders the
        package's argv as a ${VAR} reference; a stale legacy key is removed."""
        sys.path.insert(0, str(REPO / "ops" / "scripts"))
        import claude_projection as cp

        template = _template()
        stale = {"mcpServers": {"graphiti-memory": {"type": "http", "url": "${LEGACY}"}}}
        unbound = cp.render_mcp(template, stale, environ={})["mcpServers"]
        self.assertNotIn("l9-graphite-memory", unbound, "requires L9_MEMORY_INTERPRETER")
        self.assertNotIn("graphiti-memory", unbound, "retired keys are removed, not preserved")
        self.assertNotIn("context7", unbound, "context7 requires a proxied key")
        self.assertNotIn("_requires_env", json.dumps(unbound), "private directives never ship")

        bound = cp.render_mcp(
            template,
            None,
            environ={"L9_MEMORY_INTERPRETER": "/venv/bin/python", "CONTEXT7_API_KEY": "proxied"},
        )["mcpServers"]
        self.assertEqual(bound["l9-graphite-memory"]["command"], "${L9_MEMORY_INTERPRETER}")
        self.assertEqual(bound["l9-graphite-memory"]["args"], MEMORY_ARGS)
        self.assertNotIn("env", bound["l9-graphite-memory"])
        self.assertEqual(bound["context7"]["url"], "https://mcp.context7.com/mcp")

    # -- validator agrees with the design ------------------------------------

    def test_validator_accepts_the_canonical_template(self) -> None:
        sys.path.insert(0, str(CLAUDE))
        import validate_claude_env as v

        failures: list[str] = []
        v.check_mcp_uses_env_refs(failures)
        self.assertEqual(failures, [])

    def test_validator_rejects_the_retired_front_door(self) -> None:
        sys.path.insert(0, str(CLAUDE))
        import validate_claude_env as v

        template = _template()
        template["mcpServers"]["graphiti-memory"] = {"type": "http", "url": "${SOME_PROVIDER_URL}"}
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp)
            (planted / "mcp.template.json").write_text(json.dumps(template), encoding="utf-8")
            failures: list[str] = []
            with mock.patch.object(v, "HERE", planted):
                v.check_mcp_uses_env_refs(failures)
        self.assertTrue([f for f in failures if "graphiti-memory" in f], failures)

    def test_validator_rejects_a_memory_credential_in_functional_config(self) -> None:
        """A memory bearer planted under context7's REAL headers must still fail."""
        sys.path.insert(0, str(CLAUDE))
        import validate_claude_env as v

        template = _template()
        template["mcpServers"]["context7"]["headers"] = {
            "Authorization": "Bearer ${" + "GRAPHITI_MCP_TOKEN" + "}"
        }
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp)
            (planted / "mcp.template.json").write_text(json.dumps(template), encoding="utf-8")
            failures: list[str] = []
            with mock.patch.object(v, "HERE", planted):
                v.check_mcp_uses_env_refs(failures)
        self.assertTrue([f for f in failures if "credential" in f], failures)

    def test_validator_rejects_an_env_block_on_the_memory_entry(self) -> None:
        sys.path.insert(0, str(CLAUDE))
        import validate_claude_env as v

        template = _template()
        template["mcpServers"]["l9-graphite-memory"]["env"] = {"X": "${X}"}
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp)
            (planted / "mcp.template.json").write_text(json.dumps(template), encoding="utf-8")
            failures: list[str] = []
            with mock.patch.object(v, "HERE", planted):
                v.check_mcp_uses_env_refs(failures)
        self.assertTrue([f for f in failures if "env" in f], failures)

    def test_environment_template_exports_no_credentials(self) -> None:
        """The cloud variables field is plaintext and model-readable: no
        assignment of any credential name may appear in it."""
        env = (CLAUDE / "web" / "environment.env.example").read_text(encoding="utf-8")
        for token in ("GH_TOKEN", "GRAPHITI_MCP_TOKEN", "INFISICAL_CLIENT_SECRET", "SONAR_TOKEN"):
            self.assertNotRegex(env, rf"^\s*{token}\s*=", f"{token} must not be assigned")


if __name__ == "__main__":
    unittest.main()
