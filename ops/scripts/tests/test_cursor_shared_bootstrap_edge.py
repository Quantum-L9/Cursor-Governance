#!/usr/bin/env python3
"""Fail if Cursor sessionStart drops the shared-bootstrap call edge."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "ops" / "hooks" / "session_start_bootstrap.sh"
SHARED = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"

FORBIDDEN = {
    "ensure_uv_environment.sh": "locked toolchain",
    "gitleaks": "checker provisioning",
    "hydrate_infisical": "secret resolution",
    "scratch_hold.py": "scratch-hold restore",
}


def _live_path(text: str) -> str:
    marker = "\nexit 0\n"
    idx = text.rfind(marker)
    if idx < 0:
        return text
    return text[: idx + len(marker)]


class CursorSharedBootstrapEdgeTests(unittest.TestCase):
    def test_shared_script_exists(self) -> None:
        self.assertTrue(SHARED.is_file(), "missing ops/scripts/bootstrap_agent_environment.sh")
        self.assertIn("ensure_uv_environment.sh", SHARED.read_text(encoding="utf-8"))

    def test_live_hook_delegates_before_exit(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        live = _live_path(text)
        self.assertIn("bootstrap_agent_environment.sh", live)
        # F-10: the surface is forwarded from the runtime, not hard-coded. The
        # default keeps a bare Cursor session behaving exactly as before.
        self.assertIn('--surface "${L9_GOVERNANCE_SURFACE:-cursor}"', live)
        self.assertNotIn("l9_session_runtime_probe", live)

    def test_cursor_hook_does_not_invoke_claude_projection(self) -> None:
        live = _live_path(HOOK.read_text(encoding="utf-8"))
        self.assertNotIn("claude_projection.py --root", live)
        self.assertNotIn("$PROJECTION_ENGINE", live)
        self.assertNotIn("- claude-plugins:", live)

    def test_hook_does_not_reimplement_shared_concerns(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        leaked = [f"{token} ({why})" for token, why in FORBIDDEN.items() if token in text]
        self.assertEqual(
            leaked,
            [],
            "session_start_bootstrap.sh re-implements shared bootstrap concerns: "
            + ", ".join(leaked),
        )

    def test_cursor_wire_path_does_not_invoke_claude_projection(self) -> None:
        setup = REPO / "ops" / "scripts" / "setup_workspace_symlinks.sh"
        text = setup.read_text(encoding="utf-8")
        self.assertNotIn("claude_projection.py --root", text)
        self.assertNotIn("claude_projection.py", text)
        hook = _live_path(HOOK.read_text(encoding="utf-8"))
        self.assertNotIn("L9_CLAUDE_PROJECTION=1", hook)

    def test_hook_reporter_resolve_prefers_worktree_over_gc(self) -> None:
        live = _live_path(HOOK.read_text(encoding="utf-8"))
        override = live.index("L9_SESSION_RUNTIME_REPORT")
        worktree = live.index("CURSOR_PROJECT_DIR/ops/scripts/session_start_runtime_report.py")
        gc = live.index("$GC/ops/scripts/session_start_runtime_report.py")
        self.assertLess(override, worktree)
        self.assertLess(worktree, gc)

    def test_hook_drops_fault_slogans(self) -> None:
        live = _live_path(HOOK.read_text(encoding="utf-8"))
        for slogan in (
            "no publish-path breakglass",
            "itest: unavailable — neo4j absent",
            "GRANT_NOTE",
            "ITEST_NOTE",
            "BOOTSTRAP_NOTE",
        ):
            self.assertNotIn(slogan, live)

    def test_hook_emits_single_graphiti_hydrate_heading(self) -> None:
        live = _live_path(HOOK.read_text(encoding="utf-8"))
        self.assertIn("HYDRATE_BLOCK", live)
        marker = 'COMBINED="$(cat <<EOF'
        idx = live.rfind(marker)
        self.assertGreaterEqual(idx, 0)
        combined = live[idx:]
        self.assertIn("${HYDRATE_BLOCK}", combined)
        self.assertNotIn("### Graphiti hydrate\n${HYDRATE_MD}", combined)


if __name__ == "__main__":
    unittest.main()
