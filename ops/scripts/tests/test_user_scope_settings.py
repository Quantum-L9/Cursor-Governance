from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "reconcile_claude_settings.py"
TEMPLATE = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
MANAGED = {"hooks", "permissions", "env", "skillOverrides", "workflowSizeGuideline"}


class UserScopeSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / ".claude").mkdir()
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _reconcile(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--template", str(TEMPLATE), *args],
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    @property
    def _settings(self) -> Path:
        return self.home / ".claude" / "settings.json"

    @property
    def _manifest(self) -> Path:
        return self.home / ".claude" / "settings.l9-manifest.json"

    # -- T-19: the hooks land in user scope ---------------------------------

    def test_every_hook_registration_lands_in_user_scope(self) -> None:
        result = self._reconcile()
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        commands = [
            entry["command"]
            for group in settings["hooks"].values()
            for matcher in group
            for entry in matcher["hooks"]
        ]
        # 15 registrations covering 14 distinct hook scripts: skill_usage_logger
        # is registered twice (PreToolUse and UserPromptExpansion). Four are
        # fail-closed gates; eleven are observers. bootstrap_capability_preflight
        # is the first SessionStart observer so capability ownership and the
        # hosted REST-only transport rule are present before agents choose tools.
        # session_deps_cloud.sh keeps its own concurrent SessionStart registration
        # and timeout rather than consuming the governance-hydration hook budget.
        self.assertEqual(len(commands), 15, "every L9 hook registration must reach user scope")
        self.assertEqual(sum("--class gate" in c for c in commands), 4)
        self.assertEqual(sum("--class observer" in c for c in commands), 11)
        names = {c.rsplit(" ", 1)[-1].rstrip("'") for c in commands}
        self.assertEqual(len(names), 14, "fourteen distinct hook scripts")
        session_start_commands = [
            entry["command"]
            for matcher in settings["hooks"]["SessionStart"]
            for entry in matcher["hooks"]
        ]
        self.assertIn("bootstrap_capability_preflight.sh", session_start_commands[0])

    def test_managed_keys_are_all_present(self) -> None:
        self._reconcile()
        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        for key in MANAGED:
            self.assertIn(key, settings, f"{key} must reach user scope")

    def test_hook_commands_resolve_governance_at_invocation_time(self) -> None:
        """Not at install time — the clone is ephemeral and re-created per env."""
        self._reconcile()
        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        for group in settings["hooks"].values():
            for matcher in group:
                for entry in matcher["hooks"]:
                    self.assertIn("$HOME/.cursor-governance", entry["command"])
                    self.assertNotIn(str(self.home), entry["command"])

    # -- T-20 / T-22: the manifest bounds what L9 owns ----------------------

    def test_preexisting_user_keys_survive_and_manifest_lists_only_ours(self) -> None:
        self._settings.write_text(
            json.dumps({"theme": "dark", "enabledPlugins": ["x"], "myOwnKey": 42}),
            encoding="utf-8",
        )
        self._reconcile()
        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        self.assertEqual(settings["theme"], "dark")
        self.assertEqual(settings["enabledPlugins"], ["x"])
        self.assertEqual(settings["myOwnKey"], 42)

        manifest = json.loads(self._manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "l9.claude-user-settings-manifest.v1")
        self.assertEqual(set(manifest["managed_keys"]), MANAGED)

    def test_removed_managed_keys_are_removed_but_user_keys_survive(self) -> None:
        first = self._reconcile()
        self.assertEqual(first.returncode, 0, first.stderr)
        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        settings["theme"] = "dark"
        settings["managed_stale"] = "old"
        self._settings.write_text(json.dumps(settings), encoding="utf-8")

        # Simulate the previous manifest having owned a key that the current
        # template no longer owns. Reconcile must remove only that stale key.
        manifest = json.loads(self._manifest.read_text(encoding="utf-8"))
        manifest["managed_keys"].append("managed_stale")
        self._manifest.write_text(json.dumps(manifest), encoding="utf-8")

        second = self._reconcile()
        self.assertEqual(second.returncode, 0, second.stderr)
        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        self.assertNotIn("managed_stale", settings)
        self.assertEqual(settings["theme"], "dark")

    def test_dry_run_does_not_write_settings_or_manifest(self) -> None:
        before = {"theme": "dark"}
        self._settings.write_text(json.dumps(before), encoding="utf-8")
        result = self._reconcile("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self._settings.read_text(encoding="utf-8")), before)
        self.assertFalse(self._manifest.exists())


if __name__ == "__main__":
    unittest.main()
