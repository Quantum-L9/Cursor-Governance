#!/usr/bin/env python3
"""Cursor beforeSubmitPrompt skill-router adapter tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "CANONICAL_LAW.md").is_file() or (parent / ".git").exists():
            return parent
    raise RuntimeError(f"repo root not found from {start}")


ROOT = _repo_root(_HERE)
HOOK = ROOT / "ops" / "hooks" / "before_submit_skill_router.py"


class CursorSkillRouterHook(unittest.TestCase):
    def test_routes_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["L9_GOVERNANCE_DIR"] = str(ROOT)
            env["L9_PROACTIVE_SKILLS"] = "true"
            env["L9_SKILL_USAGE_LOGGING"] = "true"
            proc = subprocess.run(
                [sys.executable, str(HOOK)],
                input=json.dumps(
                    {
                        "prompt": "Improve the skills so agents proactively use skills more",
                        "session_id": "test-session",
                        "cwd": str(ROOT),
                    }
                ),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertTrue(payload.get("continue", True))
            self.assertIn("l9-recursive-optimization", payload.get("additional_context", ""))
            state = home / ".cursor" / "l9" / "skill-route.json"
            self.assertTrue(state.is_file(), "skill-route.json was not written")
            data = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(data["primary"], "l9-recursive-optimization")

    def test_trivial_prompt_is_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["L9_GOVERNANCE_DIR"] = str(ROOT)
            proc = subprocess.run(
                [sys.executable, str(HOOK)],
                input=json.dumps({"prompt": "Fix the typo in README"}),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertEqual(payload, {"continue": True})
            self.assertFalse((home / ".cursor" / "l9" / "skill-route.json").exists())


if __name__ == "__main__":
    unittest.main()
