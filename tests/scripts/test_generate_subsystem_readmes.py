"""AST module-README generator wired to readme-pipeline-v1."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_subsystem_readmes import (  # noqa: E402
    README_TEMPLATE,
    extract_subsystem_facts,
    generate_readme,
    is_root_readme,
    main,
)


def test_template_is_importable_for_dag_check():
    assert "Purpose" in README_TEMPLATE
    assert "dora:" not in README_TEMPLATE.lower()


def test_ast_extracts_class_and_function(tmp_path: Path):
    pkg = tmp_path / "demo"
    pkg.mkdir()
    (pkg / "mod.py").write_text(
        '''"""Demo module."""

__all__ = ["Widget", "build"]
MAX_ITEMS = 3


class Widget:
    """A thing."""

    def run(self) -> str:
        """Do work."""
        return "ok"


def build(name: str) -> Widget:
    """Factory."""
    return Widget()
''',
        encoding="utf-8",
    )
    facts = extract_subsystem_facts(tmp_path, "demo")
    assert [cls.name for cls in facts.classes] == ["Widget"]
    assert facts.classes[0].methods == ["run"]
    assert [fn.name for fn in facts.functions] == ["build"]
    assert "Widget" in facts.exports
    assert any(name == "MAX_ITEMS" for name, _value, _line in facts.constants)
    rendered = generate_readme(
        "demo",
        {
            "path": "demo",
            "title": "Demo",
            "tier": "operations",
            "description": "Fixture package.",
            "purpose": "Prove AST facts land in the README.",
        },
        facts,
        {},
    )
    assert "## Purpose" in rendered
    assert "`Widget`" in rendered
    assert "def build" in rendered


def test_refuses_root_readme(tmp_path: Path):
    dest = tmp_path / "README.md"
    dest.write_text("# Root\n", encoding="utf-8")
    assert is_root_readme(tmp_path, dest)
    assert not is_root_readme(tmp_path, tmp_path / "ops" / "README.md")


def test_cli_list_and_validate():
    assert main(["--root", str(REPO_ROOT), "--list"]) == 0
    assert main(["--root", str(REPO_ROOT), "--validate"]) == 0


def test_cli_dry_run_fixture(tmp_path: Path):
    pkg = tmp_path / "sample"
    pkg.mkdir()
    (pkg / "ok.py").write_text("class Gate:\n    pass\n", encoding="utf-8")
    config = tmp_path / "config" / "subsystems"
    config.mkdir(parents=True)
    (config / "readme_config.yaml").write_text(
        """version: "1.0"
defaults:
  sections:
    purpose: {required: true}
    components: {required: true}
subsystems:
  sample:
    path: sample
    title: Sample
    tier: operations
    description: Fixture
    purpose: Test dry-run
""",
        encoding="utf-8",
    )
    assert main(["--root", str(tmp_path), "--dry-run", "--subsystem", "sample"]) == 0
    assert not (pkg / "README.md").exists()
    assert main(["--root", str(tmp_path), "--subsystem", "sample"]) == 0
    text = (pkg / "README.md").read_text(encoding="utf-8")
    assert "## Purpose" in text
    assert "Gate" in text
    assert main(["--root", str(tmp_path), "--validate-sections"]) == 0


def test_skips_handwritten(tmp_path: Path):
    pkg = tmp_path / "kept"
    pkg.mkdir()
    (pkg / "ok.py").write_text("class Keep:\n    pass\n", encoding="utf-8")
    (pkg / "README.md").write_text("---\nauto_generated: false\n---\n# Hand\n", encoding="utf-8")
    config = tmp_path / "config" / "subsystems"
    config.mkdir(parents=True)
    (config / "readme_config.yaml").write_text(
        """version: "1.0"
subsystems:
  kept:
    path: kept
    title: Kept
    tier: operations
    description: Handwritten
""",
        encoding="utf-8",
    )
    assert main(["--root", str(tmp_path), "--subsystem", "kept"]) == 0
    assert (pkg / "README.md").read_text(encoding="utf-8").startswith("---")


def test_dag_no_longer_spots_donor_memory_readme():
    text = (REPO_ROOT / "workflows" / "dags" / "readme_pipeline_dag.py").read_text(encoding="utf-8")
    assert "memory/README.md" not in text
    assert "scripts/generate_subsystem_readmes.py" in text
