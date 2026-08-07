"""Tests for ops/scripts/reconcile_claude_settings.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reconcile_claude_settings import (  # noqa: E402
    merge_user_settings,
    run,
)


def test_merge_preserves_plugins() -> None:
    template = {
        "hooks": {"SessionStart": []},
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {"L9_AUTONOMY_ENABLED": "true"},
        "skillOverrides": {"l9-forge": "user-invocable-only"},
    }
    existing = {
        "enabledPlugins": {"hookify@claude-plugins-official": True},
        "theme": "light",
        "customUserKey": 1,
    }
    merged = merge_user_settings(template, existing)
    assert merged["enabledPlugins"] == existing["enabledPlugins"]
    assert merged["theme"] == "light"
    assert merged["customUserKey"] == 1
    assert merged["env"]["L9_AUTONOMY_ENABLED"] == "true"
    assert "hooks" in merged


def test_reconcile_workspace_and_check(tmp_path: Path) -> None:
    root = tmp_path / "gov"
    hooks = root / "environment" / "claude-code" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "session_start_claude_governance.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (hooks / "merge_gate_wrap.py").write_text("# wrap\n", encoding="utf-8")
    tmpl = {
        "$schema": "https://example.com/schema.json",
        "hooks": {"SessionStart": [{"hooks": []}]},
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {"L9_GOVERNANCE_SURFACE": "claude-code", "L9_AUTONOMY_ENABLED": "true"},
        "skillOverrides": {},
    }
    tmpl_path = root / "environment" / "claude-code" / "settings.template.json"
    tmpl_path.write_text(json.dumps(tmpl, indent=2) + "\n", encoding="utf-8")

    ws = tmp_path / "consumer"
    ws.mkdir()
    result = run(root, workspace=ws, user=False, gov=True, check=False)
    assert (root / ".claude" / "settings.json").is_file()
    assert (ws / ".claude" / "settings.json").is_file()
    assert (ws / ".claude" / "hooks" / "session_start_claude_governance.sh").is_file()
    check = run(root, workspace=ws, user=False, gov=True, check=True)
    assert check["ok"] is True
    assert result["wrote"]
