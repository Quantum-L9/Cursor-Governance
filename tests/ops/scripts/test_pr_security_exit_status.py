"""run_pr_security.sh must exit with the status it reports, not its trap's.

Regression for the EXIT-trap status leak: the gate printed
"RESULT: PASS — security gate (nothing in scope)" and exited 1, so `make pr`
died with "FAIL: reader wave job security" while every job in the wave had
passed or skipped, and gate-failure.json named no failing node or hook.

Under `set -e` bash lets an EXIT trap's final command status override the
script's own exit status. Every line of the script's _cleanup is a
`[[ ... ]] && rm` that returns 1 when its guard is false, and `_wave_dir` is
only populated once scans actually run — so the early `exit 0` taken when the
change set is empty became a 1.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "run_pr_security.sh"


def test_script_exists() -> None:
    assert SCRIPT.is_file(), f"missing {SCRIPT}"


def test_empty_change_set_reports_pass_and_exits_zero(tmp_path: Path) -> None:
    """The bug, pinned: PASS on stdout must come with a zero exit code."""
    changed = tmp_path / "changed.txt"
    changed.write_text("", encoding="utf-8")

    env = dict(os.environ)
    env["PR_CHANGED_FILE"] = str(changed)

    proc = subprocess.run(
        ["bash", str(SCRIPT), "--mode", "gate", str(ROOT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        timeout=600,
    )
    combined = proc.stdout + proc.stderr
    assert "RESULT: PASS" in combined, combined[-2000:]
    assert proc.returncode == 0, (
        f"gate printed PASS but exited {proc.returncode}; "
        f"an EXIT trap is leaking its own status.\n{combined[-2000:]}"
    )


def test_cleanup_trap_preserves_triggering_status() -> None:
    """_cleanup must return $? from entry, not the status of its last line.

    A bare `return 0` would also fix the empty-scope case today, but would stop
    being correct the moment a cleanup line is appended below it. Assert the
    status-preserving form directly.
    """
    body = SCRIPT.read_text(encoding="utf-8")
    start = body.index("_cleanup() {")
    end = body.index("\n}", start)
    cleanup = body[start:end]

    assert "local _rc=$?" in cleanup, "_cleanup must capture $? on entry:\n" + cleanup
    assert cleanup.rstrip().endswith('return "$_rc"'), (
        "_cleanup must end by returning the captured status:\n" + cleanup
    )


def test_trap_status_leak_semantics_are_what_we_think() -> None:
    """Pin the bash behaviour the fix depends on, so a shell change is caught.

    Guarded trap that ends false rewrites `exit 0` into 1; capturing and
    returning $? restores both directions.
    """
    leaky = (
        'set -euo pipefail; _w=""; '
        't(){ [[ -n "$_w" && -d "$_w" ]] && rm -rf "$_w"; }; '
        "trap t EXIT; exit 0"
    )
    assert subprocess.run(["bash", "-c", leaky]).returncode == 1

    fixed = (
        'set -euo pipefail; _w=""; '
        't(){ local rc=$?; [[ -n "$_w" && -d "$_w" ]] && rm -rf "$_w"; return "$rc"; }; '
        "trap t EXIT; exit 0"
    )
    assert subprocess.run(["bash", "-c", fixed]).returncode == 0

    # The direction that matters for safety: a real failure stays a failure.
    still_fails = fixed.replace("exit 0", "exit 1")
    assert subprocess.run(["bash", "-c", still_fails]).returncode == 1
