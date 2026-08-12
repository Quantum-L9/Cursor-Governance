#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "CANONICAL_LAW.md").is_file() or (parent / ".git").exists():
            return parent
    raise RuntimeError(f"repo root not found from {start}")


SCRIPT = (
    _repo_root(Path(__file__).resolve().parent)
    / "ops"
    / "scripts"
    / "reconcile_claude_l9_skills.py"
)


class SkillReconciliationTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        for name in ("l9-alpha", "l9-beta"):
            skill = root / "skills" / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n")
        generated = root / "ops" / "generated"
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
        rules = root / "environment" / "generated" / "llm-rules"
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
            # Rules are whole-dir symlinked by reconcile_llm_rule_adapters.py, not per-file here.

            check = self.run_script(root, workspace, "--check")
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)

    def test_l9_directory_duplicate_replaced_with_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            workspace = base / "workspace"
            workspace.mkdir()
            self.make_fixture(root)
            conflict = workspace / ".claude" / "skills" / "l9-alpha"
            conflict.mkdir(parents=True)
            (conflict / "SKILL.md").write_text("consumer-owned-copy\n")

            result = self.run_script(root, workspace)
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            link = workspace / ".claude" / "skills" / "l9-alpha"
            self.assertTrue(link.is_symlink())
            self.assertEqual(
                link.resolve(),
                (root / "skills" / "l9-alpha").resolve(),
            )

    def test_non_l9_unmanaged_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            workspace = base / "workspace"
            workspace.mkdir()
            self.make_fixture(root)
            # Inject a non-l9 registry name to prove consumer-owned non-l9 still fails closed.
            registry = root / "ops" / "generated" / "skill-registry.json"
            data = json.loads(registry.read_text())
            data["skills"].append({"name": "plasticos-local", "path": "skills/plasticos-local"})
            registry.write_text(json.dumps(data))
            skill = root / "skills" / "plasticos-local"
            skill.mkdir()
            (skill / "SKILL.md").write_text("---\nname: plasticos-local\ndescription: x\n---\n")
            conflict = workspace / ".claude" / "skills" / "plasticos-local"
            conflict.mkdir(parents=True)
            (conflict / "SKILL.md").write_text("consumer-owned\n")

            result = self.run_script(root, workspace)
            self.assertEqual(1, result.returncode)
            self.assertIn("unmanaged-conflict:plasticos-local", result.stdout)
            self.assertEqual("consumer-owned\n", (conflict / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
