#!/usr/bin/env python3
"""Tests for secret-safe Custom MCP draft rendering."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
RENDERER = ADAPTER / "render_infisical_mcp_connector.py"


class RenderInfisicalConnectorTests(unittest.TestCase):
    def _command(self, secret_file: Path, output: Path) -> list[str]:
        return [
            sys.executable,
            str(RENDERER),
            "--client-id",
            "machine-client-id",
            "--client-secret-file",
            str(secret_file),
            "--project-id",
            "project-id",
            "--output",
            str(output),
        ]

    def test_renderer_writes_private_connector_draft_without_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret_file = root / "client-secret"
            output = root / "connector.json"
            secret_file.write_text("renderer-test-secret", encoding="utf-8")
            os.chmod(secret_file, 0o600)
            result = subprocess.run(
                self._command(secret_file, output), capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            draft = json.loads(output.read_text(encoding="utf-8"))
            server = draft["mcpServers"]["l9-manus-infisical"]
            self.assertEqual(server["command"], "bash")
            self.assertIn("serve_infisical_mcp.sh", server["args"][0])
            self.assertEqual(
                server["env"]["L9_MANUS_INFISICAL_CLIENT_SECRET"], "renderer-test-secret"
            )

    def test_renderer_refuses_permissive_secret_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret_file = root / "client-secret"
            output = root / "connector.json"
            secret_file.write_text("renderer-test-secret", encoding="utf-8")
            os.chmod(secret_file, 0o644)
            result = subprocess.run(
                self._command(secret_file, output), capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("renderer-test-secret", result.stdout + result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
