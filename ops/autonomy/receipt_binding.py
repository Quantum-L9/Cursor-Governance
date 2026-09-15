"""Canonicalize-then-digest, in one place.

Every receipt plane in this repository answers the same question: *what
artifact is this claim bound to, and does that artifact still hash to what
the receipt says?* Before this module the answer was implemented three
separate times, which is how a binding drifts: one copy learns that a
self-referential digest field has to be zeroed before hashing, and the other
two keep hashing a file that contains its own hash.

This module is a **library**. It writes no receipt, reads no receipt path,
and decides no policy — deliberately, because a digest helper that also
decided verdicts would become a fourth writer of the planes it serves
(CANONICAL_LAW §6.2.9 item 1). Callers own their schema, their thresholds,
and their failure text.

Planes served:

* ``ops/autonomy/kernel_predicates.py`` — the tree-kernel apply report's
  ``report_sha256``, via :func:`sha256_file`.
* ``ops/autonomy/l4_local.py`` — the L4 release receipt's ``tree_digest``,
  via :func:`tree_digest`.
* ``skills/l9-plan/scripts/validate_plan_kernel_receipt.py`` — a plan's
  ``kernel_pass.*.body_sha256``, via :func:`canonical_sha256`. That pack is
  copied into consumer repos, so it prefers this module and keeps a local
  fallback; ``tests/ops/autonomy/test_receipt_binding.py`` pins the two to
  identical output so the fallback cannot drift.

Not served, and not a fourth copy: ``_gate_state_digest`` in
``ops/scripts/run_pr_gate.sh``. It is shell-native, runs on the gate's
latency-sensitive fast path before any Python starts, and every caller
already reaches it through the single ``--print-state-digest`` seam. Its
receipts are keyed on that algorithm's output, so porting it here would
invalidate every local gate receipt to buy a seam that already exists.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Iterable
from functools import cache
from pathlib import Path

ZERO_DIGEST = "0" * 64

# A digest field inside the artifact it digests. Zeroed before hashing, so the
# recorded value is a function of the artifact's meaning rather than of a
# previous recording of itself.
SELF_DIGEST_FIELDS: tuple[str, ...] = ("body_sha256",)

# Receipt and scratch state. Excluded from tree_digest whether or not the
# workspace's .gitignore covers it — see tree_digest's docstring.
DIGEST_EXCLUDED_PREFIXES: tuple[str, ...] = (".l9/", ".git/")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    """Digest a file's exact bytes.

    No canonicalization: the apply report is attested as written, so a
    whitespace edit after recording is a real mismatch and must read as one.
    """
    return sha256_bytes(Path(path).read_bytes())


@cache
def _self_field_re(field: str) -> re.Pattern[str]:
    return re.compile(rf'({re.escape(field)}:\s*["\']?)([^"\'\s]+)(["\']?)')


def canonicalize(text: str, *, self_fields: Iterable[str] = SELF_DIGEST_FIELDS) -> str:
    """Zero out self-referential digest fields so the text can hash itself.

    A document carrying its own ``body_sha256`` cannot be hashed directly:
    writing the digest changes the bytes that produced it. Replacing those
    field values with 64 zeros makes the digest stable and recomputable by
    any reader, which is the whole point — the verifier re-derives.
    """
    out = text
    for field in self_fields:
        out = _self_field_re(field).sub(lambda m: f"{m.group(1)}{ZERO_DIGEST}{m.group(3)}", out)
    return out


def canonical_sha256(text: str, *, self_fields: Iterable[str] = SELF_DIGEST_FIELDS) -> str:
    return sha256_text(canonicalize(text, self_fields=self_fields))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def tree_digest(root: Path) -> str:
    """Digest the working tree's tracked and untracked-not-ignored content.

    Returns a hex sha256 over sorted ``<path>\\0<blob-sha>`` records, so both
    content and location are bound: a rename that preserves content changes
    the digest, and a commit that changes no bytes does not. That is the
    property the L4 release receipt needs and ``head_sha`` cannot provide —
    an amend or a rebase moves HEAD without touching the attested tree, and
    a receipt that goes stale for reasons unrelated to its subject teaches
    re-stamping on a schedule (CANONICAL_LAW §6.2.9).

    Ignored paths are excluded, and ``.l9/`` is excluded unconditionally on
    top of that. Without the second rule the primitive would be unusable for
    its main caller: writing the receipt would change the digest the receipt
    records, so an attestation would be stale the instant it was made. In
    this repository ``.l9/`` is gitignored and the two rules agree; the
    explicit one is what makes the property hold in a workspace whose
    ``.gitignore`` has not been wired yet.

    Raises:
        RuntimeError: when git cannot enumerate or hash the tree. An
            unreadable tree has no digest; returning a constant here would
            let one receipt authorize every tree git failed to read.
    """
    root = Path(root)
    listing = _git(root, "ls-files", "-z")
    others = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if listing.returncode != 0 or others.returncode != 0:
        detail = (listing.stderr or others.stderr or "").strip()
        raise RuntimeError(f"tree_digest: git could not list {root}: {detail or 'unknown error'}")
    listed = {p for p in (listing.stdout + others.stdout).split("\0") if p}
    # A tracked path deleted in the worktree has no blob to hash. Its absence is
    # itself the change, and it is already visible: the path drops out of the
    # record set, so the digest moves.
    paths = sorted(
        p for p in listed if not p.startswith(DIGEST_EXCLUDED_PREFIXES) and (root / p).is_file()
    )
    if not paths:
        # An empty repository is a real state with a real (empty) digest. It is
        # distinguishable from failure because git exited 0 above.
        return sha256_text("")
    # Content is hashed here rather than by `git hash-object --stdin-paths`,
    # which takes newline-delimited input and so cannot express a path
    # containing a newline. git enumerates (NUL-delimited, exact); we digest.
    acc = hashlib.sha256()
    for rel in paths:
        try:
            blob = sha256_file(root / rel)
        except OSError as exc:
            raise RuntimeError(f"tree_digest: cannot read {rel} under {root}: {exc}") from exc
        acc.update(rel.encode("utf-8"))
        acc.update(b"\0")
        acc.update(blob.encode("ascii"))
        acc.update(b"\n")
    return acc.hexdigest()
