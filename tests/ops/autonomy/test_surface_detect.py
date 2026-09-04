"""Parity + precedence for ops.autonomy.surface_detect."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ops.autonomy.surface_detect import (
    detect_surface,
    is_claude_gate_surface,
    kernel_latch_surface,
)

ROOT = Path(__file__).resolve().parents[3]
SH_LIB = ROOT / "ops" / "scripts" / "lib" / "surface_detect.sh"

MATRIX = [
    ({"L9_GOVERNANCE_SURFACE": "cursor", "CLAUDECODE": "1"}, "cursor"),
    ({"CLAUDE_CODE_REMOTE": "true"}, "claude-code-remote"),
    ({"CLAUDECODE": "1"}, "claude-code"),
    ({"CLAUDE_CODE_ENTRYPOINT": "cli"}, "claude-code"),
    ({"CLAUDE_CODE_SESSION_ID": "abc"}, "claude-code"),
    ({"CURSOR_AGENT": "1"}, "cursor"),
    ({"L9_GOVERNANCE_SURFACE": "codex"}, "codex"),
    ({"L9_GOVERNANCE_SURFACE": "gemini"}, "gemini"),
    ({"L9_GOVERNANCE_SURFACE": "manus"}, "manus"),
    ({}, "unknown"),
]


def _shell_detect(env: dict[str, str]) -> str:
    lines = [
        "set -euo pipefail",
        f'source "{SH_LIB}"',
        "unset CURSOR_AGENT CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION_ID || true",
        "unset CLAUDE_CODE_REMOTE L9_GOVERNANCE_SURFACE || true",
    ]
    for k, v in env.items():
        lines.append(f'export {k}="{v}"')
    lines.append("l9_detect_surface")
    script = "\n".join(lines)
    base = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "CURSOR_AGENT",
            "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_CODE_REMOTE",
            "L9_GOVERNANCE_SURFACE",
        }
    }
    proc = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env=base,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc.stdout.strip()


@pytest.mark.parametrize("env,expected", MATRIX)
def test_python_detect_matrix(env: dict[str, str], expected: str) -> None:
    assert detect_surface(env) == expected


@pytest.mark.parametrize("env,expected", MATRIX)
def test_shell_python_parity(env: dict[str, str], expected: str) -> None:
    assert _shell_detect(env) == expected
    assert detect_surface(env) == expected


def test_claude_gate_and_kernel_helpers() -> None:
    assert is_claude_gate_surface({"CLAUDECODE": "1"}) is True
    assert is_claude_gate_surface({"CURSOR_AGENT": "1"}) is False
    assert is_claude_gate_surface({}) is False  # unknown → not a Claude gate surface
    assert kernel_latch_surface({"CLAUDECODE": "1"}) is True
    assert kernel_latch_surface({"CLAUDE_CODE_REMOTE": "true"}) is True
    assert kernel_latch_surface({"L9_GOVERNANCE_SURFACE": "codex"}) is True
    assert kernel_latch_surface({"CURSOR_AGENT": "1"}) is False
