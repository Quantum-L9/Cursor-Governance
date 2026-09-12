"""Conformance: SessionStart is not a second refresh brain.

The launcher (`l9_hook_exec.sh`) is the sole hosted refresh owner. It fetches
and `checkout -f`s trusted `origin/main` only. This hook must never
independently fetch or reset — including when the launcher refused an
untrusted origin, lost its lock, or never bound an attempt.
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


def test_session_start_never_owns_fetch_or_reset() -> None:
    """One owner: launcher refreshes; this hook reports."""
    text = body()
    cloud = text[text.index('if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then') :]
    cloud = cloud[: cloud.index("# shellcheck source=/dev/null")]
    assert "checkout -f" not in cloud
    assert 'git -C "$GOV" fetch' not in cloud
    assert "gov_dirty=" not in cloud
    assert 'GOV_BRANCH="main"' in cloud
    assert "L9_GOVERNANCE_BRANCH" not in cloud
    assert "launcher-absent" in cloud
    assert "no SessionStart fetch/reset" in cloud


def test_launcher_outcome_is_recorded_not_retried() -> None:
    text = body()
    assert "launcher-${L9_GOV_REFRESH_OUTCOME}" in text
    assert "not independently fetching origin/main" in text


def test_hook_still_fails_open() -> None:
    """A guard that blocks the session is worse than the bug it prevents."""
    text = body()
    assert "set -e" not in text.splitlines()[0:5]


def test_bootstrap_repair_marker_records_the_attempt_not_the_success() -> None:
    """The repair must CONVERGE, and a revision bump must be what re-arms it.

    This assertion was inverted, and the inversion is the bug. The marker was
    written only on installer success, so a repair that could not succeed inside
    the hook budget never wrote one — and re-armed on every single session,
    consuming the whole budget each time and killing the hook before it emitted
    any context at all. "Not permanently skipped" had quietly become "permanently
    re-attempted and permanently failing", which is strictly worse: it costs the
    session its entire governance context to achieve nothing.

    An attempt that fails is still an attempt. The marker therefore records the
    attempt BEFORE the installer runs, and the outcome is appended to it, so the
    marker is diagnosable rather than merely present. Re-arming stays keyed on
    the governance revision (the marker path carries it), which is what the
    original intent — repair must not be skipped forever — actually requires.
    """
    text = body()
    marker_write = text.index('>"$marker"')
    installer = text.index('bash "$installer"', marker_write)
    assert marker_write < installer, (
        "record the attempt BEFORE running the installer, or an unfinishable "
        "repair re-arms every session forever"
    )
    # The outcome is appended, so the marker distinguishes ok from failed.
    assert "printf 'ok\\n' >>\"$marker\"" in text
    assert "printf 'failed rc=%s\\n'" in text
    # Re-arming stays revision-keyed: the marker path must carry the revision.
    assert 'marker="$HOME/.l9/claude/bootstrap-repair-${revision}.attempted"' in text


def test_bootstrap_repair_is_bounded_by_the_remaining_hook_budget() -> None:
    """A 90 s ceiling inside a 30 s hook is not long-running, it is impossible.

    The repair used to be launched with a fixed ``L9_BOOTSTRAP_REPAIR_BUDGET``
    of 90 s from a hook registered with ``timeout: 30``. It could only ever be
    killed. The ceiling must be clamped to what is actually left, and the repair
    must be declined outright when that is too little to finish.
    """
    text = body()
    assert '_repair_left="$(_l9_budget_left)"' in text, "size the repair from what is LEFT"
    assert '[ "$_repair_cap" -gt "$_repair_left" ] && _repair_cap="$_repair_left"' in text, (
        "the configured ceiling must never exceed the remaining budget"
    )
    assert 'run_with_timeout "$_repair_cap"' in text, "run under the clamped ceiling"
    assert "bootstrap repair: DEFERRED" in text, (
        "a repair that cannot finish must say so rather than start and be killed"
    )
    # Never a bare `timeout` call — run_with_timeout is the portable wrapper.
    assert not re.search(r'(?<!run_with_)timeout "\$_repair_cap"', text)
    assert 'run_with_timeout() { shift; "$@"; }' not in text
    assert text.index("bootstrap repair: SKIPPED — run_with_timeout.sh missing") < text.index(
        'bash "$installer"'
    )


def test_repair_never_precedes_the_reporting_it_can_starve() -> None:
    """Provisioning runs LAST, after every line the hook must emit.

    The repair used to run first inside ``emit_bootstrap_status``, ahead of the
    environment block and the ``governance refresh`` projection. Clamping it to
    the remaining budget bounds how long it runs; it does not stop it spending
    that budget before the required lines are reached. On a runner whose
    receipt is absent — every fresh CI runner — it took its whole clamp and CI
    emitted ``bootstrap repair: FAILED rc=124`` followed by PARTIAL, with both
    required items missing (`Test Suite` on 225174b9).

    ``SESSION_START_SPEC`` lists the must-emit items and states that dependency
    provisioning is NOT one of them, so ordering is the fix rather than a
    bigger budget: reporting first can never be starved by a repair that
    follows it, however long the repair takes.
    """
    text = body()
    repair = text.index("running the installer once")
    refresh = text.index('"$refresh_reader" --read')
    environment = text.index("--- L9 Claude environment ---")
    assert refresh < repair, "the governance refresh projection must precede the repair"
    assert environment < repair, "the environment status block must precede the repair"


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


def test_tracked_dirt_survives_because_session_start_does_not_reset(
    tmp_path: Path,
) -> None:
    """In-flight tracked work survives: there is no SessionStart checkout -f."""
    import json

    gov = _synthetic_gov(tmp_path, tracked_dirt=True, untracked_dirt=False)
    receipt = tmp_path / "receipt.json"
    result = _run(tmp_path, receipt)

    assert result.returncode == 0, "SessionStart must never block"
    assert (gov / "CANONICAL_LAW.md").read_text(encoding="utf-8") == (
        "synthetic + in-flight work\n"
    )
    assert json.loads(receipt.read_text(encoding="utf-8"))["outcome"] == "launcher-absent"


def test_untracked_residue_does_not_invent_a_reset(tmp_path: Path) -> None:
    import json

    _synthetic_gov(tmp_path, tracked_dirt=False, untracked_dirt=True)
    receipt = tmp_path / "receipt.json"
    result = _run(tmp_path, receipt)

    assert result.returncode == 0
    outcome = json.loads(receipt.read_text(encoding="utf-8"))["outcome"]
    assert outcome == "launcher-absent"


def test_cursor_skip_precedes_claude_banner() -> None:
    text = body()
    skip = text.index("Skip unless surface_detect says Claude")
    # Keyed on the MESSAGE, not on how it is appended: the append call is an
    # implementation detail (it moved from `LINES+=(...)` to `say` when context
    # became durable-on-write), the banner line is the contract.
    banner = text.index('"L9 Governance — Claude Code session"')
    assert skip < banner


def test_bind_precedes_projection_in_install_and_session_start() -> None:
    """Parent-process export must happen before claude_projection.py runs."""
    adapter = REPO_ROOT / "environment" / "agents" / "adapters" / "claude-code"
    install = (adapter / "install.sh").read_text(encoding="utf-8")
    session = body()
    for text in (install, session):
        bind = text.index("bind_l9_memory_interpreter")
        project = text.index("PROJECTION_ENGINE=")
        assert bind < project, "export the bound interpreter before projection"


def _head(gov: Path) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(gov), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _launcher_receipt(sha: str, *, attempt: str, epoch: int, outcome: str = "fetched") -> dict:
    return {
        "schema": "l9.governance-refresh.v1",
        "outcome": outcome,
        "local_sha": sha,
        "origin_sha": sha,
        "refreshed_at": "2026-09-12T00:00:00Z",
        "refreshed_epoch": epoch,
        "attempt_id": attempt,
        "owner_hook": "session_start_claude_governance.sh",
        "ttl_seconds": 3600,
        "commits_behind": 0,
        "state": "fresh",
    }


def _run_with(home: Path, receipt: Path, extra: dict[str, str]):
    import subprocess

    env = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "CLAUDE_CODE_REMOTE": "true",
        "L9_GOV_REFRESH_RECEIPT": str(receipt),
        "CLAUDE_PROJECT_DIR": str(home),
    }
    env.update(extra)
    return subprocess.run(
        ["bash", str(HOOK)], capture_output=True, text=True, env=env, check=False, timeout=180
    )


def test_current_launcher_receipt_skips_the_second_reset(tmp_path: Path) -> None:
    """After THIS launcher attempt refreshed, SessionStart must not checkout -f again."""
    import json
    import time

    gov = _synthetic_gov(tmp_path, tracked_dirt=False, untracked_dirt=False)
    sha = _head(gov)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(_launcher_receipt(sha, attempt="4242-now-7", epoch=int(time.time()))),
        encoding="utf-8",
    )
    result = _run_with(
        tmp_path,
        receipt,
        {"L9_GOV_REFRESH_ATTEMPT_ID": "4242-now-7", "L9_GOV_REFRESH_OUTCOME": "fetched"},
    )
    assert result.returncode == 0, result.stderr
    blob = result.stdout + result.stderr
    assert "already applied this SessionStart" in blob
    assert "checkout -f" not in blob
    assert json.loads(receipt.read_text(encoding="utf-8"))["attempt_id"] == "4242-now-7"


def test_a_fresh_looking_receipt_from_another_attempt_does_not_fetch(
    tmp_path: Path,
) -> None:
    """A stale `fresh` receipt is not authority to run a second fetch/reset."""
    import json
    import time

    gov = _synthetic_gov(tmp_path, tracked_dirt=False, untracked_dirt=False)
    sha = _head(gov)
    receipt = tmp_path / "receipt.json"
    stale = _launcher_receipt(sha, attempt="previous-session", epoch=int(time.time()))
    receipt.write_text(json.dumps(stale), encoding="utf-8")

    result = _run_with(tmp_path, receipt, {})
    assert result.returncode == 0, result.stderr
    assert "already applied this SessionStart" not in result.stdout + result.stderr
    written = json.loads(receipt.read_text(encoding="utf-8"))
    assert written["outcome"] == "launcher-absent"

    receipt.write_text(json.dumps(stale), encoding="utf-8")
    result = _run_with(
        tmp_path,
        receipt,
        {"L9_GOV_REFRESH_ATTEMPT_ID": "this-attempt", "L9_GOV_REFRESH_OUTCOME": "lock-busy"},
    )
    blob = result.stdout + result.stderr
    assert "already applied this SessionStart" not in blob
    assert "launcher did not establish the tree (lock-busy)" in blob
    assert "no SessionStart fetch/reset" in blob
    assert json.loads(receipt.read_text(encoding="utf-8"))["outcome"] == "launcher-lock-busy"


def test_a_matching_attempt_whose_fetch_failed_still_runs_the_fallback(tmp_path: Path) -> None:
    """Same attempt id, but the launcher's own outcome was not `fetched`."""
    import json
    import time

    gov = _synthetic_gov(tmp_path, tracked_dirt=False, untracked_dirt=False)
    sha = _head(gov)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            _launcher_receipt(sha, attempt="a1", epoch=int(time.time()), outcome="fetch-failed")
        ),
        encoding="utf-8",
    )
    result = _run_with(
        tmp_path,
        receipt,
        {"L9_GOV_REFRESH_ATTEMPT_ID": "a1", "L9_GOV_REFRESH_OUTCOME": "fetch-failed"},
    )
    assert "already applied this SessionStart" not in result.stdout + result.stderr


def test_an_old_receipt_of_the_same_attempt_id_is_not_current(tmp_path: Path) -> None:
    """Attempt binding plus recency: a receipt hours old is not this SessionStart's."""
    import json
    import time

    gov = _synthetic_gov(tmp_path, tracked_dirt=False, untracked_dirt=False)
    sha = _head(gov)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(_launcher_receipt(sha, attempt="a1", epoch=int(time.time()) - 7200)),
        encoding="utf-8",
    )
    result = _run_with(
        tmp_path, receipt, {"L9_GOV_REFRESH_ATTEMPT_ID": "a1", "L9_GOV_REFRESH_OUTCOME": "fetched"}
    )
    assert "already applied this SessionStart" not in result.stdout + result.stderr


def test_the_fallback_is_not_suppressed_by_raw_state_parsing() -> None:
    """The hook must key its skip on the attempt binding, never on `state` alone."""
    text = body()
    assert '"attempt_id"' in text
    assert "L9_GOV_REFRESH_ATTEMPT_ID" in text
    assert '"state": "\\([^"]*\\)"' not in text, (
        "reading state-at-write off the receipt is the defect"
    )


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
