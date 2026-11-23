"""governance_commands: the slash-command catalog and single-command reads."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.base import RuntimeContext, ToolInputError

from tools import commands


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "commands").mkdir()
    (tmp_path / "commands/COMMANDS_MANIFEST.yaml").write_text(
        "version: 1\ncommands:\n"
        "- slash: /architect\n  file: commands/architect.md\n  enabled: true\n"
        "- slash: /clean\n  file: commands/clean.md\n  enabled: false\n",
        encoding="utf-8",
    )
    (tmp_path / "commands/architect.md").write_text(
        "# /architect\n\nDesign before code.\n", encoding="utf-8"
    )
    return tmp_path


def test_catalog_lists_all_commands(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    result = commands.handle(context, {})
    assert result["count"] == 2
    assert {item["slash"] for item in result["commands"]} == {"/architect", "/clean"}


def test_named_command_returns_excerpt(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    result = commands.handle(context, {"name": "architect"})
    assert result["command"]["slash"] == "/architect"
    assert "Design before code" in result["excerpt"]


def test_unknown_command_lists_alternatives(tmp_path: Path) -> None:
    context = RuntimeContext(_repo(tmp_path))
    with pytest.raises(ToolInputError, match="unknown command"):
        commands.handle(context, {"name": "nope"})
