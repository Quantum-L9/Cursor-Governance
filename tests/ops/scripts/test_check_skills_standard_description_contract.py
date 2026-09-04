"""Regression tests for live skill description enforcement."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "ops" / "scripts"
sys.path.insert(0, str(GATE))

from check_skills_standard import BODY_MAX, DESC_MAX, DESC_MIN, check_skills  # noqa: E402


def _skill(tmp_path: Path, description: str, *, body_lines: int = 1) -> Path:
    skill = tmp_path / "skills" / "l9-demo"
    skill.mkdir(parents=True)
    body = "\n".join(f"line {i}" for i in range(body_lines))
    (skill / "SKILL.md").write_text(
        f"---\nname: l9-demo\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return tmp_path


GOOD_DESC = (
    "validate reusable skill discovery metadata against the repository contract before "
    "publication. use when authoring or changing a live skill description so routing, "
    "trigger clauses, and discovery-budget behavior remain deterministic."
)


def test_compliant_description_is_not_an_error(tmp_path: Path) -> None:
    errs, warns, *_ = check_skills(_skill(tmp_path, GOOD_DESC))
    assert errs == []
    assert warns == []


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("x" * (DESC_MIN - 1), f"under {DESC_MIN}"),
        ("use when " + "x" * DESC_MAX, f"over {DESC_MAX}"),
        (GOOD_DESC.replace("use when", "invoked when"), "trigger clause"),
    ],
)
def test_description_contract_violations_are_errors(
    tmp_path: Path, description: str, expected: str
) -> None:
    errs, warns, *_ = check_skills(_skill(tmp_path, description))
    assert any(expected in error for error in errs), errs
    assert not any(expected in warning for warning in warns), warns


def test_body_length_remains_progressive_disclosure_warning(tmp_path: Path) -> None:
    errs, warns, *_ = check_skills(_skill(tmp_path, GOOD_DESC, body_lines=BODY_MAX + 1))
    assert errs == []
    assert any("progressive disclosure" in warning for warning in warns)
