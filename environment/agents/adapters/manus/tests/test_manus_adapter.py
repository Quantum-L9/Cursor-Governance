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

    def test_mcp_carrier_advertises_no_unprovisioned_remote_transport(self) -> None:
        connector = json.loads((ADAPTER / "mcp-connector.json").read_text(encoding="utf-8"))
        self.assertEqual(connector["transport"], "none")
        self.assertEqual(connector["status"], "retired-pending-memory-remote-transport")
        self.assertNotIn("mcpServers", connector)
        self.assertNotIn("url", connector)
        self.assertNotIn("headers", connector)

    def test_native_infisical_carrier_is_local_and_secret_free(self) -> None:
        connector = json.loads(
            (ADAPTER / "infisical-mcp-connector.json").read_text(encoding="utf-8")
        )
        self.assertEqual(connector["name"], "l9-manus-infisical")
        self.assertEqual(connector["transport"], "stdio")
        self.assertEqual(connector["secret_delivery"], "encrypted-connector-env")
        self.assertNotIn("url", connector)
        self.assertNotIn("headers", connector)
        self.assertNotIn("env", connector)

    def test_installer_is_syntax_valid_and_validates_native_carrier(self) -> None:
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
        self.assertIn("validate_manus_adapter.py", text)
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
