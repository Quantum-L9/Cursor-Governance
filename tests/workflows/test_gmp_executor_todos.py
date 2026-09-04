"""Authorized GMP --todos-json machine contract."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = ROOT / "workflows" / "gmp_executor.py"
GOV_PY = ROOT / ".venv" / "bin" / "python"
STATE = ROOT / ".l9" / "gmp" / "executor-state.json"

pytestmark = pytest.mark.xdist_group("gmp_executor_authorized")


def _env(**overrides: str) -> dict[str, str]:
    merged = os.environ.copy()
    merged["L9_L4_LOCAL_AUTONOMY"] = "0"
    merged["L9_GMP_DRY_RUN"] = "1"
    merged["L9_GOVERNANCE_SURFACE"] = "cursor"
    merged.update(overrides)
    return merged


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    python = str(GOV_PY if GOV_PY.is_file() else "python3")
    return subprocess.run(
        [python, str(EXECUTOR), *args],
        cwd=str(ROOT),
        env=_env(),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def setup_function() -> None:
    if STATE.exists():
        STATE.unlink()


def teardown_function() -> None:
    if STATE.exists():
        STATE.unlink()


def test_todos_json_inline_locks_plan(tmp_path: Path) -> None:
    payload = json.dumps(
        [{"id": "T1", "task": "touch a", "files": ["ops/autonomy/surface_detect.py"]}]
    )
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--todos-json",
            payload,
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "TODO PLAN LOCKED FROM --todos-json" in proc.stdout
    assert "READY_FOR_BUILD" in proc.stdout


def test_authorized_without_plan_or_todos_fails_fast() -> None:
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ]
    )
    assert proc.returncode != 0
    blob = proc.stderr + proc.stdout
    assert "--todos-json" in blob
    assert "No TODOs" in blob


def test_todos_json_expands_every_declared_file() -> None:
    payload = [
        {
            "id": "T1",
            "task": "touch four",
            "files": [
                "ops/autonomy/surface_detect.py",
                "ops/scripts/lib/surface_detect.sh",
                "ops/autonomy/kernel_gate.py",
                "workflows/gmp_executor.py",
            ],
        }
    ]
    todos = __import__("workflows.gmp_executor", fromlist=["parse_todos_json"]).parse_todos_json(
        json.dumps(payload)
    )
    assert [t["file"] for t in todos] == payload[0]["files"]
    assert [t["id"] for t in todos] == ["T1", "T1.2", "T1.3", "T1.4"]


def test_todos_json_rejects_path_outside_repo(tmp_path: Path) -> None:
    outsider = tmp_path / "secrets.json"
    outsider.write_text("[]", encoding="utf-8")
    mod = __import__("workflows.gmp_executor", fromlist=["parse_todos_json"])
    with pytest.raises(ValueError, match="repository root"):
        mod.parse_todos_json(f"@{outsider}")


def test_authorized_full_locks_todos_json() -> None:
    payload = json.dumps(
        [{"id": "T1", "task": "touch a", "files": ["ops/autonomy/surface_detect.py"]}]
    )
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--todos-json",
            payload,
            "--mode",
            "full",
            "--tier",
            "RUNTIME",
            "t",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "TODO PLAN LOCKED FROM --todos-json" in proc.stdout
    assert "READY_FOR_BUILD" in proc.stdout


def test_empty_todos_json_list_fails() -> None:
    proc = _run(
        [
            "--authorized-by",
            "slash-gmp",
            "--todos-json",
            "[]",
            "--mode",
            "start",
            "--tier",
            "RUNTIME",
            "t",
        ]
    )
    assert proc.returncode != 0
    assert "--todos-json" in (proc.stderr + proc.stdout) or "No TODOs" in (
        proc.stderr + proc.stdout
    )
