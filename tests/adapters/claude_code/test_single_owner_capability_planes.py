"""Keep Claude platform helpers from duplicating L9-owned planes."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "environment/agents/adapters/claude-code/settings.template.json"


def test_governance_ssot_is_persistent_additional_directory() -> None:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert settings["permissions"]["additionalDirectories"] == ["~/.cursor-governance"]


def test_claude_duplicate_memory_and_scheduler_planes_are_disabled() -> None:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    env = settings["env"]
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert env["CLAUDE_CODE_DISABLE_CRON"] == "1"
