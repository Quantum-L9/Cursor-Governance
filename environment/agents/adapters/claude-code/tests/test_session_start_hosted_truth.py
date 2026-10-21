"""SessionStart hosted remainder: STALE, two-clone, skill-usage, hook hygiene."""

from __future__ import annotations

import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "session_start_claude_governance.sh"
INSTALL = Path(__file__).resolve().parents[1] / "install.sh"
RULE = Path(__file__).resolve().parents[5] / "rules" / "22-context7-auto-invoke.mdc"


class SessionStartHostedTruthTests(unittest.TestCase):
    def test_hook_hands_workspace_ownership_to_the_reader(self) -> None:
        """A receipt for another workspace is named by the ONE reader rule.

        The hook used to parse the receipt inline and prefix STALE on a
        single-field mismatch, a rule that disagreed with the reader's
        covered_roots and with the runtime report about the same receipt.
        """
        text = HOOK.read_text(encoding="utf-8")
        self.assertIn('--workspace "$WORKSPACE"', text)
        self.assertNotIn('prefix="STALE: "', text)

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

    def test_skill_banner_reports_unique_canonical_coverage(self) -> None:
        """The banner used to SUM `find -L` SKILL.md counts over the workspace
        and user discovery paths, so a skill projected into both read twice
        ("skills loadable: 119" for 59 skills, issue #690). Coverage now comes
        from the projection owner's census, which counts each canonical
        identity once; the summing counter must not come back."""

        text = HOOK.read_text(encoding="utf-8")
        self.assertIn("reconcile_claude_l9_skills.py", text)
        self.assertIn("--coverage", text)
        self.assertNotIn("loadable=$((loadable", text)
        self.assertNotIn('"skills loadable:', text)
        # Bounded like every other SessionStart probe, and honest when it fails.
        census = text[text.index('_census="') : text.index("coverage census unavailable")]
        self.assertIn("_l9_bounded", census)

    def test_mcp_claim_is_scoped_to_governance_managed_servers(self) -> None:
        """.mcp.json is the single authority over the servers governance
        configures, not over the session's MCP surface. Hosted surfaces inject
        servers governance neither configures nor gates, so the unqualified
        "single MCP authority" claim was false wherever it mattered."""

        text = HOOK.read_text(encoding="utf-8")
        self.assertIn("GOVERNANCE-MANAGED servers only", text)
        self.assertIn("mcp_platform_injected=", text)
        self.assertNotIn("(single MCP authority)", text)

    def test_hook_does_not_probe_broker(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        self.assertNotIn("probe_broker.py", text)
        self.assertNotIn("--graphiti-probe", text)
        self.assertIn("readiness-receipt.json", text)

    def test_hook_reapplies_hosted_overlay_after_projection(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        proj = text.index("claude_projection.py")
        overlay = text.index("overlay_hosted_settings_env.py")
        self.assertLess(proj, overlay)

    def test_hook_reuses_readiness_receipt_for_capability_block(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        receipt_fn = text.index("emit_readiness_receipt")
        cap_call = text.index('emit_capability_readiness "$PY"')
        self.assertLess(receipt_fn, cap_call)
        self.assertNotIn("python - <<", text)

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
