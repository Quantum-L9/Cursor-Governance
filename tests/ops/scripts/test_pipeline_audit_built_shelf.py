"""Conformance: the plans shelver targets one shelf on every platform.

`archive_spent_plans` moved built plans into a hard-coded lowercase `built`.
That is the SAME directory as the tracked `BUILT/` on the case-insensitive
filesystem this repository is usually developed on, and a DIFFERENT one on
Linux, where the cloud containers run. There it created a stray untracked
`built/` beside the tracked shelf and moved committed plan files into it —
silently un-tracking them, and failing the plan gate on shelved plans that
carry no kernel receipt.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "skills" / "l9-pipeline-audit" / "scripts"))

from audit_pipeline import _built_shelf, archive_spent_plans  # noqa: E402

BUILT_PLAN = """---
name: spent
todos:
  - id: t1
    content: done
    status: completed
---

# spent plan
"""


def test_tracked_BUILT_wins_when_present(tmp_path: Path) -> None:
    (tmp_path / "BUILT").mkdir()
    (tmp_path / "built").mkdir()
    assert _built_shelf(tmp_path).name == "BUILT"


def test_lowercase_is_honoured_only_when_BUILT_is_absent(tmp_path: Path) -> None:
    (tmp_path / "built").mkdir()
    assert _built_shelf(tmp_path).name == "built"


def test_canonical_shelf_is_created_when_neither_exists(tmp_path: Path) -> None:
    assert _built_shelf(tmp_path).name == "BUILT"


def test_unreadable_store_still_resolves(tmp_path: Path, monkeypatch) -> None:
    def boom(_self):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "iterdir", boom)
    assert _built_shelf(tmp_path).name == "BUILT"


def test_this_repository_shelves_into_the_tracked_directory() -> None:
    plans = REPO_ROOT / "docs" / "plans"
    if not plans.is_dir():
        import pytest

        pytest.skip("no plans store in this checkout")
    assert _built_shelf(plans).name == "BUILT", (
        "a stray lowercase shelf must never win over the tracked one"
    )


def test_spent_plan_lands_in_the_tracked_shelf_not_a_stray_one(tmp_path: Path) -> None:
    """The behavioural regression: a committed plan must not leave tracking."""
    (tmp_path / "BUILT").mkdir()
    spent = tmp_path / "already_done_abcd1234.plan.md"
    spent.write_text(BUILT_PLAN, encoding="utf-8")

    moved = archive_spent_plans(tmp_path)

    assert not spent.exists(), "a spent plan should be shelved"
    assert (tmp_path / "BUILT" / spent.name).is_file(), moved
    assert not (tmp_path / "built").exists(), "no stray lowercase shelf may be created"
