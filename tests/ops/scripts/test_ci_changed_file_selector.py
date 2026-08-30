"""PR CI Test Suite uses the same changed-file selector as local make pr."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import select_pr_pytest_paths as selector  # noqa: E402
from run_python_test_suites import (  # noqa: E402
    _load_json,
    _suite_env,
    _suite_intersects,
    strip_ceremony_knobs,
    validate_registry,
)
from select_pr_pytest_paths import (  # noqa: E402
    REGISTRY_PATH,
    infer_test_path,
    select_pr_pytest_paths,
)

WORKFLOW = ROOT / ".github" / "workflows" / "l9-lint-test.yml"
RULE_48 = ROOT / "rules" / "48-make-pr-remediation.mdc"
SURFACE = ROOT / "ops" / "autonomy" / "surface_profile.yaml"
REMEDIATOR_SKILL = ROOT / "skills" / "l9-pr-remediation" / "SKILL.md"


def test_workflow_scope_exports_files_and_test_suite_does_not_recall_gh() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "files: ${{ steps.decide.outputs.files }}" in text
    assert "files_unusable: ${{ steps.decide.outputs.files_unusable }}" in text
    assert "fail open to --profile ci" in text
    test_block = text.split("name: Test Suite", 1)[1]
    assert 'gh api "repos/' not in test_block
    assert "--changed-file" in test_block
    assert "profile=local" in test_block
    assert "profile=ci" in test_block
    active = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    assert sum(line.count("run_python_test_suites.py") for line in active) == 1


def test_runner_help_names_local_and_pull_request() -> None:
    help_text = (SCRIPTS / "run_python_test_suites.py").read_text(encoding="utf-8")
    assert "changed-file selector for local make pr and pull_request CI" in help_text
    assert "Local pr-check only" not in help_text


def test_standing_remediate_zero_string_gone_from_live_surfaces() -> None:
    """One-finish teachers name ceremony publish; remediator publish is not it.

    Rule 48 and surface_profile.yaml teach ``PR_REMEDIATE=0 make pr``.
    Remediator SKILL.md still verifies with ``make precommit-repo`` and
    publishes with ``git push``.
    """
    assert "PR_REMEDIATE=0 make pr" in RULE_48.read_text(encoding="utf-8")
    assert "PR_REMEDIATE=0 make pr" in SURFACE.read_text(encoding="utf-8")
    skill = REMEDIATOR_SKILL.read_text(encoding="utf-8")
    assert "make precommit-repo" in skill
    assert "git push" in skill
    assert "do not run `make pr`" in skill


def test_foo_py_maps_to_named_test_not_dot(tmp_path: Path) -> None:
    (tmp_path / "ops" / "scripts").mkdir(parents=True)
    (tmp_path / "tests" / "ops" / "scripts").mkdir(parents=True)
    (tmp_path / "ops" / "scripts" / "foo.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "ops" / "scripts" / "test_foo.py").write_text(
        "def test_foo() -> None:\n    assert True\n", encoding="utf-8"
    )
    assert infer_test_path("ops/scripts/foo.py", repo_root=tmp_path) == (
        "tests/ops/scripts/test_foo.py"
    )


def test_live_ops_script_change_skips_autonomy_wave3_pe() -> None:
    changed = ["ops/scripts/select_pr_pytest_paths.py"]
    selected = select_pr_pytest_paths(changed)
    assert "." not in selected
    assert any("test_select_pr_pytest_paths.py" in item for item in selected)
    suites = validate_registry(_load_json(REGISTRY_PATH))
    by_id = {suite["id"]: suite for suite in suites}
    assert _suite_intersects(by_id["repo-root"], selected, changed, selector)
    for suite_id in (
        "claude-code-autonomy",
        "subagent-generated-data-wave3",
        "program-execution-controller",
    ):
        assert not _suite_intersects(by_id[suite_id], selected, changed, selector), suite_id


def test_markdown_only_file_list_is_empty_mapped_set() -> None:
    assert select_pr_pytest_paths(["README.md", "docs/plans/x.plan.md"]) == []


def test_suite_env_strips_inherited_ceremony_knobs(monkeypatch) -> None:
    monkeypatch.setenv("PR_OVERLAP", "ignore")
    monkeypatch.setenv("PR_OVERLAP_TELEMETRY", "open")
    monkeypatch.setenv("PR_STACK", "auto")
    monkeypatch.setenv("PR_REMEDIATE", "1")
    stripped = strip_ceremony_knobs(
        dict(
            **{
                k: "ignore"
                for k in (
                    "PR_OVERLAP",
                    "PR_OVERLAP_TELEMETRY",
                    "PR_STACK",
                    "PR_REMEDIATE",
                )
            }
        )
    )
    assert "PR_OVERLAP" not in stripped
    env = _suite_env({"env": {}}, {})
    assert "PR_OVERLAP" not in env
    assert "PR_STACK" not in env
    assert "PR_REMEDIATE" not in env
