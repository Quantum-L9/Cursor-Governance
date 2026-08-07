#!/usr/bin/env python3
"""Unit tests for llm-rules projection and safe rule-adapter mounts."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
GOV_ROOT = SCRIPTS.parent.parent
sys.path.insert(0, str(SCRIPTS))

from project_llm_rules import check_projection, materialize  # noqa: E402
from reconcile_llm_rule_adapters import (  # noqa: E402
    assert_safe_mount,
    expand_path,
    reconcile_adapters,
)


class ProjectLlmRulesTests(unittest.TestCase):
    def make_root(self, base: Path) -> Path:
        root = base / "governance"
        rules = root / "rules"
        rules.mkdir(parents=True)
        (root / "ops" / "config").mkdir(parents=True)
        (root / "ops" / "config" / "llm_rules_projection.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "source_relative: rules",
                    "output_relative: environment/generated/llm-rules",
                    "deny_stems:",
                    "  - 84-cursor-governance-wiring",
                    "aliases:",
                    "  23-l9-skill-routing: l9-skill-routing.md",
                    "project_agent_requested: false",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (rules / "00-always.mdc").write_text(
            "---\ndescription: always rule\nalwaysApply: true\n---\n\n# Always\n",
            encoding="utf-8",
        )
        (rules / "20-paths.mdc").write_text(
            "---\n"
            "description: paths rule\n"
            "globs:\n"
            '  - "src/**/*.py"\n'
            "alwaysApply: false\n"
            "---\n\n"
            "# Paths\n",
            encoding="utf-8",
        )
        (rules / "88-agent.mdc").write_text(
            "---\ndescription: agent requested\nalwaysApply: false\n---\n\n# Agent\n",
            encoding="utf-8",
        )
        (rules / "84-cursor-governance-wiring.mdc").write_text(
            "---\ndescription: cursor only\nalwaysApply: true\n---\n\n# Cursor\n",
            encoding="utf-8",
        )
        (rules / "23-l9-skill-routing.mdc").write_text(
            "---\ndescription: routing\nalwaysApply: true\n---\n\n# Routing\n",
            encoding="utf-8",
        )
        autonomy = root / "ops" / "autonomy"
        autonomy.mkdir(parents=True)
        for name in ("profile_loader.py", "surface_profile.yaml"):
            shutil.copy2(GOV_ROOT / "ops" / "autonomy" / name, autonomy / name)
        return root

    def test_projection_classes_alias_deny_skip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(Path(temp))
            result = materialize(root)
            out = root / "environment" / "generated" / "llm-rules"
            self.assertTrue((out / "00-always.md").is_file())
            self.assertTrue((out / "20-paths.md").is_file())
            self.assertTrue((out / "l9-skill-routing.md").is_file())
            self.assertTrue((out / "zz-autonomy-surface-override.md").is_file())
            self.assertFalse((out / "23-l9-skill-routing.md").exists())
            self.assertFalse((out / "84-cursor-governance-wiring.md").exists())
            self.assertFalse((out / "88-agent.md").exists())
            paths_text = (out / "20-paths.md").read_text(encoding="utf-8")
            self.assertIn("paths:", paths_text)
            self.assertIn("src/**/*.py", paths_text)
            self.assertIn("generated-from: rules/20-paths.mdc", paths_text)
            manifest = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["projected"], 4)
            self.assertEqual(manifest["summary"]["denied"], 1)
            self.assertEqual(manifest["summary"]["skipped_agent_requested"], 1)
            self.assertEqual(result["summary"]["projected"], 4)
            self.assertEqual([], check_projection(root))

    def test_check_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(Path(temp))
            materialize(root)
            target = root / "environment" / "generated" / "llm-rules" / "00-always.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\n# mutated\n", encoding="utf-8"
            )
            errors = check_projection(root)
            self.assertTrue(any("drift: 00-always.md" in item for item in errors))


class RuleAdapterSafetyTests(unittest.TestCase):
    def test_expand_path_does_not_follow_final_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "workspace"
            ssot = base / "governance" / "rules"
            ssot.mkdir(parents=True)
            (ssot / "00.mdc").write_text("x\n", encoding="utf-8")
            mount = workspace / ".claude" / "rules"
            mount.parent.mkdir(parents=True)
            mount.symlink_to(ssot, target_is_directory=True)
            expanded = expand_path(".claude/rules", workspace)
            self.assertEqual(expanded.name, "rules")
            self.assertEqual(expanded.parent.resolve(), mount.parent.resolve())
            # Final component must remain the mount point, not the SSOT target.
            self.assertNotEqual(expanded.resolve(), expanded)
            self.assertEqual(expanded.resolve(), ssot.resolve())

    def test_quiet_emits_json(self) -> None:
        import json
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            workspace = base / "workspace"
            gen = root / "environment" / "generated" / "llm-rules"
            gen.mkdir(parents=True)
            (gen / "x.md").write_text("# x\n", encoding="utf-8")
            (root / "environment" / "skill-adapters").mkdir(parents=True)
            (root / "environment" / "skill-adapters" / "LLM_RULE_ADAPTER_ROOTS.yaml").write_text(
                "schema_version: 1\nssot_relative: environment/generated/llm-rules\n"
                "mode: directory-symlink\nadapters:\n"
                "  - id: claude-code-user\n    surface: claude-code\n    kind: user\n"
                f"    path: {workspace / '.claude' / 'rules'}\n"
            )
            script = Path(__file__).resolve().parents[1] / "reconcile_llm_rule_adapters.py"
            create = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--root",
                    str(root),
                    "--workspace",
                    str(workspace),
                    "--quiet",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, create.returncode, create.stderr + create.stdout)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--root",
                    str(root),
                    "--workspace",
                    str(workspace),
                    "--check",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, proc.returncode, proc.stderr + proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertEqual(1, len(payload["results"]))
            self.assertEqual("ok", payload["results"][0]["status"])

    def test_refuse_protected_ssot_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "governance"
            rules = root / "rules"
            gen = root / "environment" / "generated" / "llm-rules"
            rules.mkdir(parents=True)
            gen.mkdir(parents=True)
            with self.assertRaises(RuntimeError):
                assert_safe_mount(rules, gen, root)

    def test_reconcile_retargets_project_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            workspace = base / "workspace"
            gen = root / "environment" / "generated" / "llm-rules"
            rules = root / "rules"
            gen.mkdir(parents=True)
            rules.mkdir(parents=True)
            (gen / "00-global.md").write_text("# ok\n", encoding="utf-8")
            (root / "environment" / "skill-adapters").mkdir(parents=True)
            (root / "environment" / "skill-adapters" / "LLM_RULE_ADAPTER_ROOTS.yaml").write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "ssot_relative: environment/generated/llm-rules",
                        "mode: directory-symlink",
                        "adapters:",
                        "  - id: claude-code-project",
                        "    surface: claude-code",
                        "    kind: project",
                        "    path: .claude/rules",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            mount = workspace / ".claude" / "rules"
            mount.parent.mkdir(parents=True)
            mount.symlink_to(rules, target_is_directory=True)

            payload = reconcile_adapters(root, workspace=workspace, check=False)
            self.assertEqual(1, len(payload["results"]))
            self.assertEqual("ok", payload["results"][0]["status"])
            self.assertTrue(mount.is_symlink())
            self.assertEqual(mount.resolve(), gen.resolve())
            self.assertTrue(rules.is_dir())
            self.assertFalse(rules.is_symlink())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
