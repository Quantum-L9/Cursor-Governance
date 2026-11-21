"""Merge-queue mode of stack_safe_merge.py and its merge_gate admission.

The queue path binds the grant to the head in code: enqueue only a granted
``board=merge`` head into a queue-protected base, accept it only when observed
queued at that head (else disarm), and dequeue -- or report UNBOUND_QUEUE_ENTRY
-- when the head moves while queued. GitHub's own behaviour on a push is UNKNOWN
and is never relied on here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE = REPO_ROOT / "ops" / "autonomy" / "merge_gate.py"
sys.path.insert(0, str(REPO_ROOT / "ops" / "autonomy"))

import stack_safe_merge as ssm  # noqa: E402

REPO = "Quantum-L9/Cursor-Governance"
A = "a" * 40
B = "b" * 40
C = "c" * 40


class FakeGitHub:
    """Per-PR live state; every call the queue path makes goes through here."""

    def __init__(self, prs: dict[str, dict[str, Any]], *, queue_base: bool = True) -> None:
        self.prs = prs
        self.queue_base = queue_base
        self.calls: list[tuple[str, str]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(ssm, "pr_base", lambda repo, pr: "main")
        monkeypatch.setattr(
            ssm,
            "queue_rule",
            lambda repo, base, pr="": {"type": "merge_queue"} if self.queue_base else None,
        )
        monkeypatch.setattr(ssm, "authorization_status", self._auth)
        monkeypatch.setattr(ssm, "board_verdict", lambda repo, pr: {"board": self.prs[pr]["board"]})
        monkeypatch.setattr(ssm, "live_head_sha", lambda repo, pr: self.prs[pr]["head"])
        monkeypatch.setattr(ssm, "enqueue_call", self._enqueue)
        monkeypatch.setattr(ssm, "disarm_call", self._disarm)
        monkeypatch.setattr(ssm, "dequeue_call", self._dequeue)
        monkeypatch.setattr(ssm, "queue_state", self._state)
        ledger = tmp_path / ssm.UNBOUND_LEDGER_NAME
        monkeypatch.setattr(ssm, "_unbound_ledger_path", lambda: ledger)

    def _auth(self, repo: str, pr: str, sha: str, **_: Any) -> dict[str, Any]:
        granted = self.prs[pr].get("granted")
        if granted == sha:
            return {"status": "AUTHORIZED", "head_sha": sha}
        return {"status": "MERGE_PENDING", "reason": f"no authorization for {sha}"}

    def _enqueue(self, repo: str, pr: str, sha: str) -> None:
        self.calls.append(("enqueue", pr))
        pr_state = self.prs[pr]
        pr_state["queued"] = pr_state.get("enters_queue", True)
        pr_state["armed"] = True
        # The next read is enqueue_one proving membership; the watch script starts after it.
        pr_state["proving"] = True

    def _disarm(self, repo: str, pr: str) -> None:
        self.calls.append(("disarm", pr))
        if self.prs[pr].get("disarm_fails"):
            raise RuntimeError("disarm refused")
        self.prs[pr]["armed"] = False
        if not self.prs[pr].get("sticky"):
            self.prs[pr]["queued"] = False

    def _dequeue(self, repo: str, pr: str) -> None:
        self.calls.append(("dequeue", pr))
        if self.prs[pr].get("sticky"):
            raise RuntimeError("dequeue refused")
        self.prs[pr]["queued"] = False
        self.prs[pr]["armed"] = False

    def _state(self, repo: str, pr: str) -> dict[str, Any]:
        pr_state = self.prs[pr]
        script = pr_state.get("script")
        if pr_state.pop("proving", False):
            pass
        elif script and pr_state.get("queued") is True and self.calls[-1][0] == "enqueue":
            pr_state.update(script.pop(0))
        return {
            "queued": pr_state.get("queued", False),
            "head": pr_state["head"],
            "entry_head": None,
            "merged": pr_state.get("merged", False),
            "armed": pr_state.get("armed"),
        }


def _run(fake: FakeGitHub, items: list[tuple[str, str]]) -> list[dict[str, Any]]:
    return ssm.run_queue(REPO, items, poll=0, timeout=60, sleep=lambda _: None)


def _green(head: str, **extra: Any) -> dict[str, Any]:
    return {"head": head, "granted": head, "board": "merge", **extra}


# -- detection ---------------------------------------------------------------


def test_queue_rule_is_read_from_the_base_branch_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def rest(path: str) -> Any:
        seen.append(path)
        return [{"type": "pull_request"}, {"type": "merge_queue", "parameters": {}}]

    monkeypatch.setattr(ssm, "_gh_rest_json", rest)
    monkeypatch.delenv("L9_STACK_PROBE_FILE", raising=False)
    assert ssm.queue_rule(REPO, "main") == {"type": "merge_queue", "parameters": {}}
    assert seen == [f"repos/{REPO}/rules/branches/main"]
    monkeypatch.setattr(ssm, "_gh_rest_json", lambda path: [{"type": "pull_request"}])
    assert ssm.queue_rule(REPO, "main") is None


def test_run_on_a_queue_base_hands_the_pr_to_the_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = tmp_path / "probe.json"
    probe.write_text(
        json.dumps(
            {
                f"{REPO}#7": {
                    "head": "feat/x",
                    "children": [],
                    "base": "main",
                    "merge_queue": True,
                    "sha": A,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("L9_STACK_PROBE_FILE", str(probe))
    monkeypatch.setattr(
        ssm,
        "authorization_status",
        lambda repo, pr, sha, **_: {"status": "AUTHORIZED", "head_sha": A},
    )
    handed: list[Any] = []
    monkeypatch.setattr(
        ssm,
        "run_queue",
        lambda repo, items, **_: handed.append(items) or [{"status": "MERGED", "pr": 7}],
    )
    monkeypatch.setattr(
        ssm, "_execute", lambda *a, **k: pytest.fail("direct merge on a queue base")
    )
    assert ssm.main(["--repo", REPO, "--pr", "7", "--run", "--head-sha", A]) == 0
    assert handed == [[("7", A)]]


# -- enqueue ---------------------------------------------------------------


def test_the_whole_set_is_enqueued_in_the_given_order_and_watched_to_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHub(
        {
            "3": _green(A, script=[{"merged": True}]),
            "1": _green(B, script=[{"merged": True}]),
            "2": _green(C, script=[{"merged": True}]),
        }
    )
    fake.install(monkeypatch, tmp_path)
    outcomes = _run(fake, [("3", A), ("1", B), ("2", C)])
    assert [c for c in fake.calls if c[0] == "enqueue"] == [
        ("enqueue", "3"),
        ("enqueue", "1"),
        ("enqueue", "2"),
    ]
    assert [o["status"] for o in outcomes] == ["MERGED", "MERGED", "MERGED"]


@pytest.mark.parametrize(
    "state",
    [
        {"head": A, "granted": None, "board": "merge"},  # no authorization
        {"head": B, "granted": A, "board": "merge"},  # head moved since the grant
        {"head": A, "granted": A, "board": "fix"},  # not green
    ],
)
def test_ungranted_moved_or_red_heads_are_never_enqueued(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: dict[str, Any]
) -> None:
    fake = FakeGitHub({"5": state})
    fake.install(monkeypatch, tmp_path)
    [outcome] = _run(fake, [("5", A)])
    assert outcome["status"] == "MERGE_PENDING"
    assert fake.calls == []


def test_a_pr_that_does_not_enter_the_queue_at_once_is_disarmed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHub({"5": _green(A, enters_queue=False)})
    fake.install(monkeypatch, tmp_path)
    [outcome] = _run(fake, [("5", A)])
    assert outcome["status"] == "MERGE_PENDING"
    assert outcome["withdrawn"] is True
    assert fake.calls == [("enqueue", "5"), ("dequeue", "5"), ("disarm", "5")]
    assert fake.prs["5"]["armed"] is False


def test_unobservable_membership_is_disarmed_not_assumed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHub({"5": _green(A, enters_queue=None)})
    fake.install(monkeypatch, tmp_path)
    [outcome] = _run(fake, [("5", A)])
    assert outcome["status"] == "MERGE_PENDING"
    assert "could not be observed" in outcome["reason"]
    assert ("disarm", "5") in fake.calls
    assert outcome["withdrawn"] is True


def test_no_auto_merge_on_a_base_without_a_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHub({"5": _green(A)}, queue_base=False)
    fake.install(monkeypatch, tmp_path)
    [outcome] = _run(fake, [("5", A)])
    assert outcome["status"] == "MERGE_PENDING"
    assert "no merge_queue rule" in outcome["reason"]
    assert fake.calls == []


# -- watcher -----------------------------------------------------------------


def test_the_watcher_dequeues_a_moved_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGitHub({"5": _green(A, script=[{"head": B}])})
    fake.install(monkeypatch, tmp_path)
    [outcome] = _run(fake, [("5", A)])
    assert outcome["status"] == "MERGE_PENDING"
    assert outcome["moved_head"] == B
    assert ("dequeue", "5") in fake.calls
    assert fake.prs["5"]["queued"] is False


def test_a_failed_dequeue_is_an_unbound_entry_that_stops_the_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHub({"5": _green(A, sticky=True, script=[{"head": B}]), "6": _green(C)})
    fake.install(monkeypatch, tmp_path)
    [outcome] = _run(fake, [("5", A)])
    assert outcome["status"] == "UNBOUND_QUEUE_ENTRY"
    assert (outcome["granted_head"], outcome["moved_head"]) == (A, B)
    ledger = json.loads((tmp_path / ssm.UNBOUND_LEDGER_NAME).read_text(encoding="utf-8"))
    assert REPO in ledger

    calls_before = len(fake.calls)
    [blocked] = _run(fake, [("6", C)])
    assert blocked["status"] == "MERGE_PENDING"
    assert "unbound queue entry outstanding" in blocked["reason"]
    assert len(fake.calls) == calls_before

    # Once the entry is gone from the queue the repository is enqueueable again.
    fake.prs["5"]["queued"] = False
    fake.prs["6"]["script"] = [{"merged": True}]
    [freed] = _run(fake, [("6", C)])
    assert freed["status"] == "MERGED"


def test_an_ejected_pr_is_re_enqueued_once_green_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeGitHub({"5": _green(A, script=[{"queued": False}])})
    fake.install(monkeypatch, tmp_path)
    [ejected] = _run(fake, [("5", A)])
    assert ejected["status"] == "EJECTED"

    # Remediation pushes a fix; the same instruction covers the new head.
    fake.prs["5"].update(_green(B, script=[{"merged": True}]))
    [merged] = _run(fake, [("5", B)])
    assert merged["status"] == "MERGED"
    assert [c for c in fake.calls if c[0] == "enqueue"] == [("enqueue", "5"), ("enqueue", "5")]


def test_a_failed_disarm_is_unbound_and_stops_the_rest_of_the_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex P1: an entry that cannot be proven disarmed must fail closed."""
    fake = FakeGitHub(
        {"5": _green(A, enters_queue=False, disarm_fails=True, sticky=True), "6": _green(C)}
    )
    fake.install(monkeypatch, tmp_path)
    first, second = _run(fake, [("5", A), ("6", C)])
    assert first["status"] == "UNBOUND_QUEUE_ENTRY"
    assert second["status"] == "MERGE_PENDING"
    assert "earlier item is unbound" in second["reason"]
    assert ("enqueue", "6") not in fake.calls
    assert REPO in json.loads((tmp_path / ssm.UNBOUND_LEDGER_NAME).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("sticky", "status"), [(False, "MERGE_PENDING"), (True, "UNBOUND_QUEUE_ENTRY")]
)
def test_a_watcher_timeout_withdraws_the_entry_or_records_it_unbound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sticky: bool, status: str
) -> None:
    """Codex P1: no queue entry outlives its watcher."""
    fake = FakeGitHub({"5": _green(A, sticky=sticky)})
    fake.install(monkeypatch, tmp_path)
    ticks = iter([0.0, 0.0, 120.0, 120.0])
    [outcome] = ssm.run_queue(
        REPO, [("5", A)], poll=0, timeout=60, sleep=lambda _: None, clock=lambda: next(ticks)
    )
    assert outcome["status"] == status
    assert "timed out" in outcome["reason"]
    assert ("dequeue", "5") in fake.calls


def test_a_revoked_authorization_withdraws_a_queued_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex P1: the latest instruction wins, also after the enqueue."""
    fake = FakeGitHub({"5": _green(A, script=[{"granted": None}])})
    fake.install(monkeypatch, tmp_path)
    [outcome] = _run(fake, [("5", A)])
    assert outcome["status"] == "MERGE_PENDING"
    assert "authorization withdrawn while queued" in outcome["reason"]
    assert outcome["withdrawn"] is True
    assert ("dequeue", "5") in fake.calls


def test_queue_items_must_name_a_full_head() -> None:
    assert ssm.parse_items([f"12@{A}"]) == [("12", A)]
    with pytest.raises(ValueError):
        ssm.parse_items(["12@abc"])


# -- merge_gate ------------------------------------------------------------------


def _hook(command: str, env: dict[str, str]) -> str:
    base = {**os.environ, "L9_MERGE_AUTHORITY_MODE": "strict", **env}
    base.pop("L9_MERGE_AUTHORIZED", None)
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        text=True,
        capture_output=True,
        env=base,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _grant(tmp_path: Path, pr: int, sha: str) -> Path:
    import time

    path = tmp_path / "merge-authorization.json"
    entry = {
        "repo": REPO,
        "pr": pr,
        "head_sha": sha,
        "issuer": "human",
        "expires_at": time.time() + 3600,
    }
    path.write_text(json.dumps({"authorizations": [entry]}), encoding="utf-8")
    return path


def _no_reviews(tmp_path: Path) -> Path:
    path = tmp_path / "reviews.json"
    path.write_text("{}", encoding="utf-8")
    return path


QUEUE_CMD = "python3 ops/autonomy/stack_safe_merge.py --repo " + REPO + " --queue "


def test_gate_admits_a_queue_run_only_for_granted_heads(tmp_path: Path) -> None:
    env = {
        "L9_MERGE_AUTHORIZATION_FILE": str(_grant(tmp_path, 7, A)),
        "L9_MERGE_REVIEW_FILE": str(_no_reviews(tmp_path)),
    }
    assert _hook(QUEUE_CMD + f"7@{A}", env).strip() == ""
    denied = _hook(QUEUE_CMD + f"7@{A} 8@{B}", env)
    assert "deny" in denied and "8" in denied
    assert "deny" in _hook(QUEUE_CMD + f"7@{B}", env)


def test_gate_still_denies_ad_hoc_auto_merge(tmp_path: Path) -> None:
    env = {
        "L9_MERGE_AUTHORIZATION_FILE": str(_grant(tmp_path, 7, A)),
        "L9_MERGE_REVIEW_FILE": str(_no_reviews(tmp_path)),
    }
    out = _hook(f"gh api --method PUT repos/{REPO}/pulls/7/ccr/auto_merge", env)
    assert "auto-merge" in out
    assert "deny" in _hook(f"gh pr merge 7 --repo {REPO} --auto --merge", env)


def test_rest_membership_without_a_queue_event_stays_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub documents queue membership only over GraphQL; REST never guesses it."""
    monkeypatch.setattr(ssm, "_rest_only", lambda: True)
    pulls = {"head": {"sha": A}, "merged": False, "auto_merge": {"enabled_by": {}}}

    def rest(path: str) -> Any:
        if path.endswith("/timeline?per_page=100"):
            return timeline
        return pulls

    monkeypatch.setattr(ssm, "_gh_rest_json", rest)
    timeline: list[dict[str, Any]] = [{"event": "labeled"}]
    assert ssm.queue_state(REPO, "5")["queued"] is None
    timeline = [{"event": "added_to_merge_queue"}]
    assert ssm.queue_state(REPO, "5")["queued"] is True
    timeline = [{"event": "added_to_merge_queue"}, {"event": "removed_from_merge_queue"}]
    assert ssm.queue_state(REPO, "5")["queued"] is False
