"""governance_capabilities: four discovery planes, parsed not guessed."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.base import RuntimeContext, ToolInputError

from tools import capabilities


def _repo(tmp_path: Path) -> Path:
    skill = tmp_path / "skills/demo-skill/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: demo-skill\ndescription: Demo skill for tests\n---\n# Demo\n", encoding="utf-8"
    )

    (tmp_path / "commands").mkdir()
    (tmp_path / "commands/COMMANDS_MANIFEST.yaml").write_text(
        "version: 1\ncommands:\n"
        "- slash: /architect\n  file: commands/architect.md\n  enabled: true\n",
        encoding="utf-8",
    )
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols/proto.md").write_text("# Proto\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("build: ## Build the thing\n\techo hi\n", encoding="utf-8")
    return tmp_path


def test_all_sections_are_reported(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    result = capabilities.handle(context, {})
    assert result["skills"]["count"] == 1
    assert result["skills"]["items"][0]["name"] == "demo-skill"
    assert result["commands"]["items"][0]["slash"] == "/architect"
    assert result["protocols"]["count"] == 1
    assert any(item["target"] == "build" for item in result["targets"]["items"])


def test_section_filter_returns_one_plane(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    result = capabilities.handle(context, {"section": "commands"})
    assert set(result) == {"section", "commands"}


def test_bad_section_is_rejected(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    with pytest.raises(ToolInputError, match="section must be one of"):
        capabilities.handle(context, {"section": "everything"})
