"""The git-denial residue gate must catch the drift it exists to catch.

Presence-only coverage would be worthless here: the whole point is that this
gate fires on a sentence a human would read straight past.

It must also FINISH. The gate once hung for minutes on a repository it was only
ever going to clear: its units are whole paragraphs, a generated manifest is one
50k-character paragraph with no blank line in it, and DENIAL_CLAIM is a pair of
zero-width lookaheads that `search` retried from every one of those offsets. A
validator that takes minutes is a validator someone deletes from pre-commit, so
the linear-time property is part of the contract, not a nicety.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "ops" / "scripts" / "validate_git_denial_residue.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_git_denial_residue", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load()


def _scan_line(tmp_path: Path, line: str) -> list[str]:
    path = tmp_path / "doctrine.md"
    path.write_text(f"# Doctrine\n\n{line}\n", encoding="utf-8")
    # scan() reports paths relative to ROOT; point it at the fixture instead.
    original = validator.ROOT
    validator.ROOT = tmp_path
    try:
        return validator.scan([path])
    finally:
        validator.ROOT = original


@pytest.mark.parametrize(
    "line",
    [
        "Raw `git push` / `gh pr create` are denied everywhere else.",
        "Raw `git push` is denied by ops/autonomy/local_execution_gate.py.",
        "mid-execution `git push` / `gh pr create` denied until authorize-release",
        "`gh pr edit` is blocked at every phase.",
        "A raw git push remains denied by the gate.",
    ],
)
def test_denial_claims_are_caught(tmp_path: Path, line: str) -> None:
    assert _scan_line(tmp_path, line), f"gate missed a denial claim: {line}"


@pytest.mark.parametrize(
    "line",
    [
        # The corrected phrasings this remediation introduced.
        "Raw `git push` is NOT denied by ops/autonomy/local_execution_gate.py.",
        "`git push` / `gh pr create` are off doctrine but not mechanically denied.",
        "git and gh are no longer denied; see CANONICAL_LAW §6.2.4.",
        "Where a push IS denied and the message names `make pr`, switch once.",
        # A skill's own discipline: true, self-imposed, names no mechanism.
        "NEVER: raw git push when Makefile pr exists",
        "Never raw `git push`. Publish is `PR_REMEDIATE=0 make pr`.",
        # Denials that are real and must stay sayable.
        "`make push` is denied at every phase.",
        "mcp__github__create_pull_request is denied regardless of L4 phase.",
    ],
)
def test_truthful_and_self_imposed_lines_pass(tmp_path: Path, line: str) -> None:
    assert _scan_line(tmp_path, line) == [], f"gate false-positived on: {line}"


def test_wrapped_denial_across_lines_is_caught(tmp_path: Path) -> None:
    """Markdown wrap must not hide a command + denial split across lines."""
    path = tmp_path / "doctrine.md"
    path.write_text(
        "# Doctrine\n\nRaw `git push` / `gh pr create` are\ndenied at every phase.\n",
        encoding="utf-8",
    )
    original = validator.ROOT
    validator.ROOT = tmp_path
    try:
        hits = validator.scan([path])
    finally:
        validator.ROOT = original
    assert hits, "wrapped denial claim was missed"


def test_denial_verb_must_attach_to_the_command(tmp_path: Path) -> None:
    """A paragraph is the unit for locating a claim, not for asserting one.

    This shape is live in AGENTS.md: a bullet states the remediator publishes
    with `git push`, and a later bullet says a *merge* can be blocked by
    required checks. Neither sentence claims push is denied.
    """
    path = tmp_path / "doctrine.md"
    path.write_text(
        "# Doctrine\n\n"
        "- Publish is `git push` of the already-open PR branch. Pathspecs only.\n"
        "- Do not poll CI after push. If merge is blocked by required checks,\n"
        "  record the blocker.\n",
        encoding="utf-8",
    )
    original = validator.ROOT
    validator.ROOT = tmp_path
    try:
        hits = validator.scan([path])
    finally:
        validator.ROOT = original
    assert hits == [], f"unrelated 'blocked' in the same paragraph flagged: {hits}"


def test_section_citation_alone_does_not_exempt(tmp_path: Path) -> None:
    """Citing §6.2.4 must not wash a still-false denial claim."""
    line = "`git push` is denied by the gate; see CANONICAL_LAW §6.2.4"
    assert _scan_line(tmp_path, line), f"section citation exempted a denial: {line}"


def test_repository_is_clean() -> None:
    """The tree this lands in must already satisfy the gate."""
    assert validator.scan(validator._candidates()) == []


# --- performance contract -------------------------------------------------


def test_denial_claim_is_linear_on_a_manifest_sized_unit() -> None:
    """A large single-line unit must not cost quadratic time."""
    import time

    unit = ("git push " + "x" * 200 + " ") * 250  # ~50k chars, no denial verb
    start = time.perf_counter()
    validator.DENIAL_CLAIM.search(unit)
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
    """Anchoring DENIAL_CLAIM at \\A must not change which units are claims."""
    assert bool(validator.DENIAL_CLAIM.search(unit)) is expected


def test_a_negated_claim_is_exonerated() -> None:
    unit = "`git push` is not denied by the gate"
    assert validator.DENIAL_CLAIM.search(unit)
    assert validator.ALLOW_LINE.search(unit)
