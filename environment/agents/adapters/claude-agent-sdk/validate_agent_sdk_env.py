#!/usr/bin/env python3
"""Validate the Claude Agent SDK adapter's own obligations.

Every check names a property of this adapter and the file that owns it; no
invariant registry is invented here.

  SETTING_SOURCES    the option payload loads project settings (l9_agent.py)
  SHADOW_POLICY      the payload carries no policy that .claude/settings.json /
                     .mcp.json own, and no appended governance system prompt
  GOVERNANCE_INPUTS  CLAUDE.md, .claude/settings.json, .mcp.json exist in the repo
  REPORT_IGNORED     the default report path is gitignored (runs never dirty the tree)
  DEPENDENCY_BOUND   pyproject.toml extra `agent-sdk` pins claude-agent-sdk and
                     uv.lock carries that exact version
  SDK_IMPORT         claude_agent_sdk imports from this interpreter

Exit 0 PASS, 1 FAIL (an obligation is broken), 3 UNKNOWN (no obligation is
broken but at least one could not be determined — e.g. the extra is not synced).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
SDK_EXTRA = "agent-sdk"
SDK_DIST = "claude-agent-sdk"
# Keys owned by project settings. Passing any of them re-authors governance.
SHADOW_POLICY_KEYS = (
    "allowed_tools",
    "disallowed_tools",
    "hooks",
    "agents",
    "can_use_tool",
    "mcp_servers",
    "strict_mcp_config",
    "settings",
    "plugins",
    "extra_args",
)


def _load_agent() -> ModuleType:
    spec = importlib.util.spec_from_file_location("l9_agent", HERE / "l9_agent.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load l9_agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_options(kwargs: dict) -> list[str]:
    errors: list[str] = []
    if "project" not in (kwargs.get("setting_sources") or []):
        errors.append('SETTING_SOURCES: setting_sources must include "project"')
    shadow = sorted(k for k in SHADOW_POLICY_KEYS if k in kwargs)
    if shadow:
        errors.append(f"SHADOW_POLICY: option payload re-authors project policy via {shadow}")
    prompt = kwargs.get("system_prompt")
    if isinstance(prompt, dict) and prompt.get("append"):
        errors.append("SHADOW_POLICY: system_prompt appends adapter-authored governance")
    return errors


def check_report_ignored(repo: Path, report_rel: Path) -> tuple[list[str], list[str]]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "-q", report_rel.as_posix()],
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return [], []
    if proc.returncode == 1:
        return [f"REPORT_IGNORED: {report_rel} is not gitignored; a run would dirty the tree"], []
    return [], [f"REPORT_IGNORED: git check-ignore exited {proc.returncode}"]


def bound_sdk_pin(pyproject: dict) -> str | None:
    extras = pyproject.get("project", {}).get("optional-dependencies", {})
    for req in extras.get(SDK_EXTRA, []):
        name, sep, version = str(req).partition("==")
        if sep and name.strip() == SDK_DIST:
            return version.strip()
    return None


def locked_versions(lock: dict, name: str) -> set[str]:
    return {str(pkg.get("version")) for pkg in lock.get("package", []) if pkg.get("name") == name}


def check_dependency(repo: Path) -> list[str]:
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    pin = bound_sdk_pin(pyproject)
    if pin is None:
        return [f"DEPENDENCY_BOUND: pyproject extra {SDK_EXTRA!r} has no {SDK_DIST}==<ver> pin"]
    lock = tomllib.loads((repo / "uv.lock").read_text(encoding="utf-8"))
    if pin not in locked_versions(lock, SDK_DIST):
        return [f"DEPENDENCY_BOUND: uv.lock does not carry {SDK_DIST}=={pin}; run uv lock"]
    return []


def sdk_importable() -> bool:
    return importlib.util.find_spec("claude_agent_sdk") is not None


def validate(agent: ModuleType | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, unknowns)."""
    agent = agent or _load_agent()
    repo = Path(agent.REPO)
    errors = check_options(agent.option_kwargs())
    errors += [f"GOVERNANCE_INPUTS: missing {rel}" for rel in agent.missing_governance(repo)]
    ignored_errors, unknowns = check_report_ignored(repo, agent.DEFAULT_REPORT)
    errors += ignored_errors
    errors += check_dependency(repo)
    if not sdk_importable():
        unknowns.append(
            f"SDK_IMPORT: claude_agent_sdk not importable here "
            f"(uv sync --locked --extra {SDK_EXTRA})"
        )
    return errors, unknowns


def main() -> int:
    errors, unknowns = validate()
    for line in errors:
        print(line, file=sys.stderr)
    for line in unknowns:
        print(line)
    verdict = "FAIL" if errors else "UNKNOWN" if unknowns else "PASS"
    print(f"validate_agent_sdk_env: {verdict}")
    return 1 if errors else 3 if unknowns else 0


if __name__ == "__main__":
    sys.exit(main())
