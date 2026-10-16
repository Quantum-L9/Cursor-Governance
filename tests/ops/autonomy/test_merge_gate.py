"""Tests for ops/autonomy/merge_gate.py

Merge authority is a human grant bound to repo + PR + exact head (§6.2.12), on
every transport: shell ``gh``, REST (gh api / curl), MCP, and
``stack_safe_merge.py --run``. Stack safety still applies after authority:
``gh pr merge --squash`` of a parent is denied on Shell and MCP. Non-merge
shell git/gh forms stay unrestricted here.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[3] / "ops" / "autonomy" / "merge_gate.py"
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from l4_local import authorize_release, begin  # noqa: E402

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


SHA = "a" * 40


def _auth_file(
    tmp_path: Path,
    *,
    repo: str = "Quantum-L9/SEO-Bot",
    pr: int | str = 53,
    expires_at: float | None = None,
    head_sha: str | None = SHA,
    issuer: str | None = "human",
    no_expiry: bool = False,
    extra: str = "",
) -> Path:
    """A grant in the shape authorize_merge.py writes; overrides make it invalid."""
    import time

    entry: dict = {"repo": repo, "pr": pr}
    if not no_expiry:
        entry["expires_at"] = expires_at or (time.time() + 3600)
    if head_sha is not None:
        entry["head_sha"] = head_sha
    if issuer is not None:
        entry["issuer"] = issuer
    payload = json.dumps({"authorizations": [entry]}) + extra
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


CLI_MERGE = " ".join(["gh", "pr", "merge"])


def _granted(tmp_path: Path, probe: dict | None = None, **auth) -> dict[str, str]:
    return {
        "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, **auth)),
        "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, probe)),
    }


def test_shell_squash_denied_when_head_is_base_of_open_pr(tmp_path: Path) -> None:
    """Past authority, squash of a parent must still be denied."""
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --squash "
                f"--match-head-commit {SHA}"
            },
        },
        env=_granted(tmp_path, STACKED),
    )
    assert code == 0, err
    assert "deny" in out
    assert "#54" in out


def test_shell_merge_commit_allowed_when_stacked_and_granted(tmp_path: Path) -> None:
    code, out, err = _run(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --merge "
                f"--match-head-commit {SHA}"
            },
        },
        env=_granted(tmp_path, STACKED),
    )
    assert code == 0, err
    assert out.strip() == ""


@pytest.mark.parametrize(
    "command",
    [
        f"{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --merge",
        f"{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --squash --match-head-commit {SHA}",
        f"cd /tmp && {CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --merge",
    ],
)
def test_shell_gh_merge_without_grant_is_merge_pending(tmp_path: Path, command: str) -> None:
    """The git/gh workflow exemption never covered merge authority (§6.2.12)."""
    code, out, err = _run(
        _shell(command),
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path))},
    )
    assert code == 0, err
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason.startswith("MERGE_PENDING")


def test_shell_gh_merge_with_grant_but_unnamed_head_is_denied(tmp_path: Path) -> None:
    code, out, err = _run(
        _shell(f"{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --merge"),
        env=_granted(tmp_path),
    )
    assert code == 0, err
    assert "MERGE_PENDING" in out


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
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash", sha=SHA),
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


# --- Receipt hardening: expiry required, optional immutable head_sha binding ---


def test_receipt_without_expiry_denies(tmp_path: Path) -> None:
    """A receipt that never expires is not a valid authorization (expiry required)."""
    auth = _auth_file(tmp_path, no_expiry=True)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_receipt_bound_to_head_sha_allows_matching_head(tmp_path: Path) -> None:
    sha = "a" * 40
    auth = _auth_file(tmp_path, head_sha=sha)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash", sha=sha),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_receipt_bound_to_head_sha_denies_moved_head(tmp_path: Path) -> None:
    auth = _auth_file(tmp_path, head_sha="a" * 40)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash", sha="b" * 40),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_receipt_bound_to_head_sha_denies_when_head_unnamed(tmp_path: Path) -> None:
    """A revision-bound receipt requires the merge to name that head; silence is denial."""
    auth = _auth_file(tmp_path, head_sha="a" * 40)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash"),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_head_unbound_receipt_never_authorizes(tmp_path: Path) -> None:
    """The pre-§6.2.12 receipt shape (no head_sha) is legacy: it grants nothing."""
    auth = _auth_file(tmp_path, head_sha=None)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash", sha="c" * 40),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert "MERGE_PENDING" in out


def test_repo_scope_authorization_never_authorizes(tmp_path: Path) -> None:
    """The receipt Converge used to self-issue (pr "*") authorizes no PR."""
    auth = _auth_file(tmp_path, pr="*")
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=99, merge_method="squash", sha=SHA),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert "MERGE_PENDING" in out


@pytest.mark.parametrize(
    "auth",
    [
        {"issuer": None},  # legacy source: l9-pr-remediation receipt
        {"issuer": "l9-pr-remediation"},
        {"pr": 54},  # another PR
        {"repo": "Quantum-L9/Website-Bot"},  # another repository
        {"head_sha": "abc1234"},  # short sha is not an exact head
    ],
)
def test_receipt_for_another_target_or_issuer_denies(tmp_path: Path, auth: dict) -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="merge", sha=SHA),
        env=_granted(tmp_path, **auth),
    )
    assert code == 0, err
    assert "MERGE_PENDING" in out


def test_grant_with_overlong_life_denies(tmp_path: Path) -> None:
    """A grant claiming to outlive MAX_GRANT_TTL_SECONDS is not one the issuer writes."""
    import time

    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="merge", sha=SHA),
        env=_granted(tmp_path, expires_at=time.time() + 30 * 86400),
    )
    assert code == 0, err
    assert "MERGE_PENDING" in out


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
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, sha=SHA, **tool_input),
        env=_granted(tmp_path, entries),
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
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash", sha=SHA),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path)),
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
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash", sha=SHA),
        env={
            **_granted(tmp_path, STACKED),
            "L9_STACK_CHECK_BYPASS": "children already retargeted to main",
        },
    )
    assert code == 0, err
    assert out.strip() == ""


# --- Retired standing autonomous-merge flag -----------------------------------
#
# L9_AUTONOMY_AUTONOMOUS_MERGE is no longer a merge authority. A standing
# environment boolean set once in the Claude account/session configuration must
# never grant unattended merge, so the gate does not consult it: merge requires
# the human per-session breakglass (L9_MERGE_AUTHORIZED) or a scoped, expiring
# receipt bound to the repo (and PR). Setting the flag has no effect.


def test_autonomous_merge_flag_no_longer_authorizes(tmp_path: Path) -> None:
    # Even for an unstacked PR the flag grants nothing; the merge stays denied.
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=12, merge_method="squash"),
        env={
            "L9_AUTONOMY_AUTONOMOUS_MERGE": "true",
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "not an authority" in reason


def test_autonomous_merge_flag_does_not_authorize_stacked_squash(tmp_path: Path) -> None:
    # Flag set, but merge authority fails first: denied on authority, not stack.
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash"),
        env={
            "L9_AUTONOMY_AUTONOMOUS_MERGE": "true",
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
        },
    )
    assert code == 0, err
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "not an authority" in reason


def test_autonomous_merge_flag_never_waives_admin_merge() -> None:
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=12, admin=True),
        env={"L9_AUTONOMY_AUTONOMOUS_MERGE": "true"},
    )
    assert code == 0, err
    assert "deny" in out


def test_github_mcp_owner_repo_shape_is_authorized(tmp_path: Path) -> None:
    """The GitHub MCP server splits identity across ``owner`` + ``repo``.

    It also spells the number ``pullNumber``. Parsing only ``repo``/``pull_number``
    produced the bare name ``SEO-Bot`` with no PR number, which no receipt can
    match -- ``authorize_merge.py`` refuses to write a repo without an owner --
    so a valid, in-scope receipt was rejected.
    """
    auth = _auth_file(tmp_path)
    code, out, err = _run(
        _mcp(owner="Quantum-L9", repo="SEO-Bot", pullNumber=53, merge_method="squash", sha=SHA),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_github_mcp_owner_repo_shape_wrong_repo_still_denies(tmp_path: Path) -> None:
    """Joining owner + repo must not widen scope: a receipt for another repo still denies."""
    auth = _auth_file(tmp_path, repo="Quantum-L9/Website-Bot")
    code, out, err = _run(
        _mcp(owner="Quantum-L9", repo="SEO-Bot", pullNumber=53, merge_method="squash", sha=SHA),
        env={"L9_MERGE_AUTHORIZATION_FILE": str(auth)},
    )
    assert code == 0, err
    assert "deny" in out


def test_github_mcp_owner_does_not_rewrite_explicit_owner_name(tmp_path: Path) -> None:
    """An explicit ``owner/name`` in ``repo`` wins; ``owner`` is never prepended twice."""
    auth = _auth_file(tmp_path)
    code, out, err = _run(
        _mcp(
            owner="Some-Other-Org",
            repo="Quantum-L9/SEO-Bot",
            pullNumber=53,
            merge_method="squash",
            sha=SHA,
        ),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


def test_github_mcp_shape_stack_parent_squash_still_denied(tmp_path: Path) -> None:
    """The stack probe short-circuits on an empty PR number.

    With the owner/repo shape unparsed the probe never ran, so squashing a stack
    parent was silently permitted. It must be denied once the number is read.
    """
    auth = _auth_file(tmp_path)
    probe = _probe_file(tmp_path, STACKED)
    code, out, err = _run(
        _mcp(owner="Quantum-L9", repo="SEO-Bot", pullNumber=53, merge_method="squash", sha=SHA),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(probe),
        },
    )
    assert code == 0, err
    assert "deny" in out


# --- REST transport: the same merge, a different verb -------------------------
#
# `gh pr merge` is GraphQL. Where GraphQL is unavailable -- this Claude surface
# serves only a pinned set of PR-review operations and 403s everything else --
# the REST endpoint is the merge that actually runs:
#
#   gh api -X PUT repos/<owner>/<name>/pulls/<n>/merge -f merge_method=squash
#
# The gate recognised a merge by matching the literal words `gh pr merge`, so it
# saw only the transport that does not work here. Closing it takes two halves:
# recognising the command, and resolving owner/name/number from the endpoint
# path -- the stack probe returns early on an empty PR number, so detection
# alone would still have read every REST merge as safe.

REST_SQUASH = (
    f"gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/merge -f merge_method=squash -f sha={SHA}"
)
REST_MERGE_COMMIT = (
    f"gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/merge -f merge_method=merge -f sha={SHA}"
)
REST_UNSPECIFIED = f"gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/merge -f sha={SHA}"
CURL_SQUASH = (
    "curl -X PUT https://api.github.com/repos/Quantum-L9/SEO-Bot/pulls/53/merge "
    f"-f merge_method=squash -f sha={SHA}"
)


def _shell(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


@pytest.mark.parametrize("command", [REST_SQUASH, REST_UNSPECIFIED])
def test_rest_squash_of_a_stack_parent_is_denied(tmp_path: Path, command: str) -> None:
    """The transport changes; the ancestry damage does not.

    REST_UNSPECIFIED is included deliberately: an unnamed method stays
    ANCESTRY_BREAKING, so the gate needs no claim about the endpoint's
    server-side default to stay correct.
    """
    code, out, err = _run(_shell(command), env=_granted(tmp_path, STACKED))
    assert code == 0, err
    assert "deny" in out, command
    assert "#54" in out, command


def test_curl_rest_merge_requires_authorization(tmp_path: Path) -> None:
    """curl is not a git/gh event, so it lands where authorization is enforced.

    That is stricter than the gh spelling, not weaker: the git/gh exemption
    covers `gh`, and a bare HTTP client was never exempt -- it was simply
    unrecognised, so it reached neither check.
    """
    code, out, err = _run(
        _shell(CURL_SQUASH),
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED))},
    )
    assert code == 0, err
    assert "deny" in out


def test_curl_rest_squash_of_a_stack_parent_denied_even_with_a_receipt(
    tmp_path: Path,
) -> None:
    """Past authorization, the same ancestry check must still fire."""
    code, out, err = _run(
        _shell(CURL_SQUASH),
        env=_granted(tmp_path, STACKED),
    )
    assert code == 0, err
    assert "deny" in out
    assert "#54" in out


@pytest.mark.parametrize("command_name", ["REST_MERGE_COMMIT", "REST_SQUASH"])
def test_gh_rest_merge_without_grant_is_merge_pending(tmp_path: Path, command_name: str) -> None:
    """gh api is a git/gh event, but a REST merge is an effect: authority applies."""
    code, out, err = _run(
        _shell(globals()[command_name]),
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path))},
    )
    assert code == 0, err
    assert "MERGE_PENDING" in out


def test_rest_merge_commit_of_a_stack_parent_stays_allowed(tmp_path: Path) -> None:
    """--merge's REST spelling keeps the head's commits, so the child survives."""
    code, out, err = _run(
        _shell(REST_MERGE_COMMIT),
        env=_granted(tmp_path, STACKED),
    )
    assert code == 0, err
    assert out.strip() == ""


def test_rest_squash_of_a_leaf_is_allowed(tmp_path: Path) -> None:
    """No false positive: the REST path must not block a safe leaf merge."""
    code, out, err = _run(
        _shell(REST_SQUASH),
        env=_granted(tmp_path, {"Quantum-L9/SEO-Bot#53": {"head": "fix/leaf", "children": []}}),
    )
    assert code == 0, err
    assert out.strip() == ""


@pytest.mark.parametrize(
    "command",
    [
        "gh api repos/Quantum-L9/SEO-Bot/pulls/53/merge",
        "gh api -X GET repos/Quantum-L9/SEO-Bot/pulls/53/merge",
        "gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/reviews",
    ],
)
def test_rest_non_merges_are_not_treated_as_merges(tmp_path: Path, command: str) -> None:
    """GET on the merge path only asks whether the PR is merged, and PUT
    elsewhere is not a merge at all. Neither may be blocked."""
    code, out, err = _run(
        _shell(command),
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED))},
    )
    assert code == 0, err
    assert out.strip() == "", command


# --- §6.2.12: self-issuance, the helper's --run, and alternate transports ------
#
# Literals naming the scripts are assembled from parts so this file's bytes do
# not trip the PreToolUse shell matcher that fronts the gate.

AUTHORIZE = "ops/autonomy/" + "authorize_merge.py"
STACK_SAFE = "ops/autonomy/" + "stack_safe_merge.py"
GRANT_FILE = "~/.l9/autonomy/" + "merge-authorization.json"
INSTRUCTION_FILE = "operator-merge-" + "instructions.json"


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {AUTHORIZE} --repo Quantum-L9/SEO-Bot --all-open",
        f"python3 {AUTHORIZE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA}",
        f'"$GOV_PY" {AUTHORIZE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA}',
        f"cd /x && .venv/bin/python {AUTHORIZE} --repo o/r --pr 1",
        '"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/'
        + AUTHORIZE
        + '" --repo o/r --pr 1',
        "python -m ops.autonomy.authorize_merge --repo o/r --pr 1",
        f"bash -c 'python3 {AUTHORIZE} --repo o/r --pr 1'",
        f"echo '{{}}' > {GRANT_FILE}",
        f"cat grant.json | tee {GRANT_FILE}",
        f"cp /tmp/forged.json {GRANT_FILE}",
        f"python3 - <<'PY'\nopen('{GRANT_FILE}','w').write('x')\nPY",
    ],
)
def test_agent_self_issued_authorization_is_denied(command: str) -> None:
    code, out, err = _run(_shell(command))
    assert code == 0, err
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "never by an agent" in reason, command


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
@pytest.mark.parametrize("name", ["merge-authorization.json", INSTRUCTION_FILE])
def test_file_tool_write_to_grant_or_instruction_file_is_denied(tool: str, name: str) -> None:
    code, out, err = _run(
        {
            "tool_name": tool,
            "tool_input": {"file_path": f"/root/.l9/autonomy/{name}"},
        }
    )
    assert code == 0, err
    assert "never by an agent" in out


# --- §6.2.13 operator-prompt channel: the one authorize_merge.py run an agent may make


def _instruction_env(
    tmp_path: Path, repo: str = "Quantum-L9/SEO-Bot", pr: int = 53
) -> tuple[dict, dict]:
    """A receipt as the Claude prompt hook writes it (hook env) and the live
    PreToolUse session binding Claude Code puts on the event."""
    return _hosted_env(tmp_path, f"Fix and merge {repo}#{pr} after the checks pass.")


OPERATOR_RUN = (
    f'"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/{AUTHORIZE}" '
    f"--operator-instruction --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA}"
)


def test_operator_instruction_run_is_allowed_when_a_receipt_covers_the_target(
    tmp_path: Path,
) -> None:
    env, event = _instruction_env(tmp_path)
    code, out, err = _run(_bound(OPERATOR_RUN, event), env=env)
    assert code == 0, err
    assert out.strip() == ""


def test_operator_instruction_run_is_allowed_through_a_wrapper(tmp_path: Path) -> None:
    env, event = _instruction_env(tmp_path)
    code, out, err = _run(_bound(f"bash -c '{OPERATOR_RUN}'", event), env=env)
    assert code == 0, err
    assert out.strip() == ""


@pytest.mark.parametrize(
    "env_target",
    [
        None,  # no receipt at all
        ("Quantum-L9/Other", 53),  # receipt for another repository
        ("Quantum-L9/SEO-Bot", 54),  # receipt for another pull request
    ],
)
def test_operator_instruction_run_without_a_covering_receipt_is_denied(
    tmp_path: Path, env_target: tuple[str, int] | None
) -> None:
    env, event = _instruction_env(tmp_path, *env_target) if env_target else ({}, {})
    code, out, err = _run(_bound(OPERATOR_RUN, event), env=env)
    assert code == 0, err
    assert "never by an agent" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_terminal_mode_run_stays_denied_even_with_a_receipt(tmp_path: Path) -> None:
    """The receipt licenses one mode. The terminal ceremony is still not the agent's."""
    env, event = _instruction_env(tmp_path)
    command = OPERATOR_RUN.replace("--operator-instruction ", "")
    code, out, err = _run(_bound(command, event), env=env)
    assert code == 0, err
    assert "never by an agent" in out


def test_cohort_receipt_licenses_the_attempt_for_its_snapshot_members_only(tmp_path: Path) -> None:
    """A cohort receipt covers the pull requests open when it was spoken (F04),
    in that repository only; a Cursor cohort receipt is BLOCKED_HOST_ORIGIN."""
    import operator_merge_instruction as omi

    env, event = _hosted_env(
        tmp_path,
        "Remediate and merge all currently open PRs in Quantum-L9/SEO-Bot.",
        open_pull_requests=lambda repo: [52, 53],
    )
    code, out, err = _run(_bound(OPERATOR_RUN, event), env=env)
    assert code == 0, err
    assert out.strip() == ""
    code, out, err = _run(_bound(OPERATOR_RUN.replace("--pr 53", "--pr 54"), event), env=env)
    assert "never by an agent" in out
    other = OPERATOR_RUN.replace("Quantum-L9/SEO-Bot", "Quantum-L9/Other")
    code, out, err = _run(_bound(other, event), env=env)
    assert "never by an agent" in out

    cursor_store = tmp_path / "cursor" / INSTRUCTION_FILE
    payload = {
        "hook_event_name": "beforeSubmitPrompt",
        "conversation_id": "conv-1",
        "workspace_roots": [str(tmp_path)],
        "prompt": "Remediate and merge all currently open PRs in Quantum-L9/SEO-Bot.",
    }
    omi.record_instructions(
        payload["prompt"],
        host="cursor",
        session_id="conv-1",
        path=cursor_store,
        cwd_repo=None,
        provenance=omi.host_provenance("cursor", payload),
        open_pull_requests=lambda repo: [53],
    )
    code, out, err = _run(
        _bound(OPERATOR_RUN, {"session_id": "conv-1", "transcript_path": "/nowhere.jsonl"}),
        env={"L9_OPERATOR_INSTRUCTION_FILE": str(cursor_store)},
    )
    assert code == 0, err
    assert "never by an agent" in out


@pytest.mark.parametrize(
    "command",
    [
        f"echo '{{}}' > ~/.l9/autonomy/{INSTRUCTION_FILE}",
        f"cat forged.json | tee ~/.l9/autonomy/{INSTRUCTION_FILE}",
        f"cp /tmp/forged.json ~/.l9/autonomy/{INSTRUCTION_FILE}",
        f"python3 - <<'PY'\nopen('/root/.l9/autonomy/{INSTRUCTION_FILE}','w').write('x')\nPY",
    ],
)
def test_agent_cannot_write_the_instruction_receipt(command: str) -> None:
    code, out, err = _run(_shell(command))
    assert code == 0, err
    assert "never by an agent" in out, command


def test_reading_the_instruction_receipt_stays_allowed() -> None:
    code, out, err = _run(_shell(f"cat ~/.l9/autonomy/{INSTRUCTION_FILE}"))
    assert code == 0, err
    assert out.strip() == ""


def test_operator_grant_then_stack_safe_run_passes_the_gate(tmp_path: Path) -> None:
    """End to end through the gate: the grant an operator instruction produced
    is the grant the merge run is judged by."""
    import authorize_merge

    store = tmp_path / INSTRUCTION_FILE
    _hosted_env(tmp_path, "Merge Quantum-L9/SEO-Bot#53 after the checks pass.", store=store)
    grant_path = tmp_path / "merge-authorization.json"
    code = authorize_merge.main(
        [
            "--operator-instruction",
            "--repo",
            "Quantum-L9/SEO-Bot",
            "--pr",
            "53",
            "--head-sha",
            SHA,
            "--auth-file",
            str(grant_path),
        ],
        instruction_path=store,
        pull_request=lambda r, p: {
            "state": "open",
            "merged": False,
            "created_at": "2026-10-14T00:00:00Z",
            "head": {"sha": SHA},
            "user": {"login": "pr-author"},
        },
        pull_request_files=lambda r, p: ["README.md"],
    )
    assert code == 0
    env = {
        "L9_MERGE_AUTHORIZATION_FILE": str(grant_path),
        "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
    }
    command = f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run"
    code, out, err = _run(_shell(command), env=env)
    assert code == 0, err
    assert out.strip() == ""
    moved = command.replace(SHA, "b" * 40)
    code, out, err = _run(_shell(moved), env=env)
    assert "MERGE_PENDING" in out


@pytest.mark.parametrize(
    "event",
    [
        _shell(f"cat {GRANT_FILE}"),
        _shell(f"jq . {GRANT_FILE}"),
        _shell(f"git diff -- {AUTHORIZE}"),
        _shell(f"grep -n head_sha {AUTHORIZE}"),
        _shell(f"python3 {STACK_SAFE} --repo o/r --pr 53 --json"),
        _shell(f"python3 {STACK_SAFE} --repo o/r --pr 53 --print"),
        {"tool_name": "Write", "tool_input": {"file_path": "/repo/ops/autonomy/merge_gate.py"}},
    ],
)
def test_reading_and_planning_stay_allowed(event: dict) -> None:
    code, out, err = _run(event)
    assert code == 0, err
    assert out.strip() == ""


def test_stack_safe_run_without_grant_is_merge_pending(tmp_path: Path) -> None:
    """Its gh calls are subprocesses no hook sees, so --run itself needs the grant."""
    for command in (
        f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --run",
        f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run",
    ):
        code, out, err = _run(_shell(command))
        assert code == 0, err
        assert "MERGE_PENDING" in out, command


def test_stack_safe_run_with_grant_for_other_head_is_denied(tmp_path: Path) -> None:
    command = f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {'b' * 40} --run"
    code, out, err = _run(_shell(command), env=_granted(tmp_path))
    assert code == 0, err
    assert "MERGE_PENDING" in out


def test_stack_safe_run_with_matching_grant_is_allowed(tmp_path: Path) -> None:
    command = f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run"
    code, out, err = _run(_shell(command), env=_granted(tmp_path))
    assert code == 0, err
    assert out.strip() == ""


@pytest.mark.parametrize(
    "event",
    [
        _shell(f"{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --auto --merge"),
        _shell("gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/ccr/auto_merge"),
        {"tool_name": "mcp__github__enable_pr_auto_merge", "tool_input": {"pullNumber": 53}},
    ],
)
def test_auto_merge_enablement_is_denied_even_with_a_grant(tmp_path: Path, event: dict) -> None:
    code, out, err = _run(event, env=_granted(tmp_path))
    assert code == 0, err
    assert "auto-merge" in out


def test_auto_merge_allowed_under_human_breakglass() -> None:
    code, out, err = _run(
        {"tool_name": "mcp__github__enable_pr_auto_merge", "tool_input": {"pullNumber": 53}},
        env={"L9_MERGE_AUTHORIZED": "human enabled auto-merge for #53"},
    )
    assert code == 0, err
    assert out.strip() == ""


def test_plugin_namespaced_mcp_merge_tool_is_governed(tmp_path: Path) -> None:
    """Another GitHub MCP server's merge tool is the same effect."""
    event = {
        "tool_name": "mcp__plugin_engineering_github__merge_pull_request",
        "tool_input": {"owner": "Quantum-L9", "repo": "SEO-Bot", "pullNumber": 53},
    }
    code, out, err = _run(event)
    assert "MERGE_PENDING" in out, err
    event["tool_input"].update(merge_method="merge", sha=SHA)
    code, out, err = _run(event, env=_granted(tmp_path))
    assert code == 0, err
    assert out.strip() == ""


@pytest.mark.parametrize(
    "command",
    [
        f".venv/bin/python -m ruff check {AUTHORIZE} {STACK_SAFE}",
        f"python3 -m pytest -q tests/ops/autonomy/test_authorize_merge.py  # {AUTHORIZE}",
        f"sed -n 1,20p {AUTHORIZE}",
    ],
)
def test_tools_that_only_name_the_scripts_are_not_invocations(command: str) -> None:
    code, out, err = _run(_shell(command))
    assert code == 0, err
    assert out.strip() == ""


# --- Binding is per executed merge segment (PR #712 review) --------------------
#
# A grant, head SHA or PR number appearing elsewhere in the command line must
# not vouch for a merge segment that does not itself carry them.


@pytest.mark.parametrize(
    "command",
    [
        # decoy head binding in a sibling segment; the merge itself is unbound
        f"echo --match-head-commit {SHA}; {CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --merge",
        f"echo -f sha={SHA} && gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/merge "
        "-f merge_method=merge",
        # decoy PR number: the granted #53 is only mentioned; #54 is merged
        f"echo '{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot'; {CLI_MERGE} 54 "
        f"--repo Quantum-L9/SEO-Bot --merge --match-head-commit {SHA}",
        # first merge granted, second merge rides along unauthorized
        f"{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --merge --match-head-commit {SHA} && "
        f"{CLI_MERGE} 54 --repo Quantum-L9/SEO-Bot --merge --match-head-commit {SHA}",
        # a merge reachable only through text the parser cannot bind
        f"eval '{CLI_MERGE} 53 --repo Quantum-L9/SEO-Bot --merge --match-head-commit {SHA}'",
    ],
)
def test_grant_binds_only_the_executed_merge_segment(tmp_path: Path, command: str) -> None:
    code, out, err = _run(_shell(command), env=_granted(tmp_path))
    assert code == 0, err
    assert "MERGE_PENDING" in out, command


def test_head_bound_merge_beside_unrelated_commands_is_allowed(tmp_path: Path) -> None:
    command = (
        f"git fetch origin && {CLI_MERGE} 53 -R Quantum-L9/SEO-Bot --merge "
        f"--match-head-commit {SHA}"
    )
    code, out, err = _run(_shell(command), env=_granted(tmp_path))
    assert code == 0, err
    assert out.strip() == ""


def test_curl_json_sha_binds_the_rest_merge(tmp_path: Path) -> None:
    command = (
        "curl -X PUT https://api.github.com/repos/Quantum-L9/SEO-Bot/pulls/53/merge "
        f'-d \'{{"merge_method":"merge","sha":"{SHA}"}}\''
    )
    code, out, err = _run(_shell(command), env=_granted(tmp_path))
    assert code == 0, err
    assert out.strip() == ""


def test_second_stack_safe_run_in_one_command_needs_its_own_grant(tmp_path: Path) -> None:
    command = (
        f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run; "
        f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 54 --head-sha {SHA} --run"
    )
    code, out, err = _run(_shell(command), env=_granted(tmp_path))
    assert code == 0, err
    assert "MERGE_PENDING" in out


# --- CG-712-01: every copy-ready grant / merge instruction runs from any cwd ---
#
# A human (or a remediation lane) may sit in a consumer repository, where a
# relative ops/autonomy/... path or $PWD/.venv does not exist. Every instruction
# that names either script with arguments must therefore use the locked
# governance interpreter and the absolute script path.

ABS_PREFIX = '"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/'
INSTRUCTION_SURFACES = (
    "ops/autonomy/surface_profile.yaml",
    "rules/48-make-pr-remediation.mdc",
    "environment/generated/llm-rules/48-make-pr-remediation.md",
    "environment/generated/llm-rules/zz-autonomy-surface-override.md",
    "skills/l9-pr-remediation/SKILL.md",
    "skills/l9-pr-remediation/references/merge-advise.md",
    "skills/l9-pr-remediation/references/run-contract.md",
    "skills/l9-pr-remediation/references/fleet-waves.md",
    "skills/l9-pr-remediation/references/convergence-loop.md",
)
_COMMAND = re.compile(r'(\S*?)((?:authorize|stack_safe)_merge\.py)("?)\s+--repo\b')


def _relative_commands(text: str) -> list[str]:
    bad = []
    for match in _COMMAND.finditer(text):
        start = text.rfind("\n", 0, match.start()) + 1
        line_prefix = text[start : match.start(2)]
        if not (line_prefix.endswith(ABS_PREFIX) and match.group(3) == '"'):
            bad.append(text[start : match.end()].strip())
    return bad


@pytest.mark.parametrize("rel", INSTRUCTION_SURFACES)
def test_documented_merge_commands_are_cwd_independent(rel: str) -> None:
    assert _relative_commands((REPO / rel).read_text(encoding="utf-8")) == []


def test_emitted_merge_commands_are_cwd_independent() -> None:
    import merge_gate as mg
    import pr_fleet

    assert mg.GRANT_COMMAND == ABS_PREFIX + 'authorize_merge.py"'
    assert mg.MERGE_COMMAND == ABS_PREFIX + 'stack_safe_merge.py"'
    assert pr_fleet.MERGE_COMMAND is mg.MERGE_COMMAND  # one owner, no copy
    assert _relative_commands(mg.MERGE_DENY_REASON) == []
    assert mg.MERGE_COMMAND in mg.MERGE_DENY_REASON
    assert "authorize merge <owner>/<repo>#<n>@<40-hex>" in mg.MERGE_DENY_REASON
    # The grant command appears only as the operator-prompt transcription,
    # never as a terminal ceremony the human is told to perform.
    assert f"{mg.GRANT_COMMAND} --operator-instruction" in mg.MERGE_DENY_REASON
    assert "terminal transcription is not merge permission" in mg.MERGE_DENY_REASON


def test_relative_command_detector_catches_the_old_forms() -> None:
    """The scan would have failed on PR #712 at 705acd8."""
    for old in (
        "then ops/autonomy/stack_safe_merge.py --repo o/r --pr 1",
        '"$GOV_PY" ops/autonomy/stack_safe_merge.py --repo o/r --pr 1 --run',
        "authorize_merge.py --repo <owner/name> --pr <n>",
        '"$HOME/.cursor-governance/.venv/bin/python" ops/autonomy/authorize_merge.py --repo o/r',
    ):
        assert _relative_commands(old), old


@pytest.mark.parametrize("granted", [False, True])
def test_absolute_stack_safe_run_is_governed(tmp_path: Path, granted: bool) -> None:
    """The cwd-independent spelling the docs now prescribe is still recognised."""
    command = (
        f'{ABS_PREFIX}stack_safe_merge.py" --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run'
    )
    code, out, err = _run(_shell(command), env=_granted(tmp_path) if granted else None)
    assert code == 0, err
    assert (out.strip() == "") is granted, out


# --- GAR-MERGE-AUTHORITY-735 findings (F01, F03): the gate binds receipts to the
# live host session and honours revocation --------------------------------------

RECORDER = "ops/autonomy/" + "operator_merge_instruction.py"
CLAUDE_WRAP = (
    "environment/agents/adapters/claude-code/hooks/" + "operator_merge_instruction_wrap.py"
)
CURSOR_HOOK = "ops/hooks/" + "before_submit_merge_instruction.py"
SESSION = "sess-human-1"


def _host_transcript(
    path: Path, text: str, *, origin: str = "human", session: str = SESSION
) -> Path:
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


def _hosted_env(
    tmp_path: Path,
    prompt: str = "Fix and merge Quantum-L9/SEO-Bot#53 after the checks pass.",
    *,
    now: float | None = None,
    transcript_text: str | None = None,
    session: str = SESSION,
    store: Path | None = None,
    open_pull_requests=None,
) -> tuple[dict[str, str], dict[str, str]]:
    """(hook env, event fields) for a receipt the Claude UserPromptSubmit wrapper wrote."""
    import time

    import operator_merge_instruction as omi

    store = store or tmp_path / INSTRUCTION_FILE
    stamp = int(now if now is not None else time.time())
    transcript = _host_transcript(
        tmp_path / f"transcript-{session}.jsonl", transcript_text or prompt, session=session
    )
    payload = {
        "session_id": session,
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }
    omi.record_instructions(
        prompt,
        host="claude-code",
        session_id=session,
        cwd=str(tmp_path),
        path=store,
        now=stamp,
        cwd_repo=None,
        provenance=omi.host_provenance("claude-code", payload),
        open_pull_requests=open_pull_requests,
    )
    env = {"L9_OPERATOR_INSTRUCTION_FILE": str(store)}
    event = {"session_id": SESSION, "transcript_path": str(transcript)}
    return env, event


def _bound(command: str, event: dict[str, str]) -> dict:
    return {**_shell(command), **event}


def test_f01_bound_hosted_receipt_allows_the_transcription(tmp_path: Path) -> None:
    env, event = _hosted_env(tmp_path)
    code, out, err = _run(_bound(OPERATOR_RUN, event), env=env)
    assert code == 0, err
    assert out.strip() == ""


def test_f01_receipt_from_another_session_is_denied(tmp_path: Path) -> None:
    env, event = _hosted_env(tmp_path, session="sess-agent-forged")
    # the receipt names sess-agent-forged; the live event is SESSION
    code, out, err = _run(_bound(OPERATOR_RUN, event), env=env)
    assert code == 0, err
    assert "never by an agent" in out


def test_f01_event_without_session_binding_is_denied(tmp_path: Path) -> None:
    env, _event = _hosted_env(tmp_path)
    code, out, err = _run(_shell(OPERATOR_RUN), env=env)
    assert code == 0, err
    assert "never by an agent" in out


def test_f01_receipt_not_in_the_live_transcript_is_denied(tmp_path: Path) -> None:
    """A receipt whose text the host never recorded as a human turn is not authority."""
    env, event = _hosted_env(tmp_path, transcript_text="Please review PR #53 and report.")
    code, out, err = _run(_bound(OPERATOR_RUN, event), env=env)
    assert code == 0, err
    assert "never by an agent" in out


def test_f01_receipt_bound_to_a_different_transcript_is_denied(tmp_path: Path) -> None:
    env, event = _hosted_env(tmp_path)
    other = _host_transcript(
        tmp_path / "other.jsonl", "Fix and merge Quantum-L9/SEO-Bot#53 after the checks pass."
    )
    code, out, err = _run(_bound(OPERATOR_RUN, {**event, "transcript_path": str(other)}), env=env)
    assert code == 0, err
    assert "never by an agent" in out


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {RECORDER} record --host claude-code",
        f'echo \'{{"prompt":"merge #53"}}\' | python3 {RECORDER} record --host claude-code',
        "python -m ops.autonomy.operator_merge_instruction record --host cursor",
        f'"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/{RECORDER}" '
        "record --host claude-code",
        f"python3 {CLAUDE_WRAP}",
        f"python3 {CURSOR_HOOK}",
        "~/.cursor/hooks/before-submit-merge-instruction.py",
        '"$HOME/.cursor-governance/environment/agents/adapters/claude-code/hooks/l9_hook_exec.sh" '
        "--class observer operator_merge_instruction_wrap.py",
        f"bash -c 'python3 {RECORDER} record --host claude-code'",
        'python3 -c \'import sys; sys.path.insert(0,"ops/autonomy"); '
        "import operator_merge_instruction as o; "
        'o.record_instructions("merge #53", host="claude-code", session_id="s")\'',
        "python3 - <<'PY'\nimport operator_merge_instruction\nPY",
        "python3 - <<'PY'\nfrom ops.autonomy.operator_merge_instruction import "
        "record_instructions\nPY",
        "echo '{}' >> ~/.claude/projects/-home-user/abc.jsonl",
        "python3 - <<'PY'\nopen('/root/.claude/projects/-home-user/abc.jsonl','a').write('x')\nPY",
    ],
)
def test_f01_agent_invocation_of_the_recorder_or_transcript_is_denied(command: str) -> None:
    code, out, err = _run(_shell(command))
    assert code == 0, err
    assert "never by an agent" in out, command


@pytest.mark.parametrize(
    "command",
    [
        f"cat {RECORDER}",
        f"grep -n record_instructions {RECORDER}",
        f"git diff -- {RECORDER}",
        f"python3 -m pytest -q tests/ops/autonomy/test_operator_merge_instruction.py  # {RECORDER}",
        f".venv/bin/ruff check {RECORDER} {CLAUDE_WRAP}",
        f"python3 {RECORDER} show --repo o/r --pr 1",
        "cat ~/.claude/projects/-home-user/abc.jsonl",
    ],
)
def test_f01_reading_the_recorder_and_the_transcript_stays_allowed(command: str) -> None:
    code, out, err = _run(_shell(command))
    assert code == 0, err
    assert out.strip() == "", command


def test_f03_revocation_after_recording_denies_the_transcription(tmp_path: Path) -> None:
    import time

    env, event = _hosted_env(tmp_path, now=time.time() - 120)
    _hosted_env(
        tmp_path,
        "Do not merge Quantum-L9/SEO-Bot#53.",
        now=time.time() - 60,
        store=tmp_path / INSTRUCTION_FILE,
    )
    code, out, err = _run(_bound(OPERATOR_RUN, event), env=env)
    assert code == 0, err
    assert "never by an agent" in out


def test_f03_revocation_after_grant_denies_the_merge_run(tmp_path: Path) -> None:
    """Authorize, issue the grant, then cancel: the grant no longer carries."""
    import time

    env, event = _hosted_env(tmp_path, now=time.time() - 300)
    grant_env = _granted(tmp_path)  # a live grant for #53 at SHA (legacy shape, no issued_at)
    _hosted_env(
        tmp_path,
        "Cancel the merge of Quantum-L9/SEO-Bot#53.",
        now=time.time() - 1,  # after the authorization; a grant without issued_at is older
        store=tmp_path / INSTRUCTION_FILE,
    )
    command = f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run"
    code, out, err = _run(_bound(command, event), env={**grant_env, **env})
    assert code == 0, err
    assert "MERGE_PENDING" in out and "revoked" in out


def test_f03_revocation_scoped_to_another_pr_leaves_the_grant_alone(tmp_path: Path) -> None:
    import time

    env, event = _hosted_env(tmp_path, now=time.time() - 300)
    grant_env = _granted(tmp_path)
    _hosted_env(
        tmp_path,
        "Cancel the merge of Quantum-L9/SEO-Bot#54.",
        now=time.time() - 1,
        store=tmp_path / INSTRUCTION_FILE,
    )
    command = f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run"
    code, out, err = _run(_bound(command, event), env={**grant_env, **env})
    assert code == 0, err
    assert out.strip() == ""


def test_f03_revocation_also_withdraws_a_github_record(tmp_path: Path) -> None:
    import time

    review = tmp_path / "reviews.json"
    review.write_text(
        json.dumps(
            {
                "Quantum-L9/SEO-Bot#53": {
                    "author": "pr-author",
                    "files": ["README.md"],
                    "reviews": [
                        {
                            "user": {"login": "operator", "type": "User"},
                            "state": "APPROVED",
                            "commit_id": SHA,
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
    env, event = _hosted_env(tmp_path, "Do not merge Quantum-L9/SEO-Bot#53.", now=time.time() - 30)
    env["L9_MERGE_REVIEW_FILE"] = str(review)
    env["L9_STACK_PROBE_FILE"] = str(_probe_file(tmp_path))
    command = f"python3 {STACK_SAFE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA} --run"
    code, out, err = _run(_bound(command, event), env=env)
    assert code == 0, err
    assert "MERGE_PENDING" in out and "revoked" in out
