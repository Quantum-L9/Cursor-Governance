from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from autonomy.errors import PolicyViolation
from autonomy.runtime.store import RuntimeStore
from autonomy.runtime.timeutil import utc_now_text


def claims_collide(
    *,
    mode: str,
    exclusive: bool,
    other_mode: str,
    other_exclusive: bool,
) -> bool:
    """Whether two claims on *overlapping* resource keys may not be held at once.

    Single source of truth for claim compatibility. The registry enforces it
    transactionally, the scheduler pre-filters admission with it, and the graph
    linter uses it to tell a real ordering constraint from a serialization-only
    dependency edge — all three must agree or the scheduler would offer work the
    registry then rejects.
    """

    return exclusive or other_exclusive or "write" in {mode, other_mode}


_GLOB_CHARS = ("*", "?", "[")
_PATH_PREFIX = "path:"


def _path_scope_segments(key: str) -> list[str] | None:
    """Parse a resource key as a repository-relative path scope.

    Returns the path segments, ``[]`` for a scope that covers the whole
    repository (ambiguous or deliberately broad — fail closed to broadest), or
    ``None`` when the key is an opaque identifier rather than a path scope.

    Classification rule (canonical): a key is path-scoped when it carries the
    explicit ``path:`` namespace, or when it contains no ``:`` at all — any
    colon-free key names repository content (``docs/x.md``, ``README.md``,
    ``src/**``). Every other namespaced key (``target-lineage:...``,
    ``repository:declared``) stays opaque and compares by exact equality.
    """

    raw = key.strip()
    if raw.startswith(_PATH_PREFIX):
        raw = raw[len(_PATH_PREFIX) :].strip()
    elif ":" in raw:
        return None
    if not raw or raw.startswith(("/", "~")) or raw.startswith("..") or "/../" in raw:
        # Empty, absolute, or escaping scopes are unparseable as repository
        # content: fail closed to the broadest possible scope.
        return []
    segments = [segment for segment in raw.split("/") if segment not in ("", ".")]
    if any(segment == ".." for segment in segments):
        return []
    return segments


def _segment_is_glob(segment: str) -> bool:
    return any(char in segment for char in _GLOB_CHARS)


def resource_keys_overlap(key_a: str, key_b: str) -> bool:
    """Canonical resource-key overlap rule for the claim plane.

    Opaque (namespaced) keys overlap only on exact equality. Path-scoped keys
    overlap when one scope can name content inside the other: the same file,
    a file inside a containing directory scope, or glob scopes whose literal
    prefixes do not diverge. Glob comparison is deliberately conservative —
    a glob segment is assumed to match — so uncertainty resolves toward
    conflict, never toward parallel mutation.
    """

    if key_a == key_b:
        return True
    segments_a = _path_scope_segments(key_a)
    segments_b = _path_scope_segments(key_b)
    if segments_a is None or segments_b is None:
        # At least one opaque key: only exact equality (handled above) overlaps.
        return False
    for segment_a, segment_b in zip(segments_a, segments_b, strict=False):
        if segment_a == "**" or segment_b == "**":
            return True
        if _segment_is_glob(segment_a) or _segment_is_glob(segment_b):
            # Conservative: a glob segment may match the other side's segment.
            continue
        if segment_a != segment_b:
            return False
    # One scope is a (segment-wise) prefix of the other: the shorter scope
    # contains the longer one (directory scope over descendant file), or the
    # scopes are glob-compatible along their whole shared length.
    return True


def claim_scopes_conflict(
    *,
    key: str,
    mode: str,
    exclusive: bool,
    other_key: str,
    other_mode: str,
    other_exclusive: bool,
) -> bool:
    """One primitive for scope-aware claim conflict.

    The scheduler prefilter, the transactional registry, and the graph linter
    must all call this — never a private approximation — so an admission the
    prefilter offers is exactly an admission the registry accepts.
    """

    if not resource_keys_overlap(key, other_key):
        return False
    return claims_collide(
        mode=mode,
        exclusive=exclusive,
        other_mode=other_mode,
        other_exclusive=other_exclusive,
    )


class ClaimRegistry:
    def __init__(self, store: RuntimeStore) -> None:
        self.store = store

    def assert_available(
        self,
        connection,
        *,
        campaign_id: str,
        claims: Sequence[Mapping[str, Any]],
    ) -> None:
        if not claims:
            return
        # Overlap is scope-aware, not exact-key: fetch every active claim in
        # the campaign and test each against the canonical overlap primitive.
        existing = list(
            connection.execute(
                """
                SELECT *
                FROM claims
                WHERE
                    campaign_id = ?
                    AND status = 'ACTIVE'
                """,
                (campaign_id,),
            )
        )
        for requested in claims:
            resource_key = str(requested["key"])
            requested_mode = str(requested["mode"])
            requested_exclusive = bool(
                requested.get(
                    "exclusive",
                    requested_mode == "write",
                )
            )
            for claim in existing:
                if claim_scopes_conflict(
                    key=resource_key,
                    mode=requested_mode,
                    exclusive=requested_exclusive,
                    other_key=str(claim["resource_key"]),
                    other_mode=str(claim["mode"]),
                    other_exclusive=bool(claim["exclusive"]),
                ):
                    raise PolicyViolation(
                        "CLAIM_CONFLICT: resource "
                        f"{resource_key!r} overlaps active claim "
                        f"{claim['resource_key']!r} held by "
                        f"action {claim['action_id']!r} "
                        f"under lease {claim['lease_id']!r}"
                    )

    def create_claims(
        self,
        connection,
        *,
        lease_id: str,
        campaign_id: str,
        action_id: str,
        claims: Sequence[Mapping[str, Any]],
    ) -> list[str]:
        self.assert_available(
            connection,
            campaign_id=campaign_id,
            claims=claims,
        )
        created: list[str] = []
        now = utc_now_text()
        for requested in claims:
            claim_id = f"claim-{uuid.uuid4().hex}"
            mode = str(requested["mode"])
            exclusive = bool(requested.get("exclusive", mode == "write"))
            connection.execute(
                """
                INSERT INTO claims (
                    claim_id,
                    lease_id,
                    campaign_id,
                    action_id,
                    resource_key,
                    mode,
                    exclusive,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                """,
                (
                    claim_id,
                    lease_id,
                    campaign_id,
                    action_id,
                    requested["key"],
                    mode,
                    int(exclusive),
                    now,
                ),
            )
            created.append(claim_id)
        return created

    def release_for_lease(
        self,
        connection,
        lease_id: str,
    ) -> int:
        return connection.execute(
            """
            UPDATE claims
            SET status = 'RELEASED', released_at = ?
            WHERE lease_id = ? AND status = 'ACTIVE'
            """,
            (utc_now_text(), lease_id),
        ).rowcount
