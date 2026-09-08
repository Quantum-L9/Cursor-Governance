"""Does this search receipt describe the search Cursor actually asked for?

Audit MEM-P2-01, consumer half. A ``SearchReceipt`` binds the query and the
namespaces memory authorized. It does not bind the **tag selector**, and tags
materially change the result set: the same query under different tags returns
different records. A receipt that records only query and hits therefore cannot
independently prove which request produced them.

The fix for that is memory's — it owns the receipt contract, and closing
MEM-P2-01 means the service binding every result-affecting selector into the
authoritative receipt (a ``request_digest`` over the canonical normalized
request). This module is the other end of that: what Cursor may check today,
and what it must refuse to assume.

Two rules, and the difference between them matters:

- A selector the receipt **does** echo must agree with what Cursor sent.
  Disagreement means the receipt describes a different search, and the hits are
  not answers to this question.
- A result-affecting selector the receipt does **not** echo is *unbound*, and
  unbound is recorded rather than assumed. Cursor never treats "memory did not
  say" as "memory agreed".

Deliberately absent: any attempt to recompute memory's own ``request_digest``.
Cursor would have to guess the canonicalization — field order, tag ordering,
absent-versus-empty — and a guess that disagrees is worse than no check at all,
because it turns every honest receipt into a rejection. Cursor computes its own
digest for its own evidence, compares memory's digest only against memory's
digest across calls, and leaves the canonical algorithm where it belongs.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: Selectors that change which records come back. Anything here that a receipt
#: cannot bind is a gap in the evidence, not a detail.
RESULT_AFFECTING_SELECTORS = ("query", "namespaces", "tags", "limit", "memory_classes")

#: Version of *Cursor's* normalization, stamped into its own digest so a change
#: to it can never be mistaken for a change in the request.
CURSOR_CANONICALIZATION = "cursor.search-request/v1"

#: Turns an unbound result-affecting selector from "recorded" into "refused".
ENV_REQUIRE_SEARCH_IDENTITY = "L9_MEMORY_REQUIRE_SEARCH_IDENTITY"

_TRUE = frozenset({"1", "true", "yes", "on"})


def require_search_identity(env: Mapping[str, str] | None = None) -> bool:
    environment = os.environ if env is None else env
    return str(environment.get(ENV_REQUIRE_SEARCH_IDENTITY, "")).strip().lower() in _TRUE


@dataclass(frozen=True)
class SearchRequest:
    """Exactly what Cursor asked for, normalized so it can be compared."""

    query: str
    namespaces: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    limit: int | None = None
    memory_classes: tuple[str, ...] = ()

    def canonical(self) -> dict[str, Any]:
        """Deterministic shape. Tags and classes are unordered *sets* — asking
        for ``(a, b)`` and ``(b, a)`` is the same search — while namespaces keep
        their order, since fan-in order is part of the request Cursor made."""

        return {
            "canonicalization": CURSOR_CANONICALIZATION,
            "query": self.query,
            "namespaces": list(self.namespaces),
            "tags": sorted(set(self.tags)),
            "limit": self.limit,
            "memory_classes": sorted(set(self.memory_classes)),
        }

    def digest(self) -> str:
        encoded = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RequestIdentityVerdict:
    """What the receipt proved about the request, and what it left open."""

    #: Selectors the receipt echoed and that agreed with the request.
    bound: tuple[str, ...] = ()
    #: Result-affecting selectors the receipt carries nothing about.
    unbound: tuple[str, ...] = ()
    #: Selectors the receipt echoed that *disagree* — the receipt is for another search.
    mismatched: tuple[str, ...] = ()
    #: Cursor's own digest of what it asked for (evidence, never compared to memory's).
    request_digest: str = ""
    #: Memory's digest when it emits one; comparable only against itself.
    receipt_request_digest: str | None = None
    detail: tuple[str, ...] = field(default=())

    @property
    def contradicted(self) -> bool:
        return bool(self.mismatched)

    @property
    def fully_bound(self) -> bool:
        return not self.unbound and not self.mismatched


def verify_request_identity(
    request: SearchRequest, receipt: Any, *, requested_namespaces: Sequence[str] = ()
) -> RequestIdentityVerdict:
    """Compare a search receipt against the request it should answer."""

    raw = getattr(receipt, "raw", None)
    raw = raw if isinstance(raw, dict) else {}
    bound: list[str] = []
    unbound: list[str] = []
    mismatched: list[str] = []
    detail: list[str] = []

    # query — always echoed by the canonical receipt.
    echoed_query = getattr(receipt, "query", None)
    if echoed_query is None:
        unbound.append("query")
    elif str(echoed_query) != request.query:
        mismatched.append("query")
        detail.append(f"receipt answers query {echoed_query!r}, not {request.query!r}")
    else:
        bound.append("query")

    # namespaces — the receipt reports what memory *authorized*, which is
    # legitimately a subset of what Cursor requested (memory owns that
    # decision, INV-07). Only a namespace Cursor never asked for is a
    # contradiction; a narrower set is memory doing its job.
    authorized = tuple(str(v) for v in (getattr(receipt, "namespaces_authorized", ()) or ()))
    asked = {str(v) for v in (requested_namespaces or request.namespaces)}
    if not authorized:
        unbound.append("namespaces")
    else:
        unrequested = [ns for ns in authorized if asked and ns not in asked]
        if unrequested:
            mismatched.append("namespaces")
            detail.append(f"receipt authorizes namespaces Cursor did not request: {unrequested}")
        else:
            bound.append("namespaces")

    # tags / limit / memory_classes — MEM-P2-01: memory does not bind these
    # today. Read them when it does; record the gap when it does not.
    for selector, requested in (
        ("tags", sorted(set(request.tags))),
        ("memory_classes", sorted(set(request.memory_classes))),
    ):
        echoed = raw.get(selector)
        if echoed is None:
            unbound.append(selector)
            continue
        if sorted({str(v) for v in echoed}) != requested:
            mismatched.append(selector)
            detail.append(f"receipt {selector} {sorted(echoed)} != requested {requested}")
        else:
            bound.append(selector)

    echoed_limit = raw.get("limit")
    if echoed_limit is None:
        unbound.append("limit")
    elif request.limit is not None and int(echoed_limit) != int(request.limit):
        mismatched.append("limit")
        detail.append(f"receipt limit {echoed_limit} != requested {request.limit}")
    else:
        bound.append("limit")

    receipt_digest = raw.get("request_digest")
    if receipt_digest is None:
        detail.append(
            "the receipt carries no request_digest, so the request identity rests on the "
            "selectors it echoes individually (MEM-P2-01 is memory-side and open)"
        )

    return RequestIdentityVerdict(
        bound=tuple(bound),
        unbound=tuple(unbound),
        mismatched=tuple(mismatched),
        request_digest=request.digest(),
        receipt_request_digest=None if receipt_digest is None else str(receipt_digest),
        detail=tuple(detail),
    )


__all__ = [
    "CURSOR_CANONICALIZATION",
    "ENV_REQUIRE_SEARCH_IDENTITY",
    "RESULT_AFFECTING_SELECTORS",
    "RequestIdentityVerdict",
    "SearchRequest",
    "require_search_identity",
    "verify_request_identity",
]
