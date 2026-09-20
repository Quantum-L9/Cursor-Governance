"""README target qualification: inventory is the sole membership authority.

Each test here pins a defect that reached the generated corpus: fixture
subtrees admitted as modules, nested indexes left unqualified by a
parent-first pass, and configuration inventing targets the inventory never
saw.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    # Reuse the already-imported instance. Loading a second copy under the
    # same name leaves sibling test modules holding different objects, and
    # the compatibility wrapper's identity assertion then compares one
    # instance's constants against another's.
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


df = load("doc_filetree", SCRIPTS / "doc_filetree.py")
gm = load("generate_module_readmes", SCRIPTS / "generate_module_readmes.py")

EMPTY_CONFIG: dict = {"defaults": {}, "subsystems": {}}


def kinds(root: Path) -> dict[str, str]:
    return {row.path: row.kind for row in df.walk_inventory(root).modules}


def write(path: Path, text: str = "x = 1\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- T-Q-001 / T-Q-002: exclusion is subtree-wide, before classification ---


def test_excluded_fixture_subtree_never_qualifies(tmp_path: Path):
    write(tmp_path / "pkg" / "real.py")
    write(tmp_path / "pkg" / "fixtures" / "mod.py")
    write(tmp_path / "pkg" / "fixtures" / "positive" / "other.py")
    found = kinds(tmp_path)
    assert "pkg" in found
    assert "pkg/fixtures" not in found
    assert "pkg/fixtures/positive" not in found


def test_excluded_descendant_corpus_never_qualifies(tmp_path: Path):
    write(tmp_path / "foo" / "keep.py")
    write(tmp_path / "foo" / "generated" / "schemas" / "a.json", "{}\n")
    write(tmp_path / "foo" / "generated" / "schemas" / "b.json", "{}\n")
    found = kinds(tmp_path)
    assert not [path for path in found if "generated" in Path(path).parts]


def test_exclusion_matches_whole_segments_not_substrings(tmp_path: Path):
    """`generated-data` is a real directory; only a bare `generated` is residue."""
    write(tmp_path / "agents" / "generated-data" / "a.json", "{}\n")
    write(tmp_path / "agents" / "generated-data" / "b.json", "{}\n")
    assert "agents/generated-data" in kinds(tmp_path)


def test_campaign_residue_names_are_excluded_at_any_depth(tmp_path: Path):
    for leaf in ("handoff", "deliverables", "receipts", "drafts"):
        write(tmp_path / "campaign" / leaf / "inner" / "note.py")
    found = kinds(tmp_path)
    assert not [
        path
        for path in found
        if {"handoff", "deliverables", "receipts", "drafts"} & set(Path(path).parts)
    ]


# --- T-Q-003: nested indexes reach a fixed point ---


def test_nested_indexes_are_complete(tmp_path: Path):
    for branch in ("a", "b"):
        for leaf in ("one", "two"):
            write(tmp_path / "top" / branch / leaf / f"{leaf}.py", f"def {leaf}():\n    return 1\n")
    found = kinds(tmp_path)
    for expected in (
        "top/a/one",
        "top/a/two",
        "top/a",
        "top/b/one",
        "top/b/two",
        "top/b",
        "top",
    ):
        assert expected in found, f"{expected} missing from inventory"
    assert found["top"] == "index"
    assert found["top/a"] == "index"


def test_index_qualification_is_a_fixed_point(tmp_path: Path):
    """Four levels: every parent of two qualified children must qualify."""
    for branch in ("a", "b"):
        for leaf in ("one", "two"):
            for leafer in ("x", "y"):
                write(tmp_path / "deep" / branch / leaf / leafer / "m.py")
    found = kinds(tmp_path)
    for expected in ("deep", "deep/a", "deep/b", "deep/a/one", "deep/a/two"):
        assert found.get(expected) == "index", f"{expected} not an index"


# --- T-Q-004 / T-Q-005: configuration cannot invent a target ---


def test_config_cannot_invent_a_target(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py")
    config = {
        "defaults": {},
        "subsystems": {"ghost": {"path": "ghost/path", "title": "Ghost"}},
    }
    assert gm.discover_module_paths(tmp_path, config) == ["pkg"]
    assert gm.unauthorized_config_paths(tmp_path, config) == ["ghost/path"]
    assert gm.write_missing_module_readmes(tmp_path, config=config) == ["pkg/README.md"]
    assert not (tmp_path / "ghost").exists()


def test_config_can_suppress_an_authorized_target(tmp_path: Path):
    write(tmp_path / "pkg" / "mod.py")
    config = {
        "defaults": {},
        "subsystems": {"pkg": {"path": "pkg", "title": "Pkg", "skip": True}},
    }
    assert gm.discover_module_paths(tmp_path, config) == []
    assert gm.write_missing_module_readmes(tmp_path, config=config) == []
    assert not (tmp_path / "pkg" / "README.md").exists()


# --- T-Q-006 / T-Q-007: skill roots and their sidecars ---


def test_skill_root_classifies_as_skill(tmp_path: Path):
    write(tmp_path / "skills" / "demo" / "SKILL.md", "# Demo\n")
    write(tmp_path / "skills" / "demo" / "scripts" / "a.py")
    write(tmp_path / "skills" / "demo" / "scripts" / "b.py")
    found = kinds(tmp_path)
    assert found["skills/demo"] == "skill"
    assert found["skills/demo/scripts"] == "subsystem"


def test_skill_root_stays_a_skill_even_with_code_beside_it(tmp_path: Path):
    write(tmp_path / "skills" / "demo" / "SKILL.md", "# Demo\n")
    write(tmp_path / "skills" / "demo" / "run.py")
    write(tmp_path / "skills" / "demo" / "helper.py")
    assert kinds(tmp_path)["skills/demo"] == "skill"


def test_skill_sidecars_are_not_targets(tmp_path: Path):
    write(tmp_path / "skills" / "demo" / "SKILL.md", "# Demo\n")
    write(tmp_path / "skills" / "demo" / "references" / "a.md", "# A\n")
    write(tmp_path / "skills" / "demo" / "references" / "b.md", "# B\n")
    write(tmp_path / "skills" / "demo" / "contracts" / "a.json", "{}\n")
    write(tmp_path / "skills" / "demo" / "contracts" / "b.json", "{}\n")
    found = kinds(tmp_path)
    assert "skills/demo/references" not in found
    assert "skills/demo/contracts" not in found


# --- single vs multi module boundary ---


def test_single_module_directory_is_a_module(tmp_path: Path):
    write(tmp_path / "solo" / "only.py")
    assert kinds(tmp_path)["solo"] == "module"


def test_multi_module_directory_is_a_subsystem(tmp_path: Path):
    write(tmp_path / "many" / "a.py")
    write(tmp_path / "many" / "b.py")
    assert kinds(tmp_path)["many"] == "subsystem"


# --- a directory that is both indexes ---


def test_index_wins_over_corpus_when_a_directory_is_both(tmp_path: Path):
    """A parent's children are what a reader came for, not its manifests."""
    write(tmp_path / "skills" / "MANIFEST.yaml", "a: 1\n")
    write(tmp_path / "skills" / "REGISTRY.json", "{}\n")
    for name in ("alpha", "beta"):
        write(tmp_path / "skills" / name / "SKILL.md", f"# {name}\n")
    assert kinds(tmp_path)["skills"] == "index"


def test_an_index_still_lists_its_direct_files(tmp_path: Path):
    write(tmp_path / "skills" / "MANIFEST.yaml", "a: 1\n")
    write(tmp_path / "skills" / "REGISTRY.json", "{}\n")
    for name in ("alpha", "beta"):
        write(tmp_path / "skills" / name / "SKILL.md", f"# {name}\n")
    gm.write_missing_module_readmes(tmp_path)
    text = (tmp_path / "skills" / "README.md").read_text(encoding="utf-8")
    assert "**Kind:** index" in text
    assert "[`alpha/`](alpha/)" in text
    assert "`MANIFEST.yaml`" in text
    assert "`REGISTRY.json`" in text


def test_a_corpus_without_qualifying_children_stays_a_corpus(tmp_path: Path):
    write(tmp_path / "protocols" / "a.md", "# A\n")
    write(tmp_path / "protocols" / "b.md", "# B\n")
    assert kinds(tmp_path)["protocols"] == "corpus"


# --- titles and dependency classification ---


def test_acronym_directory_names_are_cased_correctly(tmp_path: Path):
    """`github`.title() is `Github`, which reads as a misspelt product."""
    write(tmp_path / "adapters" / "github" / "mod.py")
    write(tmp_path / "adapters" / "ci" / "mod.py")
    gm.write_missing_module_readmes(tmp_path)
    assert (
        (tmp_path / "adapters" / "github" / "README.md")
        .read_text(encoding="utf-8")
        .startswith("# GitHub\n")
    )
    assert (
        (tmp_path / "adapters" / "ci" / "README.md")
        .read_text(encoding="utf-8")
        .startswith("# CI\n")
    )


def test_a_suppressed_directory_is_still_a_first_party_dependency(tmp_path: Path):
    """Suppression decides documentation, not whether code is ours."""
    write(tmp_path / "workflows" / "dags" / "a.py", "a = 1\n")
    write(tmp_path / "workflows" / "dags" / "b.py", "b = 1\n")
    write(tmp_path / "runtime" / "one.py", "import workflows\nimport langgraph\n")
    config = {
        "defaults": {},
        "subsystems": {"workflows": {"path": "workflows", "skip": True}},
    }
    gm.write_missing_module_readmes(tmp_path, config=config)
    text = (tmp_path / "runtime" / "README.md").read_text(encoding="utf-8")
    assert "**Internal:** `workflows`" in text
    assert "**External:** `langgraph`" in text
    assert not (tmp_path / "workflows" / "README.md").exists()


# --- empty directories earn nothing ---


def test_empty_directory_gets_no_readme(tmp_path: Path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "foundation" / "security").mkdir(parents=True)
    found = kinds(tmp_path)
    assert "prompts" not in found
    assert "foundation/security" not in found
    assert gm.write_missing_module_readmes(tmp_path) == []
