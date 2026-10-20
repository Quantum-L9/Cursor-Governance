"""The merge-authority switch (CANONICAL_LAW §6.2.16) on both hosts.

The root ``conftest.py`` pins ``strict`` for every test; these tests set the
mode they exercise.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
AUTONOMY = REPO / "ops" / "autonomy"
GATE = AUTONOMY / "merge_gate.py"
CURSOR_HOOK = REPO / "ops" / "hooks" / "before_submit_merge_instruction.py"
sys.path.insert(0, str(AUTONOMY))

import merge_authority_switch as switch  # noqa: E402
import merge_gate  # noqa: E402
import operator_merge_instruction as omi  # noqa: E402
import stack_safe_merge  # noqa: E402

SHA = "a" * 40
REPO_SLUG = "Quantum-L9/Cursor-Governance"


def _gate(event: dict, mode: str) -> tuple[int, str]:
    env = {**os.environ, "L9_MERGE_AUTHORITY_MODE": mode}
    env.pop("L9_MERGE_AUTHORIZED", None)
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    return proc.returncode, proc.stdout


def _denied(event: dict, mode: str) -> bool:
    code, out = _gate(event, mode)
    return code != 0 or '"deny"' in out


def _bash(command: str, **extra: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, **extra}


# --- the switch itself ---------------------------------------------------------


def _switch_file(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "merge-authority.json"
    path.write_text(body, encoding="utf-8")
    return path


def test_shipped_switch_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(switch.ENV_OVERRIDE)
    assert switch.mode() == switch.DISABLED
    assert switch.SWITCH_FILE == REPO / "ops" / "config" / "merge-authority.json"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ('{"enforcement": "disabled"}', "disabled"),
        ('{"enforcement": "strict"}', "strict"),
        ('{"enforcement": "chat"}', "strict"),
        ('{"enforcement": "nonsense"}', "strict"),
        ("not json", "strict"),
        ("[]", "strict"),
    ],
)
def test_switch_reads_file_and_fails_to_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, expected: str
) -> None:
    monkeypatch.delenv(switch.ENV_OVERRIDE)
    assert switch.mode(_switch_file(tmp_path, body)) == expected


def test_missing_switch_file_is_strict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(switch.ENV_OVERRIDE)
    assert switch.mode(tmp_path / "absent.json") == switch.STRICT


def test_env_override_wins_when_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    disabled_file = _switch_file(tmp_path, '{"enforcement": "disabled"}')
    monkeypatch.setenv(switch.ENV_OVERRIDE, "strict")
    assert switch.mode(disabled_file) == switch.STRICT
    monkeypatch.setenv(switch.ENV_OVERRIDE, "bogus")
    assert switch.mode(disabled_file) == switch.DISABLED


# --- merge gate (Claude Code PreToolUse) ----------------------------------------


@pytest.mark.parametrize(
    "event",
    [
        _bash("gh pr merge 12 --merge"),
        _bash(f"gh api -X PUT repos/{REPO_SLUG}/pulls/12/merge -f merge_method=merge"),
        _bash(f"gh pr merge 12 --auto --merge --match-head-commit {SHA}"),
        _bash(
            f"python ops/autonomy/authorize_merge.py --repo {REPO_SLUG} --pr 12 --head-sha {SHA}"
        ),
        _bash(
            f"python ops/autonomy/stack_safe_merge.py --repo {REPO_SLUG} --pr 12 "
            f"--head-sha {SHA} --run",
            agent_id="worker-1",
        ),
        {
            "tool_name": "mcp__github__merge_pull_request",
            "tool_input": {"owner": "Quantum-L9", "repo": "Cursor-Governance", "pullNumber": 12},
        },
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(Path.home() / ".l9" / "autonomy" / "merge-authorization.json"),
                "content": "{}",
            },
        },
    ],
)
def test_disabled_gate_allows_every_merge_and_grant_path(event: dict) -> None:
    assert not _denied(event, "disabled")


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 12 --admin --merge",
        "git push --force origin main",
        "git reset --hard HEAD~1",
    ],
)
def test_disabled_gate_still_denies_the_never_waive_set(command: str) -> None:
    assert _denied(_bash(command), "disabled")


def test_disabled_gate_still_denies_admin_mcp_merge() -> None:
    event = {"tool_name": "mcp__github__merge_pull_request", "tool_input": {"admin": True}}
    assert merge_gate.evaluate(event["tool_name"], event["tool_input"]) is not None


def test_strict_gate_still_denies_an_unauthorized_merge() -> None:
    assert _denied(_bash("gh pr merge 12 --merge"), "strict")


def test_evaluate_honours_the_switch_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    tool_input = {"command": "gh pr merge 12 --merge"}
    monkeypatch.setenv(switch.ENV_OVERRIDE, "disabled")
    assert merge_gate.evaluate("Bash", tool_input) is None
    monkeypatch.setenv(switch.ENV_OVERRIDE, "strict")
    assert merge_gate.evaluate("Bash", tool_input) is not None


# --- stack_safe_merge (host-agnostic: the Cursor and Claude merge executor) ------


def test_disabled_merge_is_authorized_at_the_live_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(switch.ENV_OVERRIDE, "disabled")
    monkeypatch.setattr(stack_safe_merge, "live_head_sha", lambda repo, pr: SHA)
    status = stack_safe_merge.authorization_status(
        REPO_SLUG, "12", SHA, path=tmp_path / "no-grant.json"
    )
    assert status["status"] == "AUTHORIZED"
    assert status["channel"] == "enforcement_disabled"


def test_disabled_merge_still_refuses_a_moved_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(switch.ENV_OVERRIDE, "disabled")
    monkeypatch.setattr(stack_safe_merge, "live_head_sha", lambda repo, pr: "b" * 40)
    status = stack_safe_merge.authorization_status(
        REPO_SLUG, "12", SHA, path=tmp_path / "no-grant.json"
    )
    assert status["status"] == "MERGE_PENDING"
    assert "head moved" in status["reason"]


# --- prompt recorder (both hosts) ------------------------------------------------

MERGE_PROMPT = f"merge {REPO_SLUG}#12"


def test_disabled_recorder_is_silent_for_claude_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(switch.ENV_OVERRIDE, "disabled")
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "s-1",
        "transcript_path": str(tmp_path / "t.jsonl"),
        "cwd": str(tmp_path),
        "prompt": MERGE_PROMPT,
    }
    result = omi.capture_from_payload(payload, "claude-code")
    assert result == {"recorded": [], "notes": [], "provenance": None}
    assert omi.hook_context(result["recorded"], result["notes"], None) == ""


def test_disabled_recorder_is_silent_for_cursor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = tmp_path / "operator-merge-instructions.json"
    env = {
        **os.environ,
        "L9_MERGE_AUTHORITY_MODE": "disabled",
        "L9_GOVERNANCE_DIR": str(REPO),
        "L9_OPERATOR_INSTRUCTION_FILE": str(store),
        "HOME": str(tmp_path),
    }
    payload = {
        "hook_event_name": "beforeSubmitPrompt",
        "conversation_id": "c-1",
        "generation_id": "g-1",
        "workspace_roots": [str(REPO)],
        "prompt": MERGE_PROMPT,
    }
    proc = subprocess.run(
        [sys.executable, str(CURSOR_HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == {"continue": True}
    assert not store.exists()
    assert not (tmp_path / ".l9" / "autonomy").exists()
