#!/usr/bin/env python3
"""Claude Code UserPromptSubmit adapter for the L9 skill router.

Thin I/O wrapper: scoring lives in ops/skill_routing (CANONICAL_LAW §2.1).
Never blocks a prompt; never invokes a skill itself.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

ROUTER_REL = Path("ops/skill_routing/route_prompt.py")


def load_routing(root: Path):
    path = root / ROUTER_REL
    spec = importlib.util.spec_from_file_location("l9_skill_routing", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load skill routing: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def find_governance_root() -> Path:
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / ROUTER_REL).is_file():
            return candidate
    home = Path.home() / ".cursor-governance"
    if (home / ROUTER_REL).is_file():
        return home
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ROUTER_REL).is_file():
            return parent
    return home


def log_recommendation(payload: dict[str, Any], recommendation: dict[str, Any]) -> None:
    if os.environ.get("L9_SKILL_USAGE_LOGGING", "true").lower() != "true":
        return
    log_dir = Path.home() / ".claude" / "l9"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "event": "router_recommendation",
            "session_id": payload.get("session_id", ""),
            "workspace": payload.get("cwd", ""),
            "route_id": recommendation["route_id"],
            "primary": recommendation["primary"],
            "supporting": recommendation["supporting"],
            "score": recommendation["score"],
            "source": recommendation.get("source", "route"),
        }
        with (log_dir / "skill-usage.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except OSError:
        pass


def main() -> int:
    if os.environ.get("L9_PROACTIVE_SKILLS", "true").lower() != "true":
        return 0
    try:
        payload = json.load(sys.stdin)
        prompt = str(payload.get("prompt", ""))
        root = find_governance_root()
        routing = load_routing(root)
        root = routing.resolve_root(Path(__file__))
        registry = routing.load_registry(root)
        recommendation = routing.route_prompt(prompt, registry)
        if recommendation is None:
            return 0
        supporting = recommendation["supporting"]
        support_text = (
            " Supporting candidates: " + ", ".join(f"`{name}`" for name in supporting) + "."
            if supporting
            else ""
        )
        if recommendation.get("source") == "explicit_hint":
            context = (
                "L9 explicit skill hint: Read "
                f"`{recommendation['primary']}` (SKILL.md) before continuing."
                f"{support_text} Do not execute mutations from this hint alone — requires "
                "explicit user authority, campaign packet, and/or human approve. "
                "This route grants no mutation authority."
            )
        else:
            context = (
                "High-confidence L9 skill route: invoke "
                f"`{recommendation['primary']}` through the Skill tool before normal execution."
                f"{support_text} Use at most one primary and two supporting skills. "
                "Do not auto-execute explicit-only skills without a hint_allowed route. "
                "This route grants no mutation authority."
            )
        log_recommendation(payload, recommendation)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": context,
                    }
                }
            )
        )
        return 0
    except Exception as exc:  # fail-open by contract
        print(f"WARN: L9 skill router degraded: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
