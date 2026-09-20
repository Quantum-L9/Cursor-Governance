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
import os
import re
import stat as statmod
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


def _parse_stage(stdout: str) -> list[tuple[str, str, str]]:
    """Parse ``git ls-files --stage -z`` into ``(mode, object, path)`` triples."""
    records: list[tuple[str, str, str]] = []
    for entry in stdout.split("\0"):
        if not entry:
            continue
        try:
            meta, path = entry.split("\t", 1)
        except ValueError:
            continue
        parts = meta.split(" ", 2)
        if len(parts) < 3:
            continue
        mode, obj, _stage = parts
        records.append((mode, obj, path))
    return records


def _worktree_git_mode(path: Path, *, index_mode: str | None) -> str:
    """Git-style mode for the worktree path, so chmod and gitlinks are visible."""
    if index_mode == "160000":
        return "160000"
    if path.is_symlink():
        return "120000"
    if path.is_file():
        return "100755" if path.stat().st_mode & statmod.S_IXUSR else "100644"
    return index_mode or "000000"


def _blob_digest(path: Path, *, git_mode: str, index_object: str | None) -> str:
    if git_mode == "160000":
        return index_object or ""
    if git_mode == "120000":
        return sha256_bytes(os.fsencode(os.readlink(path)))
    return sha256_file(path)


def tree_digest(root: Path) -> str:
    """Digest the working tree's tracked and untracked-not-ignored content.

    Returns a hex sha256 over sorted
    ``<path>\\0<membership>\\0<mode>\\0<blob-sha>\\n`` records. Membership is
    ``tracked`` or ``untracked`` and mode is the git-style worktree mode
    (``100644`` / ``100755`` / ``120000`` / ``160000``), so a ``git rm
    --cached`` that leaves the same bytes, a chmod that flips the executable
    bit, and a gitlink are each a different tree from the one that was
    attested. Path+bytes alone cannot see those: the set-union of ``ls-files``
    and ``ls-files --others`` collapsed index membership, which is how an
    authorize-release receipt stayed valid after a later commit deleted a
    still-on-disk file.

    Content and location stay bound: a rename that preserves content changes
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
    staged = _git(root, "ls-files", "--stage", "-z")
    others = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if staged.returncode != 0 or others.returncode != 0:
        detail = (staged.stderr or others.stderr or "").strip()
        raise RuntimeError(f"tree_digest: git could not list {root}: {detail or 'unknown error'}")
    records: list[tuple[str, str, str, str]] = []
    for mode, obj, rel in _parse_stage(staged.stdout):
        if rel.startswith(DIGEST_EXCLUDED_PREFIXES):
            continue
        path = root / rel
        git_mode = _worktree_git_mode(path, index_mode=mode)
        if git_mode == "160000":
            records.append((rel, "tracked", git_mode, obj))
            continue
        if not os.path.lexists(path):
            # A tracked path deleted in the worktree has no blob to hash. Its
            # absence is itself the change, and it is already visible: the
            # path drops out of the record set, so the digest moves.
            # lexists, not Path.exists(): exists() follows the target, so a
            # broken symlink looks deleted and would drop out of the digest
            # even though mode 120000 and readlink hashing already exist.
            continue
        try:
            blob = _blob_digest(path, git_mode=git_mode, index_object=obj)
        except OSError as exc:
            raise RuntimeError(f"tree_digest: cannot read {rel} under {root}: {exc}") from exc
        records.append((rel, "tracked", git_mode, blob))
    for rel in others.stdout.split("\0"):
        if not rel or rel.startswith(DIGEST_EXCLUDED_PREFIXES):
            continue
        path = root / rel
        if not path.is_file() and not path.is_symlink():
            continue
        git_mode = _worktree_git_mode(path, index_mode=None)
        try:
            blob = _blob_digest(path, git_mode=git_mode, index_object=None)
        except OSError as exc:
            raise RuntimeError(f"tree_digest: cannot read {rel} under {root}: {exc}") from exc
        records.append((rel, "untracked", git_mode, blob))
    if not records:
        # An empty repository is a real state with a real (empty) digest. It is
        # distinguishable from failure because git exited 0 above.
        return sha256_text("")
    acc = hashlib.sha256()
    for rel, membership, git_mode, blob in sorted(records):
        acc.update(rel.encode("utf-8"))
        acc.update(b"\0")
        acc.update(membership.encode("ascii"))
        acc.update(b"\0")
        acc.update(git_mode.encode("ascii"))
        acc.update(b"\0")
        acc.update(blob.encode("ascii"))
        acc.update(b"\n")
    return acc.hexdigest()
