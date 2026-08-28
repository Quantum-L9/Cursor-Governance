"""Standing Cursor commit-before-stop contract (always-on)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_mutation_gate_is_always_on() -> None:
    text = (ROOT / "rules" / "99-no-auto-commit.mdc").read_text(encoding="utf-8")
    assert "alwaysApply: true" in text
    assert "Always apply. Always enabled. No ask." in text
    # Substring only: the rule renders the question in curly quotes, and
    # Prettier owns Markdown here, so asserting the typography would fail
    # on a formatter pass that changes no behaviour.
    assert "should I commit" in text
    assert "Stop with unique uncommitted files you wrote this session" in text
    assert "The filename is **historical**" in text


def test_global_rule_splits_commit_from_push() -> None:
    text = (ROOT / "rules" / "00-global.mdc").read_text(encoding="utf-8")
    assert "alwaysApply: true" in text
    assert "Scoped-commit authored pathspecs" in text
    assert "Leave unique dirty files you authored this session" in text
    assert "Commit/push without satisfying" not in text
