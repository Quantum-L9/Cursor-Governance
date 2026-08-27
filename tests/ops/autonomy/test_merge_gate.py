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
    head_sha: str | None = None,
    no_expiry: bool = False,
    extra: str = "",
) -> Path:
    import time

    entry: dict = {"repo": repo, "pr": pr}
    if not no_expiry:
        entry["expires_at"] = expires_at or (time.time() + 3600)
    if head_sha is not None:
        entry["head_sha"] = head_sha
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


def test_unbound_receipt_ignores_named_head(tmp_path: Path) -> None:
    """A receipt with no head_sha stays repo/PR-scoped even when a head is named."""
    auth = _auth_file(tmp_path)
    code, out, err = _run(
        _mcp(repo="Quantum-L9/SEO-Bot", pull_number=53, merge_method="squash", sha="c" * 40),
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(auth),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path)),
        },
    )
    assert code == 0, err
    assert out.strip() == ""


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
        _mcp(owner="Quantum-L9", repo="SEO-Bot", pullNumber=53, merge_method="squash"),
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
        _mcp(owner="Quantum-L9", repo="SEO-Bot", pullNumber=53, merge_method="squash"),
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
        _mcp(owner="Quantum-L9", repo="SEO-Bot", pullNumber=53, merge_method="squash"),
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

REST_SQUASH = "gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/merge -f merge_method=squash"
REST_MERGE_COMMIT = "gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/merge -f merge_method=merge"
REST_UNSPECIFIED = "gh api -X PUT repos/Quantum-L9/SEO-Bot/pulls/53/merge"
CURL_SQUASH = (
    "curl -X PUT https://api.github.com/repos/Quantum-L9/SEO-Bot/pulls/53/merge "
    "-f merge_method=squash"
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
    code, out, err = _run(
        _shell(command),
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED))},
    )
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
        env={
            "L9_MERGE_AUTHORIZATION_FILE": str(_auth_file(tmp_path, pr="*")),
            "L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED)),
        },
    )
    assert code == 0, err
    assert "deny" in out
    assert "#54" in out


def test_rest_merge_commit_of_a_stack_parent_stays_allowed(tmp_path: Path) -> None:
    """--merge's REST spelling keeps the head's commits, so the child survives."""
    code, out, err = _run(
        _shell(REST_MERGE_COMMIT),
        env={"L9_STACK_PROBE_FILE": str(_probe_file(tmp_path, STACKED))},
    )
    assert code == 0, err
    assert out.strip() == ""


def test_rest_squash_of_a_leaf_is_allowed(tmp_path: Path) -> None:
    """No false positive: the REST path must not block a safe leaf merge."""
    code, out, err = _run(
        _shell(REST_SQUASH),
        env={
            "L9_STACK_PROBE_FILE": str(
                _probe_file(
                    tmp_path,
                    {"Quantum-L9/SEO-Bot#53": {"head": "fix/leaf", "children": []}},
                )
            )
        },
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
