#!/usr/bin/env python3
"""Cursor adapter install contract: receipt shape, $HOME refusal, thinness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPO = ADAPTER.parents[3]
INSTALL = ADAPTER / "install.sh"

sys.path.insert(0, str(REPO / "ops" / "scripts"))

import claude_bootstrap_receipt as receipt_reader  # noqa: E402


def _run(args: list[str], env_extra: dict[str, str] | None = None):
    env = dict(os.environ)
    # Receipt-contract runs skip the shared bootstrap (recorded as UNKNOWN in
    # the receipt — the state is honest, not green).
    env.setdefault("L9_CURSOR_SKIP_SHARED_BOOTSTRAP", "1")
    env.update(env_extra or {})
    return subprocess.run(
        ["bash", str(INSTALL), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=env,
    )


class WorkspaceRefusalTests(unittest.TestCase):
    def test_home_workspace_is_refused_by_name(self) -> None:
        proc = _run(["--workspace", str(Path.home()), "--quiet"])
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("refusing --workspace $HOME", proc.stderr)

    def test_non_git_workspace_is_refused(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            proc = _run(["--workspace", tmp, "--quiet"])
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("not a git work tree", proc.stderr)

    def test_shared_bootstrap_also_refuses_home_workspace(self) -> None:
        """The refusal lives in the shared brain too: every surface's installer
        goes through bootstrap_agent_environment.sh, and a $HOME workspace is
        how the Claude receipt got poisoned in the first place."""
        shared = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"
        proc = subprocess.run(
            [
                "bash",
                str(shared),
                "--surface",
                "cursor",
                "--governance",
                str(REPO),
                "--workspace",
                str(Path.home()),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("refusing --workspace $HOME", proc.stderr)


class ReceiptContractTests(unittest.TestCase):
    def test_receipt_written_with_schema_surface_and_workspace(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "bootstrap-state.json"
            proc = _run(
                ["--workspace", str(REPO), "--quiet"],
                env_extra={"L9_CURSOR_BOOTSTRAP_RECEIPT": str(receipt)},
            )
            self.assertIn(proc.returncode, (0, 6), proc.stderr)
            data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "l9.cursor-bootstrap.v1")
        self.assertEqual(data["surface"], "cursor")
        self.assertEqual(data["workspace"], str(REPO))
        self.assertNotEqual(data["workspace"], str(Path.home()))
        self.assertIn(data["state"], ("READY", "DEGRADED", "FAILED"))
        self.assertIn("generated_at", data)
        self.assertIn("governance_revision", data)

    def test_shared_reader_reads_the_cursor_receipt(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "bootstrap-state.json"
            _run(
                ["--workspace", str(REPO), "--quiet"],
                env_extra={"L9_CURSOR_BOOTSTRAP_RECEIPT": str(receipt)},
            )
            raw = json.loads(receipt.read_text(encoding="utf-8"))
            # Pin the revision the receipt was produced against: this test
            # verifies classification, not the (separately owned) supersession
            # rule that fires when the live SSOT HEAD differs from a
            # workspace-checkout HEAD.
            result = receipt_reader.read(
                receipt,
                surface="cursor",
                governance_revision=raw["governance_revision"],
            )
        # Skipped shared bootstrap records DEGRADED honestly; the reader must
        # classify it (never never_ran, never a parse failure).
        self.assertIn(result["state"], ("ready", "degraded", "failed", "blocked"))
        self.assertEqual(result.get("workspace"), str(REPO))

    def test_check_mode_does_not_touch_the_session_receipt(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".cursor").mkdir()
            proc = subprocess.run(
                ["bash", str(INSTALL), "--workspace", str(REPO), "--check", "--quiet"],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
                env={
                    **os.environ,
                    "HOME": str(home),
                    "L9_CURSOR_SKIP_SHARED_BOOTSTRAP": "1",
                },
            )
            self.assertIn(proc.returncode, (0, 6), proc.stderr)
            self.assertTrue((home / ".l9" / "cursor" / "bootstrap-check.json").is_file())
            self.assertFalse((home / ".l9" / "cursor" / "bootstrap-state.json").exists())


class ThinnessTests(unittest.TestCase):
    """ADAPTER_CONTRACT: the adapter binds shared capability, never re-owns it."""

    def test_install_never_references_claude_paths(self) -> None:
        text = INSTALL.read_text(encoding="utf-8")
        self.assertNotIn(".l9/claude", text)
        self.assertNotIn("claude-code/install.sh", text)

    def test_no_credential_values_in_pack(self) -> None:
        for name in ("environment.env.example", "mcp.template.json"):
            text = (ADAPTER / name).read_text(encoding="utf-8")
            for line in text.splitlines():
                if "GRAPHITI_MCP_TOKEN" in line:
                    self.assertNotRegex(line, r"GRAPHITI_MCP_TOKEN\s*=\s*\S")

    def test_mcp_template_has_no_broker_url(self) -> None:
        data = json.loads((ADAPTER / "mcp.template.json").read_text(encoding="utf-8"))
        self.assertNotIn("L9_CAPABILITY_BROKER_URL", json.dumps(data))
        server = data["mcpServers"]["graphiti-memory"]
        self.assertEqual(server["url"], "${GRAPHITI_MCP_URL}")


if __name__ == "__main__":
    unittest.main()
