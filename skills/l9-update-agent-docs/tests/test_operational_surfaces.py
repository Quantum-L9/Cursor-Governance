from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

import doc_policy as dp  # noqa: E402
from doc_surface_analysis import assess_surface_obligations  # noqa: E402
from surface_analyzers.makefile import analyze as analyze_makefile  # noqa: E402
from surface_analyzers.pyproject import analyze as analyze_pyproject  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_root_guard(root: Path) -> None:
    write(
        root / "ops/config/root-file-protection.json",
        json.dumps(
            {
                "justification": {"marker": "ALLOW-ROOT-DELETION"},
                "protected_files": [
                    {"path": "Makefile", "tier": "canonical", "rule": "additive_only"},
                    {
                        "path": "pyproject.toml",
                        "tier": "canonical",
                        "rule": "additive_only",
                    },
                ],
            }
        ),
    )


def test_policy_v3_declares_closed_operational_surfaces() -> None:
    policy = dp.load_policy()
    assert dp.validate_policy(policy) == []
    assert policy["schema"] == "l9.repo-docs.surface-policy.v3"
    make_analyzer = policy["surfaces"]["makefile_contract"]["analysis"]["analyzer"]
    python_analyzer = policy["surfaces"]["python_project_contract"]["analysis"]["analyzer"]
    assert make_analyzer == "makefile-contract-v1"
    assert python_analyzer == "python-project-contract-v1"


def test_makefile_analyzer_detects_locked_python_bypass(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(root / "ops/scripts/replay.py", "print('ok')\n")
    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nreplay:\n\tpython3 ops/scripts/replay.py\n",
    )
    result = analyze_makefile(root, root / "Makefile")
    assert result["status"] == "NEEDS_IMPROVEMENT"
    assert {row["rule_id"] for row in result["findings"]} == {"make.recipe.locked_python"}

    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nreplay:\n\t$(PYTHON) ops/scripts/replay.py\n",
    )
    assert analyze_makefile(root, root / "Makefile")["status"] == "PASS"


def test_makefile_analyzer_detects_missing_literal_script(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nrun:\n\t$(PYTHON) ops/scripts/missing.py\n",
    )
    result = analyze_makefile(root, root / "Makefile")
    assert any(row["rule_id"] == "make.recipe.script_resolution" for row in result["findings"])


def test_pyproject_analyzer_detects_interpreter_and_lock_drift(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(
        root / "pyproject.toml",
        "[project]\n"
        'requires-python = ">=3.12"\n\n'
        "[tool.uv]\n"
        "package = false\n\n"
        "[tool.ruff]\n"
        'target-version = "py311"\n\n'
        "[tool.mypy]\n"
        'python_version = "3.11"\n\n'
        "[tool.pyright]\n"
        'pythonVersion = "3.11"\n',
    )
    result = analyze_pyproject(root, root / "pyproject.toml")
    rule_ids = [row["rule_id"] for row in result["findings"]]
    assert result["status"] == "NEEDS_IMPROVEMENT"
    assert rule_ids.count("python.interpreter.version_alignment") == 3
    assert "python.uv.lock_presence" in rule_ids


def test_assessment_separates_ownership_and_derives_root_guard(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_root_guard(root)
    write(root / "ops/scripts/replay.py", "print('ok')\n")
    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nreplay:\n\tpython3 ops/scripts/replay.py\n",
    )
    policy = dp.load_policy()
    obligation = {
        "surface": "makefile_contract",
        "target": {"path": "Makefile", "present": True},
        "required_action": {
            "type": "REFRESH",
            "mode": "OWNER_NATIVE",
            "owner": "l9-update-agent-docs",
            "executor": None,
        },
        "evidence": [],
        "lifecycle": {"status": "OPEN", "reason": "fixture", "terminal": False},
        "validation": {"required": ["target_freshness"], "results": []},
        "blockers": [],
    }
    assessed = assess_surface_obligations(root, policy, [obligation])[0]
    assert assessed["ownership"] == {
        "obligation_owner": "l9-update-agent-docs",
        "semantic_owner": "repository-operator-contract",
        "execution_owner": "repository-native",
        "mutation_guard": "root-file-protection",
    }
    assert assessed["assessment"]["disposition"] == "IMPROVE"
    assert assessed["assessment"]["mutation_guard"]["rule"] == "additive_only"
    assert assessed["required_action"]["owner"] == "repository-native"
    assert "material_improvement" in assessed["validation"]["required"]


def test_clean_operational_surface_is_preserved(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_root_guard(root)
    write(root / "ops/scripts/replay.py", "print('ok')\n")
    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nreplay:\n\t$(PYTHON) ops/scripts/replay.py\n",
    )
    policy = dp.load_policy()
    obligation = {
        "surface": "makefile_contract",
        "target": {"path": "Makefile", "present": True},
        "required_action": {
            "type": "REFRESH",
            "mode": "OWNER_NATIVE",
            "owner": "l9-update-agent-docs",
            "executor": None,
        },
        "evidence": [],
        "lifecycle": {"status": "OPEN", "reason": "fixture", "terminal": False},
        "validation": {"required": ["target_freshness"], "results": []},
        "blockers": [],
    }
    assessed = assess_surface_obligations(root, policy, [obligation])[0]
    assert assessed["assessment"]["status"] == "PASS"
    assert assessed["assessment"]["disposition"] == "PRESERVE"
    assert assessed["required_action"]["type"] == "PRESERVE"
    assert assessed["lifecycle"]["status"] == "PRESERVED"
    assert assessed["lifecycle"]["terminal"] is True


def test_emit_generated_registry_identity() -> None:
    root = PACK.parents[1]
    generator = root / "ops/scripts/build_claude_skill_registry.py"
    spec = importlib.util.spec_from_file_location("_repo_docs_registry_probe", generator)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registry = module.build_registry(root)
    skill = next(row for row in registry["skills"] if row["name"] == "l9-update-agent-docs")
    raise AssertionError(
        json.dumps(
            {
                "generation_id": registry["generation_id"],
                "source_skill_corpus_sha256": registry["source_skill_corpus_sha256"],
                "skill_sha256": skill["skill_sha256"],
            },
            sort_keys=True,
        )
    )
