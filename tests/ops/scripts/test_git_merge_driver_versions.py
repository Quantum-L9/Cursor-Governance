"""git_merge_driver_versions.py and its registration by ensure_git_merge_drivers.sh."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
DRIVER = SCRIPTS / "git_merge_driver_versions.py"
ENSURE = SCRIPTS / "ensure_git_merge_drivers.sh"
sys.path.insert(0, str(SCRIPTS))

import git_merge_driver_versions as gmv  # noqa: E402


def _manifest(version: str, extra: str = "") -> str:
    # Shaped like a real Odoo manifest: the version line sits among other keys,
    # so an edit two lines away is a separate hunk for git merge-file.
    return (
        "{\n"
        '    "name": "Widget",\n'
        '    "summary": "Widgets",\n'
        '    "author": "L9",\n'
        f'    "version": "{version}",\n'
        '    "category": "Tools",\n'
        '    "website": "https://example.invalid",\n'
        '    "depends": ["base"],\n'
        f"{extra}"
        "}\n"
    )


def _readme(version: str, body: str = "Widget module.\n") -> str:
    return f"---\nmodule: widget\nmodule_version: {version}\n---\n\n# Widget\n\n{body}"


# --- merge_versions ----------------------------------------------------------


def test_merge_versions_both_bumped_takes_higher_and_bumps_above_both() -> None:
    assert gmv.merge_versions("19.0.1.0.3", "19.0.1.0.4", "19.0.1.0.6") == "19.0.1.0.7"


def test_merge_versions_both_bumped_to_same_value_still_bumps() -> None:
    assert gmv.merge_versions("19.0.1.0.3", "19.0.1.0.4", "19.0.1.0.4") == "19.0.1.0.5"


def test_merge_versions_higher_minor_wins_over_longer_last_component() -> None:
    assert gmv.merge_versions("19.0.1.0.3", "19.0.1.1.0", "19.0.1.0.9") == "19.0.1.1.1"


def test_merge_versions_one_side_bumped_takes_that_side() -> None:
    assert gmv.merge_versions("19.0.1.0.3", "19.0.1.0.4", "19.0.1.0.3") == "19.0.1.0.4"
    assert gmv.merge_versions("19.0.1.0.3", "19.0.1.0.3", "19.0.1.0.5") == "19.0.1.0.5"


def test_merge_versions_unparseable_is_not_mechanical() -> None:
    assert gmv.merge_versions("1.0", "1.1-beta", "1.2") is None


# --- resolve(): manifest -----------------------------------------------------


def test_manifest_both_sides_bumped_merges_clean_above_both() -> None:
    result, clean, detail = gmv.resolve(
        _manifest("19.0.1.0.3"),
        _manifest("19.0.1.0.4"),
        _manifest("19.0.1.0.5"),
        "addons/widget/__manifest__.py",
    )
    assert clean, detail
    assert result == _manifest("19.0.1.0.6")


def test_manifest_one_side_bumped_takes_that_side_without_extra_bump() -> None:
    result, clean, _ = gmv.resolve(
        _manifest("19.0.1.0.3"),
        _manifest("19.0.1.0.3"),
        _manifest("19.0.1.0.4"),
        "widget/__manifest__.py",
    )
    assert clean
    assert result == _manifest("19.0.1.0.4")


def test_manifest_disjoint_non_version_change_still_merges_like_git() -> None:
    base = _manifest("19.0.1.0.3")
    ours = _manifest("19.0.1.0.4").replace('"Widget"', '"Widget Pro"')  # 3 lines above
    theirs = _manifest("19.0.1.0.5", extra='    "license": "LGPL-3",\n')
    result, clean, _ = gmv.resolve(base, ours, theirs, "widget/__manifest__.py")
    assert clean
    assert '"version": "19.0.1.0.6"' in result
    assert '"Widget Pro"' in result
    assert '"license": "LGPL-3"' in result


def test_manifest_conflicting_non_version_change_conflicts() -> None:
    base = _manifest("19.0.1.0.3")
    ours = _manifest("19.0.1.0.4").replace('["base"]', '["base", "sale"]')
    theirs = _manifest("19.0.1.0.5").replace('["base"]', '["base", "stock"]')
    result, clean, _ = gmv.resolve(base, ours, theirs, "widget/__manifest__.py")
    assert not clean
    assert "<<<<<<<" in result and ">>>>>>>" in result


def test_manifest_with_two_version_keys_is_not_rewritten() -> None:
    base = _manifest("1.0") + '# "version": "0.9"\n'
    ours = _manifest("1.1") + '# "version": "0.9"\n'
    theirs = _manifest("1.2") + '# "version": "0.9"\n'
    _result, clean, _ = gmv.resolve(base, ours, theirs, "widget/__manifest__.py")
    assert not clean


def test_manifest_unparseable_versions_conflict() -> None:
    _result, clean, _ = gmv.resolve(
        _manifest("1.0"), _manifest("1.1-rc"), _manifest("1.2"), "w/__manifest__.py"
    )
    assert not clean


# --- resolve(): README -------------------------------------------------------


def test_readme_follows_merged_manifest_version() -> None:
    manifest, m_clean, _ = gmv.resolve(
        _manifest("19.0.1.0.3"),
        _manifest("19.0.1.0.4"),
        _manifest("19.0.1.0.5"),
        "w/__manifest__.py",
    )
    readme, r_clean, _ = gmv.resolve(
        _readme("19.0.1.0.3"), _readme("19.0.1.0.4"), _readme("19.0.1.0.5"), "w/README.md"
    )
    assert m_clean and r_clean
    assert '"version": "19.0.1.0.6"' in manifest
    assert "module_version: 19.0.1.0.6\n" in readme


def test_readme_without_front_matter_merges_like_git() -> None:
    base = "# Title\n\nalpha\n\nbeta\n\ngamma\n"
    ours = "# Title\n\nALPHA\n\nbeta\n\ngamma\n"
    theirs = "# Title\n\nalpha\n\nbeta\n\nGAMMA\n"
    result, clean, _ = gmv.resolve(base, ours, theirs, "README.md")
    assert clean
    assert result == "# Title\n\nALPHA\n\nbeta\n\nGAMMA\n"


def test_readme_conflicting_body_edit_conflicts_even_after_version_merge() -> None:
    base = _readme("1.0.3", "Text.\n")
    ours = _readme("1.0.4", "Ours text.\n")
    theirs = _readme("1.0.5", "Theirs text.\n")
    result, clean, _ = gmv.resolve(base, ours, theirs, "w/README.md")
    assert not clean
    assert "module_version: 1.0.6" in result


def test_readme_module_version_outside_front_matter_is_ignored() -> None:
    base = "# T\n\nmodule_version: 1.0\n"
    ours = "# T\n\nmodule_version: 1.1\n"
    theirs = "# T\n\nmodule_version: 1.2\n"
    _result, clean, _ = gmv.resolve(base, ours, theirs, "README.md")
    assert not clean


# --- resolve(): tests/__init__.py --------------------------------------------


def test_tests_init_union_keeps_ours_order_then_theirs_additions() -> None:
    base = "from . import test_a\n"
    ours = "from . import test_a\nfrom . import test_c\n"
    theirs = "from . import test_a\nfrom . import test_b\nfrom . import test_d\n"
    result, clean, _ = gmv.resolve(base, ours, theirs, "addons/w/tests/__init__.py")
    assert clean
    assert result == (
        "from . import test_a\nfrom . import test_c\nfrom . import test_b\nfrom . import test_d\n"
    )


def test_tests_init_same_addition_on_both_sides_appears_once() -> None:
    base = "# tests\nfrom . import test_a\n"
    both = base + "from . import test_b\n"
    result, clean, _ = gmv.resolve(base, both, both, "w/tests/__init__.py")
    assert clean
    assert result.count("test_b") == 1


def test_tests_init_respects_a_deletion_by_one_side() -> None:
    base = "from . import test_a\nfrom . import test_old\n"
    ours = "from . import test_a\nfrom . import test_old\nfrom . import test_c\n"
    theirs = "from . import test_a\n"
    result, clean, _ = gmv.resolve(base, ours, theirs, "w/tests/__init__.py")
    assert clean
    assert result == "from . import test_a\nfrom . import test_c\n"


def test_tests_init_with_code_falls_back_to_text_merge_and_conflicts() -> None:
    base = "from . import test_a\nVALUE = 1\n"
    ours = "from . import test_a\nVALUE = 2\n"
    theirs = "from . import test_a\nVALUE = 3\n"
    result, clean, _ = gmv.resolve(base, ours, theirs, "w/tests/__init__.py")
    assert not clean
    assert "<<<<<<<" in result


def test_init_outside_a_tests_directory_is_unrecognised() -> None:
    assert gmv.kind_for("w/models/__init__.py") is None
    assert gmv.kind_for("w/tests/__init__.py") == "tests_init"


# --- unrecognised / garbage --------------------------------------------------


def test_unrecognised_path_always_conflicts() -> None:
    _result, clean, detail = gmv.resolve("a\n", "b\n", "a\n", "notes/garbage.bin")
    assert not clean
    assert "unrecognised" in detail


def test_garbage_manifest_conflicts() -> None:
    # Binary input: git merge-file refuses it, so ours stays as-is and the
    # path is reported conflicted, as git does with no driver at all.
    result, clean, detail = gmv.resolve(
        "\x00garbage\n", "\x00ours junk\n", "\x00theirs junk\n", "w/__manifest__.py"
    )
    assert not clean
    assert result == "\x00ours junk\n"
    assert "binary" in detail.lower()


def test_garbage_text_manifest_without_version_conflicts() -> None:
    result, clean, _ = gmv.resolve("junk\n", "ours junk\n", "theirs junk\n", "w/__manifest__.py")
    assert not clean
    assert "<<<<<<<" in result


# --- CLI contract (%O %A %B %P) ----------------------------------------------


def _run_driver(
    tmp_path: Path, base: str, ours: str, theirs: str, pathname: str
) -> tuple[int, str]:
    paths = []
    for name, content in (("O", base), ("A", ours), ("B", theirs)):
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        paths.append(str(p))
    proc = subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, str(DRIVER), *paths, pathname], capture_output=True, text=True, check=False
    )
    return proc.returncode, (tmp_path / "A").read_text(encoding="utf-8")


def test_cli_writes_result_to_ours_and_exits_zero_when_clean(tmp_path: Path) -> None:
    code, result = _run_driver(
        tmp_path, _manifest("1.0.1"), _manifest("1.0.2"), _manifest("1.0.3"), "w/__manifest__.py"
    )
    assert code == 0
    assert result == _manifest("1.0.4")


def test_cli_exits_non_zero_on_unrecognised_path(tmp_path: Path) -> None:
    code, _ = _run_driver(tmp_path, "a\n", "b\n", "c\n", "garbage.txt")
    assert code != 0


def test_cli_rejects_wrong_arity() -> None:
    proc = subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, str(DRIVER), "only-one"], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 2


# --- ensure_git_merge_drivers.sh + a real three-way merge --------------------


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=check, env=env
    )


def _ensure(repo: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    # Use this checkout's driver, not the SSOT's, so the test proves this tree.
    env["CURSOR_GOVERNANCE_DIR"] = str(ROOT)
    return subprocess.run(  # noqa: S603 - fixed argv
        ["bash", str(ENSURE), str(repo)], capture_output=True, text=True, check=False, env=env
    )


@pytest.fixture
def odoo_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    mod = repo / "widget"
    (mod / "tests").mkdir(parents=True)
    (mod / "__manifest__.py").write_text(_manifest("19.0.1.0.3"), encoding="utf-8")
    (mod / "README.md").write_text(_readme("19.0.1.0.3"), encoding="utf-8")
    (mod / "tests" / "__init__.py").write_text("from . import test_a\n", encoding="utf-8")
    (repo / "notes.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _branch(repo: Path, name: str, version: str, test: str, notes: str | None = None) -> None:
    _git(repo, "checkout", "-q", "-b", name, "main")
    mod = repo / "widget"
    (mod / "__manifest__.py").write_text(_manifest(version), encoding="utf-8")
    (mod / "README.md").write_text(_readme(version), encoding="utf-8")
    init = mod / "tests" / "__init__.py"
    init.write_text(init.read_text(encoding="utf-8") + f"from . import {test}\n", encoding="utf-8")
    if notes is not None:
        (repo / "notes.txt").write_text(notes, encoding="utf-8")
    _git(repo, "commit", "-q", "-am", name)


def test_ensure_registers_both_drivers_and_attributes_idempotently(odoo_repo: Path) -> None:
    first = _ensure(odoo_repo)
    assert first.returncode == 0, first.stderr
    second = _ensure(odoo_repo)
    assert second.returncode == 0, second.stderr
    driver = _git(odoo_repo, "config", "--get", "merge.l9-versions.driver").stdout
    assert "git_merge_driver_versions.py" in driver and "%O %A %B %P" in driver
    assert _git(odoo_repo, "config", "--get", "merge.l9-generated.driver").stdout.strip()
    info = (odoo_repo / ".git" / "info" / "attributes").read_text(encoding="utf-8")
    assert info.count("# BEGIN l9-versions") == 1
    for line in (
        "**/__manifest__.py merge=l9-versions",
        "**/README.md merge=l9-versions",
        "**/tests/__init__.py merge=l9-versions",
    ):
        assert info.count(line) == 1
    assert not (odoo_repo / ".gitattributes").exists(), (
        "consumer .gitattributes must not be written"
    )
    assert _git(odoo_repo, "status", "--porcelain").stdout == ""


def test_ensure_keeps_unmanaged_info_attributes_lines(odoo_repo: Path) -> None:
    info = odoo_repo / ".git" / "info" / "attributes"
    info.parent.mkdir(parents=True, exist_ok=True)
    info.write_text("*.bin binary\n", encoding="utf-8")
    assert _ensure(odoo_repo).returncode == 0
    assert _ensure(odoo_repo).returncode == 0
    text = info.read_text(encoding="utf-8")
    assert text.startswith("*.bin binary\n")
    assert text.count("# BEGIN l9-versions") == 1


def test_ensure_reasserts_tracked_generated_lines_after_versions(odoo_repo: Path) -> None:
    (odoo_repo / ".gitattributes").write_text("gen/** merge=l9-generated\n", encoding="utf-8")
    _git(odoo_repo, "add", ".gitattributes")
    _git(odoo_repo, "commit", "-q", "-m", "attrs")
    assert _ensure(odoo_repo).returncode == 0
    check = _git(odoo_repo, "check-attr", "merge", "--", "gen/README.md", "widget/README.md").stdout
    assert "gen/README.md: merge: l9-generated" in check
    assert "widget/README.md: merge: l9-versions" in check


def test_real_three_way_merge_resolves_version_churn(odoo_repo: Path) -> None:
    assert _ensure(odoo_repo).returncode == 0
    _branch(odoo_repo, "pr-a", "19.0.1.0.4", "test_alpha")
    _branch(odoo_repo, "pr-b", "19.0.1.0.4.1", "test_beta")
    _git(odoo_repo, "checkout", "-q", "pr-a")
    merged = _git(odoo_repo, "merge", "--no-edit", "pr-b", check=False)
    assert merged.returncode == 0, merged.stdout + merged.stderr
    mod = odoo_repo / "widget"
    assert '"version": "19.0.1.0.4.2"' in (mod / "__manifest__.py").read_text(encoding="utf-8")
    assert "module_version: 19.0.1.0.4.2" in (mod / "README.md").read_text(encoding="utf-8")
    assert (mod / "tests" / "__init__.py").read_text(encoding="utf-8") == (
        "from . import test_a\nfrom . import test_alpha\nfrom . import test_beta\n"
    )


def test_real_merge_leaves_other_conflicts_to_git(odoo_repo: Path) -> None:
    assert _ensure(odoo_repo).returncode == 0
    _branch(odoo_repo, "pr-a", "19.0.1.0.4", "test_alpha", notes="ours\n")
    _branch(odoo_repo, "pr-b", "19.0.1.0.5", "test_beta", notes="theirs\n")
    _git(odoo_repo, "checkout", "-q", "pr-a")
    merged = _git(odoo_repo, "merge", "--no-edit", "pr-b", check=False)
    assert merged.returncode != 0
    unmerged = _git(odoo_repo, "diff", "--name-only", "--diff-filter=U").stdout.split()
    assert unmerged == ["notes.txt"]


def test_merge_tree_uses_the_driver_without_a_work_tree(odoo_repo: Path) -> None:
    assert _ensure(odoo_repo).returncode == 0
    _branch(odoo_repo, "pr-a", "19.0.1.0.4", "test_alpha")
    _branch(odoo_repo, "pr-b", "19.0.1.0.6", "test_beta")
    probe = _git(odoo_repo, "merge-tree", "--write-tree", "pr-a", "pr-b", check=False)
    assert probe.returncode == 0, probe.stdout
    tree = probe.stdout.split()[0]
    manifest = _git(odoo_repo, "show", f"{tree}:widget/__manifest__.py").stdout
    assert '"version": "19.0.1.0.7"' in manifest


def test_identical_bump_on_both_sides_is_resolved_by_git_not_the_driver(odoo_repo: Path) -> None:
    """Known limit: identical blobs never reach a merge driver.

    Two PRs that bump to the same version leave byte-identical manifests on both
    sides, which git resolves at the tree level before any driver runs. The
    merged version therefore equals both sides. Only the integration step can
    catch that reuse; this test pins the behaviour so the limit stays visible.
    """
    assert _ensure(odoo_repo).returncode == 0
    _branch(odoo_repo, "pr-a", "19.0.1.0.4", "test_alpha")
    _branch(odoo_repo, "pr-b", "19.0.1.0.4", "test_beta")
    _git(odoo_repo, "checkout", "-q", "pr-a")
    assert _git(odoo_repo, "merge", "--no-edit", "pr-b", check=False).returncode == 0
    manifest = (odoo_repo / "widget" / "__manifest__.py").read_text(encoding="utf-8")
    assert '"version": "19.0.1.0.4"' in manifest
    init = (odoo_repo / "widget" / "tests" / "__init__.py").read_text(encoding="utf-8")
    assert "test_alpha" in init and "test_beta" in init
