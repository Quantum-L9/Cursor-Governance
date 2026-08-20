"""Surface execution personality: Claude unleashed, Cursor constrained.

The resolver decides which personality applies before autonomous work begins,
and names anything that would silently re-impose a ceiling on Claude. These
tests pin the classification rules, the defect detection, and the committed
Claude settings that cloud sessions consume on clone.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from execution_profile import (  # noqa: E402
    classify,
    load_policy,
    render_block,
    resolve,
    resolve_provider,
)

POLICY = load_policy(ROOT)
SETTINGS_TEMPLATE = ROOT / "environment/agents/adapters/claude-code/settings.template.json"

CLAUDE_ENV = {
    "L9_GOVERNANCE_SURFACE": "claude-code",
    "L9_AUTONOMY_MAX_PARALLEL": "480",
    "L9_AUTONOMY_MAX_MUTATION_LANES": "128",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "480",
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "3",
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
}


def _resolve(env: dict[str, str], tmp_path: Path) -> dict:
    workspace = tmp_path / "workspace"
    home = tmp_path / "home"
    (workspace / ".claude").mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    (workspace / ".claude" / "settings.json").write_text(
        json.dumps({"workflowSizeGuideline": "unrestricted"}),
        encoding="utf-8",
    )
    return resolve(env=env, workspace=workspace, home=home, root=ROOT)


# --- classification ---------------------------------------------------------


def test_cloud_sessions_classify_from_the_documented_discriminator() -> None:
    env = {**CLAUDE_ENV, "CLAUDE_CODE_REMOTE": "true"}
    assert classify(env, POLICY) == "claude_cloud"


def test_local_claude_sessions_classify_as_claude_local() -> None:
    assert classify(CLAUDE_ENV, POLICY) == "claude_local"


def test_cursor_stays_the_constrained_surface() -> None:
    assert classify({"L9_GOVERNANCE_SURFACE": "cursor"}, POLICY) == "cursor"
    assert POLICY["profiles"]["cursor"]["execution_profile"] == "constrained"


def test_classification_never_depends_on_model_identity(tmp_path: Path) -> None:
    for model in ("deepseek-v4-pro[1m]", "claude-opus-5", ""):
        env = {**CLAUDE_ENV, "ANTHROPIC_MODEL": model}
        assert classify(env, POLICY) == "claude_local"
        assert _resolve(env, tmp_path)["execution_profile"] == "maximum_velocity"


def test_provider_resolves_from_the_endpoint(tmp_path: Path) -> None:
    assert resolve_provider(CLAUDE_ENV, POLICY) == "deepseek"
    assert resolve_provider({"ANTHROPIC_BASE_URL": "https://api.anthropic.com"}, POLICY) == (
        "anthropic"
    )


def test_deepseek_worker_target_is_the_contract_ceiling(tmp_path: Path) -> None:
    resolved = _resolve(CLAUDE_ENV, tmp_path)
    assert resolved["provider"] == "deepseek"
    assert resolved["worker_target"] == 480


# --- both Claude surfaces are unleashed -------------------------------------


def test_both_claude_surfaces_saturate(tmp_path: Path) -> None:
    for env in (CLAUDE_ENV, {**CLAUDE_ENV, "CLAUDE_CODE_REMOTE": "true"}):
        resolved = _resolve(env, tmp_path)
        assert resolved["execution_profile"] == "maximum_velocity"
        assert resolved["concurrency_policy"] == "saturate"
        assert resolved["mutation_parallelism"] == "max_non_conflicting"
        assert resolved["model_policy"] == "best_available_per_role"
        assert resolved["workflow_size_guideline"] == "unrestricted"
        assert resolved["defects"] == []


def test_cursor_is_not_reported_as_defective(tmp_path: Path) -> None:
    resolved = _resolve({"L9_GOVERNANCE_SURFACE": "cursor"}, tmp_path)
    assert resolved["runtime_surface"] == "cursor"
    assert resolved["execution_profile"] == "constrained"
    assert resolved["defects"] == []


# --- every way a ceiling can creep back in ----------------------------------


def test_legacy_lane_caps_are_reported_as_defects(tmp_path: Path) -> None:
    env = {**CLAUDE_ENV, "L9_AUTONOMY_MAX_PARALLEL": "4", "L9_AUTONOMY_MAX_MUTATION_LANES": "2"}
    defects = " ".join(_resolve(env, tmp_path)["defects"])
    assert "L9_AUTONOMY_MAX_PARALLEL=4" in defects
    assert "L9_AUTONOMY_MAX_MUTATION_LANES=2" in defects


def test_unset_native_subagent_limit_is_a_defect(tmp_path: Path) -> None:
    env = {key: value for key, value in CLAUDE_ENV.items()}
    env.pop("CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS")
    resolved = _resolve(env, tmp_path)
    assert resolved["native_subagent_limit"] == 20
    assert any("CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS is unset" in d for d in resolved["defects"])


def test_native_limit_below_worker_target_is_a_defect(tmp_path: Path) -> None:
    env = {**CLAUDE_ENV, "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "20"}
    assert any("becomes the bottleneck" in d for d in _resolve(env, tmp_path)["defects"])


def test_blocked_nesting_is_a_defect(tmp_path: Path) -> None:
    env = {**CLAUDE_ENV, "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"}
    resolved = _resolve(env, tmp_path)
    assert resolved["subagent_spawn_depth"] == 1
    assert any("nested delegation" in d for d in resolved["defects"])


def test_global_subagent_model_override_is_a_defect(tmp_path: Path) -> None:
    env = {**CLAUDE_ENV, "CLAUDE_CODE_SUBAGENT_MODEL": "haiku"}
    assert any("CLAUDE_CODE_SUBAGENT_MODEL" in d for d in _resolve(env, tmp_path)["defects"])


def test_workflow_guideline_and_disable_are_defects(tmp_path: Path) -> None:
    workspace = tmp_path / "guideline-workspace"
    home = tmp_path / "guideline-home"
    (workspace / ".claude").mkdir(parents=True)
    home.mkdir()
    (workspace / ".claude" / "settings.json").write_text(
        json.dumps({"workflowSizeGuideline": "medium", "disableWorkflows": True}),
        encoding="utf-8",
    )
    resolved = resolve(env=CLAUDE_ENV, workspace=workspace, home=home, root=ROOT)
    defects = " ".join(resolved["defects"])
    assert "workflowSizeGuideline='medium'" in defects
    assert "workflows are disabled" in defects


def test_local_settings_win_over_project_settings(tmp_path: Path) -> None:
    workspace = tmp_path / "precedence-workspace"
    home = tmp_path / "precedence-home"
    (workspace / ".claude").mkdir(parents=True)
    home.mkdir()
    (workspace / ".claude" / "settings.json").write_text(
        json.dumps({"workflowSizeGuideline": "unrestricted"}), encoding="utf-8"
    )
    (workspace / ".claude" / "settings.local.json").write_text(
        json.dumps({"workflowSizeGuideline": "small"}), encoding="utf-8"
    )
    resolved = resolve(env=CLAUDE_ENV, workspace=workspace, home=home, root=ROOT)
    assert resolved["workflow_size_guideline"] == "small"


# --- reporting --------------------------------------------------------------


def test_block_reports_every_contract_field(tmp_path: Path) -> None:
    block = render_block(_resolve(CLAUDE_ENV, tmp_path))
    for field in (
        "runtime_surface:",
        "provider:",
        "execution_profile:",
        "concurrency_policy:",
        "native_subagent_limit:",
        "subagent_spawn_depth:",
        "workflow_size_guideline:",
        "mutation_parallelism:",
        "model_policy:",
    ):
        assert field in block
    assert "CONFIG DEFECT" not in block


def test_cli_can_fail_closed_on_a_constrained_claude_session(tmp_path: Path) -> None:
    workspace = tmp_path / "cli-workspace"
    (workspace / ".claude").mkdir(parents=True)
    env = {
        **CLAUDE_ENV,
        "L9_AUTONOMY_MAX_PARALLEL": "4",
        "HOME": str(tmp_path / "cli-home"),
        "PATH": "/usr/bin:/bin",
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "ops" / "autonomy" / "execution_profile.py"),
            "--root",
            str(ROOT),
            "--workspace",
            str(workspace),
            "--fail-on-defect",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 1
    assert "CONFIG DEFECT" in result.stdout


# --- the committed settings cloud sessions actually consume -----------------


def test_committed_claude_settings_carry_the_profile() -> None:
    for path in (SETTINGS_TEMPLATE, ROOT / ".claude" / "settings.json"):
        settings = json.loads(path.read_text(encoding="utf-8"))
        env = settings["env"]
        assert int(env["L9_AUTONOMY_MAX_PARALLEL"]) >= 480, path
        assert int(env["L9_AUTONOMY_MAX_MUTATION_LANES"]) >= 128, path
        assert int(env["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"]) >= 480, path
        assert int(env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"]) >= 2, path
        assert "CLAUDE_CODE_SUBAGENT_MODEL" not in env, path
        assert settings.get("workflowSizeGuideline") == "unrestricted", path
        assert not settings.get("disableWorkflows"), path


def test_session_start_hook_exposes_the_profile() -> None:
    hook = ROOT / "environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh"
    text = hook.read_text(encoding="utf-8")
    assert "execution_profile.py" in text
    assert "--- claude execution profile ---" in text
