#!/usr/bin/env python3
"""User-scope settings survive a project directory that is not a repository.

Covers audit findings B-01, B-18, B-21 and acceptance tests T-19 … T-22, T-26.

The audited session's project directory was /home/user — the multi-repo parent,
not a repository. Claude Code read the committed per-repo .claude/settings.json
only as an additional-directory source: its ten hook registrations never
executed and its env block never applied. User scope is read regardless of
project directory, which makes it the floor that this class of session cannot
fall through.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))
RECONCILER = REPO / "ops" / "scripts" / "reconcile_claude_settings.py"
#: The authoritative resolver — one owner for "where is governance".
L9_ENV_LIB = REPO / "ops" / "scripts" / "resolve_governance_paths.sh"

MANAGED = ("hooks", "permissions", "skillOverrides", "env", "workflowSizeGuideline")


class UserScopeSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / ".claude").mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def _reconcile(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        return subprocess.run(
            ["python3", str(RECONCILER), "--root", str(REPO), "--skip-gov", *args],
            capture_output=True,
            text=True,
            env=env,
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
        # 10 registrations covering 9 distinct hook scripts: skill_usage_logger
        # is registered twice (PreToolUse and UserPromptExpansion).
        self.assertEqual(len(commands), 10, "every L9 hook registration must reach user scope")
        self.assertEqual(sum("--class gate" in c for c in commands), 3)
        self.assertEqual(sum("--class observer" in c for c in commands), 7)
        names = {c.rsplit(" ", 1)[-1].rstrip("'") for c in commands}
        self.assertEqual(len(names), 9, "nine distinct hook scripts")

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
        for key in MANAGED:
            self.assertIn(key, manifest["managed_keys"])
        for key in ("theme", "enabledPlugins", "myOwnKey"):
            self.assertNotIn(key, manifest["managed_keys"])

    def test_uninstall_removes_exactly_the_manifest_set(self) -> None:
        self._settings.write_text(json.dumps({"theme": "dark", "myOwnKey": 42}), encoding="utf-8")
        self._reconcile()
        result = self._reconcile("--uninstall-user")
        self.assertEqual(result.returncode, 0, result.stderr)

        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        self.assertEqual(settings["theme"], "dark")
        self.assertEqual(settings["myOwnKey"], 42)
        for key in MANAGED:
            self.assertNotIn(key, settings, f"{key} must be removed on uninstall")
        self.assertFalse(self._manifest.exists())

    def test_uninstall_without_a_manifest_refuses_to_guess(self) -> None:
        self._settings.write_text(json.dumps({"hooks": {"mine": []}}), encoding="utf-8")
        result = self._reconcile("--uninstall-user")
        self.assertEqual(result.returncode, 0)
        settings = json.loads(self._settings.read_text(encoding="utf-8"))
        self.assertIn("hooks", settings, "an unclaimed key must not be stripped")

    # -- T-21: idempotence --------------------------------------------------

    def test_second_run_produces_no_change(self) -> None:
        self._reconcile()
        first = self._settings.read_bytes()
        first_manifest = self._manifest.read_bytes()
        self._reconcile()
        self.assertEqual(self._settings.read_bytes(), first)
        self.assertEqual(self._manifest.read_bytes(), first_manifest)

    def test_check_mode_reports_drift_without_writing(self) -> None:
        result = self._reconcile("--check")
        self.assertNotEqual(result.returncode, 0, "missing settings is drift")
        self.assertFalse(self._settings.exists(), "--check must not write")


class NonLoginShellEnvTests(unittest.TestCase):
    """T-26: the durable env must resolve in a shell that reads no profile."""

    def _resolve(self, home: Path, env_file: Path | None) -> str:
        script = f'source "{L9_ENV_LIB}"; l9_governance_dir'
        env = {"HOME": str(home), "PATH": os.environ.get("PATH", "")}
        if env_file is not None:
            env["L9_SESSION_ENV_FILE"] = str(env_file)
        # `bash -c` with no -l and no -i: no ~/.profile, no ~/.bashrc.
        return subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True, env=env, check=True
        ).stdout.strip()

    def test_non_login_shell_reads_the_durable_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env_file = home / "cloud-session.env"
            env_file.write_text("export L9_GOVERNANCE_DIR=/custom/gov\n", encoding="utf-8")
            self.assertEqual(self._resolve(home, env_file), "/custom/gov")

    def test_falls_back_to_the_contract_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual(self._resolve(home, home / "absent.env"), f"{home}/.cursor-governance")

    def test_unexpanded_home_literal_is_refused(self) -> None:
        """The .env-format field performs no expansion; that value names nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env_file = home / "cloud-session.env"
            env_file.write_text(
                "export L9_GOVERNANCE_DIR='$HOME/.cursor-governance'\n", encoding="utf-8"
            )
            self.assertEqual(self._resolve(home, env_file), f"{home}/.cursor-governance")


if __name__ == "__main__":
    unittest.main()
