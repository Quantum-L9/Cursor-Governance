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


def test_author_cannot_authorize_an_org_007_path() -> None:
    verdict = _verdict(
        author="pr-author",
        files=["CANONICAL_LAW.md"],
        reviews=[_review("pr-author", "APPROVED", SHA)],
        comments=[
            {
                "user": _user("pr-author"),
                "author_association": "OWNER",
                "body": authz.authorization_line(SLUG, 53, SHA),
            }
        ],
    )
    assert verdict["authorized"] is False
    assert "L9-ORG-007" in verdict["reason"]


def test_a_different_human_can_authorize_an_org_007_path() -> None:
    verdict = _verdict(
        author="pr-author",
        files=["ops/config/root-file-protection.json"],
        reviews=[_review("governance-owner", "APPROVED", SHA)],
    )
    assert verdict["authorized"] is True
    assert verdict["authorizer"] == "governance-owner"


def test_unknown_files_fail_closed_for_the_author() -> None:
    verdict = _verdict(files=None, reviews=[_review("pr-author", "APPROVED", SHA)])
    assert verdict["authorized"] is False
    assert "L9-ORG-007" in verdict["reason"]


def test_unknown_author_fails_closed_on_an_org_007_path() -> None:
    verdict = _verdict(
        author="",
        files=["CANONICAL_LAW.md"],
        reviews=[_review("somebody", "APPROVED", SHA)],
    )
    assert verdict["authorized"] is False
    assert "L9-ORG-007" in verdict["reason"]


def test_unknown_author_may_still_authorize_an_ordinary_change() -> None:
    verdict = _verdict(
        author="", files=["README.md"], reviews=[_review("somebody", "APPROVED", SHA)]
    )
    assert verdict["authorized"] is True


def test_fetch_evidence_keeps_the_previous_name_of_a_renamed_file(monkeypatch) -> None:
    def pages(path: str) -> list:
        if "/files?" in path:
            return [
                {
                    "filename": "docs/old_law.md",
                    "previous_filename": "CANONICAL_LAW.md",
                    "status": "renamed",
                }
            ]
        return [_review("pr-author", "APPROVED", SHA)] if "/reviews?" in path else []

    monkeypatch.setattr(authz, "_gh_json", lambda path: {"user": {"login": "pr-author"}})
    monkeypatch.setattr(authz, "_gh_pages", pages)
    evidence = authz.fetch_evidence(SLUG, 53)
    assert "CANONICAL_LAW.md" in evidence["files"]
    verdict = authz.evaluate_evidence(SLUG, 53, SHA, evidence)
    assert verdict["authorized"] is False
    assert "L9-ORG-007" in verdict["reason"]


def test_fetch_evidence_reports_an_empty_file_list_as_unknown(monkeypatch) -> None:
    monkeypatch.setattr(authz, "_gh_json", lambda path: {"user": {"login": "pr-author"}})
    monkeypatch.setattr(authz, "_gh_pages", lambda path: [])
    assert authz.fetch_evidence(SLUG, 53)["files"] is None


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
    ],
)
def test_hook_allows_ordinary_mcp_reviews_and_comments(tool_name: str, tool_input: dict) -> None:
    _code, out = _gate({"tool_name": tool_name, "tool_input": tool_input})
    assert out.strip() == ""


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
