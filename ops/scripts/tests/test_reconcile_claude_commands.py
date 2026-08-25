#!/usr/bin/env python3
"""Unit tests for the Claude command projection (reconcile_claude_commands)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from reconcile_claude_commands import STATE_NAME, reconcile  # noqa: E402


def make_root(base: Path) -> Path:
    root = base / "governance"
    commands = root / "commands"
    commands.mkdir(parents=True)
    (commands / "alpha.md").write_text("# /alpha protocol\n", encoding="utf-8")
    (commands / "beta.md").write_text("# /beta protocol\n", encoding="utf-8")
    (commands / "l9-demo.md").write_text("# /l9-demo protocol\n", encoding="utf-8")
    write_manifest(
        root,
        [
            {"slash": "/alpha", "file": "commands/alpha.md", "enabled": True},
            {"slash": "/beta", "file": "commands/beta.md", "enabled": False},
            {"slash": "/l9-demo", "file": "commands/l9-demo.md", "enabled": True},
        ],
    )
    generated = root / "ops" / "generated"
    generated.mkdir(parents=True)
    (generated / "skill-registry.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_manifest_sha256": "test",
                "skills": [{"name": "l9-demo", "path": "skills/l9-demo"}],
            }
        ),
        encoding="utf-8",
    )
    return root


def write_manifest(root: Path, entries: list[dict]) -> None:
    lines = ["version: 1", "commands:"]
    for entry in entries:
        lines.append(f"- slash: {entry['slash']}")
        lines.append(f"  file: {entry['file']}")
        lines.append(f"  enabled: {'true' if entry['enabled'] else 'false'}")
    (root / "commands" / "COMMANDS_MANIFEST.yaml").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


class ReconcileClaudeCommandsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = make_root(base)
        self.ws = base / "consumer"
        self.ws.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def project(self, **kwargs):
        return reconcile(self.root, workspace=self.ws, scopes=("project",), **kwargs)

    def target(self) -> Path:
        return self.ws / ".claude" / "commands"

    def test_enabled_filtering_and_collision(self) -> None:
        payload = self.project()
        result = payload["results"][0]
        # /alpha projected; /beta disabled; /l9-demo collides with the skill.
        link = self.target() / "alpha.md"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (self.root / "commands" / "alpha.md").resolve())
        self.assertFalse((self.target() / "beta.md").exists())
        self.assertFalse((self.target() / "l9-demo.md").exists())
        self.assertIn("command-skill-collision:l9-demo", result["collisions"])
        self.assertEqual(result["conflicts"], [])

    def test_idempotent_and_check_clean(self) -> None:
        self.project()
        payload = self.project(check=True)
        result = payload["results"][0]
        self.assertEqual(result["drift"], [])
        self.assertEqual(result["conflicts"], [])
        self.assertIn("alpha", result["current"])

    def test_unmanaged_consumer_command_preserved(self) -> None:
        target = self.target()
        target.mkdir(parents=True)
        consumer = target / "alpha.md"
        consumer.write_text("# my own alpha\n", encoding="utf-8")
        payload = self.project()
        result = payload["results"][0]
        self.assertIn("unmanaged-conflict:alpha", result["conflicts"])
        self.assertEqual(consumer.read_text(encoding="utf-8"), "# my own alpha\n")

    def test_stale_managed_command_removed(self) -> None:
        self.project()
        self.assertTrue((self.target() / "alpha.md").is_symlink())
        # Disable alpha in the manifest — the projection must reclaim the link.
        write_manifest(
            self.root,
            [{"slash": "/alpha", "file": "commands/alpha.md", "enabled": False}],
        )
        payload = self.project()
        result = payload["results"][0]
        self.assertIn("alpha", result["removed"])
        self.assertFalse((self.target() / "alpha.md").exists())

    def test_state_lost_ssot_link_repaired(self) -> None:
        """A cache reset that loses the state file must not orphan SSOT links."""
        self.project()
        state = self.target() / STATE_NAME
        state.unlink()
        link = self.target() / "alpha.md"
        link.unlink()
        link.symlink_to(self.root / "commands" / "beta.md")  # wrong SSOT target
        payload = self.project()
        result = payload["results"][0]
        self.assertIn("alpha", result["created"])
        self.assertEqual(link.resolve(), (self.root / "commands" / "alpha.md").resolve())

    def test_duplicate_command_fails_closed(self) -> None:
        write_manifest(
            self.root,
            [
                {"slash": "/alpha", "file": "commands/alpha.md", "enabled": True},
                {"slash": "/alpha", "file": "commands/beta.md", "enabled": True},
            ],
        )
        payload = self.project()
        result = payload["results"][0]
        self.assertIn("duplicate-command:alpha", result["conflicts"])


if __name__ == "__main__":
    unittest.main()
