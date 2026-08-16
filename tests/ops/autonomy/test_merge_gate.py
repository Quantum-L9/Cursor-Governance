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


def test_human_file_authorization_allows_matching_merge(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path)
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 53 --repo Quantum-L9/SEO-Bot --squash",
            },
        },
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
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
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
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
