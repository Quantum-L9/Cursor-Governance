#!/usr/bin/env python3
"""Hosted autonomy overlay must not fork settings.template.json."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "environment" / "agents" / "adapters" / "claude-code"))

from overlay_hosted_settings_env import (  # noqa: E402
    REQUIRED_SURFACE,
    apply_overlay,
    overlay_hosted_settings,
    overlay_payload_from_environ,
)


class OverlayHostedSettingsEnvTests(unittest.TestCase):
    def test_copies_autonomy_keys_only(self) -> None:
        payload = overlay_payload_from_environ(
            {
                "L9_AUTONOMY_MAX_PARALLEL": "4",
                "GRAPHITI_MCP_URL": "https://example.invalid/should-not-copy",
                "L9_CAPABILITY_BROKER_URL": "https://broker.invalid",
            }
        )
        self.assertEqual(payload, {"L9_AUTONOMY_MAX_PARALLEL": "4"})

    def test_surface_id_cannot_be_overwritten(self) -> None:
        settings = {"env": {"L9_GOVERNANCE_SURFACE": "claude-code-mobile"}}
        apply_overlay(settings, {"L9_AUTONOMY_ENABLED": "false"})
        self.assertEqual(settings["env"]["L9_GOVERNANCE_SURFACE"], REQUIRED_SURFACE)
        self.assertEqual(settings["env"]["L9_AUTONOMY_ENABLED"], "false")

    def test_writes_workspace_and_user_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "ws"
            (workspace / ".claude").mkdir(parents=True)
            (workspace / ".claude" / "settings.json").write_text(
                json.dumps(
                    {
                        "env": {
                            "L9_GOVERNANCE_SURFACE": "claude-code",
                            "L9_AUTONOMY_MAX_PARALLEL": "480",
                        }
                    }
                ),
                encoding="utf-8",
            )
            home = base / "home"
            (home / ".claude").mkdir(parents=True)
            (home / ".claude" / "settings.json").write_text(
                json.dumps({"env": {"L9_GOVERNANCE_SURFACE": "claude-code"}}),
                encoding="utf-8",
            )
            written = overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={"L9_AUTONOMY_MAX_PARALLEL": "8"},
            )
            self.assertEqual(written, ["workspace", "user"])
            ws_settings = workspace / ".claude" / "settings.json"
            user_settings = home / ".claude" / "settings.json"
            ws_env = json.loads(ws_settings.read_text(encoding="utf-8"))["env"]
            user_env = json.loads(user_settings.read_text(encoding="utf-8"))["env"]
            self.assertEqual(ws_env["L9_AUTONOMY_MAX_PARALLEL"], "8")
            self.assertEqual(user_env["L9_AUTONOMY_MAX_PARALLEL"], "8")
            self.assertEqual(ws_env["L9_GOVERNANCE_SURFACE"], "claude-code")


if __name__ == "__main__":
    unittest.main()
