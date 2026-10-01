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


def test_every_bootstrap_generates_its_receipt_unconditionally() -> None:
    """Generation is not a repair: it is not gated on state or on a marker.

    The installer used to run only for a non-ready verdict and at most once per
    governance revision (a `.attempted` marker). A session whose on-disk receipt
    read `ready` therefore generated nothing and reported an earlier session's
    receipt as its own. Every ceremony now runs the installer and stamps its id.
    """
    text = body()
    assert ".attempted" not in text, "no once-per-revision gate on generation"
    assert "repair_verdict" not in text, "generation is not armed by a state verdict"
    assert 'env L9_BOOTSTRAP_ID="$_L9_CEREMONY_ID"' in text
    assert 'bash "$BOOTSTRAP_INSTALLER"' in text


def test_bootstrap_generation_is_bounded_by_the_remaining_hook_budget() -> None:
    """A 90 s ceiling inside a 30 s hook is not long-running, it is impossible.

    The ceiling is clamped to what is left, minus a floor kept for the reporting
    that follows, and generation is declined outright when that is too little.
    """
    text = body()
    assert "_gen_left=$(( $(_l9_budget_left) - ${L9_BOOTSTRAP_REPORT_FLOOR:-6} ))" in text
    assert '[ "$_gen_cap" -gt "$_gen_left" ] && _gen_cap="$_gen_left"' in text
    assert 'run_with_timeout "$_gen_cap"' in text, "run under the clamped ceiling"
    assert "bootstrap receipt: NOT GENERATED" in text
    # Never a bare `timeout` call — run_with_timeout is the portable wrapper.
    assert not re.search(r'(?<!run_with_)timeout "\$_gen_cap"', text)
    assert 'run_with_timeout() { shift; "$@"; }' not in text
    bounded = text.index('run_with_timeout "$_gen_cap"')
    assert text.index("NOT GENERATED — run_with_timeout.sh missing") < bounded
    assert text.index('bash "$BOOTSTRAP_INSTALLER"', bounded) > bounded


def test_bootstrap_installer_is_detached_not_killed_at_the_deadline() -> None:
    """The installer finishes even when the hook budget does not cover it.

    A deadline kill left capabilities / memory UNKNOWN until a manual
    `make claude-install`, and could tear a venv install in half. With setsid
    the installer runs in its own session, holds none of the hook's pipes, and
    the hook waits only as long as the clamped budget allows. The bounded
    run_with_timeout launch stays as the fallback when setsid is missing.
    """
    text = body()
    detached = text.index('setsid --wait flock -n -E 75 "$HOME/.l9/claude/bootstrap.lock"')
    assert detached < text.index('run_with_timeout "$_gen_cap"')
    launch = text[detached : text.index("_gen_pid=$!", detached)]
    assert 'env L9_BOOTSTRAP_ID="$_L9_CEREMONY_ID"' in launch
    # The log is opened INSIDE the lock: a refused ceremony must not truncate it.
    assert 'exec >"$L9_BOOTSTRAP_LOG_PATH" 2>&1 </dev/null' in launch
    assert "</dev/null >/dev/null 2>&1 &" in launch
    assert "repo_write_lock_acquire" in launch
    assert "installer still running after" in text
    assert "NOT killed" in text


def test_the_reader_reads_the_receipt_this_ceremony_generated() -> None:
    """Generate, THEN read — and read bound to the ceremony id.

    Printing the on-disk receipt before the installer ran reported an expired
    verdict the installer was about to replace, and nothing re-read the receipt
    the installer wrote. The environment block must follow generation, and the
    reader must be bound to the id the installer stamped.
    """
    text = body()
    generate = text.index('bash "$BOOTSTRAP_INSTALLER"')
    environment = text.index("--- L9 Claude environment ---")
    refresh = text.index('"$refresh_reader" --read')
    assert generate < environment < refresh
    assert (
        '"$reader" --read --reprobe --bootstrap-id "${_L9_CEREMONY_ID:-not-generated-$$}"' in text
    )


def test_the_installer_is_this_ceremonys_projection() -> None:
    """The standalone projection engine runs only when there is no installer.

    install.sh runs the same projection engine. Running both spent a cold
    projection (~8 s measured) twice, and left a cold ceremony too little budget
    to generate its receipt at all.
    """
    text = body()
    installer = text.index('if [ -f "$BOOTSTRAP_INSTALLER" ]; then')
    standalone = text.index('elif [ "${L9_SKIP_SESSION_PROJECTION:-}" != "1" ]')
    engine_run = text.index('"$PROJECTION_ENGINE" --root "$GOV"')
    assert installer < standalone < engine_run


def test_the_hook_carries_no_second_receipt_parser() -> None:
    """Receipt path, expiry, workspace and ceremony are the reader's rules.

    The hook used to json.load bootstrap-state.json inline and compare the
    single `workspace` field — a rule that disagreed with the reader's
    covered_roots and with the runtime report about the same receipt.
    """
    text = body()
    assert '"$HOME/.l9/claude/bootstrap-state.json"' not in text
    assert '--workspace "$WORKSPACE"' in text[text.index('"$reader" --read --reprobe') :][:200]
    # The readiness emitter reads the bootstrap receipt too; it gets the id.
    assert 'env L9_BOOTSTRAP_ID="${_L9_CEREMONY_ID:-not-generated-$$}"' in text


def test_the_readiness_emitter_reads_the_receipt_through_the_reader() -> None:
    emitter = (REPO_ROOT / "ops" / "scripts" / "emit_claude_readiness.py").read_text(
        encoding="utf-8"
    )
    assert "bootstrap_receipt.read(" in emitter
    assert '"bootstrap-state.json")' not in emitter


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
