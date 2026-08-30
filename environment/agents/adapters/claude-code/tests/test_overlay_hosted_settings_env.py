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

    @staticmethod
    def _build(base: Path) -> tuple[Path, Path]:
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
        return workspace, home

    def test_writes_workspace_local_and_user_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            written = overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={"L9_AUTONOMY_MAX_PARALLEL": "8"},
            )
            self.assertEqual(written, ["workspace-local", "user"])
            local_env = json.loads(
                (workspace / ".claude" / "settings.local.json").read_text(encoding="utf-8")
            )["env"]
            user_env = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))[
                "env"
            ]
            self.assertEqual(local_env["L9_AUTONOMY_MAX_PARALLEL"], "8")
            self.assertEqual(user_env["L9_AUTONOMY_MAX_PARALLEL"], "8")
            self.assertEqual(local_env["L9_GOVERNANCE_SURFACE"], "claude-code")

    def test_tracked_workspace_settings_is_never_modified(self) -> None:
        """The regression this overlay caused: a tracked GENERATED artifact was
        patched in place, dirtying a clean checkout at every SessionStart."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            tracked = workspace / ".claude" / "settings.json"
            before = tracked.read_bytes()
            overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={
                    "L9_AUTONOMY_MAX_PARALLEL": "8",
                    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
                },
            )
            self.assertEqual(tracked.read_bytes(), before)

    def test_local_file_carries_complete_env_not_just_overlay_keys(self) -> None:
        """Written whole because Claude Code's precedence table does not say
        whether `env` merges key-by-key or is taken whole from the top scope.
        A fragment would drop L9_GOVERNANCE_SURFACE under the second reading."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={"L9_AUTONOMY_ENABLED": "true"},
            )
            local_env = json.loads(
                (workspace / ".claude" / "settings.local.json").read_text(encoding="utf-8")
            )["env"]
            # inherited from the tracked file, absent from the overlay payload
            self.assertEqual(local_env["L9_AUTONOMY_MAX_PARALLEL"], "480")
            self.assertEqual(local_env["L9_GOVERNANCE_SURFACE"], "claude-code")
            self.assertEqual(local_env["L9_AUTONOMY_ENABLED"], "true")

    def test_preserves_unrelated_keys_already_in_local_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            local = workspace / ".claude" / "settings.local.json"
            local.write_text(
                json.dumps({"permissions": {"allow": ["Bash(ls:*)"]}}), encoding="utf-8"
            )
            overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={"L9_AUTONOMY_ENABLED": "true"},
            )
            data = json.loads(local.read_text(encoding="utf-8"))
            self.assertEqual(data["permissions"], {"allow": ["Bash(ls:*)"]})
            self.assertEqual(data["env"]["L9_AUTONOMY_ENABLED"], "true")


if __name__ == "__main__":
    unittest.main()
