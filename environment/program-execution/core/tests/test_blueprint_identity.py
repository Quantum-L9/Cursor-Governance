"""Canonical Blueprint identity: exact bytes, one owner, fail-closed (ADR-0026).

``blueprint_digest`` is what a Mission Program Binding pins. If it were
computed over a *parsed* manifest, two byte-different Blueprints could share an
identity and the binding would stop naming an exact Blueprint. These tests are
that law, executable.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PE_ROOT = ROOT.parent
TEMPLATE = ROOT / "program-execution-blueprint-template"
if str(ROOT / "shared") not in sys.path:
    sys.path.insert(0, str(ROOT / "shared"))
# APPEND, never insert(0): `scripts` is a top-level name Program Execution
# shares with the repository root (see peer_execution.imports.pe_script).
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))

from peer_execution.imports import load_module  # noqa: E402

# The official canonical manifest writer, bound by FILE LOCATION. `instantiate`
# is a basename both template `scripts/` directories define, so a bare import
# would resolve to whichever renderer was imported first in the process.
instantiate = load_module(TEMPLATE / "scripts" / "instantiate.py", "pe_blueprint_instantiate")

from blueprint_identity import (  # noqa: E402
    DIGEST_ALGORITHM,
    MANIFEST_FILENAME,
    BlueprintIdentityError,
    compute_blueprint_digest,
    is_canonical_digest,
    manifest_path,
)

MANIFEST_BYTES = b"schema: program-execution-blueprint.manifest.v2\nfiles: []\n"


def _blueprint(root: Path, manifest: bytes = MANIFEST_BYTES) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / MANIFEST_FILENAME).write_bytes(manifest)
    return root


def test_identity_is_deterministic_sha256_over_exact_manifest_bytes(tmp_path: Path) -> None:
    root = _blueprint(tmp_path / "bp")
    digest = compute_blueprint_digest(root)

    assert DIGEST_ALGORITHM == "sha256"
    assert digest == hashlib.sha256(MANIFEST_BYTES).hexdigest()
    assert digest == digest.lower()
    assert is_canonical_digest(digest)
    # Repeated computation over unchanged bytes is stable: identity, not a nonce.
    assert compute_blueprint_digest(root) == digest


def test_semantically_equal_but_byte_different_manifests_are_different_identities(
    tmp_path: Path,
) -> None:
    """The proof that nothing parses, sorts, or reserializes before hashing."""
    original = b"schema: m\nfiles:\n- path: a\n- path: b\n"
    reordered = b"files:\n- path: a\n- path: b\nschema: m\n"
    assert yaml.safe_load(original) == yaml.safe_load(reordered), "fixtures must parse equal"

    first = compute_blueprint_digest(_blueprint(tmp_path / "one", original))
    second = compute_blueprint_digest(_blueprint(tmp_path / "two", reordered))
    assert first != second

    # A single trailing byte is also a different Blueprint.
    third = compute_blueprint_digest(_blueprint(tmp_path / "three", original + b"\n"))
    assert third != first


def test_missing_manifest_fails_closed(tmp_path: Path) -> None:
    empty = tmp_path / "no-manifest"
    empty.mkdir()
    with pytest.raises(BlueprintIdentityError) as excinfo:
        compute_blueprint_digest(empty)
    assert MANIFEST_FILENAME in str(excinfo.value)


def test_non_regular_manifest_fails_closed(tmp_path: Path) -> None:
    """A directory named MANIFEST.yaml is not an empty Blueprint; it is no Blueprint."""
    root = tmp_path / "bad"
    manifest_path(root).mkdir(parents=True)
    with pytest.raises(BlueprintIdentityError) as excinfo:
        compute_blueprint_digest(root)
    assert "not a regular file" in str(excinfo.value)


def test_identity_matches_a_blueprint_written_by_the_canonical_manifest_writer(
    tmp_path: Path,
) -> None:
    """Compatibility with the one manifest owner, not a second inventory."""
    root = tmp_path / "instantiated"
    instantiate.render_tree(
        root,
        {
            "PROGRAM_NAME": "Identity Fixture",
            "PROGRAM_ID": "pe-identity-fixture",
            "PROGRAM_VERSION": "1.0.0",
            "PROGRAM_OWNER": "L9 architecture",
            "DATE": "2026-08-29T00:00:00Z",
        },
    )

    digest = compute_blueprint_digest(root)
    assert is_canonical_digest(digest)
    assert digest == hashlib.sha256(manifest_path(root).read_bytes()).hexdigest()

    # The manifest covers every other file, so a change anywhere in the
    # Blueprint reaches identity once the canonical writer runs again.
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    instantiate.write_manifest(root)
    assert compute_blueprint_digest(root) != digest
