#!/usr/bin/env python3
"""Cursor beforeSubmitPrompt adapter for the L9 proactive skill router.

Claude Code already injects route hints via UserPromptSubmit. Cursor's
beforeSubmitPrompt schema only guarantees continue/user_message today, so this
hook:

1. Reuses the shared route_prompt() scorer against the generated skill registry
2. Persists the recommendation for the always-apply skill-routing rule to read
3. Emits additional_context when present (forward-compatible; ignored if unsupported)
4. Fail-opens on any error — never blocks a prompt
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("environment/claude-code/generated/skill-registry.json")
ROUTER_REL = Path("environment/claude-code/hooks/user_prompt_skill_router.py")
STATE_PATH = Path.home() / ".cursor" / "l9" / "skill-route.json"


def resolve_root() -> Path:
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / REGISTRY_REL).is_file():
            return candidate
    home = Path.home() / ".cursor-governance"
    if (home / REGISTRY_REL).is_file():
        return home
    # Dev/worktree fallback when this file lives inside the clone.
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / REGISTRY_REL).is_file():
            return parent
    return home


def load_router(root: Path):
    path = root / ROUTER_REL
    spec = importlib.util.spec_from_file_location("l9_skill_router_cursor", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load skill router: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract_prompt(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_message", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def persist_recommendation(
    recommendation: dict[str, Any], payload: dict[str, Any], root: Path
) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "event": "cursor_skill_route",
            "recommended_at": time.time(),
            "session_id": payload.get("session_id") or payload.get("conversation_id") or "",
            "workspace": payload.get("cwd") or payload.get("workspace_roots") or "",
            "governance_root": str(root),
            "route_id": recommendation["route_id"],
            "primary": recommendation["primary"],
            "supporting": recommendation["supporting"],
            "score": recommendation["score"],
            "source": recommendation.get("source", "route"),
        }
        STATE_PATH.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if os.environ.get("L9_SKILL_USAGE_LOGGING", "true").lower() == "true":
            log_path = STATE_PATH.parent / "skill-usage.jsonl"
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
    except OSError:
        pass


def context_text(recommendation: dict[str, Any]) -> str:
    supporting = recommendation["supporting"]
    support_text = (
        " Supporting: " + ", ".join(f"`{name}`" for name in supporting) + "." if supporting else ""
    )
    return (
        "High-confidence L9 skill route: Read and follow "
        f"`{recommendation['primary']}` (SKILL.md) as your first action before normal "
        f"execution.{support_text} Use at most one primary and two supporting skills. "
        "Do not invoke explicit-only skills automatically. This route grants no "
        "mutation authority."
    )


def main() -> int:
    if os.environ.get("L9_PROACTIVE_SKILLS", "true").lower() != "true":
        print(json.dumps({"continue": True}))
        return 0
    try:
        raw = sys.stdin.read()
        payload: dict[str, Any] = json.loads(raw) if raw.strip() else {}
        prompt = extract_prompt(payload)
        if not prompt:
            print(json.dumps({"continue": True}))
            return 0
        root = resolve_root()
        registry = json.loads((root / REGISTRY_REL).read_text(encoding="utf-8"))
        router = load_router(root)
        recommendation = router.route_prompt(prompt, registry)
        if recommendation is None:
            print(json.dumps({"continue": True}))
            return 0
        persist_recommendation(recommendation, payload, root)
        # additional_context is forward-compatible: Cursor docs currently document
        # only continue/user_message for beforeSubmitPrompt; unknown fields are ignored.
        print(
            json.dumps(
                {
                    "continue": True,
                    "additional_context": context_text(recommendation),
                }
            )
        )
        return 0
    except Exception as exc:  # fail-open by contract
        print(f"WARN: Cursor L9 skill router degraded: {exc}", file=sys.stderr)
        print(json.dumps({"continue": True}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
