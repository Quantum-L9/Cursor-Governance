#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


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


sys.path.insert(0, str(SCRIPT.parent))
import reconcile_claude_l9_skills as skills_mod  # noqa: E402


class CoverageCensusTests(unittest.TestCase):
    """Issue #690: unique canonical coverage, not a SKILL.md sum across paths."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.root = base / "governance"
        self.workspace = base / "workspace"
        self.home_skills = base / "home" / ".claude" / "skills"
        self.workspace.mkdir()
        self.home_skills.mkdir(parents=True)
        self.registry: dict[str, Any] = {"source_manifest_sha256": "fixture", "skills": []}
        self.add_skill("l9-alpha", "model_allowed")
        self.add_skill("l9-beta", "explicit_only")

    def add_skill(self, name: str, invocation: str) -> None:
        skill = self.root / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: t\n---\n")
        self.registry["skills"].append(
            {"name": name, "path": f"skills/{name}", "invocation": invocation}
        )

    @property
    def project_skills(self) -> Path:
        return self.workspace / ".claude" / "skills"

    def project(self, target: Path, *, check: bool = False) -> skills_mod.Result:
        return skills_mod.reconcile_scope(
            self.root,
            self.registry,
            "project",
            self.workspace,
            "symlink",
            check,
            target_override=target,
        )

    def census(self, **kwargs: Any) -> dict[str, Any]:
        return skills_mod.coverage_census(
            self.root,
            self.registry,
            [self.project_skills, self.home_skills],
            synced_root=self.home_skills / skills_mod.SYNCED_DIR_NAME,
            **kwargs,
        )

    def test_all_expected_skills_present_counted_once_across_paths(self) -> None:
        self.project(self.project_skills)
        self.project(self.home_skills)
        census = self.census()
        self.assertEqual("complete", census["status"])
        # Two discovery paths each carry both skills: coverage is 2, not 4.
        self.assertEqual(2, census["covered_count"])
        self.assertEqual(2, len(census["discovery_paths"]))
        self.assertEqual({"explicit_only": 1, "model_allowed": 1}, census["tiers"])

    def test_missing_skill_detected(self) -> None:
        self.project(self.home_skills)
        (self.home_skills / "l9-beta").unlink()
        census = self.census()
        self.assertEqual("incomplete", census["status"])
        self.assertEqual(["l9-beta"], census["missing"])
        self.assertIn("missing:l9-beta", self.project(self.home_skills, check=True).drift)

    def test_wrong_target_link_detected(self) -> None:
        self.project(self.home_skills)
        link = self.home_skills / "l9-alpha"
        link.unlink()
        link.symlink_to(self.root / "skills" / "l9-beta", target_is_directory=True)
        census = self.census()
        self.assertEqual("incomplete", census["status"])
        self.assertEqual([str(link)], census["wrong_target"])
        self.assertIn(
            "wrong-ssot-target:l9-alpha", self.project(self.home_skills, check=True).drift
        )
        self.project(self.home_skills)
        self.assertEqual("complete", self.census()["status"])

    def test_stale_retired_skill_removed_and_reported_until_then(self) -> None:
        self.project(self.home_skills)
        self.registry["skills"] = [s for s in self.registry["skills"] if s["name"] != "l9-beta"]
        census = self.census()
        # The retired link still resolves, but it is no longer a canonical identity.
        self.assertEqual([str(self.home_skills / "l9-beta")], census["unexpected"])
        self.assertIn("obsolete:l9-beta", self.project(self.home_skills, check=True).drift)
        result = self.project(self.home_skills)
        self.assertEqual(["l9-beta"], result.removed)
        self.assertFalse((self.home_skills / "l9-beta").is_symlink())
        self.assertEqual([], self.census()["unexpected"])

    def test_second_projection_run_produces_no_changes(self) -> None:
        first = self.project(self.home_skills)
        self.assertEqual(["l9-alpha", "l9-beta"], first.created)
        state = (self.home_skills / skills_mod.STATE_NAME).read_bytes()
        second = self.project(self.home_skills)
        self.assertEqual([], second.created + second.removed + second.drift + second.conflicts)
        self.assertEqual(["l9-alpha", "l9-beta"], second.current)
        self.assertEqual(state, (self.home_skills / skills_mod.STATE_NAME).read_bytes())

    def test_new_canonical_skill_reaches_discovery_without_manual_step(self) -> None:
        self.project(self.home_skills)
        self.add_skill("l9-gamma", "model_allowed")
        self.assertEqual(["l9-gamma"], self.census()["missing"])
        self.assertEqual(["l9-gamma"], self.project(self.home_skills).created)
        self.assertEqual("complete", self.census()["status"])

    def test_account_synced_copies_classified_apart_from_coverage(self) -> None:
        self.project(self.home_skills)
        (self.root / "skills" / "_archived" / "l9-old").mkdir(parents=True)
        account = self.home_skills / skills_mod.SYNCED_DIR_NAME / "org_account"
        for name in ("l9-alpha", "l9-old", "l9-foreign", "docx"):
            (account / name).mkdir(parents=True)
            (account / name / "SKILL.md").write_text("synced\n")
        census = self.census()
        # Synced copies never count toward coverage and are not "unexpected"
        # projection entries: Claude Code owns that directory.
        self.assertEqual("complete", census["status"])
        self.assertEqual([], census["unexpected"])
        self.assertEqual(
            {"l9-alpha": "shadows_canonical", "l9-old": "archived", "l9-foreign": "unmanaged"},
            {item["name"]: item["class"] for item in census["account_synced_l9"]},
        )
        banner = "\n".join(skills_mod.coverage_banner(census))
        self.assertIn("3 l9-* account copies", banner)
        self.assertIn("UNVERIFIED", banner)
        self.assertNotIn("READY", banner)

    def test_explicit_only_tier_override_checked_in_user_settings(self) -> None:
        self.project(self.home_skills)
        settings = self.home_skills.parent / "settings.json"
        settings.write_text(json.dumps({"skillOverrides": {}, "syncClaudeAiSkills": False}))
        census = self.census(user_settings=settings)
        self.assertEqual(["l9-beta"], census["tier_override_missing"])
        self.assertEqual("incomplete", census["status"])
        self.assertIs(False, census["account_sync_policy"])
        settings.write_text(
            json.dumps(
                {"skillOverrides": {"l9-beta": "user-invocable-only"}, "syncClaudeAiSkills": False}
            )
        )
        census = self.census(user_settings=settings)
        self.assertEqual("complete", census["status"])
        self.assertIn("syncClaudeAiSkills=false", "\n".join(skills_mod.coverage_banner(census)))

    def test_cli_coverage_mode_needs_no_scope(self) -> None:
        generated = self.root / "ops" / "generated"
        generated.mkdir(parents=True)
        (generated / "skill-registry.json").write_text(json.dumps(self.registry))
        self.project(self.project_skills)
        home = self.home_skills.parent.parent
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.root),
                "--coverage",
                "--workspace",
                str(self.workspace),
            ],
            text=True,
            capture_output=True,
            check=False,
            env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("skills projected: 2/2 unique canonical", result.stdout)
        self.assertIn("runtime load not verified", result.stdout)


import build_claude_skill_registry as registry_mod  # noqa: E402


class RegistryTierContractTests(unittest.TestCase):
    """The registry is generated from AUTONOMY_MANIFEST.yaml + SKILL.md only."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.write_skill("l9-open", disable=False)
        self.write_skill("l9-gated", disable=True)
        (self.root / "skills" / "AUTONOMY_MANIFEST.yaml").write_text(
            "tiers:\n"
            "  auto_invoke:\n  - skill: l9-open\n"
            "  explicit_only:\n  - skill: l9-gated\n"
            "claude_routing:\n  primary_skills: []\n  supporting_skills: []\n  routes: []\n",
            encoding="utf-8",
        )

    def write_skill(self, name: str, *, disable: bool) -> None:
        skill = self.root / "skills" / name
        skill.mkdir(parents=True, exist_ok=True)
        flag = "disable-model-invocation: true\n" if disable else ""
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\n{flag}---\n# {name}\n", encoding="utf-8"
        )

    def check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT.parent / "build_claude_skill_registry.py"),
                "--root",
                str(self.root),
                "--check",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_tiers_follow_manifest_and_explicit_only_stays_user_invocable(self) -> None:
        records = {r["name"]: r for r in registry_mod.build_registry(self.root)["skills"]}
        self.assertEqual("model_allowed", records["l9-open"]["invocation"])
        gated = records["l9-gated"]
        self.assertEqual("explicit_only", gated["invocation"])
        # Hidden from the model, still runnable by the user by name.
        self.assertTrue(gated["disable_model_invocation"])
        self.assertTrue(gated["user_invocable"])

    def test_model_invocable_explicit_only_skill_is_rejected(self) -> None:
        self.write_skill("l9-gated", disable=False)
        with self.assertRaisesRegex(ValueError, "explicit-only skill must set"):
            registry_mod.build_registry(self.root)

    def test_generated_registry_drift_detected(self) -> None:
        out = self.root / registry_mod.DEFAULT_OUT
        out.parent.mkdir(parents=True)
        out.write_text(registry_mod.serialized(registry_mod.build_registry(self.root)))
        self.assertEqual(0, self.check().returncode)
        (self.root / "skills" / "l9-open" / "SKILL.md").write_text(
            "---\nname: l9-open\ndescription: changed\n---\n", encoding="utf-8"
        )
        result = self.check()
        self.assertEqual(1, result.returncode)
        self.assertIn("STALE", result.stdout)


if __name__ == "__main__":
    unittest.main()
