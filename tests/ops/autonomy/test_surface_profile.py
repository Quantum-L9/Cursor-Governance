"""Autonomy Surface Profile loader + SessionStart contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from profile_loader import block_sha256, llm_rules_override, session_start_block  # noqa: E402


def test_profile_block_has_doctrine() -> None:
    block = session_start_block(ROOT)
    assert "Autonomy Velocity Doctrine" in block
    assert "l9-pr-remediation" in block
    assert "L4 local autonomy" in block
    assert "Recursive Alignment" in block
    assert block_sha256(ROOT)


def test_llm_override_outranks_ask_first() -> None:
    text = llm_rules_override(ROOT)
    assert "99-no-auto-commit" in text
    assert "claude-code" in text
    assert "L4 Local Autonomy" in text
    assert "local_execution_gate.py" in text


def test_session_start_emits_profile(tmp_path: Path) -> None:
    """SessionStart resolves gov at $HOME/.cursor-governance (spec).

    Point HOME at a temp tree whose `.cursor-governance` symlinks to this
    checkout so the test proves the branch tip, not whatever is checked out
    in the developer's live clone.

    ``CLAUDE_CODE_REMOTE`` is cleared deliberately. The symlink above resolves
    to the live working tree, and in a cloud session the hook's governance
    refresh treats that tree as an ephemeral artifact and runs
    ``git checkout -f -B main origin/main`` on it -- so inheriting the cloud
    flag made this test destroy the in-flight branch and uncommitted work of
    whoever ran the suite. The hook is right (cloud clones are ephemeral); the
    test must not hand it a live checkout to reset. Clearing the flag also
    exercises the local-checkout path, which is the one whose reported
    ``governance SSOT`` / doctrine text this test actually asserts on.
    """
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cursor-governance").symlink_to(ROOT)
    script = (
        ROOT
        / "environment"
        / "agents"
        / "adapters"
        / "claude-code"
        / "hooks"
        / "session_start_claude_governance.sh"
    )
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "HOME": str(home),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "CLAUDE_CODE_REMOTE": "",
        },
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "Autonomy Velocity Doctrine" in ctx
    assert "governance SSOT" in ctx
