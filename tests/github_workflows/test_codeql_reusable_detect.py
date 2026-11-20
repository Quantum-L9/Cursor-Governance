"""The CodeQL reusable workflow's language detect step must not read an unknown
language set as "nothing to analyze".

The step's script lives inline in ``.github/workflows/codeql-reusable.yml``
because consumers call the workflow by SHA and the detect job has no checkout.
These tests run that exact script with ``curl`` replaced by a stub, so the
workflow text is the subject under test.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "codeql-reusable.yml"


def _detect_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["detect"]["steps"]
    (step,) = [s for s in steps if s.get("id") == "langs"]
    return step["run"]


def _run_detect(
    tmp_path: Path, *, curl_exit: int, curl_stdout: str
) -> tuple[int, dict[str, str], str]:
    """Run the detect script with a stub curl. Returns (exit, outputs, log)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    payload = tmp_path / "payload"
    payload.write_text(curl_stdout, encoding="utf-8")
    stub = bin_dir / "curl"
    stub.write_text(f'#!/usr/bin/env bash\ncat "{payload}"\nexit {curl_exit}\n', encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    # The script calls `python3`; bind it to the interpreter running the tests.
    (bin_dir / "python3").symlink_to(sys.executable)
    output = tmp_path / "github_output"
    output.touch()
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GH_TOKEN": "stub-token",
        "REPO": "Quantum-L9/example",
        "API": "https://api.invalid",
        "GITHUB_OUTPUT": str(output),
    }
    proc = subprocess.run(
        ["bash", "-c", _detect_script()],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    outputs = dict(
        line.split("=", 1)
        for line in output.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    return proc.returncode, outputs, proc.stdout + proc.stderr


def test_api_failure_fails_detect_and_never_reports_empty(tmp_path: Path) -> None:
    code, outputs, log = _run_detect(tmp_path, curl_exit=22, curl_stdout="")

    assert code != 0
    assert "empty" not in outputs
    assert "matrix" not in outputs
    assert "language set is unknown" in log


@pytest.mark.parametrize("body", ["", "not json", "[]", "null", '"Python"'])
def test_malformed_lookup_fails_detect_and_never_reports_empty(tmp_path: Path, body: str) -> None:
    code, outputs, log = _run_detect(tmp_path, curl_exit=0, curl_stdout=body)

    assert code != 0
    assert "empty" not in outputs
    assert "matrix" not in outputs
    assert "language set is unknown" in log


def test_supported_languages_resolve_a_matrix(tmp_path: Path) -> None:
    body = json.dumps({"Python": 10, "TypeScript": 5, "JavaScript": 1, "Shell": 3})
    code, outputs, _ = _run_detect(tmp_path, curl_exit=0, curl_stdout=body)

    assert code == 0
    assert outputs["empty"] == "false"
    assert json.loads(outputs["matrix"]) == {
        "include": [
            {"language": "javascript-typescript", "build-mode": "none"},
            {"language": "python", "build-mode": "none"},
        ]
    }


@pytest.mark.parametrize("body", ["{}", '{"Shell": 3, "Makefile": 1}'])
def test_proven_unsupported_only_is_not_applicable_with_evidence(tmp_path: Path, body: str) -> None:
    code, outputs, log = _run_detect(tmp_path, curl_exit=0, curl_stdout=body)

    assert code == 0
    assert outputs["empty"] == "true"
    assert json.loads(outputs["matrix"]) == {"include": []}
    assert f"languages reported by GitHub: {sorted(json.loads(body))}" in log
    assert "not applicable" in log


def test_detect_script_has_no_silent_empty_fallback() -> None:
    assert "|| echo '{}'" not in _detect_script()
