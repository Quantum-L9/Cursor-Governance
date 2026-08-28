"""Regression suite for the git-denial residue gate.

The gate hung for minutes on a repository it was only ever going to clear. Its
units are whole paragraphs, and a generated manifest is one 50k-character
paragraph with no blank line in it; ``DENIAL_CLAIM`` is a pair of zero-width
lookaheads, so ``search`` retried the whole scan from every one of those 50k
offsets. A validator that takes minutes is a validator someone removes from
pre-commit, so the performance property is part of the contract.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "validate_git_denial_residue", ROOT / "ops" / "scripts" / "validate_git_denial_residue.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_denial_claim_is_linear_on_a_manifest_sized_unit() -> None:
    """A large single-line unit must not cost quadratic time."""
    unit = ("git push " + "x" * 200 + " ") * 250  # ~50k chars, no denial verb
    start = time.perf_counter()
    MOD.DENIAL_CLAIM.search(unit)
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize(
    "unit,expected",
    [
        ("`git push` is denied by the gate", True),
        ("`gh pr create` is blocked at every phase", True),
        ("`git push` is not denied; prefer `make pr`", True),
        ("`make pr` is the preferred route to GitHub", False),
        ("NEVER use a raw `git push`", False),
        ("squash/rebase denied for a stacked parent", False),
    ],
)
def test_denial_claim_detects_only_a_command_plus_a_denial_verb(unit: str, expected: bool) -> None:
    """Anchoring must not change which units are considered claims."""
    assert bool(MOD.DENIAL_CLAIM.search(unit)) is expected


def test_a_negated_claim_is_exonerated() -> None:
    unit = "`git push` is not denied by the gate"
    assert MOD.DENIAL_CLAIM.search(unit)
    assert MOD.ALLOW_LINE.search(unit)


def test_repository_is_clean() -> None:
    assert MOD.main() == 0
