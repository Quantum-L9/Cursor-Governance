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

    def test_hook_does_not_reimplement_shared_concerns(self) -> None:
        text = HOOK.read_text(encoding="utf-8")
        leaked = [f"{token} ({why})" for token, why in FORBIDDEN.items() if token in text]
        self.assertEqual(
            leaked,
            [],
            "session_start_bootstrap.sh re-implements shared bootstrap concerns: "
            + ", ".join(leaked),
        )


if __name__ == "__main__":
    unittest.main()
