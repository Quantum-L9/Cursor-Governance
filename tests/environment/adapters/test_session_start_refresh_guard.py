"""Conformance: the cloud governance refresh never discards in-flight work.

The refresh block resets the ephemeral governance clone with `git checkout -f
-B main origin/main`. That is correct for a throwaway clone and destructive
anywhere else: it discards uncommitted changes AND moves HEAD off the checked
out branch. It ran unguarded, and did exactly that to a governance checkout
carrying in-flight work — reachable whenever `$HOME/.cursor-governance`
resolves to a working clone rather than the throwaway one.

The reset only ever has work to do on a clean clone, so refusing a dirty one
costs the intended path nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = (
    REPO_ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "session_start_claude_governance.sh"
)


def body() -> str:
    return HOOK.read_text(encoding="utf-8")


def test_hook_exists_and_parses() -> None:
    import subprocess

    assert HOOK.is_file()
    assert subprocess.run(["bash", "-n", str(HOOK)]).returncode == 0


def test_dirty_clone_is_probed_before_any_reset() -> None:
    text = body()
    probe = text.index("gov_dirty=")
    reset = text.index('checkout -f -B "$GOV_BRANCH"')
    assert probe < reset, "the dirtiness probe must precede the reset"


def test_probe_is_observational() -> None:
    """A probe that mutates to measure state is the defect, not the guard.

    `git status --porcelain` reads; `git stash` would not.
    """
    text = body()
    guard = text[text.index("gov_dirty=") : text.index('checkout -f -B "$GOV_BRANCH"')]
    assert "status --porcelain" in guard
    for mutating in ("git stash", "git clean", "git reset", "git restore"):
        assert mutating not in guard


def test_dirty_clone_skips_the_reset_and_says_so() -> None:
    text = body()
    assert "reset-skipped-dirty" in text, "the skip must be recorded in the receipt"
    assert "reset SKIPPED" in text, "the skip must be visible in the session banner"


def test_reset_is_reachable_only_when_clean() -> None:
    """The fetch+reset path must sit on the else branch of the dirtiness test."""
    text = body()
    guard = re.search(
        r'if \[ -n "\$gov_dirty" \]; then(?P<dirty>.*?)elif git -C "\$GOV" fetch',
        text,
        re.S,
    )
    assert guard is not None, "reset must hang off the dirtiness branch"
    assert "checkout -f" not in guard.group("dirty")


def test_hook_still_fails_open() -> None:
    """A guard that blocks the session is worse than the bug it prevents."""
    text = body()
    assert "set -e" not in text.splitlines()[0:5]
