"""Claude Code PreToolUse merge gate, exercised through the real wrapper.

The wrapper is the host integration: it loads ``merge_gate.py`` from the
governance root and fails closed when that gate is missing. These cases run it
with no controlling terminal. Authorization comes from the hook-test review
fixture, which stands in for the GitHub record the live gate fetches.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WRAP = REPO / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "merge_gate_wrap.py"
SHA = "c" * 40
SLUG = "Quantum-L9/SEO-Bot"
STACK = "ops/autonomy/" + "stack_safe_merge.py"


def _review_file(tmp_path: Path) -> Path:
    path = tmp_path / "reviews.json"
    path.write_text(
        json.dumps(
            {
                f"{SLUG}#53": {
                    "author": "pr-author",
                    "files": ["README.md"],
                    "reviews": [
                        {
                            "user": {"login": "operator", "type": "User"},
                            "state": "APPROVED",
                            "commit_id": SHA,
                            "author_association": "OWNER",
                            "permission": "admin",
                            "submitted_at": "2026-10-14T00:00:00Z",
                        }
                    ],
                    "comments": [],
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _run(tmp_path: Path, event: dict, *, review: bool) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    gov = home / ".cursor-governance"
    gov.parent.mkdir(parents=True, exist_ok=True)
    gov.symlink_to(REPO)
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    env.pop("L9_MERGE_AUTHORIZED", None)
    env.pop("L9_STACK_PROBE_FILE", None)
    env.pop("L9_MERGE_AUTHORIZATION_FILE", None)
    if review:
        env["L9_MERGE_REVIEW_FILE"] = str(_review_file(tmp_path))
    else:
        env.pop("L9_MERGE_REVIEW_FILE", None)
        probe = tmp_path / "probe.json"
        probe.write_text(
            json.dumps({f"{SLUG}#53": {"head": "fix/leaf", "children": [], "sha": SHA}}),
            encoding="utf-8",
        )
        env["L9_STACK_PROBE_FILE"] = str(probe)
    return subprocess.run(
        [sys.executable, str(WRAP)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
        timeout=30,
        start_new_session=True,
    )


def _merge_event() -> dict:
    command = f"python3 {STACK} --repo {SLUG} --pr 53 --head-sha {SHA} --run"
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_wrapper_merge_succeeds_without_a_controlling_terminal(tmp_path: Path) -> None:
    proc = _run(tmp_path, _merge_event(), review=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""
    gate_path = REPO / "ops" / "autonomy" / "merge_gate.py"
    record_path = REPO / "ops" / "autonomy" / "github_merge_authorization.py"
    gate = gate_path.read_text(encoding="utf-8")
    record = record_path.read_text(encoding="utf-8")
    assert "/dev/tty" not in gate
    assert "/dev/tty" not in record


def test_wrapper_denies_when_no_human_authorization_exists(tmp_path: Path) -> None:
    proc = _run(tmp_path, _merge_event(), review=False)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "MERGE_PENDING" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_wrapper_blocks_when_the_gate_is_missing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".cursor-governance" / "ops" / "autonomy").mkdir(parents=True)
    env = {**os.environ, "HOME": str(home)}
    proc = subprocess.run(
        [sys.executable, str(WRAP)],
        input=json.dumps(_merge_event()),
        text=True,
        capture_output=True,
        env=env,
        check=False,
        timeout=30,
        start_new_session=True,
    )
    assert proc.returncode == 2
    assert "BLOCKING" in proc.stderr


def _comment_event(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


AUTHORIZE = "ops/autonomy/" + "authorize_merge.py"


def _operator_run(repo: str = SLUG, pr: int = 53) -> str:
    return (
        f'"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/{AUTHORIZE}" '
        f"--operator-instruction --repo {repo} --pr {pr} --head-sha {SHA}"
    )


SESSION = "sess-human-1"


def _host_transcript(
    path: Path, text: str, *, origin: str = "human", session: str = SESSION
) -> Path:
    """One human turn as Claude Code writes it (observed 2026-10-15: turnOrigin/origin.kind)."""
    record = {
        "type": "user",
        "userType": "external",
        "isSidechain": False,
        "sessionId": session,
        "turnOrigin": origin,
        "origin": {"kind": origin.replace("_", "-")},
        "promptSource": "sdk" if origin == "human" else "system",
        "message": {"role": "user", "content": text},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def _run_with_instruction(
    tmp_path: Path,
    command: str,
    *,
    record_for: tuple[str, int] | None,
    through_wrapper: bool = True,
    bind_session: bool = True,
    transcript_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """The real PreToolUse wrapper, with the receipt written as the host hook writes it.

    ``through_wrapper`` records with the real UserPromptSubmit wrapper from a
    documented payload; False writes the receipt with the Python API as an
    agent that reached the implementation would. ``bind_session`` puts the live
    session and transcript on the PreToolUse event, as Claude Code does.
    """
    import sys as _sys

    _sys.path.insert(0, str(REPO / "ops" / "autonomy"))
    import operator_merge_instruction as omi

    home = tmp_path / "home"
    gov = home / ".cursor-governance"
    gov.parent.mkdir(parents=True, exist_ok=True)
    gov.symlink_to(REPO)
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    for key in (
        "L9_MERGE_AUTHORIZED",
        "L9_STACK_PROBE_FILE",
        "L9_MERGE_AUTHORIZATION_FILE",
        "L9_MERGE_REVIEW_FILE",
        "L9_OPERATOR_INSTRUCTION_FILE",
    ):
        env.pop(key, None)
    transcript = home / ".claude" / "projects" / "-ws" / f"{SESSION}.jsonl"
    prompt = ""
    if record_for:
        repo, pr = record_for
        prompt = f"Fix and merge {repo}#{pr} after the checks pass."
        _host_transcript(transcript, transcript_text or prompt)
        payload = {
            "session_id": SESSION,
            "transcript_path": str(transcript),
            "cwd": str(tmp_path),
            "permission_mode": "default",
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
        }
        if through_wrapper:
            recorded = subprocess.run(
                [
                    sys.executable,
                    str(
                        REPO
                        / "environment/agents/adapters/claude-code/hooks"
                        / ("operator_merge_instruction_" + "wrap.py")
                    ),
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env=env,
                check=False,
                timeout=60,
            )
            assert recorded.returncode == 0, recorded.stderr
        else:
            omi.record_instructions(
                prompt,
                host="claude-code",
                session_id=SESSION,
                path=home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME,
                cwd_repo=None,
                provenance=omi.host_provenance("claude-code", payload),
            )
    event = _comment_event(command)
    if bind_session:
        event.update({"session_id": SESSION, "transcript_path": str(transcript)})
    return subprocess.run(
        [sys.executable, str(WRAP)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
        timeout=30,
        start_new_session=True,
    )


def test_wrapper_accepts_the_operator_instruction_transcription(tmp_path: Path) -> None:
    """Positive 8: Claude Code's actual hook path lets the recorded instruction be transcribed."""
    proc = _run_with_instruction(tmp_path, _operator_run(), record_for=(SLUG, 53))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_wrapper_denies_the_transcription_without_a_recorded_instruction(tmp_path: Path) -> None:
    proc = _run_with_instruction(tmp_path, _operator_run(), record_for=None)
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "never by an agent" in decision["permissionDecisionReason"]


def test_wrapper_denies_the_transcription_for_another_pull_request(tmp_path: Path) -> None:
    proc = _run_with_instruction(tmp_path, _operator_run(pr=54), record_for=(SLUG, 53))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- GAR-MERGE-AUTHORITY-735 F01 on the real Claude PreToolUse path -------------------


def test_f01_wrapper_denies_a_receipt_the_live_transcript_does_not_corroborate(
    tmp_path: Path,
) -> None:
    """Same receipt shape, but the host never recorded that human turn."""
    proc = _run_with_instruction(
        tmp_path,
        _operator_run(),
        record_for=(SLUG, 53),
        through_wrapper=False,
        transcript_text="Review PR #53 and summarize the risks.",
    )
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"


def test_f01_wrapper_denies_when_the_event_carries_no_session_binding(tmp_path: Path) -> None:
    proc = _run_with_instruction(
        tmp_path, _operator_run(), record_for=(SLUG, 53), bind_session=False
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_f01_wrapper_denies_an_agent_run_of_the_recorder(tmp_path: Path) -> None:
    command = (
        '"$HOME/.cursor-governance/.venv/bin/python" '
        '"$HOME/.cursor-governance/ops/autonomy/operator_merge_instruction.py" '
        "record --host claude-code"
    )
    proc = _run_with_instruction(tmp_path, command, record_for=None)
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "never by an agent" in decision["permissionDecisionReason"]


def test_wrapper_denies_an_authorization_line_in_a_body_file(tmp_path: Path) -> None:
    payload = tmp_path / "auth.txt"
    payload.write_text(f"authorize merge {SLUG}#53@{SHA}\n", encoding="utf-8")
    command = f"gh pr comment 53 --repo {SLUG} --body-file {payload}"
    proc = _run(tmp_path, _comment_event(command), review=False)
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "never by an agent" in decision["permissionDecisionReason"]


def test_wrapper_denies_an_unreadable_review_payload(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    command = f"gh api --method POST repos/{SLUG}/pulls/53/reviews --input {missing}"
    proc = _run(tmp_path, _comment_event(command), review=False)
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "never by an agent" in decision["permissionDecisionReason"]


def test_wrapper_denies_approve_event_supplied_through_input_file(tmp_path: Path) -> None:
    payload = tmp_path / "review.json"
    payload.write_text('{"event":"APPROVE","commit_id":"' + SHA + '"}\n', encoding="utf-8")
    command = f"gh api --method POST repos/{SLUG}/pulls/53/reviews --input {payload}"
    proc = _run(tmp_path, _comment_event(command), review=False)
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "never by an agent" in decision["permissionDecisionReason"]


def test_wrapper_allows_a_visible_non_authorizing_comment(tmp_path: Path) -> None:
    command = f"gh pr comment 53 --repo {SLUG} --body 'checks are green'"
    proc = _run(tmp_path, _comment_event(command), review=False)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_wrapper_denies_a_curl_comment_on_the_github_api(tmp_path: Path) -> None:
    line = f"authorize merge {SLUG}#53@{SHA}"
    command = f"curl -X POST https://api.github.com/repos/{SLUG}/issues/53/comments -d '{line}'"
    proc = _run(tmp_path, _comment_event(command), review=False)
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "never by an agent" in decision["permissionDecisionReason"]


def test_wrapper_ignores_a_lookalike_github_host(tmp_path: Path) -> None:
    line = f"authorize merge {SLUG}#53@{SHA}"
    command = (
        "curl -X POST "
        f"https://api.github.com.evil.example/repos/{SLUG}/issues/53/comments "
        f"-d '{line}'"
    )
    proc = _run(tmp_path, _comment_event(command), review=False)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""
