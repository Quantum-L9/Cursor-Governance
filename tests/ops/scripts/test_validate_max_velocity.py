"""Repo invariant: committed execution profiles stay at maximum_velocity."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))

import validate_max_velocity as v  # noqa: E402


def test_this_checkout_is_maximum_velocity() -> None:
    assert v.collect_defects(ROOT) == []
    assert v.main(["--root", str(ROOT)]) == 0


def test_constrained_cursor_profile_fails(tmp_path: Path) -> None:
    (tmp_path / "ops" / "autonomy").mkdir(parents=True)
    shutil.copy(ROOT / v.POLICY_REL, tmp_path / v.POLICY_REL)
    shutil.copy(ROOT / v.SURFACE_REL, tmp_path / v.SURFACE_REL)
    policy = json.loads((tmp_path / v.POLICY_REL).read_text(encoding="utf-8"))
    policy["profiles"]["cursor"]["execution_profile"] = "constrained"
    policy["profiles"]["cursor"]["max_parallel"] = 4
    policy["profiles"]["cursor"]["max_mutation_lanes"] = 2
    policy["profiles"]["cursor"]["native_subagent_limit"] = None
    policy["profiles"]["cursor"]["concurrency_policy"] = "bounded"
    (tmp_path / v.POLICY_REL).write_text(json.dumps(policy), encoding="utf-8")
    defects = v.collect_defects(tmp_path)
    assert any("execution_profile='constrained'" in d for d in defects)
    assert any("max_parallel=4" in d for d in defects)
    assert v.main(["--root", str(tmp_path)]) == 1


def test_surface_default_regression_fails(tmp_path: Path) -> None:
    (tmp_path / "ops" / "autonomy").mkdir(parents=True)
    shutil.copy(ROOT / v.POLICY_REL, tmp_path / v.POLICY_REL)
    surface = yaml.safe_load((ROOT / v.SURFACE_REL).read_text(encoding="utf-8"))
    surface["claude_execution_profiles"]["cursor_default"] = "constrained"
    (tmp_path / v.SURFACE_REL).write_text(yaml.safe_dump(surface), encoding="utf-8")
    defects = v.collect_defects(tmp_path)
    assert any("cursor_default='constrained'" in d for d in defects)


def test_invariants_index_points_at_the_validator() -> None:
    text = (ROOT / "INVARIANTS.md").read_text(encoding="utf-8")
    assert "validate_max_velocity.py" in text
    assert "maximum_velocity" in text


def test_non_mapping_documents_are_defects_not_crashes(tmp_path: Path) -> None:
    """A fail-closed gate reports; it does not raise.

    Valid JSON/YAML need not be a mapping. A top-level list used to reach
    `.get` and raise AttributeError, taking the checker down instead of
    failing it closed.
    """
    for policy_text, surface_text in (
        ("[]", "profiles: {}\n"),
        ('{"profiles": {}}', "- a\n- b\n"),
        ("[1, 2]", "- a\n"),
    ):
        root = tmp_path / f"case{abs(hash((policy_text, surface_text)))}"
        (root / Path(v.POLICY_REL).parent).mkdir(parents=True, exist_ok=True)
        (root / Path(v.SURFACE_REL).parent).mkdir(parents=True, exist_ok=True)
        (root / v.POLICY_REL).write_text(policy_text, encoding="utf-8")
        (root / v.SURFACE_REL).write_text(surface_text, encoding="utf-8")
        defects = v.collect_defects(root)
        assert defects, (policy_text, surface_text)
        assert any("expected a mapping" in d for d in defects), defects
