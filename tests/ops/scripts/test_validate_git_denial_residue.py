"""The git-denial residue gate must catch the drift it exists to catch.

Presence-only coverage would be worthless here: the whole point is that this
gate fires on a sentence a human would read straight past.
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


def test_section_citation_alone_does_not_exempt(tmp_path: Path) -> None:
    """Citing §6.2.4 must not wash a still-false denial claim."""
    line = "`git push` is denied by the gate; see CANONICAL_LAW §6.2.4"
    assert _scan_line(tmp_path, line), f"section citation exempted a denial: {line}"


def test_repository_is_clean() -> None:
    """The tree this lands in must already satisfy the gate."""
    assert validator.scan(validator._candidates()) == []
