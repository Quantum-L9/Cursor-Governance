"""Autonomy Surface Profile loader + SessionStart contract."""

from __future__ import annotations

import json
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
    assert block_sha256(ROOT)


def test_llm_override_outranks_ask_first() -> None:
    text = llm_rules_override(ROOT)
    assert "99-no-auto-commit" in text
    assert "claude-code" in text


def test_session_start_emits_profile(tmp_path: Path) -> None:
    script = ROOT / "environment" / "claude-code" / "hooks" / "session_start_claude_governance.sh"
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            **dict(**{k: v for k, v in __import__("os").environ.items()}),
            "HOME": str(Path.home()),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
        },
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "Autonomy Velocity Doctrine" in ctx
    assert "governance SSOT" in ctx
