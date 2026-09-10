from __future__ import annotations

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
    make_surface = policy["surfaces"]["makefile_contract"]
    python_surface = policy["surfaces"]["python_project_contract"]
    assert make_surface["analysis"]["analyzer"] == "makefile-contract-v1"
    assert python_surface["analysis"]["analyzer"] == "python-project-contract-v1"
    assert "validation" not in make_surface
    assert "validation" not in python_surface


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


def _obligation(surface: str, target: str) -> dict:
    return {
        "surface": surface,
        "target": {"path": target, "present": True},
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


def _finding_evidence(assessed: dict, rule_id: str) -> dict:
    finding = next(row for row in assessed["assessment"]["findings"] if row["rule_id"] == rule_id)
    evidence_id = finding["evidence_ids"][0]
    return next(row for row in assessed["evidence"] if row["id"] == evidence_id)


def test_handoff_finding_does_not_force_owner_native_refresh(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_root_guard(root)
    write(root / "ops/config/python-contract.json", "{not-json")
    write(root / "pyproject.toml", "[project]\nname = 'demo'\nrequires-python = '>=3.12'\n")
    assessed = assess_surface_obligations(
        root, dp.load_policy(), [_obligation("python_project_contract", "pyproject.toml")]
    )[0]
    assert assessed["assessment"]["disposition"] == "HANDOFF"
    assert assessed["required_action"]["type"] == "HANDOFF"
    assert assessed["required_action"]["mode"] == "EXTERNAL_OWNER"
    assert assessed["lifecycle"]["status"] == "HANDOFF_REQUIRED"
    assert any(row["remediation_class"] == "HANDOFF" for row in assessed["assessment"]["findings"])
    evidence = _finding_evidence(assessed, "python.self_test.contract_parse")
    assert evidence["source"] == "ops/config/python-contract.json"
    assert evidence["locator"]["value"] == "ops/config/python-contract.json"


def test_registry_finding_uses_python_contract_as_evidence_source(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_root_guard(root)
    write(root / "skills/demo/scripts/self_test.py", "print('ok')\n")
    write(root / "ops/config/python-contract.json", json.dumps({"skill_self_test_roots": []}))
    write(root / "conftest.py", "collect_ignore = ['skills/demo/scripts/self_test.py']\n")
    write(root / "pyproject.toml", "[project]\nname = 'demo'\nrequires-python = '>=3.12'\n")
    assessed = assess_surface_obligations(
        root, dp.load_policy(), [_obligation("python_project_contract", "pyproject.toml")]
    )[0]
    assert assessed["assessment"]["disposition"] == "IMPROVE"
    evidence = _finding_evidence(assessed, "python.self_test.registry")
    assert evidence["source"] == "ops/config/python-contract.json"


def test_collection_guard_runs_without_python_contract(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_root_guard(root)
    write(root / "skills/demo/scripts/self_test.py", "print('ok')\n")
    write(root / "pyproject.toml", "[project]\nname = 'demo'\nrequires-python = '>=3.12'\n")
    assessed = assess_surface_obligations(
        root, dp.load_policy(), [_obligation("python_project_contract", "pyproject.toml")]
    )[0]
    rule_ids = {row["rule_id"] for row in assessed["assessment"]["findings"]}
    assert "python.self_test.collection_guard" in rule_ids
    assert "python.self_test.registry" not in rule_ids
    evidence = _finding_evidence(assessed, "python.self_test.collection_guard")
    assert evidence["source"] == "pyproject.toml"


def test_missing_root_guard_still_assesses_clean_makefile(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(root / "ops/scripts/replay.py", "print('ok')\n")
    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nreplay:\n\t$(PYTHON) ops/scripts/replay.py\n",
    )
    assessed = assess_surface_obligations(
        root, dp.load_policy(), [_obligation("makefile_contract", "Makefile")]
    )[0]
    assert assessed["assessment"]["status"] == "PASS"
    assert assessed["assessment"]["disposition"] == "PRESERVE"
    assert assessed["assessment"]["mutation_guard"] is None
    assert assessed["lifecycle"]["status"] == "PRESERVED"


def test_makefile_ignores_non_python_script_mentions(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write(
        root / "Makefile",
        "clean:\n\trm -f generated.py\nstamp:\n\ttouch generated.py\nnote:\n\techo missing.py\n",
    )
    assert analyze_makefile(root, root / "Makefile")["status"] == "PASS"

    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nrun:\n\t$(PYTHON) ops/scripts/missing.py\n",
    )
    result = analyze_makefile(root, root / "Makefile")
    assert any(row["rule_id"] == "make.recipe.script_resolution" for row in result["findings"])


def test_clean_operational_surface_is_preserved(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_root_guard(root)
    write(root / "ops/scripts/replay.py", "print('ok')\n")
    write(
        root / "Makefile",
        "PYTHON := $(CURDIR)/.venv/bin/python\nreplay:\n\t$(PYTHON) ops/scripts/replay.py\n",
    )
    assessed = assess_surface_obligations(
        root, dp.load_policy(), [_obligation("makefile_contract", "Makefile")]
    )[0]
    assert assessed["assessment"]["status"] == "PASS"
    assert assessed["assessment"]["disposition"] == "PRESERVE"
    assert assessed["required_action"]["type"] == "PRESERVE"
    assert assessed["lifecycle"]["status"] == "PRESERVED"
    assert assessed["lifecycle"]["terminal"] is True
    freshness = next(
        row for row in assessed["validation"]["results"] if row["name"] == "target_freshness"
    )
    assert freshness["status"] == "NotApplicable"
