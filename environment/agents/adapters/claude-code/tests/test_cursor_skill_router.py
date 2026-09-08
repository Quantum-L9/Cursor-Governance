#!/usr/bin/env python3
"""Cursor beforeSubmitPrompt skill-router adapter smoke test (Claude-side runner).

The full hook contract lives with the Cursor adapter:
environment/agents/adapters/cursor/tests/test_before_submit_router.py. This
file stays because `make claude-skills-test` and validate_skill_activation.py
invoke it by path; it asserts only the cross-surface invariants.
"""

from __future__ import annotations

import hashlib
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


def _run(payload: dict, home: Path, state: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["L9_GOVERNANCE_DIR"] = str(ROOT)
    env["L9_PROACTIVE_SKILLS"] = "true"
    env["L9_ROUTE_STATE_ROOT"] = str(state)
    env.pop("L9_ROUTE_CONVERSATION_ID", None)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


class CursorSkillRouterHook(unittest.TestCase):
    def test_routes_to_scoped_receipt_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home / "routes"
            proc = _run(
                {
                    "conversation_id": "conv-claude-side",
                    "generation_id": "gen",
                    "workspace_roots": [str(ROOT)],
                    "prompt": "Improve the skills so agents proactively use skills more",
                },
                home,
                state,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1]), {"continue": True})
            key = hashlib.sha256(b"conv-claude-side").hexdigest()[:32]
            receipt = json.loads((state / key / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "routed")
            self.assertEqual(receipt["decision"]["primary"]["name"], "l9-recursive-optimization")
            self.assertTrue(Path(receipt["decision"]["primary"]["skill_md"]).is_file())
            self.assertFalse((home / ".cursor" / "l9" / "skill-route.json").exists())

    def test_trivial_prompt_writes_no_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home / "routes"
            proc = _run(
                {"conversation_id": "conv-trivial", "prompt": "Fix the typo in README"}, home, state
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1]), {"continue": True})
            key = hashlib.sha256(b"conv-trivial").hexdigest()[:32]
            receipt = json.loads((state / key / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "no_route")


if __name__ == "__main__":
    unittest.main()
