"""A scan that could not run must not be reported as a scan that found something.

`run_semgrep` evaluated the tool with a bare `if`, so exit 1 (findings) and exit 2
(could not scan -- unfetchable registry config, bad rule syntax, crash) both landed
in the else-branch and both printed:

    FAIL: semgrep found issues in changed files

That sentence names findings that do not exist, about files nothing read. It is
expensive in exactly the situation where diagnosis matters most: a 403 on
semgrep.dev is indistinguishable from a genuine finding in the gate output, so the
operator hunts a phantom finding instead of an egress rule. `--quiet` then
suppresses the error text that would have said so.

These tests run the real gate as a subprocess, feeding it a changed-file list
through its own `PR_CHANGED_FILE` seam and a stub `semgrep` on PATH -- one per exit
status. Both failure modes still FAIL; what is asserted is that the gate says which
one happened.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "run_pr_security.sh"


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def _run(tmp_path: Path, *, exit_code: int, stdout: str = "", stderr: str = "") -> tuple[int, str]:
    """Invoke the gate with a stubbed semgrep reporting a fixed status."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    # `--version` must answer: the gate probes it before scanning.
    _stub(
        bin_dir,
        "semgrep",
        'if [[ "$1" == "--version" ]]; then echo "1.175.0"; exit 0; fi\n'
        f"printf '%s' {stdout!r}\n"
        f"printf '%s' {stderr!r} >&2\n"
        f"exit {exit_code}",
    )
    # Neutralize the sibling scanners so this test is about semgrep alone.
    _stub(bin_dir, "gitleaks", 'if [[ "$1" == "version" ]]; then echo "8.24.3"; fi\nexit 0')
    _stub(bin_dir, "bandit", 'if [[ "$1" == "--version" ]]; then echo "bandit 1.9.4"; fi\nexit 0')

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "sample.py").write_text("x = 1\n", encoding="utf-8")

    changed = tmp_path / "changed.txt"
    changed.write_text("sample.py\n", encoding="utf-8")

    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "PR_CHANGED_FILE": str(changed),
        "WS": str(workspace),
        # A config the stub never reads, so no network is involved either way.
        "SEMGREP_CONFIGS": "/dev/null",
        "PR_SECURITY_ADVISORY": "0",
    }
    completed = subprocess.run(
        ["bash", str(SCRIPT), str(workspace)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(workspace),
        timeout=180,
    )
    return completed.returncode, completed.stdout + completed.stderr


@pytest.mark.parametrize("exit_code", [2, 7, 13])
def test_a_scan_that_could_not_run_is_not_reported_as_a_finding(
    tmp_path: Path, exit_code: int
) -> None:
    """The bug. Any non-finding failure must say so in its own words."""
    _, output = _run(
        tmp_path, exit_code=exit_code, stderr="Tunnel connection failed: 403 Forbidden"
    )
    assert "semgrep found issues" not in output, (
        f"exit {exit_code} is a tool failure, not a finding, "
        "but the gate claimed findings in files nothing scanned"
    )
    assert "could not complete" in output
    assert f"exit {exit_code}" in output


def test_the_cause_reaches_the_operator(tmp_path: Path) -> None:
    """`--quiet` hides the reason; the gate must surface it on a tool failure.

    Without this the operator sees a bare exit code and has to reproduce the run
    by hand to learn that a host was unreachable.
    """
    _, output = _run(
        tmp_path,
        exit_code=2,
        stderr="ProxyError: Tunnel connection failed: 403 Forbidden (semgrep.dev)",
    )
    assert "403 Forbidden" in output
    assert "semgrep.dev" in output


def test_real_findings_are_still_reported_as_findings(tmp_path: Path) -> None:
    """The fix must not silence exit 1 while teaching exit 2 to speak."""
    _, output = _run(
        tmp_path, exit_code=1, stdout="sample.py:1  hardcoded-secret  Hardcoded credential"
    )
    assert "semgrep found issues" in output
    assert "could not complete" not in output


def test_findings_output_is_not_swallowed(tmp_path: Path) -> None:
    """Capturing output to inspect the status must not hide the findings themselves."""
    _, output = _run(
        tmp_path, exit_code=1, stdout="sample.py:1  hardcoded-secret  Hardcoded credential"
    )
    assert "hardcoded-secret" in output


def test_a_clean_scan_still_passes(tmp_path: Path) -> None:
    code, output = _run(tmp_path, exit_code=0)
    assert "semgrep found issues" not in output
    assert "could not complete" not in output
    assert code == 0, output


@pytest.mark.parametrize("exit_code", [1, 2])
def test_both_failure_modes_remain_failures(tmp_path: Path, exit_code: int) -> None:
    """Accuracy, not leniency.

    The point of this change is what the gate *says*, never what it admits. A scan
    that could not run is not a scan that passed, and neither status may become a
    pass.
    """
    code, output = _run(tmp_path, exit_code=exit_code, stderr="boom")
    assert code != 0, f"exit {exit_code} must still fail the gate:\n{output}"
    assert "RESULT: FAIL" in output


def _run_bandit_case(tmp_path: Path, *, stdout: str) -> tuple[int, str]:
    """Drive the gate with a failing bandit whose output is unterminated.

    Deliberately bandit rather than semgrep: `run_bandit` lets the tool write
    straight to the wave log and then calls `fail`, which is the shape the
    swallow needs. `run_semgrep` now captures and re-prints its output, so that
    path can no longer reproduce it -- testing there would pass for the wrong
    reason.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "semgrep", 'if [[ "$1" == "--version" ]]; then echo "1.175.0"; fi\nexit 0')
    _stub(bin_dir, "gitleaks", 'if [[ "$1" == "version" ]]; then echo "8.24.3"; fi\nexit 0')
    # `uvx` is how the gate reaches bandit; intercept it and answer as bandit.
    _stub(
        bin_dir,
        "uvx",
        'for a in "$@"; do\n'
        '  if [[ "$a" == "--version" ]]; then echo "bandit 1.9.4"; exit 0; fi\n'
        "done\n"
        f"printf '%s' {stdout!r}\n"
        "exit 1",
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "sample.py").write_text("x = 1\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("sample.py\n", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "PR_CHANGED_FILE": str(changed),
        "WS": str(workspace),
        "SEMGREP_CONFIGS": "/dev/null",
        "PR_SECURITY_ADVISORY": "0",
    }
    completed = subprocess.run(
        ["bash", str(SCRIPT), str(workspace)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(workspace),
        timeout=180,
    )
    return completed.returncode, completed.stdout + completed.stderr


def test_unterminated_tool_output_cannot_swallow_a_failure(tmp_path: Path) -> None:
    """A finding must survive a scanner that forgets its trailing newline.

    Scanners run as background wave jobs whose output is redirected to a log. The
    subshell's own counters die with it, so `_replay_scanner_log` re-counting
    `FAIL: ` markers is the only accounting the gate has -- and it matches at
    column 0.

    A tool whose last write is not newline-terminated puts its bytes on the same
    line as the marker:

        boomFAIL: bandit reported issues in changed Python files

    which matches nothing. The failure goes uncounted and a gate holding a real
    finding reports RESULT: PASS -- silent, and in the direction that admits work
    rather than blocking it.
    """
    code, output = _run_bandit_case(tmp_path, stdout="issue found")  # no trailing newline
    assert "\nFAIL: " in output, (
        "the FAIL marker did not start its own line, so the replay could not count it"
    )
    assert "fail=0" not in output, "a real finding was counted as zero failures"
    assert code != 0, f"a finding must fail the gate:\n{output}"
