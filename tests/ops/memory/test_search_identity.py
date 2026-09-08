"""Does the search receipt answer the search Cursor made? (MEM-P2-01, consumer half)

The finding is memory-side: a ``SearchReceipt`` binds the query and the
namespaces memory authorized, and binds nothing about the **tag selector**,
which materially changes the result set. Memory closes it by binding every
result-affecting selector into the authoritative receipt.

These tests cover the other end — what Cursor may check today, and what it must
refuse to assume. Two properties, and the difference is the point:

- a selector the receipt *echoes* must agree, or the hits answer another
  question and are refused;
- a result-affecting selector the receipt *omits* is recorded as unbound and
  never assumed to have matched.
"""

from __future__ import annotations

from typing import Any

import pytest
from memory_boundary_fixtures import continuation_record, search_payload

from ops.memory import search_identity as si
from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.receipts import SearchReceipt

NAMESPACES = ("cursor-governance", "l9-workspace")


def _receipt(**overrides: Any) -> SearchReceipt:
    payload = search_payload(continuation_record())
    payload.update(overrides)
    return SearchReceipt.parse(payload)


def _request(**overrides: Any) -> si.SearchRequest:
    base: dict[str, Any] = {
        "query": "task",
        "namespaces": NAMESPACES,
        "tags": ("session_continuation",),
        "limit": 10,
    }
    base.update(overrides)
    return si.SearchRequest(**base)


# ---------------------------------------------------------------------------
# The request digest Cursor computes for its own evidence
# ---------------------------------------------------------------------------


def test_same_normalized_request_has_the_same_digest() -> None:
    assert _request().digest() == _request().digest()


def test_tag_order_does_not_change_the_request() -> None:
    """Tags are a set: asking for (a, b) and (b, a) is the same search."""
    left = _request(tags=("alpha", "beta"))
    right = _request(tags=("beta", "alpha"))
    assert left.digest() == right.digest()


def test_a_different_tag_is_a_different_request() -> None:
    assert _request(tags=("alpha",)).digest() != _request(tags=("beta",)).digest()


def test_absent_and_empty_tags_are_the_same_and_differ_from_a_tag() -> None:
    """Defined rather than accidental: no tag selector and an empty one both
    mean 'unfiltered', and neither equals a request that filters."""
    assert (
        _request(tags=()).digest()
        == si.SearchRequest(query="task", namespaces=NAMESPACES, limit=10).digest()
    )
    assert _request(tags=()).digest() != _request(tags=("x",)).digest()


def test_namespace_order_is_part_of_the_request() -> None:
    """Unlike tags, fan-in order is something Cursor asked for."""
    assert _request(namespaces=("a", "b")).digest() != _request(namespaces=("b", "a")).digest()


def test_limit_and_memory_classes_change_the_request() -> None:
    assert _request(limit=10).digest() != _request(limit=50).digest()
    assert _request().digest() != _request(memory_classes=("semantic",)).digest()


def test_the_digest_is_stamped_with_cursors_own_canonicalization() -> None:
    """So a change to Cursor's normalization can never read as a changed request."""
    assert _request().canonical()["canonicalization"] == si.CURSOR_CANONICALIZATION


# ---------------------------------------------------------------------------
# Verification against a real receipt
# ---------------------------------------------------------------------------


def test_a_receipt_for_a_different_query_is_contradicted() -> None:
    verdict = si.verify_request_identity(_request(), _receipt(query="something else"))
    assert verdict.contradicted
    assert "query" in verdict.mismatched
    assert any("not 'task'" in d for d in verdict.detail)


def test_a_matching_query_binds() -> None:
    verdict = si.verify_request_identity(_request(), _receipt())
    assert not verdict.contradicted
    assert "query" in verdict.bound


def test_tags_are_unbound_today_and_recorded_as_such() -> None:
    """The live gap: memory echoes no tag selector, so the receipt cannot prove
    these hits came from the tags Cursor asked for."""
    verdict = si.verify_request_identity(_request(), _receipt())
    assert "tags" in verdict.unbound
    assert not verdict.fully_bound
    assert any("no request_digest" in d for d in verdict.detail)


def test_tags_bind_once_memory_echoes_them() -> None:
    """Pre-wired: when the memory-side fix lands, the check works with no
    further Cursor change."""
    verdict = si.verify_request_identity(
        _request(tags=("session_continuation",)),
        _receipt(tags=["session_continuation"]),
    )
    assert "tags" in verdict.bound
    assert not verdict.contradicted


def test_a_different_tag_selector_is_contradicted_once_echoed() -> None:
    verdict = si.verify_request_identity(
        _request(tags=("session_continuation",)), _receipt(tags=["something_else"])
    )
    assert verdict.contradicted and "tags" in verdict.mismatched


def test_a_narrower_authorized_namespace_set_is_not_a_contradiction() -> None:
    """Memory authorizes; Cursor requests. A subset is memory doing its job,
    and treating it as a mismatch would make Cursor an authorization authority."""
    verdict = si.verify_request_identity(
        _request(), _receipt(namespaces_authorized=["cursor-governance"])
    )
    assert not verdict.contradicted
    assert "namespaces" in verdict.bound


def test_a_namespace_cursor_never_requested_is_a_contradiction() -> None:
    verdict = si.verify_request_identity(
        _request(), _receipt(namespaces_authorized=["cursor-governance", "someone-elses-repo"])
    )
    assert verdict.contradicted and "namespaces" in verdict.mismatched
    assert any("someone-elses-repo" in d for d in verdict.detail)


def test_memory_s_own_digest_is_carried_not_recomputed() -> None:
    """Cursor never guesses memory's canonicalization: it reports the digest
    memory emitted and compares it only against memory's own."""
    verdict = si.verify_request_identity(_request(), _receipt(request_digest="a" * 64))
    assert verdict.receipt_request_digest == "a" * 64
    assert verdict.request_digest != "a" * 64


# ---------------------------------------------------------------------------
# The live client path
# ---------------------------------------------------------------------------


def _search(client: MemoryControlPlaneClient, **kwargs: Any) -> Any:
    return client.search(
        kwargs.pop("query", "task"),
        workspace="/tmp",
        write_namespace_hint="cursor-governance",
        read_namespace_hints=NAMESPACES,
        **kwargs,
    )


def test_search_succeeds_and_records_the_unbound_selectors(bound, fake_cli) -> None:
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run, session_id="s")
    fake_cli.reply("search", 0, search_payload(continuation_record()))
    outcome = _search(client, tags=("session_continuation",))
    assert outcome.status is OutcomeStatus.OK
    assert "tags" in client._last_search_identity.unbound


def test_search_refuses_a_receipt_that_answers_another_query(bound, fake_cli) -> None:
    """The receipt is well-formed and canonical — and answers something else."""
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run, session_id="s")
    fake_cli.echo_search_query = False
    payload = search_payload(continuation_record())
    fake_cli.on("search", lambda _argv, _stdin: (0, {**payload, "query": "a different task"}, ""))
    outcome = _search(client)
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT
    assert "does not answer this request" in (outcome.error or "")


def test_required_identity_refuses_an_unbound_selector(bound, fake_cli, monkeypatch) -> None:
    client = MemoryControlPlaneClient(
        bound,
        runner=fake_cli.run,
        session_id="s",
        env={si.ENV_REQUIRE_SEARCH_IDENTITY: "1"},
    )
    fake_cli.reply("search", 0, search_payload(continuation_record()))
    outcome = _search(client, tags=("session_continuation",))
    assert outcome.status is OutcomeStatus.REQUEST_IDENTITY_UNPROVEN
    assert outcome.ok is False
    assert "cannot prove these hits answer this request" in (outcome.error or "")


def test_the_requirement_is_off_by_default(bound, fake_cli) -> None:
    """Cursor does not fail closed on a gap memory has not closed yet; it
    records it. The switch is for callers that need the stronger guarantee."""
    assert si.require_search_identity({}) is False
    assert si.require_search_identity({si.ENV_REQUIRE_SEARCH_IDENTITY: "1"}) is True


def test_contradiction_outranks_the_requirement(bound, fake_cli) -> None:
    """A receipt that is provably wrong is INVALID_RECEIPT, not merely unproven
    — the two verdicts must not collapse."""
    client = MemoryControlPlaneClient(
        bound,
        runner=fake_cli.run,
        session_id="s",
        env={si.ENV_REQUIRE_SEARCH_IDENTITY: "1"},
    )
    fake_cli.echo_search_query = False
    payload = search_payload(continuation_record())
    fake_cli.on("search", lambda _argv, _stdin: (0, {**payload, "query": "elsewhere"}, ""))
    assert _search(client).status is OutcomeStatus.INVALID_RECEIPT


@pytest.mark.parametrize("bad", [["nope"], "nope", 3])
def test_a_non_receipt_never_binds_anything(bad: Any) -> None:
    verdict = si.verify_request_identity(_request(), bad)
    assert set(si.RESULT_AFFECTING_SELECTORS) <= set(verdict.unbound) | set(verdict.mismatched)
