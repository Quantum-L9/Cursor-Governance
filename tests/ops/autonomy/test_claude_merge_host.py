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
