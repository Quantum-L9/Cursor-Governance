"""Tests for ops/scripts/check_skills_standard."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_skills_standard import check_skills  # noqa: E402


def _write_skill(root: Path, name: str, frontmatter: str, archived: bool = False) -> None:
    if archived:
        parent = root / "skills" / "_archived" / name
    else:
        parent = root / "skills" / name
    parent.mkdir(parents=True, exist_ok=True)
    (parent / "SKILL.md").write_text(
        f"---\n{frontmatter}---\n\n# {name}\n",
        encoding="utf-8",
    )


def test_folded_description_counts_full_text(tmp_path: Path) -> None:
    desc = (
        "bounded autonomy campaign SOP for Cursor — parallel non-dependent Tasks, "
        "background PR-poll subagents while main continues. use when user runs "
        "/autonomy or needs PR convergence while continuing other work."
    )
    _write_skill(
        tmp_path,
        "l9-bounded-autonomy",
        "name: l9-bounded-autonomy\n"
        "description: >-\n"
        f"  {desc}\n"
        "disable-model-invocation: true\n"
        "metadata:\n"
        "  skill_schema: 1\n",
    )
    errs, warns, live, arch, disc = check_skills(tmp_path)
    assert errs == []
    assert live == 1
    assert arch == 0
    assert disc == len(b"l9-bounded-autonomy") + len(desc.encode())
    assert not any("under 150" in w for w in warns)


def test_non_native_top_level_fails(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "l9-demo",
        "name: l9-demo\n"
        "description: demo skill used only in unit tests. use when checking the gate.\n"
        "skill_schema: 1\n",
    )
    errs, _warns, _live, _arch, _disc = check_skills(tmp_path)
    assert any("non-native top-level keys" in e for e in errs)


def test_archived_missing_flag_fails(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "l9-old",
        "name: l9-old\ndescription: deprecated — do not activate.\n",
        archived=True,
    )
    errs, _warns, _live, arch, _disc = check_skills(tmp_path)
    assert arch == 1
    assert any("disable-model-invocation" in e for e in errs)


def test_empty_paths_fails(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "l9-demo",
        "name: l9-demo\n"
        "description: demo skill used only in unit tests. use when checking the gate.\n"
        "paths: \n",
    )
    errs, _warns, _live, _arch, _disc = check_skills(tmp_path)
    assert any("empty `paths`" in e for e in errs)


def test_pack_test_fixtures_are_not_live_skills(tmp_path: Path) -> None:
    desc = (
        "demo skill used only in unit tests. use when checking the discovery "
        "gate and verifying nested fixture packs stay excluded from live inventory."
    )
    _write_skill(tmp_path, "l9-demo", f"name: l9-demo\ndescription: {desc}\n")

    fixture = tmp_path / "skills" / "l9-demo" / "tests" / "fixtures" / "repo" / "skills" / "l9-fake"
    fixture.mkdir(parents=True)
    (fixture / "SKILL.md").write_text(
        "---\nname: l9-fake\ndescription: fixture pack.\n---\n\n# l9-fake\n",
        encoding="utf-8",
    )

    errs, warns, live, _arch, disc = check_skills(tmp_path)
    assert errs == []
    assert live == 1
    assert disc == len(b"l9-demo") + len(desc.encode())
    assert not any("l9-fake" in w for w in warns)


DESC = (
    "activate governed L9 CI from the org seeder or l9-ci-core stamp. never invent "
    "ci.yml or biome.json. use when bootstrapping CI, activating l9-ci-core, adding "
    "Biome, or adding lint/test/type-check stages."
)


def test_paths_on_a_model_invocable_skill_is_an_error(tmp_path: Path) -> None:
    """The regression: `paths` does not rank a skill lower when the globs miss, it
    removes the entry from the listing until a matching file is in context. Seven
    skills declared auto_invoke carried one and were absent from every session
    roster (7/7 gated missing, 0/16 listed gated, measured 2026-08-30). The
    pre-existing check only rejected an EMPTY `paths`, so it passed all seven."""

    _write_skill(
        tmp_path,
        "l9-setting-up-ci",
        "name: l9-setting-up-ci\n"
        f"description: {DESC}\n"
        'paths: ".github/workflows/**, biome.json"\n'
        "metadata:\n  skill_schema: 1\n",
    )
    errs, _, _, _, _ = check_skills(tmp_path)
    assert any("hides it from the skill listing" in e for e in errs)


def test_paths_is_allowed_when_the_skill_is_explicitly_hidden(tmp_path: Path) -> None:
    """A genuinely file-triggered skill may keep `paths`, but must then also carry
    disable-model-invocation so no manifest claims automatic availability the
    frontmatter withholds."""

    _write_skill(
        tmp_path,
        "l9-python-tdd-with-uv",
        "name: l9-python-tdd-with-uv\n"
        f"description: {DESC}\n"
        'paths: "**/*.py, pyproject.toml"\n'
        "disable-model-invocation: true\n"
        "metadata:\n  skill_schema: 1\n",
    )
    errs, _, _, _, _ = check_skills(tmp_path)
    assert not any("hides it from the skill listing" in e for e in errs)


def test_empty_paths_still_rejected_separately(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "l9-empty-paths",
        f"name: l9-empty-paths\ndescription: {DESC}\npaths: ''\nmetadata:\n  skill_schema: 1\n",
    )
    errs, _, _, _, _ = check_skills(tmp_path)
    assert any("empty `paths`" in e for e in errs)
    assert not any("hides it from the skill listing" in e for e in errs)
