"""Tests for ops/autonomy/merge_gate.py

Shell ``git``/``gh`` skip merge *authorization*. Stack safety still applies:
``gh pr merge --squash`` of a parent is denied on Shell and MCP. Other shell
git/gh forms stay unrestricted here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[3] / "ops" / "autonomy" / "merge_gate.py"
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from l4_local import authorize_release, begin, record_kernels  # noqa: E402

MERGE_TOOL = "mcp__github__merge_pull_request"


def _run(event: dict, env: dict | None = None) -> tuple[int, str, str]:
    base = {**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"}
    base.pop("L9_MERGE_AUTHORIZED", None)
    base.pop("L9_AUTONOMY_AUTONOMOUS_MERGE", None)
    base.pop("L9_LOCAL_PUSH_AUTHORIZED", None)
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env={**base, **(env or {})},
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _mcp(**tool_input) -> dict:
    return {"tool_name": MERGE_TOOL, "tool_input": tool_input}


def _auth_file(
    tmp_path: Path,
    *,
    repo: str = "Quantum-L9/SEO-Bot",
    pr: int | str = 53,
    expires_at: float | None = None,
    extra: str = "",
) -> Path:
    import time

    entries = [{"repo": repo, "pr": pr, "expires_at": expires_at or (time.time() + 3600)}]
    payload = json.dumps({"authorizations": entries}) + extra
    path = tmp_path / "merge-authorization.json"
    path.write_text(payload, encoding="utf-8")
    return path


def _probe_file(tmp_path: Path, entries: dict[str, dict] | None = None) -> Path:
    """Injected stack-probe result so the gate never reaches the network in tests."""
    path = tmp_path / "stack-probe.json"
    payload: dict[str, dict] = {"default": {"head": "feat/x", "children": []}}
    payload.update(entries or {})
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


STACKED = {"Quantum-L9/SEO-Bot#53": {"head": "fix/parent", "children": [54]}}


# --- Shell git/gh: exempt from this gate --------------------------------------
#
# Policy still forbids force-push, hard-reset, destructive clean and
# admin-merge, and still routes merges through /l9-pr-remediation. None of that
# is enforced here any more for a shell command.

EXEMPT_SHELL = [
    "git commit -m 'ok'",
    "git push --force origin HEAD",
    "git reset --hard HEAD~1",
    "git clean -fd",
]


def test_commit_message_mentioning_squash_is_not_a_merge() -> None:
    """Heredoc / -m text is data. Matching it as gh pr merge blocked commits."""
    command = (
        "git commit -m \"$(cat <<'EOF'\nfix: never gh pr merge --squash a stack parent\nEOF\n)\""
    )
    code, out, err = _run({"tool_name": "Bash", "tool_input": {"command": command}})
    assert code == 0, err
    assert out.strip() == ""


@pytest.mark.parametrize("command", EXEMPT_SHELL)
def test_shell_git_and_gh_are_allowed(command: str) -> None:
    code, out, err = _run({"tool_name": "Bash", "tool_input": {"command": command}})
    assert code == 0, err
    assert out.strip() == "", command


def test_shell_squash_denied_when_head_is_base_of_open_pr(tmp_path: Path) -> None:
    """Agents type gh in Shell; squash of a parent must still be denied."""
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash"},
        },
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED))},
    )
    assert code == 0, err
    assert "deny" in out
    assert "#54" in out


def test_shell_merge_commit_allowed_when_stacked(tmp_path: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot --merge"},
        },
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED))},
    )
    assert code == 0, err
    assert out.strip() == ""


# --- MCP merge tool: authorization --------------------------------------------


def test_denies_mcp_merge_tool_without_receipt(stacked_repo: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": MERGE_TOOL,
            "tool_input": {"cwd": str(stacked_repo)},
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    assert "deny" in out


def test_breakglass_allows_merge() -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=1),
        env={"L9_MERGE_AUTHORIZED": "human approved merge of #1"},
    )
    assert code == 0, err
    assert out.strip() == ""


def test_l4_release_receipt_does_not_allow_merge(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="merge-auth-test")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)

    code, out, err = _run(
        {
            "tool_name": MERGE_TOOL,
            "tool_input": {"repo": "Quantum-L9/SEO-Bot", "pull_number": 99},
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_l4_release_receipt_still_denies_admin_merge(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="merge-admin-test")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)

    code, out, err = _run(
        {
            "tool_name": MERGE_TOOL,
            "tool_input": {"repo": "Quantum-L9/SEO-Bot", "pull_number": 99, "admin": True},
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    assert "deny" in out


def test_human_file_authorization_allows_matching_merge(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash"),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_human_file_authorization_expired_denies(tmp_path: Path) -> None:
    import time

    auth = _auth_file(tmp_path, expires_at=time.time() - 60)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_human_file_authorization_wrong_repo_denies(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, repo="Quantum-L9/Website-Bot")
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_human_file_authorization_malformed_denies(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, extra="{broken")
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_repo_scope_authorization_allows_any_pr_in_repo(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=99, merge_method="squash"),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_repo_scope_authorization_wrong_repo_denies(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        _mcp(repo="Quantum-L9/Website-Bot", pull_number=99),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_repo_scope_authorization_requires_a_known_repo(tmp_path: Path) -> None:
    """An unidentifiable target cannot match a repo-scoped authorization."""
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        _mcp(pull_number=99, merge_method="squash"),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_authorization_never_waives_admin_merge(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, admin=True),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_env_authorization_never_waives_admin_merge() -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=1, admin=True),
        env={"L9_MERGE_AUTHORIZED": "human approved merge of #1"},
    )
    assert code == 0, err
    assert "deny" in out


# --- Stack safety (the PR 199 -> PR 200 silent-deletion class) -----------------
#
# PR 199's head was the base of open PR 200. Squash-merging 199 rewound 200's
# merge base and deleted, without conflict, three files 199 had removed and 200
# was carrying forward. These cases pin that shape closed on the tool the gate
# still governs.


def _authorized_merge(tmp_path: Path, entries: dict, **tool_input) -> tuple[int, str, str]:
    return _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, **tool_input),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*")),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, entries)),
        },
    )


def test_squash_denied_when_head_is_base_of_open_pr(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(tmp_path, STACKED, merge_method="squash")
    assert code == 0, err
    payload = json.loads(out)
    reason = payload["hookSpecificOutput"]["permissionDecisionReason"]
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "#54" in reason and "fix/parent" in reason


def test_rebase_denied_when_head_is_base_of_open_pr(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(tmp_path, STACKED, merge_method="rebase")
    assert code == 0, err
    assert "deny" in out


def test_unspecified_method_denied_when_stacked(tmp_path: Path) -> None:
    """The repo default may be squash, so an unnamed method is not provably safe."""
    code, out, err = _authorized_merge(tmp_path, STACKED)
    assert code == 0, err
    assert "deny" in out


def test_merge_commit_allowed_when_stacked(tmp_path: Path) -> None:
    """--merge keeps the head's commits as ancestors, so the child's base survives."""
    code, out, err = _authorized_merge(tmp_path, STACKED, merge_method="merge")
    assert code == 0, err
    assert out.strip() == ""


def test_squash_allowed_when_no_open_child(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(
        tmp_path,
        {"Quantum-L9/SEO-Bot#53": {"head": "fix/parent", "children": []}},
        merge_method="squash",
    )
    assert code == 0, err
    assert out.strip() == ""


def test_unknown_stack_state_fails_closed_for_squash(tmp_path: Path) -> None:
    """An unreadable probe cannot prove safety, so deny rather than guess."""
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash"),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*")),
            "L9_STACK_PROBE_FILE": str(tmp_path / "missing-probe.json"),
        },
    )
    assert code == 0, err
    assert "deny" in out


def test_human_breakglass_skips_the_stack_probe(tmp_path: Path) -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash"),
        env={
            "L9_MERGE_AUTHORIZED": "human accepted the stack risk",
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_stack_bypass_env_allows_squash(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(tmp_path, STACKED, merge_method="squash")
    assert "deny" in out
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash"),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*")),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
            "L9_STACK_CHECK_BYPASS": "children already retargeted to main",
        },
    )
    assert code == 0, err
    assert out.strip() == ""


# --- Standing autonomous-merge flag -------------------------------------------
#
# The flag grants merge authority. It is deliberately not routed through
# _human_breakglass(), so it does not also waive stack safety: unattended
# merging is exactly when an orphaned child PR would go unnoticed.


def test_autonomous_merge_flag_allows_ordinary_merge(tmp_path: Path) -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=12, merge_method="squash"),
        env={
            "L9_AUTONOMY_AUTONOMOUS_MERGE": "true",
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_autonomous_merge_flag_still_denies_stacked_squash(tmp_path: Path) -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash"),
        env={
            "L9_AUTONOMY_AUTONOMOUS_MERGE": "true",
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
        },
    )
    assert code == 0, err
    assert "#54" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_autonomous_merge_flag_never_waives_admin_merge() -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=12, admin=True),
        env={"L9_AUTONOMY_AUTONOMOUS_MERGE": "true"},
    )
    assert code == 0, err
    assert "deny" in out
