#!/usr/bin/env python3
"""Manus adapter tests: shared binding, identity, and retired memory transport."""

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

    def test_environment_identity_derives_from_the_registry(self) -> None:
        environment = (ADAPTER / "environment.env.example").read_text(encoding="utf-8")
        self.assertIn("L9_GOVERNANCE_SURFACE=manus", environment)
        self.assertIn("USER_ID=manus_agent", environment)
        self.assertIn("L9_MEMORY_AGENT_ID=manus", environment)
        self.assertIn("L9_MEMORY_SOURCE=manus", environment)
        self.assertNotIn("GRAPHITI_MCP_URL=", environment)
        self.assertNotIn("GRAPHITI_MCP_TOKEN=", environment)
        self.assertNotIn("INFISICAL_CLIENT_SECRET=", environment)

    def test_mcp_carrier_advertises_no_unprovisioned_remote_transport(self) -> None:
        connector = json.loads((ADAPTER / "mcp-connector.json").read_text(encoding="utf-8"))
        self.assertEqual(connector["transport"], "none")
        self.assertEqual(connector["status"], "retired-pending-memory-remote-transport")
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
