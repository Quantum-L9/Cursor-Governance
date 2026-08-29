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


def test_bootstrap_repair_marker_follows_installer_success() -> None:
    """A failed installer must not permanently skip repair at this revision."""
    text = body()
    installer = text.index('timeout "${L9_BOOTSTRAP_REPAIR_BUDGET:-90}" bash "$installer"')
    marker_write = text.index(': >"$marker"')
    assert installer < marker_write, "persist the attempt marker only after installer success"


def _synthetic_gov(home: Path, *, tracked_dirt: bool, untracked_dirt: bool) -> Path:
    """A minimal governance clone the hook will accept as $GOV."""
    import subprocess

    gov = home / ".cursor-governance"
    gov.mkdir(parents=True)
    (gov / "CANONICAL_LAW.md").write_text("synthetic\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(gov)], check=True)
    subprocess.run(["git", "-C", str(gov), "add", "CANONICAL_LAW.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(gov),
            "-c",
            "user.email=t@e",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "base",
        ],
        check=True,
    )
    if tracked_dirt:
        (gov / "CANONICAL_LAW.md").write_text("synthetic + in-flight work\n", encoding="utf-8")
    if untracked_dirt:
        (gov / "scratch.txt").write_text("residue\n", encoding="utf-8")
    return gov


def _run(home: Path, receipt: Path):
    import subprocess

    return subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "CLAUDE_CODE_REMOTE": "true",
            "L9_GOV_REFRESH_RECEIPT": str(receipt),
            "CLAUDE_PROJECT_DIR": str(home),
        },
        check=False,
        timeout=180,
    )


def test_tracked_dirt_actually_prevents_the_reset(tmp_path: Path) -> None:
    """Behavioural proof, not a text match: in-flight tracked work survives."""
    import json

    gov = _synthetic_gov(tmp_path, tracked_dirt=True, untracked_dirt=False)
    receipt = tmp_path / "receipt.json"
    result = _run(tmp_path, receipt)

    assert result.returncode == 0, "SessionStart must never block"
    assert (gov / "CANONICAL_LAW.md").read_text(encoding="utf-8") == (
        "synthetic + in-flight work\n"
    ), "the reset discarded tracked work the guard exists to protect"
    assert json.loads(receipt.read_text(encoding="utf-8"))["outcome"] == "reset-skipped-dirty"


def test_untracked_residue_does_not_trip_the_guard(tmp_path: Path) -> None:
    """A fresh ephemeral clone carries untracked bootstrap residue.

    `checkout -f` leaves untracked files alone, so counting them would strand
    the very clone this refresh exists to reset.
    """
    import json

    _synthetic_gov(tmp_path, tracked_dirt=False, untracked_dirt=True)
    receipt = tmp_path / "receipt.json"
    result = _run(tmp_path, receipt)

    assert result.returncode == 0
    outcome = json.loads(receipt.read_text(encoding="utf-8"))["outcome"]
    assert outcome != "reset-skipped-dirty", "untracked residue must not block the reset"


def test_cursor_skip_precedes_claude_banner() -> None:
    text = body()
    skip = text.index("_l9_claude_runtime")
    banner = text.index('LINES+=("L9 Governance — Claude Code session")')
    assert skip < banner


def test_cursor_runtime_emits_empty_context(tmp_path: Path) -> None:
    """Cursor loads this hook via projected .claude/settings.json.

    Without a Claude Code runtime marker it must not inject account-field
    drift, broker probes, or never_ran installer receipts.
    """
    import json
    import subprocess

    home = tmp_path / "home"
    home.mkdir()
    (home / ".cursor-governance").symlink_to(REPO_ROOT)
    result = subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        env={
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "CURSOR_AGENT": "1",
            "CLAUDE_PROJECT_DIR": str(tmp_path),
        },
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert ctx == ""
    assert "account field drift" not in ctx
    assert "capability plane" not in ctx
    assert "never_ran" not in ctx
