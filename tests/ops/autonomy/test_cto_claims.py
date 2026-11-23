"""cto_claims.py: advisory lane registry for parallel CTO campaigns.

The shapes are the ones the IB-Odoo_19 campaign met: a second campaign whose
ci/ baseline change landed under thirteen open PRs, an operator deciding who
owns a consumer repository's ci/, and a base-change notice with no channel.
GitHub is a fake REST layer holding one repository's issues and comments.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ops" / "autonomy"))

import cto_claims  # noqa: E402

REPO = "cryptoxdog/IB-Odoo_19"
SCHEMA = json.loads(cto_claims.CLAIMS_SCHEMA_PATH.read_text(encoding="utf-8"))


class FakeRest:
    """In-memory GitHub REST for issues, issue comments and labels."""

    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.comments: dict[int, dict[str, Any]] = {}
        self.labels: dict[int, list[str]] = {}
        self.calls: list[tuple[str, str]] = []
        self._next = 100

    def _id(self) -> int:
        self._next += 1
        return self._next

    def get(self, path: str) -> Any:
        self.calls.append(("GET", path))
        route, _, query = path.partition("?")
        params = dict(part.split("=", 1) for part in query.split("&") if part)
        if int(params.get("page", "1")) > 1:
            return []
        parts = route.split("/")
        if parts[-1] == "issues":
            label = params.get("labels")
            return [
                issue
                for issue in self.issues.values()
                if issue["state"] == "open" and (label is None or label in issue["labels"])
            ]
        if parts[-1] == "comments":
            issue = int(parts[-2])
            return [c for c in self.comments.values() if c["issue"] == issue]
        raise AssertionError(f"unexpected GET {path}")

    def send(self, method: str, path: str, body: dict[str, Any]) -> Any:
        self.calls.append((method, path))
        parts = path.split("/")
        if method == "POST" and parts[-1] == "issues":
            number = self._id()
            self.issues[number] = {
                "number": number,
                "title": body["title"],
                "labels": list(body["labels"]),
                "state": "open",
            }
            return {"number": number}
        if method == "POST" and parts[-1] == "comments":
            cid = self._id()
            self.comments[cid] = {"id": cid, "issue": int(parts[-2]), "body": body["body"]}
            return {"id": cid}
        if method == "PATCH" and parts[-2] == "comments":
            self.comments[int(parts[-1])]["body"] = body["body"]
            return {"id": int(parts[-1])}
        if method == "POST" and parts[-1] == "labels":
            self.labels.setdefault(int(parts[-2]), []).extend(body["labels"])
            return [{"name": name} for name in body["labels"]]
        raise AssertionError(f"unexpected {method} {path}")

    def docs(self) -> list[dict[str, Any]]:
        out = []
        for comment in self.comments.values():
            doc, error = cto_claims.parse_body(comment["body"])
            assert error is None
            if doc is not None:
                out.append(doc)
        return out


OWNERSHIP = cto_claims.load_ownership()
CLOCK = iter(f"2026-11-23T10:{m:02d}:00Z" for m in range(60))


def _now() -> str:
    return next(CLOCK)


def _register(rest: FakeRest, campaign: str, session: str, lane: str, paths, **kw) -> dict:
    return cto_claims.register(
        rest,
        repo=REPO,
        campaign=campaign,
        session=session,
        lane=lane,
        paths=paths,
        now=_now,
        **kw,
    )


def _check(rest: FakeRest, paths, prs=(), **kw) -> dict:
    return cto_claims.check(
        rest,
        repo=REPO,
        paths=paths,
        open_prs=lambda _repo: list(prs),
        ownership=OWNERSHIP,
        **kw,
    )


def _pr(number: int, files: list[str]) -> dict:
    return {"number": number, "headRefOid": f"{number:x}" * 40, "files": files}


def _advisory(result: dict) -> None:
    assert result["grants_permission"] is False
    assert result["advisory"] is True


# ---------------------------------------------------------------------------
# register / upsert
# ---------------------------------------------------------------------------


def test_register_creates_registry_issue_and_one_comment() -> None:
    rest = FakeRest()
    result = _register(rest, "odoo-golive", "session_A", "lane-a", ["addons/x/**"])
    _advisory(result)
    assert len(rest.issues) == 1
    issue = next(iter(rest.issues.values()))
    assert issue["title"] == "L9 CTO lane registry"
    assert issue["labels"] == ["l9-cto-registry"]
    (doc,) = rest.docs()
    jsonschema.validate(doc, SCHEMA)
    assert doc["lanes"] == [
        {"lane": "lane-a", "paths": ["addons/x/**"], "pr": None, "state": "planned"}
    ]
    assert doc["cto_session"] == "session_A" and doc["base"] == "main"


def test_register_upserts_the_same_comment() -> None:
    rest = FakeRest()
    first = _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])
    second = _register(rest, "c1", "session_A", "lane-a", ["ops/a.py", "ops/b.py"], pr=7)
    third = _register(rest, "c1", "session_A", "lane-b", ["docs/"])
    assert first["comment_id"] == second["comment_id"] == third["comment_id"]
    assert len(rest.comments) == 1 and len(rest.issues) == 1
    (doc,) = rest.docs()
    lanes = {row["lane"]: row for row in doc["lanes"]}
    assert lanes["lane-a"] == {
        "lane": "lane-a",
        "paths": ["ops/a.py", "ops/b.py"],
        "pr": 7,
        "state": "published",
    }
    assert lanes["lane-b"]["paths"] == ["docs/**"]
    patches = [call for call in rest.calls if call[0] == "PATCH"]
    assert len(patches) == 2


def test_register_reuses_an_existing_registry_issue() -> None:
    rest = FakeRest()
    _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])
    _register(rest, "c2", "session_B", "lane-x", ["ops/z.py"])
    assert len(rest.issues) == 1 and len(rest.comments) == 2


def test_release_marks_lane_then_campaign_released() -> None:
    rest = FakeRest()
    _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])
    _register(rest, "c1", "session_A", "lane-b", ["ops/b.py"])
    one = cto_claims.release(rest, repo=REPO, campaign="c1", session="session_A", lane="lane-a")
    _advisory(one)
    assert one["released"] == ["lane-a"]
    every = cto_claims.release(rest, repo=REPO, campaign="c1", session="session_A")
    assert every["released"] == ["lane-a", "lane-b"]
    assert {row["state"] for row in rest.docs()[0]["lanes"]} == {"released"}


def test_released_lanes_do_not_overlap() -> None:
    rest = FakeRest()
    _register(rest, "other", "session_B", "ci", ["ci/**"])
    cto_claims.release(rest, repo=REPO, campaign="other", session="session_B")
    assert _check(rest, ["ci/check.py"], campaign="mine")["status"] == "clear"


# ---------------------------------------------------------------------------
# foreign-comment protection
# ---------------------------------------------------------------------------


def test_a_cto_cannot_edit_another_sessions_claim() -> None:
    rest = FakeRest()
    _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])
    before = dict(rest.comments)
    with pytest.raises(cto_claims.ClaimsError, match="edits only its own claim"):
        _register(rest, "c1", "session_B", "lane-a", ["ops/hijack.py"])
    with pytest.raises(cto_claims.ClaimsError, match="edits only its own claim"):
        cto_claims.release(rest, repo=REPO, campaign="c1", session="session_B")
    with pytest.raises(cto_claims.ClaimsError, match="edits only its own claim"):
        cto_claims.notice(
            rest,
            repo=REPO,
            campaign="c1",
            session="session_B",
            kind="gate-change",
            paths=["ci/**"],
            text="x",
            now=_now,
        )
    assert rest.comments == before
    assert not [call for call in rest.calls if call[0] == "PATCH"]


def test_duplicate_campaign_comments_fail_closed() -> None:
    rest = FakeRest()
    _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])
    (comment,) = rest.comments.values()
    rest.comments[999] = {"id": 999, "issue": comment["issue"], "body": comment["body"]}
    with pytest.raises(cto_claims.ClaimsError, match="refusing to choose"):
        _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])


def test_non_claim_comments_are_ignored_and_broken_claims_are_unknown() -> None:
    rest = FakeRest()
    _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])
    issue = next(iter(rest.issues))
    rest.comments[500] = {"id": 500, "issue": issue, "body": "a human note"}
    assert _check(rest, ["ops/zzz.py"], campaign="c2")["status"] == "clear"
    rest.comments[501] = {"id": 501, "issue": issue, "body": "<!-- l9-cto-claims x -->\n```json\n{"}
    result = _check(rest, ["ops/zzz.py"], campaign="c2")
    assert result["status"] == "unknown"
    assert any("501" in line for line in result["unknown"])


# ---------------------------------------------------------------------------
# check: other campaigns, open PRs, ownership
# ---------------------------------------------------------------------------


def test_overlap_with_another_campaign_names_it() -> None:
    rest = FakeRest()
    _register(rest, "ci-hardening", "session_B", "detectors", ["ci/**"], pr=630, state="active")
    _register(rest, "odoo-golive", "session_A", "lane-a", ["addons/x/**"])
    result = _check(rest, ["ci/baselines/*.json", "addons/x/models.py"], campaign="odoo-golive")
    _advisory(result)
    assert result["status"] == "overlap"
    (hit,) = [row for row in result["overlaps"] if row["source"] == "claim"]
    assert hit["campaign"] == "ci-hardening"
    assert hit["cto_session"] == "session_B"
    assert hit["lane"] == "detectors" and hit["pr"] == 630
    assert hit["paths"] == ["ci/**"]


def test_own_campaign_is_excluded_from_check() -> None:
    rest = FakeRest()
    _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"], pr=11)
    result = _check(rest, ["ops/a.py"], prs=[_pr(11, ["ops/a.py"])], campaign="c1")
    assert result["status"] == "clear" and result["overlaps"] == []


def test_overlap_with_an_open_pr_names_pr_and_owning_campaign() -> None:
    rest = FakeRest()
    _register(rest, "ci-hardening", "session_B", "detectors", ["ci/check.py"], pr=630)
    prs = [
        _pr(630, ["ci/check_audit_class_detectors.py", "ci/baseline.json"]),
        _pr(631, ["README.md"]),
        _pr(632, ["ci/baseline.json", "ops/generated/skill-registry.json"]),
    ]
    result = _check(rest, ["ci/baseline.json"], prs=prs, campaign="odoo-golive")
    by_pr = {row["pr"]: row for row in result["overlaps"] if row["source"] == "open_pr"}
    assert set(by_pr) == {630, 632}
    assert by_pr[630]["campaign"] == "ci-hardening"
    assert by_pr[630]["cto_session"] == "session_B"
    assert by_pr[630]["lane"] == "detectors"
    assert by_pr[630]["paths"] == ["ci/baseline.json"]
    assert by_pr[630]["generated_only"] is False
    assert by_pr[632]["campaign"] is None


def test_generated_only_pr_overlap_is_flagged() -> None:
    rest = FakeRest()
    prs = [_pr(9, ["ops/generated/skill-registry.json"])]
    result = _check(rest, ["ops/generated/**"], prs=prs)
    (hit,) = result["overlaps"]
    assert hit["generated_only"] is True


def test_inventory_failure_is_unknown_not_clear() -> None:
    rest = FakeRest()

    def broken(_repo: str) -> list[dict]:
        raise RuntimeError("gh api repos/x/pulls failed")

    result = cto_claims.check(
        rest, repo=REPO, paths=["ops/a.py"], open_prs=broken, ownership=OWNERSHIP
    )
    assert result["status"] == "unknown"
    assert "open-PR inventory unavailable" in result["unknown"][0]


def test_ownership_mismatch_is_flagged_for_a_foreign_role() -> None:
    rest = FakeRest()
    _register(rest, "odoo-golive", "session_A", "ci-fix", ["ci/**"], state="active")
    result = _check(rest, ["ci/baseline.json"], campaign="ci-core", role="ci-core-architect")
    (hit,) = result["overlaps"]
    assert hit["ownership"] == [{"path": "ci/**", "owner": "consumer-repo-cto", "mismatch": True}]
    assert result["requested_ownership"] == [
        {"path": "ci/baseline.json", "owner": "consumer-repo-cto", "mismatch": True}
    ]
    same = _check(rest, ["ci/baseline.json"], campaign="c2", role="consumer-repo-cto")
    assert same["requested_ownership"][0]["mismatch"] is False
    unknown_role = _check(rest, ["ci/baseline.json"], campaign="c2")
    assert unknown_role["requested_ownership"][0]["mismatch"] is None


def test_ownership_seed_follows_the_operator_decision() -> None:
    assert cto_claims.owner_of(OWNERSHIP, REPO, "ci/check.py") == "consumer-repo-cto"
    assert cto_claims.owner_of(OWNERSHIP, REPO, ".github/workflows/ci.yml") == "consumer-repo-cto"
    assert cto_claims.owner_of(OWNERSHIP, REPO, "addons/x/models.py") is None
    for upstream in ("Quantum-L9/l9-ci-core", "Quantum-L9/l9-ci-sdk", "Quantum-L9/.github"):
        assert cto_claims.owner_of(OWNERSHIP, upstream, "ci/check.py") == "ci-core-architect"
        assert cto_claims.owner_of(OWNERSHIP, upstream, "anything.md") == "ci-core-architect"
    assert OWNERSHIP["grants_permission"] is False and OWNERSHIP["advisory"] is True


# ---------------------------------------------------------------------------
# path grammar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("ci/**", "ci/a/b.py", True),
        ("ci/*.py", "ci/a/b.py", False),
        ("ci/*.py", "ci/**", True),
        ("ops/*.py", "ops/*.md", False),
        ("ops/a/*.py", "ops/*/b.py", True),
        ("docs/", "docs/x.md", True),
        ("ops/a.py", "ops/a.py", True),
        ("ops/a.py", "ops/b.py", False),
        ("./.github/workflows/ci.yml", ".github/workflows/**", True),
        ("**/__init__.py", "addons/x/tests/__init__.py", True),
    ],
)
def test_glob_overlap(left: str, right: str, expected: bool) -> None:
    assert cto_claims.globs_overlap(left, right) is expected
    assert cto_claims.globs_overlap(right, left) is expected


# ---------------------------------------------------------------------------
# label and notice
# ---------------------------------------------------------------------------


def test_label_adds_campaign_and_cto_labels() -> None:
    rest = FakeRest()
    result = cto_claims.label(rest, repo=REPO, pr=42, campaign="odoo-golive", session="session_A")
    _advisory(result)
    assert rest.labels[42] == ["campaign:odoo-golive", "cto:session_A"]


def test_label_refuses_names_github_would_reject() -> None:
    rest = FakeRest()
    with pytest.raises(cto_claims.ClaimsError, match="50-character"):
        cto_claims.label(rest, repo=REPO, pr=42, campaign="x" * 60, session="s")
    assert rest.labels == {}


def test_notice_records_and_formats_messages_for_affected_campaigns() -> None:
    rest = FakeRest()
    _register(rest, "odoo-golive", "session_A", "lane-a", ["ci/baseline.json"], pr=640)
    _register(rest, "odoo-golive", "session_A", "lane-b", ["addons/y/**"], state="active")
    _register(rest, "docs-sweep", "session_C", "docs", ["docs/**"], state="active")
    _register(rest, "ci-hardening", "session_B", "detectors", ["ci/check.py"], state="active")
    result = cto_claims.notice(
        rest,
        repo=REPO,
        campaign="ci-hardening",
        session="session_B",
        kind="gate-change",
        paths=["ci/**"],
        text="Changing ci/ baselines; re-merge base after #638 lands.",
        now=_now,
    )
    _advisory(result)
    assert result["sent"] is False
    assert result["notice"]["affected"] == [
        {"campaign": "odoo-golive", "cto_session": "session_A", "lanes": ["lane-a"]}
    ]
    (message,) = result["messages"]
    assert message["to"] == "session_A"
    assert message["text"].splitlines() == [
        "CTO NOTICE gate-change | repo cryptoxdog/IB-Odoo_19 | from campaign ci-hardening "
        "(cto_session session_B)",
        "Changing ci/ baselines; re-merge base after #638 lands.",
        "Paths: ci/**",
        "Your affected lanes (campaign odoo-golive): lane-a",
        "Advisory: this notice is not a lock and grants no permission.",
    ]
    own = next(doc for doc in rest.docs() if doc["campaign"] == "ci-hardening")
    jsonschema.validate(own, SCHEMA)
    assert own["notices"][0]["kind"] == "gate-change"


def test_base_change_notice_reaches_every_live_campaign_on_that_base() -> None:
    rest = FakeRest()
    _register(rest, "odoo-golive", "session_A", "lane-a", ["addons/x/**"])
    _register(rest, "other-base", "session_D", "lane", ["addons/x/**"], base="release")
    result = cto_claims.notice(
        rest,
        repo=REPO,
        campaign="ci-hardening",
        session="session_B",
        kind="base-change",
        paths=["ci/**"],
        text="main moved",
        now=_now,
    )
    assert [row["campaign"] for row in result["notice"]["affected"]] == ["odoo-golive"]


def test_notice_rejects_unknown_kind() -> None:
    with pytest.raises(cto_claims.ClaimsError, match="notice kind"):
        cto_claims.notice(
            FakeRest(),
            repo=REPO,
            campaign="c",
            session="s",
            kind="lock",
            paths=["x"],
            text="t",
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_check_exit_codes_and_advisory_json(capsys, monkeypatch) -> None:
    rest = FakeRest()
    _register(rest, "other", "session_B", "lane", ["ci/**"], state="active")
    monkeypatch.setattr(cto_claims, "_fleet_inventory", lambda _repo: [])
    code = cto_claims.main(
        ["check", "--repo", REPO, "--paths", "ci/x.py", "--campaign", "mine"], rest=rest
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["status"] == "overlap"
    _advisory(out)
    code = cto_claims.main(["check", "--repo", REPO, "--paths", "addons/z.py"], rest=rest)
    assert code == 0 and json.loads(capsys.readouterr().out)["status"] == "clear"


def test_cli_error_is_advisory_json_exit_2(capsys) -> None:
    rest = FakeRest()
    _register(rest, "c1", "session_A", "lane-a", ["ops/a.py"])
    code = cto_claims.main(
        [
            "register",
            "--repo",
            REPO,
            "--campaign",
            "c1",
            "--cto-session",
            "session_X",
            "--lane",
            "lane-a",
            "--paths",
            "ops/b.py",
        ],
        rest=rest,
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out["status"] == "error"
    _advisory(out)
