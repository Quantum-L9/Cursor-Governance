"""Canonical Program Execution Blueprint identity.

Authority: ADR-0026; ``MISSION_PROGRAM_BINDING_CONTRACT``.

One Blueprint identity implementation for the whole Program Execution layer.
It is provider-neutral and lives under ``core/shared`` deliberately: Mission,
the compiler, and any later consumer must agree byte-for-byte on what
``blueprint_digest`` means, and two implementations would eventually disagree.

The canonical input is the **exact bytes** of the Blueprint's final
``MANIFEST.yaml``::

    blueprint_digest = lowercase_hex(SHA-256(MANIFEST.yaml bytes))

``MANIFEST.yaml`` is already the canonical inventory of every other Blueprint
file and its SHA-256 (written by the official template manifest writer,
``core/program-execution-blueprint-template/scripts/instantiate.py``), so
hashing its bytes covers the whole Blueprint through exactly one owner. This
module never forks that inventory.

Two properties are load-bearing and are the reason this is not a one-line
``sha256sum``:

*Exactness.* The bytes are hashed as they are on disk. Parsing the YAML,
sorting keys, or reserializing would let two different files map to one
identity, and a binding that names ``blueprint_digest`` would then no longer
name an exact Blueprint.

*Acyclicity.* The digest is computed only after the official Blueprint
validator reports the instantiated Blueprint valid, and the Mission Program
Binding that references the digest is written **outside** the Blueprint root.
A binding stored inside the Blueprint would put ``blueprint_digest`` inside the
content that digest covers.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

#: The single file whose exact bytes are Blueprint identity.
MANIFEST_FILENAME = "MANIFEST.yaml"

#: Identity algorithm. Named so callers assert on it rather than assume it.
DIGEST_ALGORITHM = "sha256"

#: Canonical representation: lowercase hexadecimal, 64 characters.
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")


class BlueprintIdentityError(ValueError):
    """Blueprint identity could not be computed from an exact manifest."""


def manifest_path(blueprint_root: Path) -> Path:
    """The canonical identity input for ``blueprint_root``."""
    return Path(blueprint_root) / MANIFEST_FILENAME


def read_manifest_bytes(blueprint_root: Path) -> bytes:
    """Exact ``MANIFEST.yaml`` bytes, or fail closed.

    A missing manifest, a directory, or a symlink-to-nowhere is not "an empty
    Blueprint": it is an unidentifiable one. Returning a digest for it would
    hand a caller a well-formed identity for a Blueprint that does not exist.
    """
    path = manifest_path(blueprint_root)
    if not path.exists():
        raise BlueprintIdentityError(f"no {MANIFEST_FILENAME} at {path}")
    if not path.is_file():
        raise BlueprintIdentityError(f"{path} is not a regular file")
    try:
        return path.read_bytes()
    except OSError as exc:  # unreadable manifest is also an unidentifiable Blueprint
        raise BlueprintIdentityError(f"cannot read {path}: {exc}") from exc


def compute_blueprint_digest(blueprint_root: Path) -> str:
    """Lowercase SHA-256 over the exact bytes of the Blueprint's manifest.

    No parsing, no YAML normalization, no key sorting, no reserialization.
    """
    # hashlib.new(DIGEST_ALGORITHM), not hashlib.sha256: the constant the law
    # file and callers assert on is then the algorithm that actually runs.
    return hashlib.new(DIGEST_ALGORITHM, read_manifest_bytes(blueprint_root)).hexdigest()


def is_canonical_digest(value: str) -> bool:
    """True for the canonical 64-character lowercase hexadecimal form."""
    return bool(DIGEST_RE.match(value or ""))


__all__ = [
    "DIGEST_ALGORITHM",
    "DIGEST_RE",
    "MANIFEST_FILENAME",
    "BlueprintIdentityError",
    "compute_blueprint_digest",
    "is_canonical_digest",
    "manifest_path",
    "read_manifest_bytes",
]
