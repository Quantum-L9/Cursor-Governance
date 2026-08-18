"""Tests for ops/autonomy/merge_gate.py"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parents[3] / "ops" / "autonomy" / "merge_gate.py"
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from l4_local import authorize_release, begin, record_kernels  # noqa: E402


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


def test_denies_gh_pr_merge_without_receipt(stacked_repo: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 12", "cwd": str(stacked_repo)},
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_denies_force_push() -> None:
    code, out, err = _run(
        {"tool_name": "Bash", "tool_input": {"command": "git push --force origin HEAD"}}
    )
    assert code == 0, err
    assert "deny" in out


def test_allows_normal_commit() -> None:
    code, out, err = _run({"tool_name": "Bash", "tool_input": {"command": "git commit -m 'ok'"}})
    assert code == 0, err
    assert out.strip() == ""


def test_breakglass_allows_merge() -> None:
    code, out, err = _run(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"}},
        env={"L9_MERGE_AUTHORIZED": "human approved merge of #1"},
    )
    assert code == 0, err
    assert out.strip() == ""


def test_denies_mcp_merge_tool_without_receipt(stacked_repo: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": "mcp__github__merge_pull_request",
            "tool_input": {"cwd": str(stacked_repo)},
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    assert "deny" in out


def test_l4_release_receipt_does_not_allow_merge(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="merge-auth-test")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)

    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 99",
                "cwd": str(stacked_repo),
            },
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_l4_release_receipt_still_denies_force(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="merge-force-test")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)

    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "git push --force origin HEAD",
                "cwd": str(stacked_repo),
            },
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    assert "deny" in out


def test_l4_release_receipt_still_denies_admin_merge(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="merge-admin-test")
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)

    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 99 --admin",
                "cwd": str(stacked_repo),
            },
            "cwd": str(stacked_repo),
        }
    )
    assert code == 0, err
    assert "deny" in out


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


def test_human_file_authorization_allows_matching_merge(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path)
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash",
            },
        },
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
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot"},
        },
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_human_file_authorization_wrong_repo_denies(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, repo="Quantum-L9/Website-Bot")
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot"},
        },
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_human_file_authorization_malformed_denies(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, extra="{broken")
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot"},
        },
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_repo_scope_authorization_allows_any_pr_in_repo(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 99 --repo Quantum-L9/SEO-Bot --squash",
            },
        },
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
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 99 --repo Quantum-L9/Website-Bot"},
        },
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_repo_scope_authorization_requires_repo_on_command(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 99 --squash"},
        },
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_authorization_never_waives_admin_merge(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot --admin",
            },
        },
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_env_authorization_never_waives_force_push() -> None:
    code, out, err = _run(
        {"tool_name": "Bash", "tool_input": {"command": "git push --force origin HEAD"}},
        env={"L9_MERGE_AUTHORIZED": "human approved merge of #1"},
    )
    assert code == 0, err
    assert "deny" in out


# --- Stack safety (the PR 199 -> PR 200 silent-deletion class) -----------------
#
# PR 199's head was the base of open PR 200. Squash-merging 199 rewound 200's
# merge base and deleted, without conflict, three files 199 had removed and 200
# was carrying forward. These cases pin that shape closed.

STACKED = {"Quantum-L9/SEO-Bot#53": {"head": "fix/parent", "children": [54]}}


def _authorized_merge(tmp_path: Path, command: str, entries: dict) -> tuple[int, str, str]:
    return _run(
        {"tool_name": "Bash", "tool_input": {"command": command}},
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*")),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, entries)),
        },
    )


def test_squash_denied_when_head_is_base_of_open_pr(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(
        tmp_path, "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash", STACKED
    )
    assert code == 0, err
    payload = json.loads(out)
    reason = payload["hookSpecificOutput"]["permissionDecisionReason"]
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "#54" in reason and "fix/parent" in reason


def test_rebase_denied_when_head_is_base_of_open_pr(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(
        tmp_path, "gh pr merge 53 --repo Quantum-L9/SEO-Bot --rebase", STACKED
    )
    assert code == 0, err
    assert "deny" in out


def test_unspecified_method_denied_when_stacked(tmp_path: Path) -> None:
    """The repo default may be squash, so an unnamed method is not provably safe."""
    code, out, err = _authorized_merge(
        tmp_path, "gh pr merge 53 --repo Quantum-L9/SEO-Bot", STACKED
    )
    assert code == 0, err
    assert "deny" in out


def test_merge_commit_allowed_when_stacked(tmp_path: Path) -> None:
    """--merge keeps the head's commits as ancestors, so the child's base survives."""
    code, out, err = _authorized_merge(
        tmp_path, "gh pr merge 53 --repo Quantum-L9/SEO-Bot --merge", STACKED
    )
    assert code == 0, err
    assert out.strip() == ""


def test_squash_allowed_when_no_open_child(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(
        tmp_path,
        "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash",
        {"Quantum-L9/SEO-Bot#53": {"head": "fix/parent", "children": []}},
    )
    assert code == 0, err
    assert out.strip() == ""


def test_unknown_stack_state_fails_closed_for_squash(tmp_path: Path) -> None:
    """No --repo and no probe entry: cannot prove safety, so deny rather than guess."""
    code, out, err = _run(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 53 --squash"}},
        env={"L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*"))},
    )
    assert code == 0, err
    assert "deny" in out


def test_stack_bypass_env_allows_squash(tmp_path: Path) -> None:
    code, out, err = _authorized_merge(
        tmp_path, "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash", STACKED
    )
    assert "deny" in out
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash"},
        },
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*")),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
            "L9_STACK_CHECK_BYPASS": "children already retargeted to main",
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_mcp_merge_tool_honours_stack_check(tmp_path: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": "mcp__github__merge_pull_request",
            "tool_input": {
                "repo": "Quantum-L9/SEO-Bot",
                "pull_number": 53,
                "merge_method": "squash",
            },
        },
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*")),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
        },
    )
    assert code == 0, err
    assert "deny" in out


# --- Standing autonomous-merge flag -------------------------------------------
#
# The flag grants merge authority. It is deliberately not routed through
# _human_breakglass(), so it does not also waive stack safety: unattended
# merging is exactly when an orphaned child PR would go unnoticed.


def test_autonomous_merge_flag_allows_ordinary_merge(tmp_path: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 12 --repo Quantum-L9/SEO-Bot --squash"},
        },
        env={
            "L9_AUTONOMY_AUTONOMOUS_MERGE": "true",
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_autonomous_merge_flag_still_denies_stacked_squash(tmp_path: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash"},
        },
        env={
            "L9_AUTONOMY_AUTONOMOUS_MERGE": "true",
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
        },
    )
    assert code == 0, err
    assert "#54" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_autonomous_merge_flag_never_waives_admin_merge() -> None:
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 12 --repo Quantum-L9/SEO-Bot --admin"},
        },
        env={"L9_AUTONOMY_AUTONOMOUS_MERGE": "true"},
    )
    assert code == 0, err
    assert "deny" in out


def test_autonomous_merge_flag_never_waives_force_push() -> None:
    code, out, err = _run(
        {"tool_name": "Bash", "tool_input": {"command": "git push --force origin HEAD"}},
        env={"L9_AUTONOMY_AUTONOMOUS_MERGE": "true"},
    )
    assert code == 0, err
    assert "deny" in out
