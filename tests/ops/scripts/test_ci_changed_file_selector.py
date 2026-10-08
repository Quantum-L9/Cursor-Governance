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
from select_pr_pytest_paths import tests_naming_path as naming_path  # noqa: E402

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


def test_test_suite_environment_is_owned_by_ensure_gov_python() -> None:
    """The Test Suite venv is materialized by the repository's own owner, once.

    Regression (PR #696 CI): a raw ``uv sync`` built ``.venv`` without the
    readiness state ``ensure_uv_environment.sh`` owns (``.l9-uv-fingerprint``,
    the memory artifact seal). The first repository test to reach
    ``run_pr_gate.sh`` → ``ensure_gov_python.sh`` then re-entered sync + seal
    under live xdist workers and ``.venv/bin/python3`` vanished mid-run. The
    wrapper must run before pytest, and nothing else may sync that venv.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    test_block = text.split("name: Test Suite", 1)[1]
    active = [line for line in test_block.splitlines() if not line.lstrip().startswith("#")]
    active_text = "\n".join(active)
    assert 'bash ops/scripts/ensure_gov_python.sh "$PWD"' in active_text
    assert "uv sync" not in active_text, "one environment owner: no raw uv sync in Test Suite"
    assert active_text.index("ensure_gov_python.sh") < active_text.index(
        "run_python_test_suites.py"
    ), "the environment must be complete before pytest-xdist starts"
    assert sum(line.count("run_python_test_suites.py") for line in active) == 1
    # `uv run --frozen` re-syncs the venv and reinstalls the pip-sealed memory
    # wheel from the lock's path source, erasing the PEP 610 seal the owner
    # just wrote; the first gate call under xdist would then force-reinstall
    # it again. The runner is invoked with the verified locked interpreter,
    # exactly as run_pr_gate.sh does locally.
    assert "uv run" not in active_text, "no uv run in Test Suite: it undoes the memory seal"
    assert ".venv/bin/python ops/scripts/run_python_test_suites.py" in active_text
    # Changed-file / local-vs-ci selection is untouched by the environment change.
    assert "--changed-file" in active_text
    assert "profile=local" in active_text
    assert "profile=ci" in active_text
    assert 'gh api "repos/' not in active_text


def test_runner_help_names_local_and_pull_request() -> None:
    help_text = (SCRIPTS / "run_python_test_suites.py").read_text(encoding="utf-8")
    assert "changed-file selector for local make pr and pull_request CI" in help_text
    assert "Local pr-check only" not in help_text


def test_standing_remediate_zero_string_gone_from_live_surfaces() -> None:
    """Ceremony publish stays ``PR_REMEDIATE=0 make pr``.

    Rule 48 and surface_profile.yaml teach that ceremony. Remediator
    SKILL.md verifies with ``make precommit-repo``. An in-scope fix
    publishes with ``git push``. A fix that touches a file outside the
    PR publishes a stacked child with ``PR_STACK=auto PR_REMEDIATE=0 make pr``
    (ADR-0052).
    """
    assert "PR_REMEDIATE=0 make pr" in RULE_48.read_text(encoding="utf-8")
    assert "PR_REMEDIATE=0 make pr" in SURFACE.read_text(encoding="utf-8")
    skill = REMEDIATOR_SKILL.read_text(encoding="utf-8")
    assert "make precommit-repo" in skill
    assert "git push" in skill
    assert "PR_STACK=auto PR_REMEDIATE=0 make pr" in skill


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


def test_live_ops_script_change_skips_non_owner_suites() -> None:
    changed = ["ops/scripts/select_pr_pytest_paths.py"]
    selected = select_pr_pytest_paths(changed)
    assert "." not in selected
    assert any("test_select_pr_pytest_paths.py" in item for item in selected)
    suites = validate_registry(_load_json(REGISTRY_PATH))
    by_id = {suite["id"]: suite for suite in suites}
    assert _suite_intersects(by_id["repo-root"], selected, changed, selector)
    for suite_id in (
        "skill-contracts",
        "claude-code-autonomy",
        "subagent-generated-data-wave3",
        "program-execution-controller",
    ):
        assert not _suite_intersects(by_id[suite_id], selected, changed, selector), suite_id


def test_changed_or_new_skill_self_test_selects_skill_contracts() -> None:
    suites = validate_registry(_load_json(REGISTRY_PATH))
    by_id = {suite["id"]: suite for suite in suites}
    for changed in (
        ["skills/l9-wire-into-repo/scripts/self_test.py"],
        ["skills/l9-future-skill/scripts/self_test.py"],
    ):
        selected = select_pr_pytest_paths(changed)
        assert _suite_intersects(by_id["skill-contracts"], selected, changed, selector)


def test_directory_path_selects_non_generic_basename_mentions(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_full.py").write_text('assert "ops/scripts/run_pr_gate.sh"\n', encoding="utf-8")
    (tests / "test_base.py").write_text('assert "run_pr_gate.sh"\n', encoding="utf-8")
    (tests / "test_make.py").write_text('assert "Makefile"\n', encoding="utf-8")
    selected = naming_path("ops/scripts/run_pr_gate.sh", repo_root=tmp_path)
    assert selected == ["tests/test_full.py", "tests/test_base.py"]
    generic = naming_path("ops/scripts/Makefile", repo_root=tmp_path)
    assert generic == []


def test_run_pr_gate_selects_lifecycle_and_failure_suites() -> None:
    selected = naming_path("ops/scripts/run_pr_gate.sh")
    assert "tests/ops/scripts/test_pr_lifecycle.py" in selected
    assert "tests/ops/scripts/test_pr_gate_failure.py" in selected
    assert naming_path("README.md") == []


def test_selected_skill_test_does_not_run_skill_self_tests() -> None:
    suites = validate_registry(_load_json(REGISTRY_PATH))
    by_id = {suite["id"]: suite for suite in suites}
    changed = ["ops/scripts/run_pr_gate.sh"]
    selected = ["skills/l9-update-agent-docs/tests/test_consumer_contracts.py"]
    assert not _suite_intersects(by_id["skill-contracts"], selected, changed, selector)


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
