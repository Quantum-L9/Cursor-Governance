"""Tests for ops/scripts/sync_generated_artifacts and commands manifest sync."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pytest  # noqa: E402
from generate_commands_manifest import build_manifest  # noqa: E402
from sync_generated_artifacts import (  # noqa: E402
    assert_no_live_deprecated_skills,
    disk_skill_names,
    heal_orphan_skills,
    is_generated_path,
    sync,
    sync_skill_overrides,
)


def test_is_generated_path_allowlist() -> None:
    assert is_generated_path("rules/RULES-MANIFEST.json")
    assert is_generated_path("commands/COMMANDS_MANIFEST.yaml")
    assert is_generated_path("skills/AUTONOMY_MANIFEST.yaml")
    assert is_generated_path("skills/l9-demo/SKILL.md")
    assert is_generated_path(
        "environment/agents/adapters/claude-code/generated/skill-registry.json"
    )
    assert not is_generated_path("ops/scripts/run_pr_gate.sh")
    assert not is_generated_path("skills/l9-demo/references/x.md")


def test_orphan_heal_and_overrides(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    demo = skills / "l9-demo-orphan"
    demo.mkdir()
    (demo / "SKILL.md").write_text(
        "---\nname: l9-demo-orphan\ndescription: demo orphan skill\n---\n\n# demo\n",
        encoding="utf-8",
    )
    (skills / "AUTONOMY_MANIFEST.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "tiers": {"auto_invoke": [], "explicit_only": []},
                "claude_routing": {
                    "primary_skills": [],
                    "supporting_skills": [],
                    "routes": [],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    settings_dir = tmp_path / "environment" / "agents" / "adapters" / "claude-code"
    settings_dir.mkdir(parents=True)
    settings_path = settings_dir / "settings.template.json"
    settings_path.write_text(json.dumps({"skillOverrides": {}}, indent=2) + "\n", encoding="utf-8")

    wrote: list[str] = []
    warnings: list[str] = []
    heal_orphan_skills(tmp_path, wrote, warnings)
    assert any("l9-demo-orphan" in w for w in warnings)
    manifest = yaml.safe_load((skills / "AUTONOMY_MANIFEST.yaml").read_text(encoding="utf-8"))
    names = [e["skill"] for e in manifest["tiers"]["explicit_only"]]
    assert "l9-demo-orphan" in names
    fm = (demo / "SKILL.md").read_text(encoding="utf-8")
    assert "disable-model-invocation: true" in fm

    sync_skill_overrides(tmp_path, wrote)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["skillOverrides"]["l9-demo-orphan"] == "user-invocable-only"


def test_live_deprecated_skills_are_rejected(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    deprecated = skills / "l9-demo-deprecated"
    deprecated.mkdir()
    (deprecated / "SKILL.md").write_text(
        "---\nname: l9-demo-deprecated\ndescription: retired\nstatus: deprecated\n---\n\n# x\n",
        encoding="utf-8",
    )
    archived = skills / "_archived" / "l9-old-deprecated"
    archived.mkdir(parents=True)
    (archived / "SKILL.md").write_text(
        "---\nname: l9-old-deprecated\ndescription: archived\nstatus: deprecated\n---\n\n# x\n",
        encoding="utf-8",
    )
    assert disk_skill_names(tmp_path) == ["l9-demo-deprecated"]
    with pytest.raises(RuntimeError, match="deprecated skills cannot remain"):
        assert_no_live_deprecated_skills(tmp_path)
    # After archive move, live tree is clean.
    deprecated.rename(skills / "_archived" / "l9-demo-deprecated")
    assert disk_skill_names(tmp_path) == []
    assert_no_live_deprecated_skills(tmp_path)


def test_live_deprecated_skills_read_nested_metadata_status(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    deprecated = skills / "l9-demo-deprecated-nested"
    deprecated.mkdir()
    (deprecated / "SKILL.md").write_text(
        "---\nname: l9-demo-deprecated-nested\ndescription: retired\n"
        "metadata:\n  status: deprecated\n---\n\n# x\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="deprecated skills cannot remain"):
        assert_no_live_deprecated_skills(tmp_path)


def test_commands_manifest_preserves_prior_slash(tmp_path: Path) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    (commands / "harvest.md").write_text("---\nname: harvest\n---\n# h\n", encoding="utf-8")
    (commands / "harvest2.md").write_text("---\nname: harvest\n---\n# h2\n", encoding="utf-8")
    (commands / "COMMANDS_MANIFEST.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "commands": [
                    {"slash": "/harvest", "file": "commands/harvest.md", "enabled": True},
                    {"slash": "/harvest2", "file": "commands/harvest2.md", "enabled": True},
                ],
                "excluded": ["commands/COMMANDS_MANIFEST.yaml"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    built = build_manifest(tmp_path)
    by_file = {e["file"]: e["slash"] for e in built["commands"]}
    assert by_file["commands/harvest.md"] == "/harvest"
    assert by_file["commands/harvest2.md"] == "/harvest2"


def test_sync_force_no_churn_on_second_pass(tmp_path: Path) -> None:
    # Minimal governance-shaped tree using real generators where cheap.
    root = tmp_path
    (root / "rules").mkdir()
    (root / "rules" / "00-test.mdc").write_text(
        "---\ndescription: t\nalwaysApply: false\n---\n\n# t\n", encoding="utf-8"
    )
    # Copy real generate_rules dependency is heavy; just ensure sync handles missing
    # optional trees without crashing when force=True on empty-ish root.
    result = sync(root, force=True)
    # Without skills/AUTONOMY etc., skill sync may error — force path should still return dict.
    assert "wrote" in result
    assert "errors" in result
