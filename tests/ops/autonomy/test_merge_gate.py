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


@pytest.mark.parametrize(
    "command",
    [
        f"python3 {AUTHORIZE} --repo Quantum-L9/SEO-Bot --all-open",
        f"python3 {AUTHORIZE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA}",
        f'"$GOV_PY" {AUTHORIZE} --repo Quantum-L9/SEO-Bot --pr 53 --head-sha {SHA}',
        f"cd /x && .venv/bin/python {AUTHORIZE} --repo o/r --pr 1",
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
def test_file_tool_write_to_grant_file_is_denied(tool: str) -> None:
    code, out, err = _run(
        {
            "tool_name": tool,
            "tool_input": {"file_path": "/root/.l9/autonomy/merge-authorization.json"},
        }
    )
    assert code == 0, err
    assert "never by an agent" in out


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
