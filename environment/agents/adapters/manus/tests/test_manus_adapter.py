#!/usr/bin/env python3
"""Manus adapter tests: shared binding, identity, and governance MCP boundary."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPOSITORY = ADAPTER.parents[3]
sys.path.insert(0, str(ADAPTER))

validator = importlib.import_module("validate_manus_adapter")


class ManusAdapterContractTests(unittest.TestCase):
    def test_pack_passes_its_structural_validator(self) -> None:
        self.assertEqual(validator.validate(REPOSITORY), [])

    def test_bootstrap_states_the_repository_authority_order(self) -> None:
        bootstrap = (ADAPTER / "session_bootstrap.md").read_text(encoding="utf-8")
        self.assertEqual(validator.authority_order_errors(bootstrap), [])
        self.assertEqual(
            validator.AUTHORITY_ORDER,
            ("CANONICAL_LAW.md", "ops/autonomy/surface_profile.yaml", "AGENTS.md", "SKILL.md"),
        )

    def test_authority_order_check_rejects_agents_before_the_surface_profile(self) -> None:
        # Regression for the audited defect: every marker was present, but
        # AGENTS.md was placed ahead of the Autonomy Surface Profile SSOT.
        # The exact shape of the audited paragraph: the profile is named only
        # after AGENTS.md and SKILL.md, inside the same paragraph.
        swapped = (
            "Apply authority in this order: `CANONICAL_LAW.md`, then `AGENTS.md`, then the\n"
            "applicable `SKILL.md`, then this document.\n"
            "The shared autonomy policy is `ops/autonomy/surface_profile.yaml`.\n"
        )
        errors = validator.authority_order_errors(swapped)
        self.assertEqual(len(errors), 1)
        self.assertIn("authority order is wrong", errors[0])

        omitted = (
            "Apply authority in this order: `CANONICAL_LAW.md`, then `AGENTS.md`, then the\n"
            "applicable `SKILL.md`, then this document.\n"
            "\n"
            "The shared autonomy policy is `ops/autonomy/surface_profile.yaml`.\n"
        )
        errors = validator.authority_order_errors(omitted)
        self.assertEqual(len(errors), 1)
        self.assertIn("omits ops/autonomy/surface_profile.yaml", errors[0])

        reordered = (
            "Apply authority in this order: `CANONICAL_LAW.md`, then `AGENTS.md`, then\n"
            "`ops/autonomy/surface_profile.yaml`, then the applicable `SKILL.md`.\n"
        )
        errors = validator.authority_order_errors(reordered)
        self.assertEqual(len(errors), 1)
        self.assertIn("authority order is wrong", errors[0])

        missing_sentence = "The shared autonomy policy is `ops/autonomy/surface_profile.yaml`.\n"
        self.assertEqual(len(validator.authority_order_errors(missing_sentence)), 1)

    def test_environment_identity_derives_from_the_registry(self) -> None:
        environment = (ADAPTER / "environment.env.example").read_text(encoding="utf-8")
        self.assertIn("L9_GOVERNANCE_SURFACE=manus", environment)
        self.assertIn("USER_ID=manus_agent", environment)
        self.assertIn("L9_MEMORY_AGENT_ID=manus", environment)
        self.assertIn("L9_MEMORY_SOURCE=manus", environment)
        self.assertNotIn("GRAPHITI_MCP_URL=", environment)
        self.assertNotIn("GRAPHITI_MCP_TOKEN=", environment)
        self.assertNotIn("INFISICAL_CLIENT_SECRET=", environment)

    def test_mcp_carrier_declares_the_bounded_memory_lifecycle_boundary(self) -> None:
        connector = json.loads((ADAPTER / "mcp-connector.json").read_text(encoding="utf-8"))
        self.assertEqual(connector["transport"], "streamable-http")
        self.assertEqual(connector["endpoint_path"], "/mcp")
        self.assertEqual(connector["health_path"], "/health")
        self.assertEqual(
            connector["memory"],
            {
                "agent_lane": "package-owned-l9-graphite-memory-mcp-or-cli",
                "lifecycle": "bearer-protected-canonical-hydrate-and-close-only",
                "fallback": "fail-closed-no-local-operator-identity",
            },
        )
        self.assertTrue(connector["safety"]["no_shell"])
        self.assertTrue(connector["safety"]["no_credentials"])
        self.assertTrue(connector["safety"]["no_arbitrary_file_access"])
        self.assertTrue(connector["safety"]["no_repository_write_tools"])
        self.assertNotIn("mcpServers", connector)
        self.assertNotIn("url", connector)
        self.assertNotIn("headers", connector)

    def test_memory_mcp_carrier_is_separate_and_package_owned(self) -> None:
        connector = json.loads((ADAPTER / "memory-mcp-connector.json").read_text(encoding="utf-8"))
        self.assertEqual(connector["name"], "l9-memory-manus")
        self.assertEqual(connector["transport"], "stdio")
        self.assertEqual(connector["command"], "rendered-locally")
        self.assertEqual(
            connector["authentication"],
            {
                "mode": "inherited-signed-agent-assertion",
                "agent_id": "manus",
                "human_door": "forbidden",
                "local_operator_fallback": "forbidden",
            },
        )
        self.assertEqual(connector["package"]["distribution"], "l9-graphite-memory")
        self.assertEqual(connector["package"]["entrypoint"], "l9-memory-server --transport stdio")
        self.assertTrue(connector["scope"]["ordinary_agent_reads"])
        self.assertTrue(connector["scope"]["cold_safe_agent_writes"])
        self.assertTrue(connector["scope"]["governed_writes_and_phase_locks"])
        self.assertFalse(connector["scope"]["lifecycle_start_close"])
        self.assertNotIn("mcpServers", connector)
        self.assertNotIn("url", connector)
        self.assertNotIn("headers", connector)

    def test_installer_is_syntax_valid_and_calls_the_shared_bootstrap(self) -> None:
        installer = ADAPTER / "install.sh"
        syntax = subprocess.run(
            ["bash", "-n", str(installer)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        help_output = subprocess.run(
            ["bash", str(installer), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_output.returncode, 0, help_output.stderr)
        text = installer.read_text(encoding="utf-8")
        self.assertIn("bootstrap_agent_environment.sh", text)
        self.assertIn("--surface manus", text)

    def test_mcp_launcher_uses_the_locked_interpreter(self) -> None:
        launcher = ADAPTER / "serve_mcp.sh"
        syntax = subprocess.run(
            ["bash", "-n", str(launcher)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        text = launcher.read_text(encoding="utf-8")
        self.assertIn(".venv/bin/python", text)
        self.assertIn("mcp_server.py", text)
        self.assertIn("export_agent_assertion_env.sh", text)

    def test_memory_mcp_launcher_fails_closed_without_signed_assertion(self) -> None:
        launcher = ADAPTER / "serve_memory_mcp.sh"
        syntax = subprocess.run(
            ["bash", "-n", str(launcher)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        result = subprocess.run(
            ["bash", str(launcher), "--governance", str(REPOSITORY)],
            capture_output=True,
            text=True,
            check=False,
            env={"HOME": str(Path.home()), "PATH": "/usr/bin:/bin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("signed Manus memory door unavailable", result.stderr)
        text = launcher.read_text(encoding="utf-8")
        self.assertIn("l9-memory-server", text)
        self.assertIn("export_agent_assertion_env.sh", text)
        self.assertIn("local-operator compatibility principal", text)

    def test_memory_mcp_renderer_emits_no_secret_stdio_draft(self) -> None:
        renderer = importlib.import_module("render_memory_mcp_connector")
        draft = renderer.draft(REPOSITORY)
        server = draft["mcpServers"]["l9-memory-manus"]
        self.assertEqual(server["command"], str(ADAPTER / "serve_memory_mcp.sh"))
        self.assertEqual(server["args"], ["--governance", str(REPOSITORY)])
        self.assertNotIn("env", server)
        self.assertNotIn("headers", server)

    def test_installer_refuses_a_non_repository_before_bootstrapping(self) -> None:
        installer = ADAPTER / "install.sh"
        with tempfile.TemporaryDirectory() as workspace:
            result = subprocess.run(
                ["bash", str(installer), "--workspace", workspace, "--quiet"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a git work tree", result.stderr)


if __name__ == "__main__":
    unittest.main()
