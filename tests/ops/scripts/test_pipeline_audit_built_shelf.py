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

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "skills" / "l9-pipeline-audit" / "scripts"))

from audit_pipeline import _built_shelf, archive_spent_plans  # noqa: E402


def _listing(directory: Path) -> set[str]:
    """Names as the filesystem reports them — the only casing git will see."""
    return {child.name for child in directory.iterdir()}


@pytest.fixture
def case_sensitive_fs(tmp_path: Path) -> bool:
    """Measure, do not assume: can two names differing only by case coexist here?

    APFS and NTFS default to case-insensitive, ext4 to case-sensitive; a
    macOS volume can be formatted either way. The probe is the truth for the
    volume `tmp_path` sits on, which is the one the tests write to.
    """
    probe = tmp_path / ".case-probe"
    probe.mkdir()
    (probe / "A").mkdir()
    try:
        (probe / "a").mkdir()
    except FileExistsError:
        return False
    return len(_listing(probe)) == 2


BUILT_PLAN = """---
name: spent
todos:
  - id: t1
    content: done
    status: completed
---

# spent plan
"""


def test_tracked_BUILT_wins_when_present(tmp_path: Path, case_sensitive_fs: bool) -> None:
    if not case_sensitive_fs:
        # The discriminator — `BUILT/` and `built/` as two directories — cannot
        # be constructed on this volume; the second mkdir is FileExistsError.
        # The Linux-only regression this pins is covered where it can exist
        # (CI containers). Owner: skills/l9-pipeline-audit. Remove if the
        # shelver stops resolving by directory listing.
        pytest.skip("case-insensitive volume: BUILT/ and built/ are one directory")
    (tmp_path / "BUILT").mkdir()
    (tmp_path / "built").mkdir()
    assert _built_shelf(tmp_path).name == "BUILT"


def test_lowercase_is_honoured_only_when_BUILT_is_absent(tmp_path: Path) -> None:
    (tmp_path / "built").mkdir()
    # On every platform the answer is the spelling the filesystem reports. A
    # case-insensitive volume would also answer `is_dir()` for "BUILT", and
    # that spelling is exactly what must not leak back to a caller.
    assert _built_shelf(tmp_path).name == "built"
    assert _built_shelf(tmp_path).name in _listing(tmp_path)


def test_shelf_spelling_is_always_the_on_disk_spelling(tmp_path: Path) -> None:
    """Property: the resolved shelf is a real listing entry, or BUILT when none is.

    This is the platform-independent form of the two tests above. Whatever the
    volume's casing rules, a path handed to `git add` must be spelled the way
    `readdir` will spell it back, or the tracked and on-disk trees split.
    """
    for index, spelling in enumerate(("BUILT", "built", "Built")):
        # Store names differ by more than case; the trap under test must not
        # also catch the test's own scaffolding.
        store = tmp_path / f"store-{index}"
        store.mkdir()
        (store / spelling).mkdir()
        resolved = _built_shelf(store)
        assert resolved.parent == store
        assert resolved.name in _listing(store), (spelling, resolved.name, _listing(store))
    empty = tmp_path / "s-empty"
    empty.mkdir()
    assert _built_shelf(empty).name == "BUILT"


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
    # `(tmp_path / "built").exists()` is true on a case-insensitive volume even
    # when only BUILT/ was ever created, so it cannot discriminate there. The
    # directory listing can, on every platform: a stray shelf is a second entry.
    assert "built" not in _listing(tmp_path), "no stray lowercase shelf may be created"
    assert _listing(tmp_path) == {"BUILT"}
