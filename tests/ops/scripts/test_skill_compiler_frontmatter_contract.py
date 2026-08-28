"""The compiler must emit what the install gate accepts.

Three packs reached this repository needing hand repair — one shipped a
top-level `license:` — because `l9-skill-compiler`'s own validator allowed keys
`ops/scripts/check_skills_standard.py` rejects. Two contracts, no test holding
them together, so the drift was invisible until install.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "ops" / "scripts"
PACK = ROOT / "skills" / "l9-skill-compiler"

sys.path.insert(0, str(GATE))
from check_skills_standard import DESC_MAX, DESC_MIN, NATIVE  # noqa: E402


def _load_validator():
    path = PACK / "scripts" / "validate_skill_pack.py"
    spec = importlib.util.spec_from_file_location("validate_skill_pack", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def test_default_profile_matches_the_install_gate_exactly() -> None:
    assert validator.FRONTMATTER_PROFILES["l9"] == NATIVE
    assert (validator.DESC_MIN, validator.DESC_MAX) == (DESC_MIN, DESC_MAX)


def test_agent_skills_profile_is_a_superset_and_never_the_default() -> None:
    """Portability may widen the set, but only when a build asks for it."""
    assert validator.FRONTMATTER_PROFILES["agent-skills"] > NATIVE
    assert validator.validate.__defaults__ == ("l9",)


def _pack(tmp_path: Path, name: str, frontmatter: str) -> Path:
    root = tmp_path / name
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(f"---\n{frontmatter}---\n\n# {name}\n", encoding="utf-8")
    return root


GOOD_DESC = (
    "compile, rebuild, and validate reusable agent skill packs from prompts, SOPs, "
    "and existing skills. use when creating a reusable skill, making one portable "
    "across agents, or producing a validated archive for install."
)


def test_a_compliant_pack_passes(tmp_path: Path) -> None:
    root = _pack(tmp_path, "l9-demo", f"name: l9-demo\ndescription: {GOOD_DESC}\n")
    assert validator.validate(root) == []


@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [
        (f"name: l9-demo\ndescription: {GOOD_DESC}\nlicense: Proprietary\n", "license"),
        (f"name: l9-demo\ndescription: {GOOD_DESC}\nallowed-tools: Bash\n", "allowed-tools"),
        (f"name: l9-demo\ndescription: {GOOD_DESC}\nskill_schema: 1\n", "skill_schema"),
        (f"name: l9-other\ndescription: {GOOD_DESC}\n", "must match the pack directory"),
        ("name: l9-demo\ndescription: too short.\n", "under 150"),
        (
            f"name: l9-demo\ndescription: {GOOD_DESC.replace('use when', 'invoked when')}\n",
            "trigger",
        ),
        (f"name: l9-demo\ndescription: {GOOD_DESC}\npaths:\n", "empty `paths`"),
    ],
)
def test_the_gate_rejects_what_ci_rejects(tmp_path: Path, frontmatter: str, expected: str) -> None:
    root = _pack(tmp_path, "l9-demo", frontmatter)
    errors = validator.validate(root)
    assert any(expected in error for error in errors), f"missed {expected!r}: {errors}"


def test_agent_skills_profile_admits_the_two_extra_keys(tmp_path: Path) -> None:
    root = _pack(tmp_path, "l9-demo", f"name: l9-demo\ndescription: {GOOD_DESC}\nlicense: MIT\n")
    assert validator.validate(root, profile="agent-skills") == []


def test_archived_pack_must_disable_model_invocation(tmp_path: Path) -> None:
    root = tmp_path / "_archived" / "l9-demo"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        f"---\nname: l9-demo\ndescription: {GOOD_DESC}\n---\n\n# l9-demo\n", encoding="utf-8"
    )
    assert any("disable-model-invocation" in e for e in validator.validate(root))


def test_the_pack_satisfies_its_own_contract() -> None:
    """The compiler is a skill; it passes the gate it enforces."""
    assert validator.validate(PACK) == []


def test_meta_standard_does_not_teach_a_top_level_license() -> None:
    """The reference is what the model reads while writing frontmatter."""
    text = (PACK / "references" / "meta-standard.md").read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        # Indentation is the whole question: `license:` under `metadata:` is
        # exactly what the contract asks for; at column 0 it is the defect.
        if line.startswith(("license:", "allowed-tools:")):
            pytest.fail(f"meta-standard.md line {number} shows a top-level {line.strip()!r}")
    assert "nest" in text.lower(), "the reference must say where those keys go instead"
