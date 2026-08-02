#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / ".." / "ops" / "scripts" / "reconcile_claude_l9_skills.py"
)
SCRIPT = SCRIPT.resolve()


class SkillReconciliationTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        for name in ("l9-alpha", "l9-beta"):
            skill = root / "skills" / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n")
        generated = root / "environment" / "claude-code" / "generated"
        generated.mkdir(parents=True)
        (generated / "skill-registry.json").write_text(
            json.dumps(
                {
                    "source_manifest_sha256": "fixture",
                    "skills": [
                        {"name": "l9-alpha", "path": "skills/l9-alpha"},
                        {"name": "l9-beta", "path": "skills/l9-beta"},
                    ],
                }
            )
        )
        rules = root / "environment" / "claude-code" / "rules"
        rules.mkdir(parents=True)
        (rules / "l9-skill-routing.md").write_text("# routing\n")

    def run_script(
        self, root: Path, workspace: Path, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--scope",
                "project",
                "--workspace",
                str(workspace),
                *extra,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_reconcile_preserves_unmanaged_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            workspace = base / "workspace"
            workspace.mkdir()
            self.make_fixture(root)
            local = workspace / ".claude" / "skills" / "local-skill"
            local.mkdir(parents=True)
            (local / "SKILL.md").write_text("local\n")

            result = self.run_script(root, workspace)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((workspace / ".claude" / "skills" / "l9-alpha").is_symlink())
            self.assertTrue((workspace / ".claude" / "skills" / "l9-beta").is_symlink())
            self.assertTrue(local.is_dir())
            self.assertTrue((workspace / ".claude" / "rules" / "l9-skill-routing.md").is_symlink())

            check = self.run_script(root, workspace, "--check")
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)

    def test_unmanaged_name_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            workspace = base / "workspace"
            workspace.mkdir()
            self.make_fixture(root)
            conflict = workspace / ".claude" / "skills" / "l9-alpha"
            conflict.mkdir(parents=True)
            (conflict / "SKILL.md").write_text("consumer-owned\n")

            result = self.run_script(root, workspace)
            self.assertEqual(1, result.returncode)
            self.assertIn("unmanaged-conflict:l9-alpha", result.stdout)
            self.assertEqual("consumer-owned\n", (conflict / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
