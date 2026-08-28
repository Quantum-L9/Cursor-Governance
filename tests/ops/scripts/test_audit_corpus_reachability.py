"""C5 corpus reachability: declared entrypoints, name-load, advisory (not a delete gate)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_corpus_reachability import ENTRYPOINTS, audit, main  # noqa: E402


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_entrypoints(root: Path) -> None:
    _write(
        root,
        "skills/AUTONOMY_MANIFEST.yaml",
        "tiers:\n  auto_invoke:\n  - skill: l9-fixture-named\n    use_when: fixture\n",
    )
    _write(root, "commands/COMMANDS_MANIFEST.yaml", "commands: []\n")
    _write(
        root,
        "rules/RULES-MANIFEST.yaml",
        "rules:\n  - file: zz-fixture.mdc\n    id: l9.rule.zz.fixture\n",
    )
    _write(root, "ops/generated/skill-registry.json", "{}\n")
    _write(root, ".pre-commit-config.yaml", "repos: []\n")
    _write(root, "Makefile", "help:\n\t@echo ok\n")
    _write(root, "ops/hooks/hooks.json.template", "{}\n")
    _write(
        root,
        "environment/agents/adapters/claude-code/plugins.desired.json",
        "{}\n",
    )
    _write(
        root,
        "environment/agents/adapters/claude-code/settings.template.json",
        "{}\n",
    )


def test_doc_only_file_is_unreachable_and_entrypoints_are_named(tmp_path: Path) -> None:
    """File referenced only from a design doc is unreachable; report names the set."""
    _minimal_entrypoints(tmp_path)
    _write(
        tmp_path,
        "ops/scripts/inert_design_note.md",
        "# leftover design note never loaded\n",
    )
    _write(
        tmp_path,
        "docs/design.md",
        "See ops/scripts/inert_design_note.md for the retired sketch.\n",
    )
    report = audit(tmp_path)
    assert report["entrypoints"] == list(ENTRYPOINTS)
    assert "ops/scripts/inert_design_note.md" in report["unreachable"]
    assert report["summary"]["unreachable"] >= 1


def test_name_loaded_skill_and_rule_are_reachable(tmp_path: Path) -> None:
    """Skills/rules loaded by name are reachable even with no import graph."""
    _minimal_entrypoints(tmp_path)
    _write(
        tmp_path,
        "skills/l9-fixture-named/SKILL.md",
        "---\nname: l9-fixture-named\n---\n# fixture\n",
    )
    _write(tmp_path, "rules/zz-fixture.mdc", "---\nid: l9.rule.zz.fixture\n---\n# fixture\n")
    report = audit(tmp_path)
    assert "skills/l9-fixture-named/SKILL.md" not in report["unreachable"]
    assert "rules/zz-fixture.mdc" not in report["unreachable"]


def test_report_is_not_a_delete_gate(tmp_path: Path) -> None:
    """Orphans present still exit 0; report forbids delete authorization."""
    _minimal_entrypoints(tmp_path)
    _write(tmp_path, "ops/scripts/orphan_never_wired.md", "inert\n")
    json_out = tmp_path / "out.json"
    md_out = tmp_path / "out.md"
    rc = main(
        [
            "--root",
            str(tmp_path),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
        ]
    )
    assert rc == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["advisory"] is True
    assert payload["delete_authorization"] is False
    assert "ops/scripts/orphan_never_wired.md" in payload["unreachable"]
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "audit_corpus_reachability.py"),
            "--root",
            str(tmp_path),
            "--json-out",
            str(tmp_path / "sub.json"),
            "--md-out",
            str(tmp_path / "sub.md"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "delete_authorization=False" in proc.stdout


def test_import_one_hop_from_entrypoint_script(tmp_path: Path) -> None:
    _minimal_entrypoints(tmp_path)
    _write(
        tmp_path,
        "Makefile",
        "help:\n\tpython ops/scripts/seed_entry.py\n",
    )
    _write(
        tmp_path,
        "ops/scripts/seed_entry.py",
        "from helper_mod import run\n\nrun()\n",
    )
    _write(tmp_path, "ops/scripts/helper_mod.py", "def run() -> None:\n    return None\n")
    report = audit(tmp_path)
    assert "ops/scripts/seed_entry.py" not in report["unreachable"]
    assert "ops/scripts/helper_mod.py" not in report["unreachable"]


def test_archived_paths_are_excluded_from_population(tmp_path: Path) -> None:
    _minimal_entrypoints(tmp_path)
    _write(tmp_path, "ops/scripts/_archived/retired.py", "print('gone')\n")
    report = audit(tmp_path)
    assert "ops/scripts/_archived/retired.py" not in report["unreachable"]
    assert all("_archived" not in row for row in report["unreachable"])
