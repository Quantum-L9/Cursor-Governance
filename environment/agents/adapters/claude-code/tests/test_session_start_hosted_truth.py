"""SessionStart hosted remainder: STALE, two-clone, skill-usage, hook hygiene."""

from __future__ import annotations

import unittest
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[1] / "hooks" / "session_start_claude_governance.sh"
)
INSTALL = Path(__file__).resolve().parents[1] / "install.sh"
RULE = Path(__file__).resolve().parents[5] / "rules" / "22-context7-auto-invoke.mdc"


class SessionStartHostedTruthTests(unittest.TestCase):
    def test_hook_marks_stale_workspace(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        self.assertIn('prefix="STALE: "', text)
        self.assertIn("STALE: bootstrap receipt workspace", text)

    def test_hook_prints_two_clone_banner(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        self.assertIn("two-clone: workspace", text)
        self.assertIn("two-clone: live SSOT", text)
        self.assertIn("rules resolve from live SSOT", text)

    def test_hook_names_skill_usage_log(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        self.assertIn("skill-usage.jsonl", text)
        self.assertIn("absent — logger never wrote", text)

    def test_hook_removes_raw_precommit_on_hosted(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        self.assertIn("SKIP_PLUGIN_MARKETPLACE", text)
        self.assertIn("hooks/pre-commit", text)
        self.assertIn("removed forbidden raw .git/hooks/pre-commit", text)

    def test_hook_probes_loadable_skills(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        self.assertIn("skills loadable:", text)
        self.assertIn(".claude/skills", text)

    def test_hook_does_not_probe_broker(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        self.assertNotIn("probe_broker.py", text)
        self.assertIn("--graphiti-probe", text)

    def test_install_runs_validate_claude_env(self) -> None:
        text = INSTALL.read_text(encoding="utf-8")
        self.assertIn("validate_claude_env.py", text)
        self.assertIn("validate_claude_env structural fail", text)

    def test_install_does_not_probe_broker(self) -> None:
        text = INSTALL.read_text(encoding="utf-8")
        self.assertNotIn("probe_broker.py", text)
        self.assertIn("memory.cli", text)

    def test_rule_22_hosted_fallback(self) -> None:
        text = RULE.read_text(encoding="utf-8")
        self.assertIn("l9-context7-docs", text)
        self.assertIn("mcp__context7__*", text)
        self.assertIn("SKIP_PLUGIN_MARKETPLACE", text)


if __name__ == "__main__":
    unittest.main()
