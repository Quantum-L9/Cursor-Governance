"""Fail-closed operator-alignment consumer boundary.

Lane B's producer contract is not frozen. This module does not declare a view
schema, select a source, or project a view. It refuses unverified material.
Two role results are complete for this lane: Coding Agent confidentiality is
BLOCKED_PRIVACY, and Meta Planner with no admissible consumer is
BLOCKED_NO_CONSUMER.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

MISSING_RECEIPT = "MISSING_RECEIPT"
DIGEST_MISMATCH = "DIGEST_MISMATCH"
FORGED_VIEW = "FORGED_VIEW"
BLOCKED_PRIVACY = "BLOCKED_PRIVACY"
BLOCKED_NO_CONSUMER = "BLOCKED_NO_CONSUMER"

# Empty until a frozen producer contract names exact receipt bytes.
# Parsing a receipt would invent that contract.
ADMITTED_PRODUCER_RECEIPTS: frozenset[bytes] = frozenset()


def view_digest(view: bytes) -> str:
    """sha256 of the presented view bytes. Not a receipt schema."""
    return "sha256:" + hashlib.sha256(view).hexdigest()


def reject_unverified_view(*, receipt: Path | None, view: bytes, claimed_digest: str) -> str:
    """Refuse a view. Never returns a loaded view or a pass status.

    A missing receipt, a claimed digest that is not the view's sha256, and any
    view whose receipt is not an admitted producer emission are refused. The
    admitted set is empty while the producer contract is unfrozen, so a
    digest-matching hand-written view is FORGED_VIEW.
    """
    if receipt is None or not receipt.is_file():
        return MISSING_RECEIPT
    if claimed_digest != view_digest(view):
        return DIGEST_MISMATCH
    if not _origin_admitted(receipt):
        return FORGED_VIEW
    raise RuntimeError("PRODUCER_CONTRACT_UNFROZEN")


def _origin_admitted(receipt: Path) -> bool:
    if not ADMITTED_PRODUCER_RECEIPTS:
        return False
    return receipt.read_bytes() in ADMITTED_PRODUCER_RECEIPTS


def full_github_read_possible(github_root: Path) -> bool:
    """True when this actor can open a file under a .github checkout.

    Prefers strategy/ when that directory exists: that is the operator-owned
    tree a Coding Agent must not treat as cleared.
    """
    if not github_root.is_dir():
        return False
    strategy = github_root / "strategy"
    bases = (strategy, github_root) if strategy.is_dir() else (github_root,)
    for base in bases:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                with path.open("rb") as handle:
                    handle.read(1)
            except OSError:
                continue
            return True
    return False


def coding_agent_confidentiality(github_root: Path, *, claimed: str | None = None) -> str:
    """Complete confidentiality result for the Coding Agent.

    A claimed PASS while a full .github read is possible is refused. This
    function never returns PASS. An unreadable tree is not an ACL denial, so
    it is BLOCKED_PRIVACY as well.
    """
    if claimed == "PASS" and full_github_read_possible(github_root):
        return BLOCKED_PRIVACY
    return BLOCKED_PRIVACY


def meta_planner_status(*, consumer_path: Path | None = None) -> str:
    """Complete Meta Planner result: no admissible consumer exists.

    A file on disk, including a view stub, is not a consumer. The producer
    contract is not frozen, so nothing in this lane is admissible.
    """
    # A present file, including a view stub, is still not an admissible consumer.
    if consumer_path is not None and consumer_path.is_file():
        return BLOCKED_NO_CONSUMER
    return BLOCKED_NO_CONSUMER
