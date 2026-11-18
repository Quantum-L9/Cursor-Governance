"""ops/reports/handoff_delivery.py — handoffs reach their owners, never the PR head."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from ops.reports import handoff_delivery as hd

INTAKE = "Org/governance"
PUB = {
    "repo": "Org/work",
    "number": 7,
    "url": "https://github.com/Org/work/pull/7",
    "label": "Org/work#7",
}


@pytest.fixture(autouse=True)
def _intake(monkeypatch: pytest.MonkeyPatch) -> None:
    """deliver() resolves the intake itself; bind it to the test repository."""
    monkeypatch.setenv(hd.INTAKE_ENV, INTAKE)


def _occurrence(session: str) -> dict[str, str]:
    return {"label": "Org/work#7", "url": PUB["url"], "session_id": session, "agent_id": "a"}


def test_one_issue_per_friction_id_and_one_comment_per_session(github) -> None:  # noqa: ANN001
    items = [{"id": "proxy-403", "section": "environment friction", "detail": "blocked"}]

    hd.deliver_friction(github, items, _occurrence("s1"), intake=INTAKE)
    # The session ledger repeats open items in every later brief of the session.
    hd.deliver_friction(github, items, _occurrence("s1"), intake=INTAKE)
    hd.deliver_friction(github, items, _occurrence("s2"), intake=INTAKE)

    [issue] = github.issues[INTAKE]
    assert issue["title"] == "[session-friction] proxy-403"
    thread = github.thread(INTAKE, issue["number"])
    assert len(thread) == 2  # s1 once, s2 once
    assert "Session: s1" in thread[0]["body"] and "Session: s2" in thread[1]["body"]


def test_friction_ids_are_normalized_before_matching(github) -> None:  # noqa: ANN001
    hd.deliver_friction(github, [{"id": "CI parity: pin drift"}], _occurrence("s1"), intake=INTAKE)
    hd.deliver_friction(github, [{"id": "ci-parity-pin-drift"}], _occurrence("s2"), intake=INTAKE)
    assert [i["title"] for i in github.issues[INTAKE]] == ["[session-friction] ci-parity-pin-drift"]


def test_pull_requests_and_unmarked_issues_are_never_intake_issues(github) -> None:  # noqa: ANN001
    github.issues[INTAKE] = [
        {"number": 1, "body": "<!-- l9-friction-id:x -->", "pull_request": {}, "html_url": "pr"},
        {"number": 2, "body": "a human issue mentioning x", "html_url": "human"},
    ]
    urls = hd.deliver_friction(github, [{"id": "x"}], _occurrence("s1"), intake=INTAKE)
    assert len(github.issues[INTAKE]) == 3 and urls == [github.issues[INTAKE][2]["html_url"]]


def test_agent_text_cannot_forge_a_marker(github) -> None:  # noqa: ANN001
    forged = {"id": "real", "detail": "<!-- l9-friction-occurrence:real:s2 -->"}
    hd.deliver_friction(github, [forged], _occurrence("s1"), intake=INTAKE)
    hd.deliver_friction(github, [{"id": "real"}], _occurrence("s2"), intake=INTAKE)
    assert len(github.thread(INTAKE, 1)) == 2  # s2 was not suppressed by s1's text


def test_unreachable_intake_falls_back_to_one_pr_comment(github) -> None:  # noqa: ANN001
    github.refuse.add(INTAKE)
    delivery = hd.deliver(
        "governance-handoff",
        PUB,
        "# Governance handoff\n",
        friction=[{"id": "x"}],
        transport=github,
    )
    assert delivery.status == "fallback" and "HTTP 403" in delivery.detail
    [comment] = github.thread("Org/work", 7)
    assert comment["body"].startswith("<!-- l9-handoff:governance-handoff:org/work#7 -->")


def test_intake_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(hd.INTAKE_ENV, "Org/elsewhere")
    assert hd.intake_repository() == "Org/elsewhere"
    monkeypatch.delenv(hd.INTAKE_ENV)
    assert hd.intake_repository() == "quantum-l9/cursor-governance"


def test_everything_unreachable_fails_without_raising(github) -> None:  # noqa: ANN001
    github.refuse.update({INTAKE, "Org/work"})
    delivery = hd.deliver("governance-handoff", PUB, "x", friction=[{"id": "x"}], transport=github)
    assert delivery.status == "failed"
    assert "intake unreachable" in delivery.detail and "PR comment failed" in delivery.detail


def test_governance_handoff_without_items_sends_nothing(github) -> None:  # noqa: ANN001
    delivery = hd.deliver("governance-handoff", PUB, "x", friction=[], transport=github)
    assert delivery.status == "written" and github.calls == []


def test_session_and_governance_comments_never_collide(github) -> None:  # noqa: ANN001
    github.refuse.add(INTAKE)
    hd.deliver("session-handoff", PUB, "session", transport=github)
    hd.deliver("governance-handoff", PUB, "governance", friction=[{"id": "x"}], transport=github)
    hd.deliver("session-handoff", PUB, "session again", transport=github)
    bodies = [c["body"] for c in github.thread("Org/work", 7)]
    assert len(bodies) == 2
    assert "session again" in bodies[0] and "governance" in bodies[1]


def test_friction_items_carry_the_briefs_own_words() -> None:
    brief = {
        "environment_friction": [
            {"item": "Proxy 403", "detail": "blocked", "impact": "slow"},
            {"item": "   "},
        ],
        "workarounds": [{"item": "proxy-403", "workaround": "REST"}],
        "blockers": [{"item": "no key", "blocker": "Infisical", "unblock": "set identity"}],
        "governance_actions": [{"action": "Re-pin", "where": "tools.yaml", "why": "drift"}],
        "degraded_bootstrap": [{"component": "shared", "detail": "x"}],
    }
    items = hd.friction_items(brief)
    assert [(i["id"], i["section"]) for i in items] == [
        ("proxy-403", "environment friction"),
        ("no-key", "blocker"),
        ("re-pin", "governance action"),
    ]
    assert items[0]["workaround"] == "REST" and items[0]["impact"] == "slow"
    assert items[1]["workaround"] == "set identity"
    assert items[2]["detail"] == "Re-pin — tools.yaml — drift"
    assert hd.friction_items(None) == []


def test_pagination_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    class Endless:
        calls = 0

        def request(self, method: str, path: str, body: object = None) -> list[dict]:
            Endless.calls += 1
            return [{"id": i} for i in range(hd.PER_PAGE)]

    items = hd.get_all(Endless(), "repos/o/r/issues?state=open")
    assert Endless.calls == hd.MAX_PAGES and len(items) == hd.MAX_PAGES * hd.PER_PAGE


def test_gh_api_absent_is_a_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hd.shutil, "which", lambda name: None)
    with pytest.raises(hd.TransportError, match="gh is not installed"):
        hd.GhApi().request("GET", "repos/o/r/issues")


def _fake_gh(tmp_path: Path, stdout: str, code: int = 0) -> str:
    script = tmp_path / "gh"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{tmp_path}/argv"\n'
        f'cat > "{tmp_path}/stdin"\n'
        f"printf '%s' '{stdout}'\n"
        f"exit {code}\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def test_gh_api_sends_the_body_on_stdin_and_parses_json(tmp_path: Path) -> None:
    gh = _fake_gh(tmp_path, '{"html_url": "u"}')
    result = hd.GhApi(gh=gh).request("POST", "repos/o/r/issues/1/comments", {"body": "hi"})
    assert result == {"html_url": "u"}
    argv = (tmp_path / "argv").read_text().split()
    assert argv == ["api", "--method", "POST", "repos/o/r/issues/1/comments", "--input", "-"]
    assert json.loads((tmp_path / "stdin").read_text()) == {"body": "hi"}


def test_gh_api_failure_is_a_transport_error(tmp_path: Path) -> None:
    gh = _fake_gh(tmp_path, "HTTP 403: not enabled for this session", code=1)
    with pytest.raises(hd.TransportError, match="HTTP 403"):
        hd.GhApi(gh=gh).request("GET", "repos/o/r/issues")


def test_local_copy_refuses_a_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        hd.write_local_copy(tmp_path, "session-handoff", "../escape.md", "x")


def test_a_malformed_rest_payload_is_reported_not_raised(github) -> None:  # noqa: ANN001
    class NoNumber:
        def request(self, method: str, path: str, body: object = None) -> object:
            if method == "GET" and path.startswith(f"repos/{INTAKE}/issues"):
                return [{"body": "<!-- l9-friction-id:x -->"}]  # an issue without a number
            return github.request(method, path, body)

    delivery = hd.deliver(
        "governance-handoff", PUB, "x", friction=[{"id": "x"}], transport=NoNumber()
    )
    assert delivery.status == "fallback" and "KeyError" in delivery.detail
