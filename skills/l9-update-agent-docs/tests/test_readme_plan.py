"""Reconciliation: exact desired corpus versus generator-owned corpus.

A README this generator wrote for a target it no longer authorizes is
stale and is retired. A README it did not write is never touched, whether
or not the target still exists. Convergence is a merge gate: a second run
over an unchanged tree mutates nothing.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gm = load("generate_module_readmes", SCRIPTS / "generate_module_readmes.py")
rr = load("readme_renderers", SCRIPTS / "readme_renderers.py")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def actions(plan) -> dict[str, str]:
    return {item.path: item.action for item in plan.items}


# --- T-P-001 .. T-P-004 ---


def test_create_for_an_authorized_target_without_a_readme(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    assert actions(gm.plan_module_readmes(tmp_path)) == {"pkg/README.md": "create"}


def test_unchanged_when_owned_bytes_are_already_current(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    gm.write_missing_module_readmes(tmp_path)
    assert actions(gm.plan_module_readmes(tmp_path)) == {"pkg/README.md": "unchanged"}


def test_refresh_when_owned_bytes_are_stale(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    gm.write_missing_module_readmes(tmp_path)
    write(tmp_path / "pkg" / "README.md", "# Drifted\n\n" + rr.marker_for("module") + "\n")
    assert actions(gm.plan_module_readmes(tmp_path)) == {"pkg/README.md": "refresh"}


def test_preserve_a_handwritten_readme(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    write(tmp_path / "pkg" / "README.md", "# Mine\n\nHand-authored notes.\n")
    plan = gm.plan_module_readmes(tmp_path)
    assert actions(plan) == {"pkg/README.md": "preserve"}
    assert plan.mutations == ()
    gm.apply_module_readme_plan(tmp_path, plan)
    assert (tmp_path / "pkg" / "README.md").read_text(encoding="utf-8").startswith("# Mine")


# --- T-P-005 .. T-P-007: staleness and ownership ---


def test_retire_an_owned_readme_at_a_no_longer_authorized_target(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    stale = tmp_path / "pkg" / "fixtures" / "README.md"
    write(stale, "# Fixture\n\n" + rr.marker_for("module") + "\n")
    plan = gm.plan_module_readmes(tmp_path)
    assert actions(plan)["pkg/fixtures/README.md"] == "retire"
    gm.apply_module_readme_plan(tmp_path, plan)
    assert not stale.exists()


def test_retire_recognizes_a_legacy_marker(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    stale = tmp_path / "pkg" / "fixtures" / "README.md"
    write(stale, "# Fixture\n\n" + gm.GENERATED_MARKER + "\n")
    plan = gm.plan_module_readmes(tmp_path)
    assert actions(plan)["pkg/fixtures/README.md"] == "retire"


def test_handwritten_readme_at_a_stale_path_is_untouched(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    kept = tmp_path / "pkg" / "fixtures" / "README.md"
    write(kept, "# Why these fixtures exist\n")
    plan = gm.plan_module_readmes(tmp_path)
    assert "pkg/fixtures/README.md" not in actions(plan)
    gm.apply_module_readme_plan(tmp_path, plan)
    assert kept.read_text(encoding="utf-8") == "# Why these fixtures exist\n"


def test_a_future_format_version_is_a_conflict_not_a_rewrite(tmp_path: Path):
    """Rolling back the compiler must not silently destroy newer output."""
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    future = "<!-- l9-readme: generated-by=l9-update-agent-docs version=99 kind=module -->"
    body = "# Newer\n\n" + future + "\n"
    write(tmp_path / "pkg" / "README.md", body)
    write(tmp_path / "gone" / "README.md", body)
    plan = gm.plan_module_readmes(tmp_path)
    assert actions(plan)["pkg/README.md"] == "conflict"
    assert actions(plan)["gone/README.md"] == "conflict"
    gm.apply_module_readme_plan(tmp_path, plan)
    assert (tmp_path / "pkg" / "README.md").read_text(encoding="utf-8") == body
    assert (tmp_path / "gone" / "README.md").is_file()


def test_an_explicit_opt_out_outranks_an_ownership_marker(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    body = "---\nauto_generated: false\n---\n# Mine\n\n" + rr.marker_for("module") + "\n"
    write(tmp_path / "pkg" / "README.md", body)
    plan = gm.plan_module_readmes(tmp_path)
    assert actions(plan) == {"pkg/README.md": "preserve"}
    gm.apply_module_readme_plan(tmp_path, plan)
    assert (tmp_path / "pkg" / "README.md").read_text(encoding="utf-8") == body


def test_legacy_shape_without_a_marker_is_never_deleted(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    ambiguous = tmp_path / "gone" / "README.md"
    write(
        ambiguous,
        "# Gone\n\n**Path:** `gone` | **Tier:** operations\n\n"
        "## Purpose\n\nOld.\n\n## Components\n\nx\n\n## Functions\n\nx\n\n"
        "## Exports\n\nx\n\n## Dependencies\n\nx\n",
    )
    plan = gm.plan_module_readmes(tmp_path)
    assert "gone/README.md" not in actions(plan)
    gm.apply_module_readme_plan(tmp_path, plan)
    assert ambiguous.is_file()


def test_root_readme_is_never_planned(tmp_path: Path):
    write(tmp_path / "mod.py", "x = 1\n")
    write(tmp_path / "README.md", "# Root\n\n" + rr.marker_for("module") + "\n")
    plan = gm.plan_module_readmes(tmp_path)
    assert "README.md" not in actions(plan)
    gm.apply_module_readme_plan(tmp_path, plan)
    assert (tmp_path / "README.md").is_file()


# --- T-P-008: a real dry run ---


def test_dry_run_reports_every_mutation_and_writes_nothing(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    write(tmp_path / "pkg" / "fixtures" / "README.md", "# F\n\n" + rr.marker_for("module") + "\n")
    planned = gm.write_missing_module_readmes(tmp_path, write=False)
    assert sorted(planned) == ["pkg/README.md", "pkg/fixtures/README.md"]
    assert not (tmp_path / "pkg" / "README.md").exists()
    assert (tmp_path / "pkg" / "fixtures" / "README.md").is_file()


# --- T-P-009: convergence ---


def test_second_run_over_an_unchanged_tree_mutates_nothing(tmp_path: Path):
    write(tmp_path / "skills" / "demo" / "SKILL.md", "---\ndescription: demo skill\n---\n\n# D\n")
    write(tmp_path / "skills" / "demo" / "scripts" / "a.py", '"""A."""\n')
    write(tmp_path / "skills" / "demo" / "scripts" / "b.py", '"""B."""\n')
    write(tmp_path / "skills" / "other" / "SKILL.md", "---\ndescription: other skill\n---\n\n# O\n")
    write(tmp_path / "protocols" / "a.md", "# A\n")
    write(tmp_path / "protocols" / "b.md", "# B\n")
    write(tmp_path / "solo" / "only.py", '"""Solo."""\n')

    first = gm.write_missing_module_readmes(tmp_path)
    assert first, "first run must create the corpus"

    second = gm.plan_module_readmes(tmp_path)
    counts = second.counts()
    assert counts["create"] == 0
    assert counts["refresh"] == 0
    assert counts["retire"] == 0
    assert counts["conflict"] == 0
    assert second.mutations == ()
    assert gm.write_missing_module_readmes(tmp_path) == []


def test_plan_counts_cover_every_action(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    counts = gm.plan_module_readmes(tmp_path).counts()
    assert set(counts) == {
        "create",
        "refresh",
        "unchanged",
        "preserve",
        "retire",
        "conflict",
    }


def test_stale_config_entry_is_an_error_finding(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    config = {"defaults": {}, "subsystems": {"ghost": {"path": "ghost/path"}}}
    plan = gm.plan_module_readmes(tmp_path, config=config)
    assert any(finding.rule_id == "readme.config.unauthorized_target" for finding in plan.errors)


def test_validation_is_fail_closed_nothing_is_written(tmp_path: Path, capsys):
    """An ERROR must stop the write, not be reported after it.

    Applying first leaves a failed run with a mutated worktree: invalid
    documentation written and stale artifacts already deleted.
    """
    write(tmp_path / "pkg" / "mod.py", "x = 1\n")
    stale = tmp_path / "pkg" / "fixtures" / "README.md"
    write(stale, "# F\n\n" + rr.marker_for("module") + "\n")
    write(
        tmp_path / "config" / "subsystems" / "readme_config.yaml",
        'version: "1.0"\nsubsystems:\n  ghost:\n    path: ghost/path\n',
    )
    assert gm.main(["--root", str(tmp_path)]) == 1
    assert "nothing was written" in capsys.readouterr().err
    assert not (tmp_path / "pkg" / "README.md").exists()
    assert stale.is_file(), "a retirement must not run when validation failed"


def test_changed_scope_does_not_retire(tmp_path: Path):
    """A scoped run sees only part of the tree, so it cannot judge staleness."""
    write(tmp_path / "alpha" / "a.py", "a = 1\n")
    write(tmp_path / "beta" / "b.py", "b = 1\n")
    write(tmp_path / "beta" / "fixtures" / "README.md", "# F\n\n" + rr.marker_for("module") + "\n")
    plan = gm.plan_module_readmes(tmp_path, changed=["beta/b.py"])
    assert actions(plan) == {"beta/README.md": "create"}
