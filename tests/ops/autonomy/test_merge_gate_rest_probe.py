"""Tests for the REST stack probe in ops/autonomy/merge_gate.py.

The probe answers "is this PR the base of an open PR?". It backs a fail-closed
gate: an unanswerable probe denies an ancestry-breaking merge, because squashing
a stack parent silently destroys the child's content.

Before the REST path existed the probe ran only over `gh pr view` / `gh pr list`,
both GraphQL-backed. On a session gateway that serves only a pinned set of
GraphQL operations every such call returns 403, so the gate denied every squash
merge it was asked about -- including provably safe leaf pull requests.

The three cases the improvement record requires:

  * 403-fallback  -- one transport refused, the other answers
  * empty-children -- a leaf resolves to no children (squash stays allowed)
  * stacked-parent -- a parent resolves to its children (squash stays denied)

plus the invariant that matters most: when NO transport can answer, the probe
still raises and the caller still fails closed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import merge_gate as mg  # noqa: E402

GRAPHQL_403 = (
    "HTTP 403: This GraphQL query is not enabled for this session - only the "
    "pinned set of PR-review operations is served."
)


class _Transport:
    """Records the calls the probe makes and replays scripted answers."""

    def __init__(self, rest=None, cli=None):
        self.rest = rest
        self.cli = cli
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]):
        self.calls.append(list(args))
        handler = self.rest if args and args[0] == "api" else self.cli
        if handler is None:
            raise RuntimeError("no handler scripted for this transport")
        if isinstance(handler, Exception):
            raise handler
        return handler(args)


def _rest_repo(head: str, children: list[int]):
    def handler(args: list[str]):
        path = args[1]
        if "/pulls?" in path:
            return [{"number": n} for n in children]
        return {"head": {"ref": head}}

    return handler


@pytest.fixture(autouse=True)
def _no_probe_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """These exercise the live transports, not the injected probe file."""
    monkeypatch.delenv("L9_STACK_PROBE_FILE", raising=False)


# --- 403 fallback -------------------------------------------------------------


def test_rest_answers_when_graphql_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The case that broke every merge: GraphQL 403, REST fine."""
    transport = _Transport(
        rest=_rest_repo("feature/a", [77]),
        cli=RuntimeError(GRAPHQL_403),
    )
    monkeypatch.setattr(mg, "_gh_json", transport)
    head, children = mg._stacked_children("Quantum-L9/x", "12")
    assert head == "feature/a"
    assert children == [77]
    # REST is tried first, so the refused transport is never reached at all.
    assert all(c[0] == "api" for c in transport.calls)


def test_gh_pr_answers_when_rest_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reverse surface still gets an answer -- the fallback is real."""

    def cli(args: list[str]):
        if args[1] == "view":
            return {"headRefName": "feature/b"}
        return [{"number": 88}]

    transport = _Transport(rest=RuntimeError("HTTP 403 Forbidden"), cli=cli)
    monkeypatch.setattr(mg, "_gh_json", transport)
    head, children = mg._stacked_children("Quantum-L9/x", "12")
    assert head == "feature/b"
    assert children == [88]


def test_both_transports_refused_still_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Widening HOW the question is answered must not change what happens when it cannot be."""
    transport = _Transport(rest=RuntimeError(GRAPHQL_403), cli=RuntimeError(GRAPHQL_403))
    monkeypatch.setattr(mg, "_gh_json", transport)
    with pytest.raises(mg.ProbeError) as excinfo:
        mg._stacked_children("Quantum-L9/x", "12")
    assert excinfo.value.kind == "transport_blocked"


def test_one_blocked_transport_plus_a_real_error_is_not_a_transport_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reporting this as 'transport blocked' would send the operator to the wrong remedy."""
    transport = _Transport(
        rest=RuntimeError("HTTP 404: Not Found"),
        cli=RuntimeError(GRAPHQL_403),
    )
    monkeypatch.setattr(mg, "_gh_json", transport)
    with pytest.raises(mg.ProbeError) as excinfo:
        mg._stacked_children("Quantum-L9/x", "12")
    assert excinfo.value.kind != "transport_blocked"


# --- empty children (leaf) ----------------------------------------------------


def test_leaf_resolves_to_no_children(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _Transport(rest=_rest_repo("feature/leaf", []))
    monkeypatch.setattr(mg, "_gh_json", transport)
    head, children = mg._stacked_children("Quantum-L9/x", "12")
    assert head == "feature/leaf"
    assert children == []


def test_squash_of_a_leaf_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The regression this whole record exists to remove."""
    monkeypatch.setattr(mg, "_gh_json", _Transport(rest=_rest_repo("feature/leaf", [])))
    reason = mg._stack_safety_reason(
        "gh pr merge 12 --repo Quantum-L9/x --squash",
        "Bash",
        {"command": "gh pr merge 12 --repo Quantum-L9/x --squash"},
    )
    assert reason is None


def test_a_pr_is_never_its_own_child(monkeypatch: pytest.MonkeyPatch) -> None:
    """A self-referencing listing must not make a leaf look stacked."""
    monkeypatch.setattr(mg, "_gh_json", _Transport(rest=_rest_repo("feature/self", [12])))
    _, children = mg._stacked_children("Quantum-L9/x", "12")
    assert children == []


# --- stacked parent -----------------------------------------------------------


def test_parent_resolves_to_its_children(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mg, "_gh_json", _Transport(rest=_rest_repo("feature/parent", [20, 21])))
    head, children = mg._stacked_children("Quantum-L9/x", "12")
    assert head == "feature/parent"
    assert children == [20, 21]


def test_squash_of_a_stack_parent_is_still_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """The safety property. A REST answer must deny exactly as a GraphQL answer did."""
    monkeypatch.setattr(mg, "_gh_json", _Transport(rest=_rest_repo("feature/parent", [20])))
    reason = mg._stack_safety_reason(
        "gh pr merge 12 --repo Quantum-L9/x --squash",
        "Bash",
        {"command": "gh pr merge 12 --repo Quantum-L9/x --squash"},
    )
    assert reason is not None
    assert "20" in reason


def test_merge_commit_of_a_stack_parent_stays_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """--merge preserves the child's ancestry, so it was never the risky method."""
    monkeypatch.setattr(mg, "_gh_json", _Transport(rest=_rest_repo("feature/parent", [20])))
    reason = mg._stack_safety_reason(
        "gh pr merge 12 --repo Quantum-L9/x --merge",
        "Bash",
        {"command": "gh pr merge 12 --repo Quantum-L9/x --merge"},
    )
    assert reason is None


# --- deny message names the obstacle -----------------------------------------


def test_blocked_transport_message_names_the_transport() -> None:
    reason = mg._stack_unknown_reason("12", "Quantum-L9/x", GRAPHQL_403, "transport_blocked")
    assert "refused by this session" in reason


def test_blocked_transport_message_does_not_advise_a_blocked_command() -> None:
    """The old message sent operators to `gh pr list`, refused by the same policy."""
    reason = mg._stack_unknown_reason("12", "Quantum-L9/x", GRAPHQL_403, "transport_blocked")
    assert "gh pr list" not in reason
    assert "gh api" in reason
    assert "repos/Quantum-L9/x/pulls" in reason


def test_an_ordinary_probe_failure_still_reads_as_unknown() -> None:
    reason = mg._stack_unknown_reason("12", "Quantum-L9/x", "boom", "probe_failed")
    assert "cannot determine whether" in reason


# --- the injected probe file still wins --------------------------------------


def test_probe_file_short_circuits_both_transports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Determinism offline and in tests must not regress."""
    probe = tmp_path / "probe.json"
    probe.write_text('{"default": {"head": "from/file", "children": [9]}}', encoding="utf-8")
    monkeypatch.setenv("L9_STACK_PROBE_FILE", str(probe))

    def explode(_args):
        raise AssertionError("no transport may be consulted when a probe file is set")

    monkeypatch.setattr(mg, "_gh_json", explode)
    head, children = mg._stacked_children("Quantum-L9/x", "12")
    assert head == "from/file"
    assert children == [9]
