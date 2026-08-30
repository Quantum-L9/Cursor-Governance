#!/usr/bin/env python3
"""Resolve the execution personality of the current session.

Two personalities exist: Claude is unleashed, Cursor is constrained. Which one
applies is decided here, once, before autonomous work begins — from the runtime,
never from model identity.

    CLAUDE_CODE_REMOTE=true            -> claude_cloud
    Claude Code without that flag      -> claude_local
    Cursor                             -> cursor

The resolver also reports the settings that can silently re-impose a ceiling
after the L9 scheduler is unleashed: the L9 lane caps, Claude Code's own
concurrent-subagent and spawn-depth limits, the dynamic-workflow size guideline,
and any global subagent-model override. A Claude session that resolves to a
constrained profile is a configuration defect, and this module names it.

Stdlib only: SessionStart runs it with bare `python3`, without a venv.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

POLICY_REL = Path("ops/autonomy/claude-execution-profiles.json")
RESOURCE_POLICY_REL = Path("autonomy/policies/resource-classes.json")

CLAUDE_SURFACES = ("claude_local", "claude_cloud")


def governance_root() -> Path:
    return Path.home() / ".cursor-governance"


def load_policy(root: Path | None = None) -> dict[str, Any]:
    path = (root or governance_root()) / POLICY_REL
    return json.loads(path.read_text(encoding="utf-8"))


def classify(env: Mapping[str, str], policy: Mapping[str, Any]) -> str:
    """Resolve exactly one runtime surface. Model identity is never consulted."""

    rules = policy.get("classification", {})
    surface = str(env.get(str(rules.get("surface_env", "L9_GOVERNANCE_SURFACE")), "")).strip()
    is_claude = surface == str(rules.get("claude_surface_value", "claude-code")) or bool(
        env.get("CLAUDECODE") or env.get("CLAUDE_CODE_ENTRYPOINT")
    )
    if is_claude:
        remote = str(env.get(str(rules.get("cloud_env", "CLAUDE_CODE_REMOTE")), "")).strip()
        if remote == str(rules.get("cloud_value", "true")):
            return "claude_cloud"
        return "claude_local"
    return "cursor"


def resolve_provider(env: Mapping[str, str], policy: Mapping[str, Any]) -> str:
    base_url = str(env.get("ANTHROPIC_BASE_URL", "")).lower()
    model = str(env.get("ANTHROPIC_MODEL", "")).lower()
    for name, config in policy.get("providers", {}).items():
        needle = str(config.get("match_base_url") or "").lower()
        if needle and (needle in base_url or needle in model):
            return name
    if base_url and "anthropic.com" not in base_url:
        return "unknown"
    return "anthropic"


def worker_target(
    provider: str,
    policy: Mapping[str, Any],
    root: Path | None = None,
) -> tuple[int | None, str]:
    """Worker slots for this provider, and where the number came from."""

    declared = policy.get("providers", {}).get(provider, {})
    target = declared.get("worker_target")
    if isinstance(target, int):
        ceiling = declared.get("provider_concurrency_ceiling")
        reserved = declared.get("reserved_control_slots")
        return target, f"{provider} ceiling {ceiling} - {reserved} reserved"
    path = (root or governance_root()) / RESOURCE_POLICY_REL
    try:
        resource_policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "no provider ceiling declared and resource policy unreadable"
    block = resource_policy.get("global", {})
    ceiling = block.get("provider_concurrency_ceiling")
    reserved = block.get("reserved_control_slots", 0)
    if isinstance(ceiling, int):
        return max(0, ceiling - int(reserved)), "resource-classes.json global"
    return None, "no provider ceiling declared"


def settings_candidates(workspace: Path, home: Path) -> list[Path]:
    """Settings files in Claude Code precedence order (most specific first)."""

    return [
        workspace / ".claude" / "settings.local.json",
        workspace / ".claude" / "settings.json",
        home / ".claude" / "settings.json",
    ]


def read_setting(key: str, workspace: Path, home: Path) -> tuple[Any, str | None]:
    for path in settings_candidates(workspace, home):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, Mapping) and key in data:
            return data[key], str(path)
    return None, None


#: Env names the Claude Code runtime rewrites as a session nests. The live
#: process value describes the depth REMAINING at this level, not how the
#: surface is configured, so comparing it to a static expectation reports a
#: permanent defect that no configuration change can clear. Mirrors
#: verify_account_env.RUNTIME_MANAGED, which documents the observed 3 -> 1
#: decrement within a single session and declines to report it as a deviation.
#: Both modules must agree; a defect the operator cannot act on trains them to
#: ignore the banner.
RUNTIME_DECREMENTED = frozenset({"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"})


def declared_env_int(name: str, workspace: Path, home: Path) -> int | None:
    """Read an `env` sub-key from the scopes that DECLARE configuration.

    Deliberately skips `.claude/settings.local.json`. That file is written from
    the live process environment by the hosted-env overlay, so it mirrors
    runtime rather than intent; reading it here would reintroduce the very
    decremented value this function exists to look past.
    """

    for path in (workspace / ".claude" / "settings.json", home / ".claude" / "settings.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, Mapping):
            continue
        env_block = data.get("env")
        if isinstance(env_block, Mapping) and name in env_block:
            try:
                return int(str(env_block[name]).strip())
            except (TypeError, ValueError):
                return None
    return None


def _int_env(env: Mapping[str, str], name: str) -> int | None:
    try:
        return int(str(env[name]).strip())
    except (KeyError, TypeError, ValueError):
        return None


def resolve(
    *,
    env: Mapping[str, str] | None = None,
    workspace: Path | None = None,
    home: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    env = os.environ if env is None else env
    workspace = Path(env.get("CLAUDE_PROJECT_DIR", os.getcwd())) if workspace is None else workspace
    home = Path(env.get("HOME", str(Path.home()))) if home is None else home
    policy = load_policy(root)

    surface = classify(env, policy)
    expected = policy["profiles"][surface]
    provider = resolve_provider(env, policy) if surface in CLAUDE_SURFACES else "cursor"
    target, target_source = (
        worker_target(provider, policy, root) if surface in CLAUDE_SURFACES else (None, "")
    )

    guideline, guideline_source = read_setting("workflowSizeGuideline", workspace, home)
    disable_workflows, _ = read_setting("disableWorkflows", workspace, home)
    native_limit = _int_env(env, "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS")
    spawn_depth_live = _int_env(env, "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH")
    spawn_depth_declared = declared_env_int(
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH", workspace, home
    )
    # Declared wins where it exists: a decremented live value describes this
    # agent's remaining nesting budget, not a misconfiguration. Where nothing is
    # declared, the live value is the only evidence there is, and a depth of 1
    # genuinely does block nested delegation.
    spawn_depth = spawn_depth_declared if spawn_depth_declared is not None else spawn_depth_live
    max_parallel = _int_env(env, "L9_AUTONOMY_MAX_PARALLEL")
    max_mutation_lanes = _int_env(env, "L9_AUTONOMY_MAX_MUTATION_LANES")
    subagent_model = str(env.get("CLAUDE_CODE_SUBAGENT_MODEL", "")).strip()
    natives = policy.get("native_defaults", {})

    resolved: dict[str, Any] = {
        "runtime_surface": surface,
        "provider": provider,
        "execution_profile": expected["execution_profile"],
        "concurrency_policy": expected["concurrency_policy"],
        "parallel_read": expected["parallel_read"],
        "mutation_parallelism": expected["mutation_parallelism"],
        "model_policy": expected["model_policy"],
        "workflow_size_guideline": (
            guideline if guideline is not None else natives.get("workflowSizeGuideline")
        ),
        "workflow_size_guideline_source": guideline_source or "Claude Code default",
        "native_subagent_limit": (
            native_limit
            if native_limit is not None
            else natives.get("CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS")
        ),
        "native_subagent_limit_declared": native_limit is not None,
        "subagent_spawn_depth": (
            spawn_depth
            if spawn_depth is not None
            else natives.get("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH")
        ),
        "subagent_spawn_depth_live": spawn_depth_live,
        "subagent_spawn_depth_declared": spawn_depth_declared,
        "l9_max_parallel": max_parallel,
        "l9_max_mutation_lanes": max_mutation_lanes,
        "worker_target": target,
        "worker_target_source": target_source,
        "subagent_model_override": subagent_model or None,
        "defects": [],
    }
    if surface in CLAUDE_SURFACES:
        resolved["defects"] = _claude_defects(
            resolved,
            expected=expected,
            disable_workflows=bool(disable_workflows)
            or str(env.get("CLAUDE_CODE_DISABLE_WORKFLOWS", "")).strip() == "1",
        )
    return resolved


def _claude_defects(
    resolved: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
    disable_workflows: bool,
) -> list[str]:
    """Everything that would silently re-impose a ceiling on a Claude surface."""

    defects: list[str] = []
    target = resolved["worker_target"]
    ceiling = target if isinstance(target, int) else expected["max_parallel"]

    max_parallel = resolved["l9_max_parallel"]
    if max_parallel is not None and max_parallel < ceiling:
        defects.append(
            f"L9_AUTONOMY_MAX_PARALLEL={max_parallel} is below the {ceiling}-worker target — "
            "a Cursor economy cap is constraining Claude"
        )
    lanes = resolved["l9_max_mutation_lanes"]
    if lanes is not None and lanes < int(expected["max_mutation_lanes"]):
        defects.append(
            f"L9_AUTONOMY_MAX_MUTATION_LANES={lanes} serializes mutation by lane count; "
            "mutation must be bounded by claim conflict"
        )
    native = resolved["native_subagent_limit"]
    if not resolved["native_subagent_limit_declared"]:
        defects.append(
            f"CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS is unset — Claude Code's default of "
            f"{native} becomes the effective ceiling and refuses further spawns"
        )
    elif isinstance(native, int) and native < ceiling:
        defects.append(
            f"CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS={native} is below the {ceiling}-worker "
            "target — native Claude concurrency becomes the bottleneck"
        )
    depth = resolved["subagent_spawn_depth"]
    if isinstance(depth, int) and depth < 2:
        defects.append(
            f"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH={depth} blocks nested delegation "
            "(main -> specialist -> delegated specialist)"
        )
    guideline = resolved["workflow_size_guideline"]
    if guideline != expected["workflow_size_guideline"]:
        defects.append(
            f"workflowSizeGuideline={guideline!r} aims workflows below the task; expected "
            f"{expected['workflow_size_guideline']!r}"
        )
    if disable_workflows:
        defects.append("dynamic workflows are disabled on a maximum-velocity surface")
    if resolved["subagent_model_override"]:
        defects.append(
            f"CLAUDE_CODE_SUBAGENT_MODEL={resolved['subagent_model_override']} forces every "
            "subagent onto one model — role-specific model choice is the policy"
        )
    return defects



def _depth_note(resolved: Mapping[str, Any]) -> str:
    """Explain a live depth below the declared one without calling it a defect."""

    declared = resolved.get("subagent_spawn_depth_declared")
    live = resolved.get("subagent_spawn_depth_live")
    if declared is None or live is None or live >= declared:
        return ""
    return f" (declared; runtime-decremented to {live} at this nesting level)"


def render_block(resolved: Mapping[str, Any]) -> str:
    native = resolved["native_subagent_limit"]
    native_note = "" if resolved["native_subagent_limit_declared"] else " (Claude Code default)"
    target = resolved["worker_target"]
    lines = [
        f"runtime_surface: {resolved['runtime_surface']}",
        f"provider: {resolved['provider']}",
        f"execution_profile: {resolved['execution_profile']}",
        f"concurrency_policy: {resolved['concurrency_policy']}",
        f"native_subagent_limit: {native}{native_note}",
        f"subagent_spawn_depth: {resolved['subagent_spawn_depth']}{_depth_note(resolved)}",
        f"workflow_size_guideline: {resolved['workflow_size_guideline']} "
        f"({resolved['workflow_size_guideline_source']})",
        f"mutation_parallelism: {resolved['mutation_parallelism']}",
        f"model_policy: {resolved['model_policy']}",
    ]
    if target is not None:
        lines.append(f"worker_target: {target} ({resolved['worker_target_source']})")
    for defect in resolved["defects"]:
        lines.append(f"CONFIG DEFECT: {defect}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Emit the resolved profile as JSON")
    parser.add_argument(
        "--fail-on-defect",
        action="store_true",
        help="Exit non-zero when a Claude surface resolves to a constrained configuration",
    )
    arguments = parser.parse_args(argv)
    try:
        resolved = resolve(workspace=arguments.workspace, root=arguments.root)
    except (OSError, ValueError, KeyError) as exc:
        # SessionStart is fail-open: report, never block a session.
        print(f"execution profile: unresolved ({exc})", file=sys.stderr)
        return 0 if not arguments.fail_on_defect else 1
    print(
        json.dumps(resolved, indent=2, sort_keys=True) if arguments.json else render_block(resolved)
    )
    if arguments.fail_on_defect and resolved["defects"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
