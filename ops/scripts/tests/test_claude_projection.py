#!/usr/bin/env python3
"""Unit tests for the one Claude projection engine (claude_projection.py).

Covers the projection-receipt contract, second-run idempotency, the
cached-environment reconciliation path (SessionStart and setup call the SAME
engine — repairing a wiped mirror must need nothing but a re-run), stale
cleanup across domains, consumer-field preservation in settings, and the
declarative plugin desired-state helpers.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
GOV_ROOT = SCRIPTS.parent.parent
sys.path.insert(0, str(SCRIPTS))

import claude_projection  # noqa: E402

RECEIPT_REQUIRED_FIELDS = (
    "schema_version",
    "timestamp",
    "governance_SHA",
    "workspace",
    "managed_domains",
    "projected_count_by_domain",
    "stale_removed_by_domain",
    "collisions",
    "failures",
    "status",
)


def make_root(base: Path) -> Path:
    root = base / "governance"

    # Skills SSOT + registry.
    skill = root / "skills" / "l9-demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: l9-demo\n---\n# demo\n", encoding="utf-8")
    generated = root / "ops" / "generated"
    generated.mkdir(parents=True)
    write_registry(root, ["l9-demo"])

    # Commands SSOT + manifest (one clean command, one skill collision).
    commands = root / "commands"
    commands.mkdir(parents=True)
    (commands / "alpha.md").write_text("# /alpha\n", encoding="utf-8")
    (commands / "l9-demo.md").write_text("# /l9-demo\n", encoding="utf-8")
    (commands / "COMMANDS_MANIFEST.yaml").write_text(
        "version: 1\n"
        "commands:\n"
        "- slash: /alpha\n"
        "  file: commands/alpha.md\n"
        "  enabled: true\n"
        "- slash: /l9-demo\n"
        "  file: commands/l9-demo.md\n"
        "  enabled: true\n",
        encoding="utf-8",
    )

    # Adapter configs: project scope only, so tests stay inside tmp dirs.
    adapters = root / "environment" / "skill-adapters"
    adapters.mkdir(parents=True)
    (adapters / "SKILL_ADAPTER_ROOTS.yaml").write_text(
        "schema_version: 1\n"
        "ssot_relative: skills\n"
        "mode: symlink\n"
        "adapters:\n"
        "- id: claude-code-project\n"
        "  surface: claude-code\n"
        "  kind: project\n"
        "  path: .claude/skills\n",
        encoding="utf-8",
    )
    (adapters / "LLM_RULE_ADAPTER_ROOTS.yaml").write_text(
        "schema_version: 1\n"
        "ssot_relative: environment/generated/llm-rules\n"
        "mode: directory-symlink\n"
        "adapters:\n"
        "- id: claude-code-project\n"
        "  surface: claude-code\n"
        "  kind: project\n"
        "  path: .claude/rules\n",
        encoding="utf-8",
    )

    # Rules SSOT + projection config (mirrors test_project_llm_rules fixture).
    rules = root / "rules"
    rules.mkdir(parents=True)
    (rules / "00-always.mdc").write_text(
        "---\ndescription: always rule\nalwaysApply: true\n---\n\n# Always\n",
        encoding="utf-8",
    )
    config = root / "ops" / "config"
    config.mkdir(parents=True)
    (config / "llm_rules_projection.yaml").write_text(
        "schema_version: 1\n"
        "source_relative: rules\n"
        "output_relative: environment/generated/llm-rules\n"
        "deny_stems: []\n"
        "aliases: {}\n"
        "project_agent_requested: false\n",
        encoding="utf-8",
    )
    autonomy = root / "ops" / "autonomy"
    autonomy.mkdir(parents=True)
    for name in ("profile_loader.py", "surface_profile.yaml"):
        shutil.copy2(GOV_ROOT / "ops" / "autonomy" / name, autonomy / name)

    # Settings template + hook sources.
    adapter_dir = root / "environment" / "agents" / "adapters" / "claude-code"
    hooks = adapter_dir / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "session_start_claude_governance.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (hooks / "merge_gate_wrap.py").write_text("# wrap\n", encoding="utf-8")
    (adapter_dir / "settings.template.json").write_text(
        json.dumps(
            {
                "$schema": "https://example.com/schema.json",
                "hooks": {"SessionStart": [{"hooks": []}]},
                "permissions": {"allow": ["Read"], "deny": []},
                "env": {"L9_GOVERNANCE_SURFACE": "claude-code"},
                "skillOverrides": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Declarative plugin desired state.
    (adapter_dir / "plugins.desired.json").write_text(
        json.dumps(
            {
                "schema": "l9.claude-plugins-desired.v1",
                "core": {
                    "marketplaces": ["anthropics/claude-plugins-official"],
                    "plugins": ["hookify@claude-plugins-official"],
                },
                "classes": {
                    "aws_infra": {
                        "marketplaces": ["anthropics/claude-plugins-official"],
                        "plugins": ["aws-core@claude-plugins-official"],
                    }
                },
                "retired_user_scope": [],
            }
        ),
        encoding="utf-8",
    )
    return root


def write_registry(root: Path, names: list[str]) -> None:
    (root / "ops" / "generated" / "skill-registry.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_manifest_sha256": "test",
                "skills": [{"name": name, "path": f"skills/{name}"} for name in names],
            }
        ),
        encoding="utf-8",
    )


class ClaudeProjectionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = make_root(base)
        self.ws = base / "consumer"
        self.ws.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        patcher = mock.patch.dict(
            os.environ,
            {"HOME": str(self.home), "SKIP_PLUGIN_MARKETPLACE": "true"},
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.receipt_path = self.home / ".l9" / "claude" / "projection-receipt.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_engine(self, **kwargs):
        kwargs.setdefault("receipt_path", self.receipt_path)
        return claude_projection.run(self.root, self.ws, **kwargs)

    def test_initial_projection_and_receipt_contract(self) -> None:
        receipt = self.run_engine()
        for field in RECEIPT_REQUIRED_FIELDS:
            self.assertIn(field, receipt)
        self.assertEqual(receipt["schema_version"], "l9.claude-projection.v1")
        self.assertEqual(receipt["status"], "ok")
        self.assertEqual(
            receipt["managed_domains"],
            ["commands", "hooks", "plugins", "rules", "settings", "skills"],
        )
        self.assertEqual(receipt["collisions"], ["command-skill-collision:l9-demo"])
        self.assertEqual(receipt["failures"], [])
        self.assertGreater(receipt["projected_count_by_domain"]["skills"], 0)
        self.assertGreater(receipt["projected_count_by_domain"]["commands"], 0)
        # The receipt is persisted for SessionStart to project.
        self.assertTrue(self.receipt_path.is_file())
        on_disk = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["status"], "ok")
        # The actual mirrors exist.
        self.assertTrue((self.ws / ".claude" / "skills" / "l9-demo").is_symlink())
        self.assertTrue((self.ws / ".claude" / "commands" / "alpha.md").is_symlink())
        self.assertTrue((self.ws / ".claude" / "rules").is_symlink())
        self.assertTrue((self.ws / ".claude" / "settings.json").is_file())

    def test_second_run_idempotent(self) -> None:
        self.run_engine()
        check = self.run_engine(check=True)
        self.assertEqual(check["status"], "ok")
        self.assertEqual(check["failures"], [])

    def test_cached_environment_reconciliation(self) -> None:
        """SessionStart repair: a wiped mirror heals on the next engine run."""
        self.run_engine()
        shutil.rmtree(self.ws / ".claude" / "skills")
        (self.ws / ".claude" / "commands" / "alpha.md").unlink()
        (self.ws / ".claude" / "settings.json").unlink()
        check = self.run_engine(check=True)
        self.assertEqual(check["status"], "drift")
        repaired = self.run_engine()
        self.assertEqual(repaired["status"], "ok")
        self.assertTrue((self.ws / ".claude" / "skills" / "l9-demo").is_symlink())
        self.assertTrue((self.ws / ".claude" / "commands" / "alpha.md").is_symlink())
        self.assertTrue((self.ws / ".claude" / "settings.json").is_file())

    def test_stale_skill_and_command_cleanup(self) -> None:
        self.run_engine()
        # Retire the skill and the command from their registries.
        write_registry(self.root, [])
        (self.root / "commands" / "COMMANDS_MANIFEST.yaml").write_text(
            "version: 1\ncommands: []\n", encoding="utf-8"
        )
        receipt = self.run_engine()
        self.assertEqual(receipt["status"], "ok")
        self.assertGreater(receipt["stale_removed_by_domain"]["skills"], 0)
        self.assertGreater(receipt["stale_removed_by_domain"]["commands"], 0)
        self.assertFalse((self.ws / ".claude" / "skills" / "l9-demo").exists())
        self.assertFalse((self.ws / ".claude" / "commands" / "alpha.md").exists())

    def test_settings_merge_preserves_consumer_fields(self) -> None:
        claude_dir = self.ws / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(
            json.dumps({"enabledPlugins": {"mine@repo": True}, "consumerKey": 7}),
            encoding="utf-8",
        )
        self.run_engine()
        merged = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(merged["enabledPlugins"], {"mine@repo": True})
        self.assertEqual(merged["consumerKey"], 7)
        self.assertEqual(merged["env"]["L9_GOVERNANCE_SURFACE"], "claude-code")

    def test_plugins_skipped_when_marketplace_disabled(self) -> None:
        receipt = self.run_engine()
        plugin_domain = next(d for d in receipt["domains"] if d["domain"] == "plugins")
        self.assertEqual(plugin_domain["status"], "skipped")


class PluginDesiredStateTests(unittest.TestCase):
    DESIRED = {
        "core": {
            "marketplaces": ["anthropics/claude-plugins-official"],
            "plugins": ["hookify@claude-plugins-official"],
        },
        "classes": {
            "zep_memory": {
                "marketplaces": ["getzep/zep"],
                "plugins": ["building-with-zep@zep"],
            }
        },
    }

    def test_class_merge(self) -> None:
        marketplaces, plugins = claude_projection.plugin_desired_set(self.DESIRED, "zep_memory")
        self.assertEqual(marketplaces, ["anthropics/claude-plugins-official", "getzep/zep"])
        self.assertEqual(plugins, ["hookify@claude-plugins-official", "building-with-zep@zep"])

    def test_core_default_gets_core_only(self) -> None:
        marketplaces, plugins = claude_projection.plugin_desired_set(self.DESIRED, "core_default")
        self.assertEqual(marketplaces, ["anthropics/claude-plugins-official"])
        self.assertEqual(plugins, ["hookify@claude-plugins-official"])

    def test_hash_matches_shell_contract(self) -> None:
        # setup_claude_code_plugins.sh stamps sha256 of newline-joined
        # marketplaces + plugins with a trailing newline; both writers must
        # agree or the stamp fast-path never matches.
        import hashlib

        marketplaces, plugins = claude_projection.plugin_desired_set(self.DESIRED, "core_default")
        expected = hashlib.sha256(
            ("\n".join([*marketplaces, *plugins]) + "\n").encode("utf-8")
        ).hexdigest()
        self.assertEqual(claude_projection.plugin_desired_hash(marketplaces, plugins), expected)

    def test_live_desired_state_declaration(self) -> None:
        live = json.loads(
            (
                GOV_ROOT
                / "environment"
                / "agents"
                / "adapters"
                / "claude-code"
                / "plugins.desired.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(live["schema"], "l9.claude-plugins-desired.v1")
        self.assertTrue(live["core"]["plugins"])
        # The imperative fallback must carry no plugin ids of its own.
        script = (GOV_ROOT / "ops" / "scripts" / "setup_claude_code_plugins.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("plugins.desired.json", script)
        for entry in live["core"]["plugins"]:
            self.assertNotIn(f'"{entry}"', script)


class SkillStateUnfreezeTests(unittest.TestCase):
    """A conflict in one skill must not freeze stale cleanup for the scope."""

    def test_state_written_despite_conflict(self) -> None:
        from reconcile_claude_l9_skills import reconcile_scope

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "gov"
            for name in ("l9-a", "plasticos-local"):
                skill = root / "skills" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text("# s\n", encoding="utf-8")
            registry = {
                "source_manifest_sha256": "x",
                "skills": [
                    {"name": "l9-a", "path": "skills/l9-a"},
                    {"name": "plasticos-local", "path": "skills/plasticos-local"},
                ],
            }
            ws = base / "ws"
            target = ws / ".claude" / "skills"
            target.mkdir(parents=True)
            # Consumer-owned non-l9 skill directory: unmanaged conflict.
            local = target / "plasticos-local"
            local.mkdir()
            (local / "SKILL.md").write_text("# mine\n", encoding="utf-8")

            result = reconcile_scope(root, registry, "project", ws, "symlink", False)
            self.assertIn("unmanaged-conflict:plasticos-local", result.conflicts)
            state = json.loads((target / ".l9-managed-skills.json").read_text(encoding="utf-8"))
            # The conflicted name is not claimed; the managed one is recorded.
            self.assertEqual(state["skills"], ["l9-a"])

            # Retiring l9-a from the registry now reclaims its link — the
            # sweep is no longer frozen by the standing conflict.
            registry["skills"] = [{"name": "plasticos-local", "path": "skills/plasticos-local"}]
            result2 = reconcile_scope(root, registry, "project", ws, "symlink", False)
            self.assertIn("l9-a", result2.removed)
            self.assertFalse((target / "l9-a").exists())


if __name__ == "__main__":
    unittest.main()
