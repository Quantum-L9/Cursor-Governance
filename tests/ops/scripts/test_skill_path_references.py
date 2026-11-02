"""Every skill pack in this repository names only pack files it ships.

`skills/l9-skill-compiler/references/meta-standard.md` ("Path references in
SKILL.md"): a backticked path means a file inside the pack, and anything else
says where it lives. The compiler's validator enforces that for one pack at a
time; this test holds every live and archived pack in the repository to it, so
an unqualified path to another repository or another pack fails CI instead of
reading as a missing pack file.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"
VALIDATOR = SKILLS / "l9-skill-compiler" / "scripts" / "validate_skill_pack.py"
MISSING = "SKILL.md references a pack file that does not exist: "


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_skill_pack_repo_sweep", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()

PACKS = sorted(
    p
    for p in [*SKILLS.iterdir(), *(SKILLS / "_archived").iterdir()]
    if p.is_dir() and (p / "SKILL.md").is_file()
)


def test_the_sweep_sees_the_repository_packs() -> None:
    names = {p.name for p in PACKS}
    assert {"l9-skill-compiler", "l9-repo-birth", "l9-wire-skill-into-repo"} <= names


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.relative_to(SKILLS).as_posix())
def test_pack_names_only_files_it_ships(pack: Path) -> None:
    missing = [e.removeprefix(MISSING) for e in validator.validate(pack) if e.startswith(MISSING)]
    assert missing == [], (
        f"{pack.relative_to(ROOT)}/SKILL.md names files the pack does not ship: {missing}. "
        "Qualify paths outside the pack: skills/<pack>/..., <repo>:path, or <pack>/... "
        "(skills/l9-skill-compiler/references/meta-standard.md)."
    )


def _pack(tmp_path: Path, body: str) -> Path:
    root = tmp_path / "l9-demo"
    root.mkdir()
    desc = (
        "demonstrate path qualification for skill packs in tests of the repository "
        "sweep. use when checking that qualified references to other repositories, "
        "other packs and template paths pass validation."
    )
    (root / "SKILL.md").write_text(
        f"---\nname: l9-demo\ndescription: {desc}\n---\n\n# Demo\n\n{body}\n", encoding="utf-8"
    )
    return root


@pytest.mark.parametrize(
    "reference",
    [
        "`l9-repo-template:scripts/birth-runner/birth_frontdoor.py`",
        "`PlasticOS:scripts/check_module_wiring.py`",
        "`<consumer-repo>:scripts/repo_generators/export_repo_indexes.py`",
        "`<pack>/agents/meta.yaml`",
        "`skills/l9-other/scripts/validate_exemplary_skill.py`",
    ],
)
def test_qualified_forms_pass(tmp_path: Path, reference: str) -> None:
    root = _pack(tmp_path, f"See {reference}.")
    assert [e for e in validator.validate(root) if e.startswith(MISSING)] == []


def test_the_unqualified_form_still_fails(tmp_path: Path) -> None:
    root = _pack(tmp_path, "See `scripts/birth-runner/birth_frontdoor.py`.")
    assert [e.removeprefix(MISSING) for e in validator.validate(root) if e.startswith(MISSING)] == [
        "scripts/birth-runner/birth_frontdoor.py"
    ]
