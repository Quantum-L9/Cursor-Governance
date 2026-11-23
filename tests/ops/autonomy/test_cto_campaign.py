"""CTO campaign state, tick delta and operator-decision ledger (ops/autonomy/cto_campaign.py)."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import cto_campaign  # noqa: E402

GH = "Quantum-L9/Cursor-Governance"
SHA_A = "a" * 40
SHA_B = "b" * 40


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    return tmp_path


def _init(ws: Path, *, repos: tuple[str, ...] = (GH,), train: str | None = None) -> None:
    argv = ["--workspace", str(ws), "init", "--campaign", "c1", "--cto-session", "session_cto"]
    for repo in repos:
        argv += ["--repo", repo]
    if train:
        argv += ["--train", train]
    assert cto_campaign.main(argv) == 0


def _cli(ws: Path, *argv: str) -> int:
    return cto_campaign.main(["--workspace", str(ws), *argv])


def _observation(
    pr: int,
    *,
    head: str = SHA_A,
    state: str = "open",
    board: str = "wait",
    failing: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "key": f"{GH}#{pr}",
        "state": state,
        "head": head,
        "mergeable_state": "blocked",
        "draft": False,
        "merge_commit": "c" * 40 if state == "merged" else "",
        "board": board if state == "open" else None,
        "failing": list(failing),
        "pending": [],
    }


class FakeGitHub:
    """Stands in for the REST pull read and pr_board's verdict."""

    def __init__(self) -> None:
        self.pulls: dict[int, dict[str, Any]] = {}
        self.boards: dict[int, dict[str, Any]] = {}

    def fetch_pull(self, repo: str, pr: int) -> dict[str, Any]:
        if pr not in self.pulls:
            raise cto_campaign.CampaignError(f"gh api repos/{repo}/pulls/{pr} failed: 404")
        return dict(self.pulls[pr])

    def board(self, repo: str, pr: int) -> dict[str, Any]:
        return dict(self.boards.get(pr, {"board": "wait", "reason": "pending"}))

    def open(self, pr: int, head: str = SHA_A, failing: tuple[str, ...] = ()) -> None:
        self.pulls[pr] = {
            "state": "open",
            "head": head,
            "mergeable_state": "blocked",
            "draft": False,
            "merge_commit": "",
        }
        self.boards[pr] = {
            "board": "fix" if failing else "wait",
            "reason": "r",
            "failing_required": list(failing),
            "pending_required": [],
        }


@pytest.fixture
def gh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeGitHub:
    fake = FakeGitHub()
    monkeypatch.setattr(cto_campaign, "fetch_pull", fake.fetch_pull)
    monkeypatch.setattr(cto_campaign, "board_verdict", fake.board)
    monkeypatch.setattr(cto_campaign, "TRIAGE_TOOL", tmp_path / "absent" / "ci_triage.py")
    return fake


# ---------------------------------------------------------------- campaign + pool


def test_init_writes_schema_valid_campaign(ws: Path) -> None:
    _init(ws)
    document = json.loads(cto_campaign.campaign_path(ws).read_text())
    cto_campaign.validate(document, cto_campaign.CAMPAIGN_SCHEMA)
    assert document["grants_permission"] is False
    assert document["checkin"] == {"cadence_min": 10, "last_tick_at": None, "last_digest": None}


def test_init_refuses_to_overwrite_without_force(
    ws: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _init(ws)
    assert _cli(ws, "init", "--campaign", "c2", "--cto-session", "s", "--repo", GH) == 1
    assert "exists" in capsys.readouterr().err
    assert _cli(ws, "init", "--campaign", "c2", "--cto-session", "s", "--repo", GH, "--force") == 0


def test_pool_set_upserts_and_lane_set_updates(
    ws: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _init(ws)
    assert _cli(ws, "pool", "set", "--agent", "agent-e", "--session", "s-e", "--lane", "E") == 0
    assert _cli(ws, "pool", "set", "--agent", "agent-e", "--state", "working") == 0
    assert _cli(ws, "lane", "set", "--lane", "E", "--add-pr", "12", "--add-pr", "12") == 0
    assert (
        _cli(ws, "lane", "set", "--lane", "E", "--add-pr", "13", "--state", "ready-to-merge") == 0
    )
    capsys.readouterr()
    assert _cli(ws, "pool", "show", "--json") == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["grants_permission"] is False
    assert shown["pool"] == [
        {
            "agent": "agent-e",
            "session": "s-e",
            "lane": "E",
            "state": "ready-to-merge",
            "prs": [12, 13],
        }
    ]


def test_new_pool_agent_needs_a_session(ws: Path) -> None:
    _init(ws)
    assert _cli(ws, "pool", "set", "--agent", "agent-x", "--lane", "X") == 1


def test_lane_set_unknown_lane_is_an_error(ws: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init(ws)
    assert _cli(ws, "lane", "set", "--lane", "Z", "--state", "working") == 1
    assert "no pool agent holds lane" in capsys.readouterr().err


def test_invalid_state_on_disk_is_refused_not_used(
    ws: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _init(ws)
    path = cto_campaign.campaign_path(ws)
    document = json.loads(path.read_text())
    document["grants_permission"] = True
    path.write_text(json.dumps(document))
    assert _cli(ws, "pool", "show") == 1
    assert "grants_permission" in capsys.readouterr().err


def test_campaign_schema_rejects_unknown_pool_state() -> None:
    document = {
        "schema": "l9.cto-campaign/v1",
        "grants_permission": False,
        "campaign": "c",
        "cto_session": "s",
        "repos": [GH],
        "pool": [{"agent": "a", "session": "s", "lane": None, "state": "napping", "prs": []}],
        "train": None,
        "checkin": {"cadence_min": 10, "last_tick_at": None, "last_digest": None},
        "updated_at": "2026-11-23T00:00:00Z",
    }
    with pytest.raises(cto_campaign.CampaignError, match="napping"):
        cto_campaign.validate(document, cto_campaign.CAMPAIGN_SCHEMA)


def test_multi_repo_pool_prs_need_a_repo(ws: Path, gh: FakeGitHub) -> None:
    _init(ws, repos=(GH, "Quantum-L9/other"))
    assert _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "5") == 0
    with pytest.raises(cto_campaign.CampaignError, match="several"):
        cto_campaign.tick(ws)
    assert _cli(ws, "pool", "set", "--agent", "a", "--repo", GH) == 0
    gh.open(5)
    assert cto_campaign.tick(ws)["observations"].keys() == {f"{GH}#5"}


# ---------------------------------------------------------------- tick delta


def _tick_text(ws: Path, capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    assert _cli(ws, "tick") == 0
    return capsys.readouterr().out


def test_tick_unchanged_state_prints_nothing(
    ws: Path, gh: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--lane", "E", "--pr", "7")
    gh.open(7)
    first = _tick_text(ws, capsys)
    assert f"NEW {GH}#7 open head aaaaaaa" in first
    assert "list_sessions" in first  # the pool reminder rides with every delta
    assert _tick_text(ws, capsys) == ""
    campaign = cto_campaign.load_campaign(ws)
    assert campaign["checkin"]["last_digest"].startswith("sha256:")
    assert campaign["checkin"]["last_tick_at"]


def test_tick_head_move_prints_exactly_one_line(
    ws: Path, gh: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "7", "--pr", "8")
    gh.open(7)
    gh.open(8)
    _tick_text(ws, capsys)
    gh.open(7, head=SHA_B)
    out = _tick_text(ws, capsys).splitlines()
    assert out[:-1] == [f"HEAD {GH}#7 aaaaaaa -> bbbbbbb"]
    assert "list_sessions" in out[-1]


def test_tick_reports_merge_and_board_change(ws: Path, gh: FakeGitHub) -> None:
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "7", "--pr", "8")
    gh.open(7)
    gh.open(8)
    cto_campaign.tick(ws)
    gh.pulls[7]["state"] = "merged"
    gh.pulls[7]["merge_commit"] = "c" * 40
    gh.boards[8] = {"board": "merge", "reason": "green", "failing_required": []}
    lines = cto_campaign.tick(ws)["lines"]
    assert lines == [
        f"MERGED {GH}#7 head aaaaaaa merge ccccccc",
        f"BOARD {GH}#8 wait -> merge (green)",
    ]


def test_tick_unknown_telemetry_stays_explicit(ws: Path, gh: FakeGitHub) -> None:
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "9")
    result = cto_campaign.tick(ws)
    assert result["observations"][f"{GH}#9"]["state"] == "unknown"
    assert result["lines"][0].startswith(f"UNKNOWN {GH}#9 ")
    assert cto_campaign.tick(ws)["lines"] == []


def test_tick_red_check_without_triage_tool_is_marked_unavailable(ws: Path, gh: FakeGitHub) -> None:
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "7")
    gh.open(7)
    cto_campaign.tick(ws)
    gh.open(7, failing=("CI Gate",))
    result = cto_campaign.tick(ws)
    assert result["triage_available"] is False
    assert (
        f"RED {GH}#7 'CI Gate' at aaaaaaa triage=UNAVAILABLE (ci_triage.py absent)"
        in result["lines"]
    )
    gh.open(7)
    assert f"CLEARED {GH}#7 'CI Gate'" in cto_campaign.tick(ws)["lines"]


def _fake_triage(tmp_path: Path, body: str) -> Path:
    tool = tmp_path / "bin" / "ci_triage.py"
    tool.parent.mkdir(parents=True, exist_ok=True)
    tool.write_text(textwrap.dedent(body), encoding="utf-8")
    return tool


def test_tick_red_check_with_triage_tool_carries_verdict(
    ws: Path, gh: FakeGitHub, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = _fake_triage(
        tmp_path,
        """
        import json, sys
        args = sys.argv[1:]
        assert args[0] == "classify" and "--json" in args
        print(json.dumps({
            "schema": "l9.ci-triage/v1", "repo": args[args.index("--repo") + 1],
            "pr": int(args[args.index("--pr") + 1]), "head": args[args.index("--sha") + 1],
            "grants_permission": False,
            "checks": [{"name": "CI Gate", "conclusion": "failure", "verdict": "billing",
                        "evidence": "spending limit", "failing_paths": [],
                        "owner_hint": "operator"}],
        }))
        """,
    )
    monkeypatch.setattr(cto_campaign, "TRIAGE_TOOL", tool)
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "7")
    gh.open(7, failing=("CI Gate", "lint"))
    result = cto_campaign.tick(ws)
    assert result["triage_available"] is True
    assert f"RED {GH}#7 'CI Gate' at aaaaaaa triage=billing owner=operator" in result["lines"]
    # A failing check the classifier did not return stays unknown, not green.
    assert f"RED {GH}#7 'lint' at aaaaaaa triage=unknown" in result["lines"]


def test_tick_triage_failure_is_explicit_unknown(
    ws: Path, gh: FakeGitHub, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = _fake_triage(tmp_path, "import sys\nsys.exit(3)\n")
    monkeypatch.setattr(cto_campaign, "TRIAGE_TOOL", tool)
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "7")
    gh.open(7, failing=("CI Gate",))
    line = next(x for x in cto_campaign.tick(ws)["lines"] if x.startswith("RED"))
    assert "triage=UNKNOWN (ci_triage exited 3" in line


def test_tick_reads_train_prs(ws: Path, gh: FakeGitHub) -> None:
    train = {
        "schema": "l9.cto-train/v1",
        "campaign": "c1",
        "repo": GH,
        "base": "main",
        "prs": [{"number": 21, "lane": "A", "proven_head": None}],
        "order": [21],
        "pairs": [],
        "integration_receipt": None,
        "runtime": None,
        "static": [],
        "suite": [],
    }
    path = cto_campaign.default_train_path(ws)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(train))
    _init(ws)
    gh.open(21)
    result = cto_campaign.tick(ws)
    assert result["train"] == str(path)
    assert list(result["observations"]) == [f"{GH}#21"]


def test_tick_named_missing_train_is_an_error(ws: Path, gh: FakeGitHub) -> None:
    _init(ws, train="nowhere/train.json")
    with pytest.raises(cto_campaign.CampaignError, match="does not exist"):
        cto_campaign.tick(ws)


def test_tick_lost_snapshot_rebaselines_explicitly(ws: Path, gh: FakeGitHub) -> None:
    _init(ws)
    _cli(ws, "pool", "set", "--agent", "a", "--session", "s", "--pr", "7")
    gh.open(7)
    cto_campaign.tick(ws)
    cto_campaign.snapshot_path(ws).unlink()
    gh.open(7, head=SHA_B)
    lines = cto_campaign.tick(ws)["lines"]
    assert lines == [f"NEW {GH}#7 open head bbbbbbb board=wait mergeable=blocked"]


def test_tick_json_output_grants_no_permission(
    ws: Path, gh: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    _init(ws)
    capsys.readouterr()
    assert _cli(ws, "tick", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "l9.cto-campaign-tick/v1"
    assert payload["grants_permission"] is False
    assert payload["changed"] is False
    assert "list_sessions" in payload["reminder"]


def test_checkin_text_is_fixed_and_offline(ws: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _cli(ws, "tick", "--checkin-text") == 0
    text = capsys.readouterr().out.strip()
    assert text.startswith("CTO check-in: run ")
    assert 'cto_campaign.py" tick --workspace' in text
    assert text.endswith("and act on its delta.")
    assert text == cto_campaign.checkin_text(ws.resolve())


def test_delta_of_identical_snapshots_is_empty() -> None:
    snap = {f"{GH}#1": _observation(1, failing=("x",))}
    assert cto_campaign.delta(snap, json.loads(json.dumps(snap))) == []


def test_delta_red_check_is_new_again_on_a_new_head() -> None:
    old = {f"{GH}#1": _observation(1, failing=("x",))}
    new = {f"{GH}#1": _observation(1, head=SHA_B, failing=("x",))}
    new[f"{GH}#1"]["triage"] = {"available": False}
    assert cto_campaign.delta(old, new) == [
        f"HEAD {GH}#1 aaaaaaa -> bbbbbbb",
        f"RED {GH}#1 'x' at bbbbbbb triage=UNAVAILABLE (ci_triage.py absent)",
    ]


# ---------------------------------------------------------------- decisions


def _ask(ws: Path, decision_id: str = "D23", *extra: str) -> int:
    return _cli(
        ws,
        "decide",
        "ask",
        "--id",
        decision_id,
        "--question",
        "Ship the version driver now?",
        "--option",
        "A:Ship now",
        "--option",
        "B:Wait for lane C",
        "--recommended",
        "A",
        *extra,
    )


def test_decision_lifecycle(ws: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _ask(ws) == 0
    asked = capsys.readouterr().out
    assert asked.splitlines() == [
        "D23 — Ship the version driver now?",
        "  1. A: Ship now (recommended)",
        "  2. B: Wait for lane C",
        'Reply with the option key, e.g. "D23: A".',
    ]
    assert _cli(ws, "decide", "pending") == 0
    assert capsys.readouterr().out.strip() == asked.strip()  # re-askable after a restart

    assert (
        _cli(ws, "decide", "answer", "--id", "D23", "--answer", "B", "--note", "after C lands") == 0
    )
    capsys.readouterr()
    assert _cli(ws, "decide", "pending") == 0
    assert capsys.readouterr().out == ""
    assert _cli(ws, "decide", "answer", "--id", "D23", "--answer", "A") == 1  # already answered

    document = json.loads(cto_campaign.decisions_path(ws).read_text())
    cto_campaign.validate(document, cto_campaign.DECISIONS_SCHEMA)
    (decision,) = document["decisions"]
    assert decision["state"] == "answered"
    assert decision["answer"] == "B"
    assert decision["note"] == "after C lands"


def test_decision_ask_rejects_duplicates_and_bad_recommendation(ws: Path) -> None:
    assert _ask(ws) == 0
    assert _ask(ws) == 1
    assert (
        _cli(
            ws,
            "decide",
            "ask",
            "--id",
            "D24",
            "--question",
            "q",
            "--option",
            "A:x",
            "--recommended",
            "Z",
        )
        == 1
    )
    assert _cli(ws, "decide", "ask", "--id", "D25", "--question", "q", "--option", "nocolon") == 1


def test_decision_answer_outside_options_needs_free(ws: Path) -> None:
    assert _ask(ws) == 0
    assert _cli(ws, "decide", "answer", "--id", "D23", "--answer", "C") == 1
    assert _cli(ws, "decide", "answer", "--id", "D23", "--answer", "Do both", "--free") == 0


def test_supersede_answered_decision_on_answer(ws: Path) -> None:
    assert _ask(ws, "D1") == 0
    assert _cli(ws, "decide", "answer", "--id", "D1", "--answer", "A") == 0
    assert _ask(ws, "D2", "--supersedes", "D1") == 0
    # D1 stays in force until its replacement is answered.
    assert cto_campaign.load_decisions(ws)["decisions"][0]["state"] == "answered"
    assert _cli(ws, "decide", "answer", "--id", "D2", "--answer", "B") == 0
    d1, d2 = cto_campaign.load_decisions(ws)["decisions"]
    assert (d1["state"], d1["superseded_by"]) == ("superseded", "D2")
    assert d2["supersedes"] == "D1"


def test_supersede_pending_decision_withdraws_it(ws: Path) -> None:
    assert _ask(ws, "D1") == 0
    assert _ask(ws, "D2", "--supersedes", "D1") == 0
    assert [d["id"] for d in cto_campaign.pending(ws)] == ["D2"]


def test_brief_block_is_verbatim_and_omits_superseded(
    ws: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli(ws, "decide", "brief") == 0
    assert capsys.readouterr().out.splitlines()[1] == "(none recorded)"
    _ask(ws, "D1")
    _cli(ws, "decide", "answer", "--id", "D1", "--answer", "A")
    _ask(ws, "D2", "--supersedes", "D1")
    _cli(ws, "decide", "answer", "--id", "D2", "--answer", "B", "--note", "operator, 2026-11-23")
    _ask(ws, "D3")  # pending: never in a brief
    capsys.readouterr()
    assert _cli(ws, "decide", "brief") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("OPERATOR DECISIONS (verbatim from decisions.json")
    body = "\n".join(lines[1:])
    assert "D1 " not in body
    assert "D3 " not in body
    assert "D2 [" in body
    assert "  Answer: B — Wait for lane C" in lines
    assert "  Note: operator, 2026-11-23" in lines
    assert "  Supersedes: D1" in lines


def test_decide_json_outputs_grant_no_permission(
    ws: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for argv in (
        ("decide", "ask", "--id", "D9", "--question", "q", "--option", "A:x", "--json"),
        ("decide", "pending", "--json"),
        ("decide", "brief", "--json"),
        ("decide", "answer", "--id", "D9", "--answer", "A", "--json"),
        ("decide", "show"),
    ):
        capsys.readouterr()
        assert _cli(ws, *argv) == 0
        assert json.loads(capsys.readouterr().out)["grants_permission"] is False


def test_decisions_schema_requires_answer_when_answered() -> None:
    document = {
        "schema": "l9.cto-decisions/v1",
        "grants_permission": False,
        "decisions": [
            {
                "id": "D1",
                "asked_at": "t",
                "question": "q",
                "options": [{"key": "A", "text": "x"}],
                "recommended": None,
                "state": "answered",
                "answer": None,
                "answered_at": None,
                "supersedes": None,
            }
        ],
    }
    with pytest.raises(cto_campaign.CampaignError, match="decisions/0/answer"):
        cto_campaign.validate(document, cto_campaign.DECISIONS_SCHEMA)
