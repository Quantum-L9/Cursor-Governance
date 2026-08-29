"""One beforeShellExecution process: Graphiti + L4 + plan-kernel."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ops" / "hooks" / "hooks.json.template"
COMBINED_PY = ROOT / "ops" / "hooks" / "before_shell_execution_gate.py"
COMBINED_SH = ROOT / "ops" / "hooks" / "before-shell-execution-gate.sh"


def test_template_has_one_before_shell_execution_command() -> None:
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    entries = data["hooks"]["beforeShellExecution"]
    assert len(entries) == 1
    assert entries[0]["command"] == "./hooks/before-shell-execution-gate.sh"


def test_combined_python_names_all_three_denies() -> None:
    text = COMBINED_PY.read_text(encoding="utf-8")
    assert "shell_gate" in text
    assert "cursor_shell_verdict" in text
    assert "execute_verdict" in text


def test_combined_allows_echo() -> None:
    proc = subprocess.run(
        [sys.executable, str(COMBINED_PY)],
        input='{"command":"echo hi","cwd":"' + str(ROOT) + '"}',
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.splitlines()[-1])
    assert payload["permission"] == "allow"


def test_combined_shell_wrapper_exists() -> None:
    assert COMBINED_SH.is_file()
    assert "before_shell_execution_gate.py" in COMBINED_SH.read_text(encoding="utf-8")
