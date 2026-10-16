"""Operator merge instructions (CANONICAL_LAW §6.2.13, operator-prompt channel).

The recorder runs inside the host prompt hooks. These cases prove the parser
(what is and is not an instruction), the receipt store (binding, expiry, cohort
snapshot), and both host adapters run as real subprocesses. A mocked prompt
payload proves parser and adapter behavior; it does not establish that the live
host delivered the prompt, which is why the module says so in its docstring.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import operator_merge_instruction as omi  # noqa: E402

SLUG = "Quantum-L9/Cursor-Governance"
OTHER = "Quantum-L9/SEO-Bot"
CLAUDE_WRAP = (
    REPO
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "operator_merge_instruction_wrap.py"
)
CURSOR_HOOK = REPO / "ops" / "hooks" / "before_submit_merge_instruction.py"
NOW = 1_800_000_000


def _targets(prompt: str, cwd_repo: str | None = None) -> list[tuple[str, str | None, int | None]]:
    """Authorizations only; cancellations are covered by the F03 block below."""
    return [
        (item["scope"], item["repo"], item["pr"])
        for item in omi.parse_instructions(prompt, cwd_repo=cwd_repo)
        if item["kind"] == omi.KIND_AUTHORIZE
    ]


# --- parser: positive -----------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "Merge PR #735 after the checks pass.",
        "Fix and merge PR #735.",
        "fix, then merge pull request #735",
        "I authorize the eventual merge of PR #735 after validation.",
        "merge #735 once CI is green",
        "Please merge pull request 735 when ready",
    ],
)
def test_explicit_instruction_names_the_pull_request(prompt: str) -> None:
    assert _targets(prompt, cwd_repo=SLUG) == [("pr", SLUG, 735)]


def test_qualified_reference_carries_its_repository() -> None:
    assert _targets(f"fix and merge {OTHER}#53", cwd_repo=SLUG) == [("pr", OTHER, 53)]


def test_github_url_reference_carries_its_repository() -> None:
    prompt = f"merge https://github.com/{OTHER}/pull/53"
    assert _targets(prompt, cwd_repo=SLUG) == [("pr", OTHER, 53)]


def test_a_list_of_pull_requests_yields_one_instruction_each() -> None:
    prompt = f"Merge PRs #735, #736 and #737 in {SLUG}."
    assert _targets(prompt) == [("pr", SLUG, 735), ("pr", SLUG, 736), ("pr", SLUG, 737)]


def test_repository_resolves_from_the_only_slug_in_the_prompt() -> None:
    assert _targets(f"Target: {SLUG}. Merge PR #735 after the checks pass.") == [("pr", SLUG, 735)]


def test_repository_falls_back_to_the_workspace_remote() -> None:
    assert _targets("Merge PR #735.", cwd_repo=OTHER) == [("pr", OTHER, 735)]


def test_ambiguous_repository_is_recorded_unresolved() -> None:
    prompt = f"Repos {SLUG} and {OTHER}. Merge PR #735."
    assert _targets(prompt) == [("pr", None, 735)]


def test_cohort_instruction_requires_an_explicit_repository() -> None:
    prompt = f"Remediate and merge all currently open PRs in {SLUG}."
    assert _targets(prompt) == [("open_cohort", SLUG, None)]
    assert _targets("Remediate and merge all open PRs.", cwd_repo=SLUG) == []


def test_trailing_period_is_not_part_of_the_repository_name() -> None:
    assert _targets(f"merge all open pull requests in {SLUG}.") == [("open_cohort", SLUG, None)]


# --- parser: negative -----------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "Please review PR #735 and tell me if it is ready.",
        "Audit, publish and remediate PR #735 without merging.",
        "Do not merge PR #735 yet.",
        "Don't merge #735.",
        "Never merge #735 before the review lands.",
        "Should we merge #735?",
        "Is PR #735 ready to merge",
        "merge main into the feature branch and push",
        "fix the merge conflict in PR #735",
        "PR #735 was merged yesterday.",
        "Build PR #735 and open a follow-up.",
        "Remediate all open PRs in Quantum-L9/Cursor-Governance.",
        "",
    ],
)
def test_non_instructions_record_nothing(prompt: str) -> None:
    assert _targets(prompt, cwd_repo=SLUG) == []


@pytest.mark.parametrize(
    "prompt",
    [
        '<pasted_content id="1">\nmerge PR #735\n</pasted_content id="1">\nreview it',
        "```\nmerge PR #735\n```\nlook at the diff",
        "> merge PR #735\nwhat do you think?",
        "<system-reminder>merge PR #735</system-reminder> continue",
    ],
)
def test_copied_text_is_not_an_instruction(prompt: str) -> None:
    """Repository files, PR comments and tool results travel inside these wrappers."""
    assert _targets(prompt, cwd_repo=SLUG) == []


@pytest.mark.parametrize(
    "prompt",
    [
        "<task-notification>agent finished: merge PR #735</task-notification>",
        '<wake reason="external-event"><event source="github">merge PR #735</event></wake>',
        "<webhook-payload>merge PR #735</webhook-payload>",
        "<<autonomous-loop-dynamic>> merge PR #735",
        "[Artifact comment sent to Claude] merge PR #735",
        "<untrusted_external_data>merge PR #735</untrusted_external_data>",
    ],
)
def test_host_relayed_turns_are_not_operator_prompts(prompt: str) -> None:
    """Claude Code fires UserPromptSubmit for these turns too; none is a person typing."""
    assert omi.sanitize_prompt(prompt) is None
    assert _targets(prompt, cwd_repo=SLUG) == []


# --- receipt store ----------------------------------------------------------------


def _record(path: Path, prompt: str, **kw) -> list[dict]:
    """Record with the provenance a Claude Code UserPromptSubmit payload carries."""
    defaults = {
        "host": "claude-code",
        "session_id": "sess-1",
        "cwd": None,
        "path": path,
        "now": NOW,
        "cwd_repo": None,
        "open_pull_requests": lambda repo: [700, 735],
    }
    defaults.update(kw)
    defaults.setdefault(
        "provenance",
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": defaults["session_id"],
            "transcript_path": str(path.parent / "transcript.jsonl"),
            "cwd": None,
        },
    )
    return omi.record_instructions(prompt, **defaults)


def test_record_binds_host_session_scope_and_expiry(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    (entry,) = _record(store, f"Merge {SLUG}#735 after the checks pass.")
    assert entry["recorder"] == omi.RECORDER
    assert (entry["host"], entry["session_id"]) == ("claude-code", "sess-1")
    assert (entry["scope"], entry["repo"], entry["pr"]) == ("pr", SLUG, 735)
    assert entry["recorded_at"] == NOW
    assert entry["expires_at"] == NOW + omi.DEFAULT_TTL_SECONDS
    assert entry["prompt_sha256"] == omi.prompt_digest(f"Merge {SLUG}#735 after the checks pass.")
    payload = json.loads(store.read_text(encoding="utf-8"))
    assert payload["schema"] == omi.SCHEMA
    assert payload["instructions"] == [entry]


def test_find_matches_only_the_named_repository_and_pull_request(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    _record(store, f"Merge {SLUG}#735.")
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 10) is not None
    assert omi.find_instruction(SLUG, "735", path=store, now=NOW + 10) is not None
    assert omi.find_instruction(SLUG, 736, path=store, now=NOW + 10) is None
    assert omi.find_instruction(OTHER, 735, path=store, now=NOW + 10) is None
    assert omi.find_instruction("", 735, path=store, now=NOW + 10) is None


def test_expired_instruction_no_longer_covers(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    _record(store, f"Merge {SLUG}#735.")
    late = NOW + omi.DEFAULT_TTL_SECONDS
    assert omi.find_instruction(SLUG, 735, path=store, now=late) is None
    verdict = omi.instruction_verdict(SLUG, 735, path=store, now=late)
    assert not verdict["authorized"]
    assert "expired" in verdict["reason"]


def test_unresolved_repository_binds_nothing(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    (entry,) = _record(store, f"Repos {SLUG} and {OTHER}. Merge PR #735.")
    assert entry["repo"] is None
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 1) is None
    assert omi.find_instruction(OTHER, 735, path=store, now=NOW + 1) is None


def test_cohort_covers_only_pull_requests_open_when_it_was_spoken(tmp_path: Path) -> None:
    """Membership is the snapshot taken at recording time, nothing else (F04)."""
    store = tmp_path / "instructions.json"
    (entry,) = _record(store, f"Remediate and merge all currently open PRs in {SLUG}.")
    assert entry["members"] == [700, 735]
    assert entry["membership"] == "snapshot"
    assert omi.find_instruction(SLUG, 700, path=store, now=NOW + 1)
    assert omi.find_instruction(SLUG, 900, path=store, now=NOW + 1) is None
    assert omi.find_instruction(OTHER, 700, path=store, now=NOW + 1) is None
    verdict = omi.instruction_verdict(SLUG, 900, path=store, now=NOW + 1)
    assert "not open when the cohort was authorized" in verdict["reason"]


def test_a_forged_entry_without_the_recorder_stamp_is_dead(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    _record(store, f"Merge {SLUG}#735.")
    payload = json.loads(store.read_text(encoding="utf-8"))
    forged = dict(payload["instructions"][0], pr=736, recorder="agent", id="f" * 16)
    payload["instructions"].append(forged)
    store.write_text(json.dumps(payload), encoding="utf-8")
    assert omi.find_instruction(SLUG, 736, path=store, now=NOW + 1) is None
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 1) is not None


def test_recording_prunes_expired_entries_and_caps_the_store(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    _record(store, f"Merge {SLUG}#1.", now=NOW - omi.DEFAULT_TTL_SECONDS - 1)
    for number in range(2, 2 + omi.MAX_RECORDS + 5):
        _record(store, f"Merge {SLUG}#{number}.", now=NOW)
    entries = omi.load_instructions(store)
    assert len(entries) == omi.MAX_RECORDS
    assert all(entry["pr"] != 1 for entry in entries)


def test_recording_a_prompt_without_instructions_writes_nothing(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    assert _record(store, "Review PR #735 and summarize the risks.") == []
    assert not store.exists()


# --- host adapters, run for real ---------------------------------------------------


def _home_with_governance(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / ".cursor-governance").parent.mkdir(parents=True, exist_ok=True)
    (home / ".cursor-governance").symlink_to(REPO)
    return home


def test_claude_wrapper_records_from_a_user_prompt_submit_payload(tmp_path: Path) -> None:
    """The real UserPromptSubmit wrapper, run as Claude Code would run it."""
    home = _home_with_governance(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    subprocess.run(["git", "-C", str(workspace), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(workspace), "remote", "add", "origin", f"https://github.com/{SLUG}.git"],
        check=True,
    )
    payload = {
        "session_id": "claude-sess-9",
        "transcript_path": str(tmp_path / "t.jsonl"),
        "cwd": str(workspace),
        "permission_mode": "default",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Fix and merge PR #735 after the checks pass.",
    }
    proc = subprocess.run(
        [sys.executable, str(CLAUDE_WRAP)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)},
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    output = json.loads(proc.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "UserPromptSubmit"
    assert f"{SLUG}#735" in output["additionalContext"]
    assert "--operator-instruction" in output["additionalContext"]
    store = home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME
    (entry,) = omi.load_instructions(store)
    assert (entry["host"], entry["session_id"]) == ("claude-code", "claude-sess-9")
    assert (entry["repo"], entry["pr"]) == (SLUG, 735)
    assert omi.find_instruction(SLUG, 735, path=store) is not None


def test_claude_wrapper_is_silent_for_a_prompt_without_an_instruction(tmp_path: Path) -> None:
    home = _home_with_governance(tmp_path)
    payload = {"session_id": "s", "cwd": str(tmp_path), "prompt": "Review PR #735, no merge."}
    proc = subprocess.run(
        [sys.executable, str(CLAUDE_WRAP)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)},
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""
    assert not (home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME).exists()


def test_cursor_hook_records_and_never_blocks(tmp_path: Path) -> None:
    """The real beforeSubmitPrompt adapter: conversation_id is the session identity.

    ``PATH`` carries no ``gh``, so the cohort snapshot is recorded as unavailable
    instead of reaching GitHub from a unit test; the receipt then covers nothing.
    """
    home = _home_with_governance(tmp_path)
    no_tools = tmp_path / "no-tools"
    no_tools.mkdir()
    payload = {
        "hook_event_name": "beforeSubmitPrompt",
        "conversation_id": "conv-7",
        "generation_id": "gen-1",
        "workspace_roots": [str(tmp_path)],
        "prompt": f"Remediate and merge all currently open PRs in {SLUG}.",
        "attachments": [],
    }
    proc = subprocess.run(
        [sys.executable, str(CURSOR_HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "HOME": str(home),
            "L9_GOVERNANCE_DIR": str(REPO),
            "PATH": str(no_tools),
        },
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == {"continue": True}
    store = home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME
    (entry,) = omi.load_instructions(store)
    assert (entry["host"], entry["session_id"], entry["scope"]) == (
        "cursor",
        "conv-7",
        "open_cohort",
    )
    assert entry["repo"] == SLUG
    assert entry["provenance"]["hook_event_name"] == "beforeSubmitPrompt"
    assert entry["members"] is None and entry["membership"] == "unavailable"
    assert omi.find_instruction(SLUG, 735, path=store) is None


def test_cursor_hook_fails_open_on_garbage(tmp_path: Path) -> None:
    home = _home_with_governance(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(CURSOR_HOOK)],
        input="not json",
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home), "L9_GOVERNANCE_DIR": str(REPO)},
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == {"continue": True}


def test_show_reports_the_verdict(tmp_path: Path, monkeypatch, capsys) -> None:
    store = tmp_path / "instructions.json"
    _record(store, f"Merge {SLUG}#735.", now=int(time.time()))
    monkeypatch.setattr(omi, "default_store_path", lambda: store)
    assert omi.main(["show", "--repo", SLUG, "--pr", "735"]) == 0
    assert json.loads(capsys.readouterr().out)["authorized"] is True
    assert omi.main(["show", "--repo", SLUG, "--pr", "736"]) == 3


# =============================================================================
# GAR-MERGE-AUTHORITY-735 remediation findings (F01-F04). Each block names the
# defect it reproduces; every case below failed or errored against head d8723211.
# =============================================================================

MODULE = REPO / "ops" / "autonomy" / "operator_merge_instruction.py"
SESSION = "sess-human-1"


def _kinds(
    prompt: str, cwd_repo: str | None = SLUG
) -> list[tuple[str, str, str | None, int | None]]:
    return [
        (item["kind"], item["scope"], item["repo"], item["pr"])
        for item in omi.parse_instructions(prompt, cwd_repo=cwd_repo)
    ]


def _transcript(
    path: Path,
    *lines: tuple[str, str] | tuple[str, str, dict],
    session: str = SESSION,
) -> Path:
    """A transcript as Claude Code writes it: one JSON record per line.

    Each line is ``(turn_origin, text)`` or ``(turn_origin, text, extra)``; the
    human prompt carries ``turnOrigin: "human"`` and ``origin.kind: "human"``,
    which is what was observed in a live Claude Code transcript on 2026-10-15.
    """
    records = []
    for item in lines:
        origin, text = item[0], item[1]
        extra = item[2] if len(item) > 2 else {}
        record = {
            "type": "user",
            "userType": "external",
            "isSidechain": False,
            "sessionId": session,
            "turnOrigin": origin,
            "origin": {"kind": origin.replace("_", "-")},
            "promptSource": "sdk" if origin == "human" else "system",
            "message": {"role": "user", "content": text},
            "timestamp": "2026-10-15T20:00:00Z",
        }
        record.update(extra)
        records.append(json.dumps(record))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(records) + "\n", encoding="utf-8")
    return path


def _claude_payload(
    prompt: str, transcript: Path, session: str = SESSION, cwd: str = "/ws"
) -> dict:
    return {
        "session_id": session,
        "transcript_path": str(transcript),
        "cwd": cwd,
        "permission_mode": "default",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }


def _host_record(
    store: Path,
    prompt: str,
    *,
    transcript: Path,
    session: str = SESSION,
    now: int = NOW,
    open_pull_requests=None,
) -> list[dict]:
    """Record the way the Claude wrapper does: payload provenance, no shortcuts."""
    payload = _claude_payload(prompt, transcript, session=session)
    return omi.record_instructions(
        prompt,
        host="claude-code",
        session_id=session,
        cwd="/ws",
        path=store,
        now=now,
        cwd_repo=None,
        provenance=omi.host_provenance("claude-code", payload),
        open_pull_requests=open_pull_requests,
    )


# --- F02: quoted, reported or discussed text is not a directed instruction -------


@pytest.mark.parametrize(
    "prompt",
    [
        "Review this report: 'Merge PR #735 after the checks pass.'",
        'Review this report: "Merge PR #735 after the checks pass."',
        "Review this report: “Merge PR #735 after the checks pass.”",
        "Audit PR #735; do not merge it.",
        "The PR description says: merge PR #735 once green.",
        "Someone commented 'merge PR #735' on the thread; ignore it.",
        "The operator authorizes the eventual merge of PR #735 after validation.",
        "The report recommends that we merge PR #735.",
        "Here is the audit: merge PR #735 after the checks pass",
        "Summarize the thread where they asked to merge #735.",
    ],
)
def test_f02_quoted_or_reported_merge_text_does_not_authorize(prompt: str) -> None:
    assert [k for k in _kinds(prompt) if k[0] == "authorize"] == []


@pytest.mark.parametrize(
    "prompt",
    [
        "Fix and merge PR #735 after validation.",
        "Please merge PR #735.",
        "Go ahead and merge #735.",
        "You may merge PR #735 once CI is green.",
        "I authorize the merge of PR #735.",
        "Remediate, test and merge PR #735.",
        "Review and merge PR #735.",
    ],
)
def test_f02_affirmative_directed_instructions_still_authorize(prompt: str) -> None:
    assert _kinds(prompt) == [("authorize", "pr", SLUG, 735)]


def test_f02_mixed_clauses_are_interpreted_independently() -> None:
    assert _kinds("Don't merge #735, but merge #736.") == [
        ("revoke", "pr", SLUG, 735),
        ("authorize", "pr", SLUG, 736),
    ]
    assert _kinds("Merge PR #735. Do not merge PR #736.") == [
        ("authorize", "pr", SLUG, 735),
        ("revoke", "pr", SLUG, 736),
    ]
    assert _kinds("Fix and merge #735; leave #736 alone and do not merge it.") == [
        ("authorize", "pr", SLUG, 735),
    ]


# --- F03: explicit cancellation is recorded and the latest instruction wins ------


@pytest.mark.parametrize(
    "prompt",
    [
        "Cancel the merge of PR #735.",
        "Do not merge PR #735 after all.",
        "Stop. Do not merge #735.",
        "Revoke the merge authorization for #735.",
        "Hold off on merging #735.",
        f"Withdraw my merge instruction for {SLUG}#735.",
    ],
)
def test_f03_cancellations_are_recorded_as_revocations(prompt: str) -> None:
    assert _kinds(prompt) == [("revoke", "pr", SLUG, 735)]


def test_f03_cohort_cancellation_is_recorded() -> None:
    assert _kinds(f"Do not merge any open PRs in {SLUG}.") == [
        ("revoke", "open_cohort", SLUG, None)
    ]
    assert _kinds(f"Cancel all merges in {SLUG}.") == [("revoke", "open_cohort", SLUG, None)]


def test_f03_revocation_after_authorization_withdraws_it(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", f"Merge {SLUG}#735."))
    _host_record(store, f"Merge {SLUG}#735.", transcript=transcript, now=NOW)
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 1) is not None
    _host_record(store, f"Do not merge {SLUG}#735.", transcript=transcript, now=NOW + 60)
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 120) is None
    verdict = omi.instruction_verdict(SLUG, 735, path=store, now=NOW + 120)
    assert "revoked" in verdict["reason"]
    revoke = omi.revocation_for(SLUG, 735, path=store, now=NOW + 120)
    assert revoke is not None and revoke["kind"] == "revoke"


def test_f03_reauthorization_after_revocation_wins(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))
    _host_record(store, f"Merge {SLUG}#735.", transcript=transcript, now=NOW)
    _host_record(store, f"Do not merge {SLUG}#735.", transcript=transcript, now=NOW + 60)
    _host_record(store, f"Merge {SLUG}#735 after all.", transcript=transcript, now=NOW + 120)
    found = omi.find_instruction(SLUG, 735, path=store, now=NOW + 180)
    assert found is not None and found["recorded_at"] == NOW + 120
    assert omi.revocation_for(SLUG, 735, path=store, now=NOW + 180) is None


def test_f03_revocation_is_scoped_to_the_named_pull_request(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))
    _host_record(store, f"Merge {SLUG}#735 and {SLUG}#736.", transcript=transcript, now=NOW)
    _host_record(store, f"Cancel the merge of {SLUG}#735.", transcript=transcript, now=NOW + 60)
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 120) is None
    assert omi.find_instruction(SLUG, 736, path=store, now=NOW + 120) is not None


def test_f03_revocation_blocks_authority_issued_before_it_only(tmp_path: Path) -> None:
    """``since`` is the grant's issue time: a revoke after it kills it, a revoke
    before it (followed by the re-authorization that produced the grant) does not."""
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))
    _host_record(store, f"Merge {SLUG}#735.", transcript=transcript, now=NOW)
    _host_record(store, f"Do not merge {SLUG}#735.", transcript=transcript, now=NOW + 60)
    assert omi.revocation_for(SLUG, 735, path=store, now=NOW + 120, since=NOW + 30) is not None
    _host_record(store, f"Merge {SLUG}#735 again.", transcript=transcript, now=NOW + 120)
    assert omi.revocation_for(SLUG, 735, path=store, now=NOW + 180, since=NOW + 150) is None


def test_f03_cohort_revocation_covers_every_member(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))
    _host_record(
        store,
        f"Remediate and merge all currently open PRs in {SLUG}.",
        transcript=transcript,
        now=NOW,
        open_pull_requests=lambda repo: [700, 735],
    )
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 1) is not None
    _host_record(
        store, f"Do not merge any open PRs in {SLUG}.", transcript=transcript, now=NOW + 60
    )
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 120) is None
    assert omi.find_instruction(SLUG, 700, path=store, now=NOW + 120) is None


def test_f03_revocation_persists_across_processes(tmp_path: Path) -> None:
    home = tmp_path / "home"
    store = home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))
    stamp = int(time.time())
    _host_record(store, f"Merge {SLUG}#735.", transcript=transcript, now=stamp - 120)
    _host_record(store, f"Do not merge {SLUG}#735.", transcript=transcript, now=stamp - 60)
    proc = subprocess.run(
        [sys.executable, str(MODULE), "show", "--repo", SLUG, "--pr", "735"],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
        timeout=60,
    )
    assert proc.returncode == 3, proc.stdout
    assert "revoked" in json.loads(proc.stdout)["reason"]


# --- F04: a cohort is the set of pull requests actually open when it was spoken --


def test_f04_cohort_membership_is_snapshotted_from_github_at_record_time(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))
    asked: list[str] = []

    def lister(repo: str) -> list[int]:
        asked.append(repo)
        return [700, 735]

    (entry,) = _host_record(
        store,
        f"Remediate and merge all currently open PRs in {SLUG}.",
        transcript=transcript,
        open_pull_requests=lister,
    )
    assert asked == [SLUG]
    assert entry["members"] == [700, 735]
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 1) is not None
    # opened after the instruction: never in the snapshot
    assert omi.find_instruction(SLUG, 900, path=store, now=NOW + 1) is None
    # closed before the instruction and reopened later: not open at the time
    assert omi.find_instruction(SLUG, 650, path=store, now=NOW + 1) is None
    verdict = omi.instruction_verdict(SLUG, 900, path=store, now=NOW + 1)
    assert "not open" in verdict["reason"] or "cohort" in verdict["reason"]


def test_f04_unknown_membership_fails_closed(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))

    def broken(repo: str) -> list[int]:
        raise RuntimeError("HTTP 503")

    (entry,) = _host_record(
        store,
        f"Remediate and merge all currently open PRs in {SLUG}.",
        transcript=transcript,
        open_pull_requests=broken,
    )
    assert entry["members"] is None
    assert omi.find_instruction(SLUG, 735, path=store, now=NOW + 1) is None
    assert "membership" in omi.instruction_verdict(SLUG, 735, path=store, now=NOW + 1)["reason"]


def test_f04_creation_time_alone_no_longer_proves_membership(tmp_path: Path) -> None:
    """The old heuristic accepted any PR created before the instruction."""
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", "x"))
    _host_record(
        store,
        f"Remediate and merge all currently open PRs in {SLUG}.",
        transcript=transcript,
        open_pull_requests=lambda repo: [735],
    )
    # #600 existed long before the instruction but was not open at the time.
    assert omi.find_instruction(SLUG, 600, path=store, now=NOW + 1) is None


# --- F01: a receipt is trusted only when the host delivered it ----------------------


def test_f01_payload_without_hook_provenance_records_nothing(tmp_path: Path) -> None:
    """An agent-shaped JSON blob is not a host prompt event."""
    home = tmp_path / "home"
    store = home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME
    assert omi.host_provenance("claude-code", {"session_id": "s", "prompt": "merge #735"}) is None
    assert (
        omi.host_provenance("claude-code", {"session_id": "s", "hook_event_name": "PreToolUse"})
        is None
    )
    proc = subprocess.run(
        [sys.executable, str(MODULE), "record", "--host", "claude-code"],
        input=json.dumps({"session_id": "s", "prompt": f"Merge {SLUG}#735."}),
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0
    assert not store.exists()


def test_f01_record_requires_provenance(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        omi.record_instructions(
            f"Merge {SLUG}#735.",
            host="claude-code",
            session_id=SESSION,
            path=tmp_path / "s.json",
            now=NOW,
            cwd_repo=None,
            provenance=None,
        )


def test_f01_entry_without_provenance_is_dead(tmp_path: Path) -> None:
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", f"Merge {SLUG}#735."))
    _host_record(store, f"Merge {SLUG}#735.", transcript=transcript)
    payload = json.loads(store.read_text(encoding="utf-8"))
    forged = dict(payload["instructions"][0], pr=736, id="f" * 16)
    forged.pop("provenance")
    payload["instructions"].append(forged)
    store.write_text(json.dumps(payload), encoding="utf-8")
    assert omi.find_instruction(SLUG, 736, path=store, now=NOW + 1) is None


def test_f01_transcript_corroborates_only_a_human_turn_of_the_same_session(tmp_path: Path) -> None:
    prompt = f"Fix and merge {SLUG}#735 after the checks pass."
    store = tmp_path / "instructions.json"
    human = _transcript(tmp_path / "human.jsonl", ("human", prompt))
    (entry,) = _host_record(store, prompt, transcript=human)
    ok, _ = omi.transcript_corroborates(entry)
    assert ok

    relayed = _transcript(tmp_path / "relay.jsonl", ("task_notification", prompt))
    ok, reason = omi.transcript_corroborates(entry, transcript_path=relayed)
    assert not ok and "human" in reason

    other_session = _transcript(tmp_path / "other.jsonl", ("human", prompt), session="sess-other")
    ok, reason = omi.transcript_corroborates(entry, transcript_path=other_session)
    assert not ok

    meta = _transcript(tmp_path / "meta.jsonl", ("human", prompt, {"isMeta": True}))
    ok, _ = omi.transcript_corroborates(entry, transcript_path=meta)
    assert not ok

    absent_text = _transcript(tmp_path / "absent.jsonl", ("human", "Review PR #735 please."))
    ok, _ = omi.transcript_corroborates(entry, transcript_path=absent_text)
    assert not ok

    ok, reason = omi.transcript_corroborates(entry, transcript_path=tmp_path / "missing.jsonl")
    assert not ok


def test_f01_receipt_verdict_binds_session_and_transcript(tmp_path: Path) -> None:
    prompt = f"Merge {SLUG}#735."
    store = tmp_path / "instructions.json"
    transcript = _transcript(tmp_path / "t.jsonl", ("human", prompt))
    (entry,) = _host_record(store, prompt, transcript=transcript)
    live = {"now": NOW + 1, "transcript_path": str(transcript)}
    assert omi.receipt_verdict(entry, session_id=SESSION, **live)["ok"]
    assert not omi.receipt_verdict(entry, session_id="sess-agent", **live)["ok"]
    assert not omi.receipt_verdict(
        entry, session_id=SESSION, now=NOW + 1, transcript_path="/elsewhere.jsonl"
    )["ok"]
    cursor = dict(
        entry,
        host="cursor",
        provenance={"hook_event_name": "beforeSubmitPrompt", "session_id": SESSION},
    )
    verdict = omi.receipt_verdict(cursor, session_id=SESSION, **live)
    assert not verdict["ok"] and omi.BLOCKED_HOST_ORIGIN in verdict["reason"]


def test_f01_claude_wrapper_records_hook_provenance(tmp_path: Path) -> None:
    home = _home_with_governance(tmp_path)
    prompt = f"Fix and merge {SLUG}#735 after the checks pass."
    transcript = _transcript(tmp_path / "t.jsonl", ("human", prompt))
    proc = subprocess.run(
        [sys.executable, str(CLAUDE_WRAP)],
        input=json.dumps(_claude_payload(prompt, transcript)),
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home), "USERPROFILE": str(home)},
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    store = home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME
    (entry,) = omi.load_instructions(store)
    assert entry["provenance"]["hook_event_name"] == "UserPromptSubmit"
    assert entry["provenance"]["transcript_path"] == str(transcript)
    assert omi.receipt_verdict(entry, session_id=SESSION, transcript_path=str(transcript))["ok"]
