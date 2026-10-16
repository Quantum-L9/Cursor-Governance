"""GitHub merge authorization (CANONICAL_LAW §6.2.13).

The ordinary record is an identity-backed GitHub review or the exact
authorization line, bound to the current head. A local fixture authorizes the
hook under test only. It does not authorize stack_safe_merge.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import github_merge_authorization as authz  # noqa: E402

SHA = "a" * 40
OLD = "b" * 40
SLUG = "Quantum-L9/SEO-Bot"
GATE = REPO / "ops" / "autonomy" / "merge_gate.py"
STACK = "ops/autonomy/" + "stack_safe_merge.py"


def _user(login: str, kind: str = "User") -> dict:
    return {"login": login, "type": kind}


def _review(
    login: str,
    state: str,
    commit: str,
    *,
    body: str = "",
    association: str = "OWNER",
    submitted_at: str = "2026-10-14T00:00:00Z",
    kind: str = "User",
    permission: str = "write",
) -> dict:
    return {
        "user": _user(login, kind),
        "state": state,
        "commit_id": commit,
        "body": body,
        "author_association": association,
        "permission": permission,
        "submitted_at": submitted_at,
    }


def _evidence(**overrides) -> dict:
    payload = {
        "author": "pr-author",
        "files": ["README.md"],
        "reviews": [],
        "comments": [],
    }
    payload.update(overrides)
    return payload


def _verdict(**overrides) -> dict:
    return authz.evaluate_evidence(SLUG, 53, SHA, _evidence(**overrides))


def test_approved_human_review_on_the_head_authorizes() -> None:
    verdict = _verdict(reviews=[_review("operator", "APPROVED", SHA)])
    assert verdict["authorized"] is True
    assert verdict["channel"] == "approved_review"
    assert verdict["authorizer"] == "operator"


def test_absent_authorization_is_denied() -> None:
    verdict = _verdict()
    assert verdict["authorized"] is False
    assert "no human GitHub merge authorization" in verdict["reason"]


def test_approval_of_an_older_head_is_denied() -> None:
    verdict = _verdict(reviews=[_review("operator", "APPROVED", OLD)])
    assert verdict["authorized"] is False
    assert verdict["reason"] == "head changed after authorization"


def test_bot_approval_is_not_human_authorization() -> None:
    verdict = _verdict(
        reviews=[_review("copilot-pull-request-reviewer", "APPROVED", SHA, kind="Bot")]
    )
    assert verdict["authorized"] is False


def test_member_association_without_repository_permission_is_denied() -> None:
    review = _review("operator", "APPROVED", SHA, association="MEMBER")
    review.pop("permission")
    verdict = _verdict(reviews=[review])
    assert verdict["authorized"] is False
    assert "no human GitHub merge authorization" in verdict["reason"]


def test_write_permission_authorizes_when_association_is_none() -> None:
    verdict = _verdict(
        reviews=[_review("operator", "APPROVED", SHA, association="NONE", permission="write")]
    )
    assert verdict["authorized"] is True
    assert verdict["authorizer"] == "operator"


def test_read_permission_does_not_authorize() -> None:
    verdict = _verdict(
        reviews=[_review("operator", "APPROVED", SHA, association="MEMBER", permission="read")]
    )
    assert verdict["authorized"] is False


def test_drive_by_comment_without_write_access_is_denied() -> None:
    verdict = _verdict(
        comments=[
            {
                "user": _user("stranger"),
                "author_association": "NONE",
                "body": authz.authorization_line(SLUG, 53, SHA),
            }
        ]
    )
    assert verdict["authorized"] is False


def test_authorization_line_on_the_current_head_authorizes() -> None:
    verdict = _verdict(
        comments=[
            {
                "user": _user("operator"),
                "author_association": "MEMBER",
                "permission": "write",
                "body": "ship it\n" + authz.authorization_line(SLUG, 53, SHA) + "\n",
            }
        ]
    )
    assert verdict["authorized"] is True
    assert verdict["channel"] == "authorization_line"


def test_authorization_line_for_a_different_head_is_denied() -> None:
    verdict = _verdict(
        comments=[
            {
                "user": _user("operator"),
                "author_association": "OWNER",
                "body": authz.authorization_line(SLUG, 53, OLD),
            }
        ]
    )
    assert verdict["authorized"] is False


def test_later_changes_requested_revokes_an_approval() -> None:
    verdict = _verdict(
        reviews=[
            _review("operator", "APPROVED", SHA, submitted_at="2026-10-14T00:00:00Z"),
            _review("operator", "CHANGES_REQUESTED", SHA, submitted_at="2026-10-14T01:00:00Z"),
        ]
    )
    assert verdict["authorized"] is False


def test_later_comment_does_not_revoke_an_approval() -> None:
    verdict = _verdict(
        reviews=[
            _review("operator", "APPROVED", SHA, submitted_at="2026-10-14T00:00:00Z"),
            _review("operator", "COMMENTED", SHA, submitted_at="2026-10-14T01:00:00Z"),
        ]
    )
    assert verdict["authorized"] is True


def test_author_may_authorize_an_ordinary_change() -> None:
    verdict = _verdict(
        author="pr-author",
        files=["README.md"],
        reviews=[_review("pr-author", "APPROVED", SHA)],
    )
    assert verdict["authorized"] is True


def test_authorized_owner_may_authorize_their_own_protected_change() -> None:
    """L9-ORG-007 as amended by CANONICAL_LAW §6.2.14: an authorized repository
    owner may authorize their own pull request, governance-protected paths
    included. The filename alone never demands a second human."""
    verdict = _verdict(
        author="pr-author",
        files=["CANONICAL_LAW.md", "pyproject.toml", ".github/workflows/publish.yml"],
        comments=[
            {
                "user": _user("pr-author"),
                "author_association": "OWNER",
                "permission": "admin",
                "body": authz.authorization_line(SLUG, 53, SHA),
            }
        ],
    )
    assert verdict["authorized"] is True
    assert verdict["authorizer"] == "pr-author"


def test_author_without_repository_authority_cannot_authorize() -> None:
    verdict = _verdict(
        author="pr-author",
        files=["CANONICAL_LAW.md"],
        comments=[
            {
                "user": _user("pr-author"),
                "author_association": "CONTRIBUTOR",
                "permission": "read",
                "body": authz.authorization_line(SLUG, 53, SHA),
            }
        ],
    )
    assert verdict["authorized"] is False


def test_a_different_human_can_authorize_an_org_007_path() -> None:
    verdict = _verdict(
        author="pr-author",
        files=["ops/config/root-file-protection.json"],
        reviews=[_review("governance-owner", "APPROVED", SHA)],
    )
    assert verdict["authorized"] is True
    assert verdict["authorizer"] == "governance-owner"


@pytest.mark.parametrize("author", ["", "pr-author", "somebody"])
def test_the_authors_identity_no_longer_changes_the_verdict(author: str) -> None:
    verdict = _verdict(author=author, files=None, reviews=[_review("somebody", "APPROVED", SHA)])
    assert verdict["authorized"] is True


def test_fetch_evidence_reads_no_file_list(monkeypatch) -> None:
    """The independence check was the file list's only consumer."""
    asked: list[str] = []

    def pages(path: str) -> list:
        asked.append(path)
        return [_review("pr-author", "APPROVED", SHA)] if "/reviews?" in path else []

    monkeypatch.setattr(authz, "_gh_json", lambda path: {"user": {"login": "pr-author"}})
    monkeypatch.setattr(authz, "_gh_pages", pages)
    evidence = authz.fetch_evidence(SLUG, 53)
    assert not any("/files" in path for path in asked)
    assert authz.evaluate_evidence(SLUG, 53, SHA, evidence)["authorized"] is True


@pytest.mark.parametrize(
    ("permissions", "role"),
    [
        ({"admin": True, "maintain": True, "push": True, "pull": True}, "admin"),
        ({"admin": False, "maintain": True, "push": True, "pull": True}, "maintain"),
        ({"admin": False, "maintain": False, "push": True, "pull": True}, "write"),
        ({"admin": False, "maintain": False, "push": False, "triage": True}, "triage"),
        ({"pull": True}, "read"),
        (None, ""),
    ],
)
def test_repository_role_reads_the_highest_rest_permission(permissions, role) -> None:
    assert authz._repository_role(permissions) == role


def test_session_principal_is_the_operator_and_their_role(monkeypatch) -> None:
    payloads = {
        "user": {"login": "cryptoxdog", "type": "User"},
        f"repos/{SLUG}": {"permissions": {"admin": True, "push": True, "pull": True}},
    }
    monkeypatch.setattr(authz, "_gh_json", lambda path: payloads[path])
    principal = authz.fetch_session_principal(SLUG)
    assert principal == {
        "login": "cryptoxdog",
        "type": "User",
        "permission": "admin",
        "human": True,
    }
    assert authz.principal_may_authorize(principal)


@pytest.mark.parametrize(
    "principal",
    [
        {"login": "reader", "type": "User", "permission": "read", "human": True},
        {"login": "ci[bot]", "type": "Bot", "permission": "admin", "human": False},
        {},
    ],
)
def test_principal_without_write_authority_may_not_authorize(principal: dict) -> None:
    assert not authz.principal_may_authorize(principal)


def test_review_fixture_does_not_authorize_the_merge_helper(tmp_path: Path, monkeypatch) -> None:
    fixture = tmp_path / "reviews.json"
    fixture.write_text(
        json.dumps(
            {
                f"{SLUG}#53": _evidence(reviews=[_review("operator", "APPROVED", SHA)]),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("L9_MERGE_REVIEW_FILE", str(fixture))
    monkeypatch.delenv("L9_STACK_PROBE_FILE", raising=False)
    monkeypatch.setattr(
        authz,
        "fetch_evidence",
        lambda repo, pr: _evidence(),
    )
    verdict = authz.authorize_for_merge(SLUG, 53, SHA)
    assert verdict["authorized"] is False


def _gate(event: dict, env: dict | None = None) -> tuple[int, str]:
    base = {**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"}
    base.pop("L9_MERGE_AUTHORIZED", None)
    base.pop("L9_MERGE_REVIEW_FILE", None)
    base.pop("L9_STACK_PROBE_FILE", None)
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env={**base, **(env or {})},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.returncode, proc.stdout


def _fixture(tmp_path: Path, evidence: dict) -> str:
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps({f"{SLUG}#53": evidence}), encoding="utf-8")
    return str(path)


def _probe(tmp_path: Path) -> str:
    path = tmp_path / "probe.json"
    path.write_text(
        json.dumps({f"{SLUG}#53": {"head": "fix/leaf", "children": [], "sha": SHA}}),
        encoding="utf-8",
    )
    return str(path)


def test_hook_allows_merge_when_the_review_fixture_matches(tmp_path: Path) -> None:
    command = f"python3 {STACK} --repo {SLUG} --pr 53 --head-sha {SHA} --run"
    code, out = _gate(
        {"tool_name": "Bash", "tool_input": {"command": command}},
        {
            "L9_MERGE_REVIEW_FILE": _fixture(
                tmp_path, _evidence(reviews=[_review("operator", "APPROVED", SHA)])
            ),
            "L9_STACK_PROBE_FILE": _probe(tmp_path),
        },
    )
    assert code == 0
    assert out.strip() == ""


def test_hook_denies_merge_without_authorization(tmp_path: Path) -> None:
    command = f"python3 {STACK} --repo {SLUG} --pr 53 --head-sha {SHA} --run"
    _code, out = _gate(
        {"tool_name": "Bash", "tool_input": {"command": command}},
        {"L9_STACK_PROBE_FILE": _probe(tmp_path)},
    )
    assert "MERGE_PENDING" in out
    assert "no human GitHub merge authorization" in out or "offline probe" in out


def test_hook_denies_when_the_approved_head_is_stale(tmp_path: Path) -> None:
    command = f"python3 {STACK} --repo {SLUG} --pr 53 --head-sha {SHA} --run"
    _code, out = _gate(
        {"tool_name": "Bash", "tool_input": {"command": command}},
        {
            "L9_MERGE_REVIEW_FILE": _fixture(
                tmp_path, _evidence(reviews=[_review("operator", "APPROVED", OLD)])
            )
        },
    )
    assert "head changed after authorization" in out


def test_hook_denies_admin_merge_even_with_github_authorization(tmp_path: Path) -> None:
    command = f"gh pr merge 53 --repo {SLUG} --merge --admin --match-head-commit {SHA}"
    _code, out = _gate(
        {"tool_name": "Bash", "tool_input": {"command": command}},
        {
            "L9_MERGE_REVIEW_FILE": _fixture(
                tmp_path, _evidence(reviews=[_review("operator", "APPROVED", SHA)])
            )
        },
    )
    assert "never waives" in out


def test_hook_denies_squash_of_a_parent_even_with_github_authorization(tmp_path: Path) -> None:
    probe = tmp_path / "probe.json"
    probe.write_text(
        json.dumps({f"{SLUG}#53": {"head": "fix/parent", "children": [54], "sha": SHA}}),
        encoding="utf-8",
    )
    command = f"gh pr merge 53 --repo {SLUG} --squash --match-head-commit {SHA}"
    _code, out = _gate(
        {"tool_name": "Bash", "tool_input": {"command": command}},
        {
            "L9_MERGE_REVIEW_FILE": _fixture(
                tmp_path, _evidence(reviews=[_review("operator", "APPROVED", SHA)])
            ),
            "L9_STACK_PROBE_FILE": str(probe),
        },
    )
    assert "Stack safety" in out
    assert "#54" in out


@pytest.mark.parametrize(
    "command",
    [
        f"gh pr review 53 --repo {SLUG} --approve",
        f"gh pr review 53 --repo {SLUG} -a",
        f"/usr/bin/gh pr review 53 --repo {SLUG} --approve",
        f"gh pr comment 53 --repo {SLUG} --body '{authz.authorization_line(SLUG, 53, SHA)}'",
        f"gh pr comment 53 --repo {SLUG} -b '{authz.authorization_line(SLUG, 53, SHA).upper()}'",
        f"gh issue comment 53 --repo {SLUG} --body '{authz.authorization_line(SLUG, 53, SHA)}'",
        "gh api --method POST repos/Quantum-L9/SEO-Bot/pulls/53/reviews -f event=APPROVE",
        "gh api graphql -f query='mutation{addPullRequestReview(input:"
        + '{pullRequestId:"x",event:APPROVE}){clientMutationId}}\'',
        "gh api graphql -f query='mutation{submitPullRequestReview(input:"
        + '{pullRequestReviewId:"x",event:APPROVE}){clientMutationId}}\'',
    ],
)
def test_hook_denies_an_agent_posting_the_authorization(command: str) -> None:
    _code, out = _gate({"tool_name": "Bash", "tool_input": {"command": command}})
    assert "never by an agent" in out


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        (
            "mcp__github__pull_request_review_write",
            {
                "method": "create",
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "pullNumber": 53,
                "event": "APPROVE",
            },
        ),
        (
            "mcp__github__pull_request_review_write",
            {
                "method": "submit_pending",
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "pullNumber": 53,
                "event": "approve",
            },
        ),
        (
            "mcp__github__add_issue_comment",
            {
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "issue_number": 53,
                "body": authz.authorization_line(SLUG, 53, SHA),
            },
        ),
        (
            "mcp__github__add_reply_to_pull_request_comment",
            {
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "pullNumber": 53,
                "commentId": 1,
                "body": f"ok\n{authz.authorization_line(SLUG, 53, SHA)}",
            },
        ),
        # Other GitHub MCP providers name the same acts differently: the review
        # verdict is ``action``, the comment text is ``comment``.
        (
            "mcp__GitHub__add_review_to_pr",
            {
                "repo_owner": "Quantum-L9",
                "repo_name": "SEO-Bot",
                "pr_number": 53,
                "action": "APPROVE",
            },
        ),
        (
            "mcp__GitHub__add_review_to_pr",
            {
                "repo_owner": "Quantum-L9",
                "repo_name": "SEO-Bot",
                "pr_number": 53,
                "action": "approve",
                "review": "lgtm",
            },
        ),
        (
            "mcp__github__add_review_to_pr",
            {"owner": "Quantum-L9", "repo": "SEO-Bot", "pr": 53, "review": {"event": "APPROVE"}},
        ),
        (
            "mcp__GitHub__add_comment_to_issue",
            {
                "repo_owner": "Quantum-L9",
                "repo_name": "SEO-Bot",
                "issue_number": 53,
                "comment": authz.authorization_line(SLUG, 53, SHA),
            },
        ),
        (
            "mcp__plugin_engineering_github__add_issue_comment",
            {
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "issue_number": 53,
                "body": authz.authorization_line(SLUG, 53, SHA),
            },
        ),
        (
            "mcp__github__create_pull_request_review",
            {"owner": "Quantum-L9", "repo": "SEO-Bot", "pull_number": 53, "event": "APPROVE"},
        ),
        (
            "mcp__github__create_and_submit_pull_request_review",
            {"owner": "Quantum-L9", "repo": "SEO-Bot", "pullNumber": 53, "event": "APPROVE"},
        ),
        (
            "mcp__github__submit_pending_pull_request_review",
            {"owner": "Quantum-L9", "repo": "SEO-Bot", "pullNumber": 53, "event": "APPROVE"},
        ),
        (
            "mcp__github__create_issue_comment",
            {
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "issue_number": 53,
                "body": authz.authorization_line(SLUG, 53, SHA),
            },
        ),
    ],
)
def test_hook_denies_an_agent_posting_the_authorization_through_mcp(
    tool_name: str, tool_input: dict
) -> None:
    _code, out = _gate({"tool_name": tool_name, "tool_input": tool_input})
    assert "never by an agent" in out


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        (
            "mcp__github__pull_request_review_write",
            {
                "method": "create",
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "pullNumber": 53,
                "event": "COMMENT",
                "body": "looks fine",
            },
        ),
        (
            "mcp__github__add_issue_comment",
            {
                "owner": "Quantum-L9",
                "repo": "SEO-Bot",
                "issue_number": 53,
                "body": "MERGE_PENDING: a human must authorize",
            },
        ),
        (
            "mcp__GitHub__add_review_to_pr",
            {
                "repo_owner": "Quantum-L9",
                "repo_name": "SEO-Bot",
                "pr_number": 53,
                "action": "COMMENT",
                "review": "consider renaming this helper",
            },
        ),
        (
            "mcp__GitHub__add_review_to_pr",
            {
                "repo_owner": "Quantum-L9",
                "repo_name": "SEO-Bot",
                "pr_number": 53,
                "action": "REQUEST_CHANGES",
                "review": "approve once the test is fixed",
            },
        ),
        (
            "mcp__GitHub__add_comment_to_issue",
            {
                "repo_owner": "Quantum-L9",
                "repo_name": "SEO-Bot",
                "issue_number": 53,
                "comment": "CI is green; waiting on the operator to merge",
            },
        ),
    ],
)
def test_hook_allows_ordinary_mcp_reviews_and_comments(tool_name: str, tool_input: dict) -> None:
    _code, out = _gate({"tool_name": tool_name, "tool_input": tool_input})
    assert out.strip() == ""


def _merge_gate_matchers() -> list[str]:
    settings = json.loads(
        (
            REPO / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
        ).read_text(encoding="utf-8")
    )
    return [
        entry["matcher"]
        for entry in settings["hooks"]["PreToolUse"]
        if any("merge_gate_wrap.py" in hook.get("command", "") for hook in entry["hooks"])
    ]


@pytest.mark.parametrize(
    "tool_name",
    [
        "mcp__github__pull_request_review_write",
        "mcp__github__add_issue_comment",
        "mcp__GitHub__add_review_to_pr",
        "mcp__GitHub__add_comment_to_issue",
        "mcp__GITHUB__add_issue_comment",
        "mcp__plugin_engineering_github__add_issue_comment",
    ],
)
def test_merge_gate_hook_matcher_routes_every_github_mcp_provider(tool_name: str) -> None:
    """Claude Code matchers are case-sensitive regexes: ``mcp__GitHub__*`` must reach the gate."""
    import re

    matchers = _merge_gate_matchers()
    assert matchers, "merge_gate_wrap.py is not wired into PreToolUse"
    assert any(re.fullmatch(matcher, tool_name) for matcher in matchers)


def test_hook_allows_an_ordinary_issue_comment() -> None:
    command = f"gh issue comment 53 --repo {SLUG} --body 'MERGE_PENDING: a human must authorize'"
    _code, out = _gate({"tool_name": "Bash", "tool_input": {"command": command}})
    assert out.strip() == ""


def test_paginated_pages_flatten_past_one_hundred_records() -> None:
    first = [{"id": index} for index in range(100)]
    second = [{"id": 100, "permission": "admin"}]
    separate = json.dumps(first) + "\n" + json.dumps(second)
    slurped = json.dumps([first, second])
    assert authz.flatten_list_pages(authz.parse_paginated_documents(separate)) == first + second
    assert authz.flatten_list_pages(authz.parse_paginated_documents(slurped)) == first + second


def test_fetch_evidence_keeps_an_approval_after_the_first_page(monkeypatch) -> None:
    reviews = [
        {
            "user": {"login": "reader", "type": "User"},
            "state": "COMMENTED",
            "commit_id": SHA,
            "author_association": "MEMBER",
            "permission": "read",
        }
        for _ in range(100)
    ]
    reviews.append(_review("operator", "APPROVED", SHA, permission="admin"))

    def pages(path: str) -> list:
        if "/reviews?" in path:
            return reviews
        if "/comments?" in path:
            return []
        return [{"filename": "README.md"}]

    monkeypatch.setattr(authz, "_gh_json", lambda path: {"user": {"login": "pr-author"}})
    monkeypatch.setattr(authz, "_gh_pages", pages)
    evidence = authz.fetch_evidence(SLUG, 53)
    assert evidence["truncated"] is False
    assert len(evidence["reviews"]) == 101
    verdict = authz.evaluate_evidence(SLUG, 53, SHA, evidence)
    assert verdict["authorized"] is True
    assert verdict["authorizer"] == "operator"


def test_mentioning_the_authorization_line_is_not_posting_it() -> None:
    command = f"echo '{authz.authorization_line(SLUG, 53, SHA)}'"
    _code, out = _gate({"tool_name": "Bash", "tool_input": {"command": command}})
    assert out.strip() == ""
