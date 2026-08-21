#!/usr/bin/env python3
"""The installer restores its mounts and verifies them (B-16, B-21, B-22).

Covers acceptance tests T-23, T-24, T-25.

None of these ran on the audited environment, because install.sh was never
reached: `.claude/rules` and `.claude/skills` were absent and `.git/info/exclude`
still held only git's default template — which is how the audit established that
the installer had not executed at all.

The shared bootstrap is stubbed so these exercise the ADAPTER's own wiring
without a network round trip; the shared half has its own suite.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
INSTALL = REPO / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"
BOOTSTRAP = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"


class InstallMountTests(unittest.TestCase):
    """Runs the real install.sh against the real governance tree."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        (self.home / ".claude").mkdir(parents=True)
        self.workspace = self.root / "consumer"
        self.workspace.mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        self.receipt = self.root / "bootstrap-state.json"
        self.addCleanup(self._tmp.cleanup)

    def _run(self, workspace: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update(
            {
                "HOME": str(self.home),
                "L9_CLAUDE_BOOTSTRAP_RECEIPT": str(self.receipt),
                # The shared bootstrap needs network and a uv sync; its own suite
                # covers it. Skipping it here keeps this test about the adapter.
                "L9_SKIP_SHARED_BOOTSTRAP": "1",
            }
        )
        env.pop("L9_GOVERNANCE_DIR", None)
        return subprocess.run(
            [
                "bash", str(INSTALL),
                "--governance", str(REPO),
                "--workspace", str(workspace or self.workspace),
                "--quiet",
            ],
            capture_output=True, text=True, env=env, check=False,
        )

    # -- T-24 ---------------------------------------------------------------

    def test_mounts_and_excludes_are_installed_and_verified(self) -> None:
        result = self._run()
        self.assertIn(result.returncode, (0, 1), result.stderr[-2000:])

        claude = self.workspace / ".claude"
        self.assertTrue((claude / "settings.json").is_file(), "settings triad not installed")
        self.assertTrue((claude / "hooks").is_dir(), "hooks not installed")

        exclude = self.workspace / ".git" / "info" / "exclude"
        self.assertTrue(exclude.is_file())
        body = exclude.read_text(encoding="utf-8")
        for glob in (".claude/skills/", ".claude/rules/"):
            self.assertIn(glob, body, f"{glob} must be excluded from the consumer repo")

    def test_install_is_idempotent(self) -> None:
        self._run()
        settings = self.workspace / ".claude" / "settings.json"
        first = settings.read_bytes()
        exclude = self.workspace / ".git" / "info" / "exclude"
        first_exclude = exclude.read_bytes()
        self._run()
        self.assertEqual(settings.read_bytes(), first)
        self.assertEqual(exclude.read_bytes(), first_exclude, "excludes must not accumulate")

    def test_receipt_records_the_wired_workspace(self) -> None:
        self._run()
        parsed = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(parsed["workspace"], str(self.workspace))

    # -- T-25 ---------------------------------------------------------------

    def test_unrelated_consumer_hooks_are_preserved(self) -> None:
        """SEO-Bot ships its own .claude/hooks/session-start.sh. Different file,
        different owner — the installer must not touch it."""
        hooks = self.workspace / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        foreign = hooks / "session-start.sh"
        foreign.write_text("#!/usr/bin/env bash\necho 'consumer owned'\n", encoding="utf-8")
        before = foreign.read_bytes()
        self._run()
        self.assertTrue(foreign.is_file(), "a consumer's own hook must survive install")
        self.assertEqual(foreign.read_bytes(), before, "a consumer's own hook must be byte-identical")


class LockedInterpreterPinTests(unittest.TestCase):
    """T-23: a pin mismatch is reported, not silently tolerated."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.gov = self.root / "gov"
        for sub in ("ops/scripts", "ops/autonomy", "ops/secrets", "kernels", ".venv/bin"):
            (self.gov / sub).mkdir(parents=True, exist_ok=True)
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic\n", encoding="utf-8")
        (self.gov / "ops" / "scripts" / "ensure_uv_environment.sh").write_text(
            "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
        )
        self.workspace = self.root / "ws"
        self.workspace.mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        self.addCleanup(self._tmp.cleanup)

    def _install_fake_python(self, version: str) -> None:
        python3 = self.gov / ".venv" / "bin" / "python3"
        python3.write_text(
            "#!/bin/sh\n"
            'case "$*" in\n'
            f"  *version_info*) echo '{version}' ;;\n"
            f"  --version) echo 'Python {version}.0' ;;\n"
            "  *) exit 0 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        python3.chmod(0o755)

    def _run(self) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("L9_GOVERNANCE_SURFACE", None)
        return subprocess.run(
            ["bash", str(BOOTSTRAP), "--surface", "claude-code",
             "--governance", str(self.gov), "--workspace", str(self.workspace)],
            capture_output=True, text=True, env=env, check=False,
        )

    def test_absent_locked_interpreter_is_reported_not_silently_replaced(self) -> None:
        (self.gov / ".python-version").write_text("3.12\n", encoding="utf-8")
        result = self._run()
        self.assertIn("locked interpreter ABSENT", result.stderr)
        self.assertIn("UNLOCKED FALLBACK", result.stderr)
        self.assertNotIn("Agent environment ready", result.stderr)

    def test_pin_mismatch_names_the_pin_and_the_fetch_host(self) -> None:
        (self.gov / ".python-version").write_text("3.12\n", encoding="utf-8")
        self._install_fake_python("3.11")
        result = self._run()
        self.assertIn("pins 3.12", result.stderr)
        self.assertIn("astral.sh", result.stderr)
        self.assertNotIn("Agent environment ready", result.stderr)

    def test_matching_pin_is_silent(self) -> None:
        (self.gov / ".python-version").write_text("3.12\n", encoding="utf-8")
        self._install_fake_python("3.12")
        result = self._run()
        self.assertNotIn("pins 3.12", result.stderr)
        self.assertIn("locked interpreter:", result.stderr)


if __name__ == "__main__":
    unittest.main()
