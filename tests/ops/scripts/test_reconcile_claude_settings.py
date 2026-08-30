"""Tests for ops/scripts/reconcile_claude_settings.py"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reconcile_claude_settings import (  # noqa: E402
    merge_user_settings,
    merge_workspace_settings,
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
    hooks = root / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
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
    tmpl_path = (
        root / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
    )
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


# -- issue #281: a git-tracked workspace settings file owns its hooks --------


def test_merge_composes_hooks_for_tracked_file() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}],
            "PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "gov-edit"}]}
            ],
        },
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {},
        "skillOverrides": {},
    }
    existing = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "python3 tools/contract_scanner.py --quick"}
                    ],
                }
            ],
            "Stop": [{"hooks": [{"type": "command", "command": "consumer-stop"}]}],
        },
        "enabledPlugins": {"plugin@official": True},
    }
    merged = merge_workspace_settings(template, existing, compose_hooks=True)
    pretool = merged["hooks"]["PreToolUse"]
    # Consumer guard first and kept, governance group appended.
    assert pretool[0]["hooks"][0]["command"] == "python3 tools/contract_scanner.py --quick"
    assert pretool[1]["hooks"][0]["command"] == "gov-edit"
    # Consumer-only event survives; governance-only event lands.
    assert merged["hooks"]["Stop"][0]["hooks"][0]["command"] == "consumer-stop"
    assert merged["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "gov-session-start"
    assert merged["enabledPlugins"] == {"plugin@official": True}


def test_merge_wholesale_replaces_hooks_when_untracked() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}]
        }
    }
    existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "consumer-stop"}]}]}}
    merged = merge_workspace_settings(template, existing)  # default: untracked file
    assert "Stop" not in merged["hooks"]
    assert merged["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "gov-session-start"


def test_compose_churn_free_when_hooks_already_match_template() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}],
            "PreToolUse": [
                {"matcher": "Edit", "hooks": [{"type": "command", "command": "gov-edit"}]}
            ],
        }
    }
    existing = {"hooks": template["hooks"], "theme": "dark"}
    merged = merge_workspace_settings(template, existing, compose_hooks=True)
    assert merged["hooks"] == template["hooks"]
    assert merged["theme"] == "dark"


def test_compose_replaces_malformed_event_value_with_template() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}]
        }
    }
    existing = {
        "hooks": {
            "SessionStart": {"not": "a list"},
            "Stop": [{"hooks": [{"type": "command", "command": "consumer-stop"}]}],
        }
    }
    merged = merge_workspace_settings(template, existing, compose_hooks=True)
    # A malformed event value is not a hook list: governance groups replace it.
    assert merged["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "gov-session-start"
    # Consumer-owned events stay verbatim.
    assert merged["hooks"]["Stop"][0]["hooks"][0]["command"] == "consumer-stop"


def test_reconcile_workspace_composes_tracked_settings(tmp_path: Path) -> None:
    root = tmp_path / "gov"
    hooks = root / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "session_start_claude_governance.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (hooks / "merge_gate_wrap.py").write_text("# wrap\n", encoding="utf-8")
    tmpl = {
        "$schema": "https://example.com/schema.json",
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}]
        },
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {"L9_GOVERNANCE_SURFACE": "claude-code", "L9_AUTONOMY_ENABLED": "true"},
        "skillOverrides": {},
    }
    tmpl_path = (
        root / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
    )
    tmpl_path.write_text(json.dumps(tmpl, indent=2) + "\n", encoding="utf-8")

    ws = tmp_path / "consumer"
    ws.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    settings = ws / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 tools/contract_scanner.py --quick",
                                }
                            ],
                        }
                    ]
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", ".claude/settings.json"], cwd=ws, check=True)

    result = run(root, workspace=ws, user=False, gov=True, check=False)
    assert result["wrote"]

    reconciled = json.loads(settings.read_text(encoding="utf-8"))
    pretool_commands = [g["hooks"][0]["command"] for g in reconciled["hooks"]["PreToolUse"]]
    assert "python3 tools/contract_scanner.py --quick" in pretool_commands, (
        "a tracked consumer guard must survive reconciliation"
    )
    assert reconciled["hooks"]["SessionStart"], "governance hooks must still land"

    # Idempotent: the composed file must not churn on the next reconcile.
    second = run(root, workspace=ws, user=False, gov=True, check=False)
    assert second["wrote"] == []
    check = run(root, workspace=ws, user=False, gov=True, check=True)
    assert check["ok"] is True
