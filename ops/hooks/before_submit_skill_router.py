#!/usr/bin/env python3
"""Cursor beforeSubmitPrompt adapter for the L9 proactive skill router.

Thin I/O wrapper over ops/skill_routing (CANONICAL_LAW §2.1):

1. Scores via shared route_prompt() against ops/generated/skill-registry.json
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

ROUTER_REL = Path("ops/skill_routing/route_prompt.py")
STATE_PATH = Path.home() / ".cursor" / "l9" / "skill-route.json"


def load_routing(root: Path):
    path = root / ROUTER_REL
    spec = importlib.util.spec_from_file_location("l9_skill_routing_cursor", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load skill routing: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def resolve_root() -> Path:
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / ROUTER_REL).is_file():
            routing = load_routing(candidate)
            if (candidate / routing.REGISTRY_REL).is_file():
                return candidate
    home = Path.home() / ".cursor-governance"
    if (home / ROUTER_REL).is_file():
        routing = load_routing(home)
        if (home / routing.REGISTRY_REL).is_file():
            return home
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ROUTER_REL).is_file():
            routing = load_routing(parent)
            if (parent / routing.REGISTRY_REL).is_file():
                return parent
    return home


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


def kernel_pass_inject(payload: dict[str, Any]) -> str:
    """Plan/tree kernels fire in kernel_gate.py before precommit, not here.

    Mid-session inject applied kernels too early and re-ran checks later.
    Keep the payload argument so callers and tests stay stable.
    """
    del payload
    return ""


def merge_context(inject: str, route: str) -> str:
    inject = inject.strip()
    route = route.strip()
    if inject and route:
        return inject + "\n\n" + route
    return inject or route


def context_text(recommendation: dict[str, Any]) -> str:
    supporting = recommendation["supporting"]
    support_text = (
        " Supporting: " + ", ".join(f"`{name}`" for name in supporting) + "." if supporting else ""
    )
    if recommendation.get("source") == "explicit_hint":
        return (
            "L9 explicit skill hint: Read "
            f"`{recommendation['primary']}` (SKILL.md) before continuing.{support_text} "
            "Do not execute mutations from this hint alone — requires explicit user "
            "authority, campaign packet, and/or human approve per the skill contract. "
            "This route grants no mutation authority."
        )
    return (
        "High-confidence L9 skill route: Read and follow "
        f"`{recommendation['primary']}` (SKILL.md) as your first action before normal "
        f"execution.{support_text} Use at most one primary and two supporting skills. "
        "Follow that skill's contract. Do not auto-execute a different explicit-only skill."
    )


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload: dict[str, Any] = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    inject = kernel_pass_inject(payload)
    if os.environ.get("L9_PROACTIVE_SKILLS", "true").lower() != "true":
        out: dict[str, Any] = {"continue": True}
        if inject:
            out["additional_context"] = inject
        print(json.dumps(out))
        return 0
    try:
        prompt = extract_prompt(payload)
        route = ""
        if prompt:
            root = resolve_root()
            routing = load_routing(root)
            root = routing.resolve_root(Path(__file__))
            registry = routing.load_registry(root)
            recommendation = routing.route_prompt(prompt, registry)
            if recommendation is not None:
                persist_recommendation(recommendation, payload, root)
                route = context_text(recommendation)
        combined = merge_context(inject, route)
        out = {"continue": True}
        if combined:
            out["additional_context"] = combined
        print(json.dumps(out))
        return 0
    except Exception as exc:  # routing fail-open; inject still emitted
        print(f"WARN: Cursor L9 skill router degraded: {exc}", file=sys.stderr)
        out = {"continue": True}
        if inject:
            out["additional_context"] = inject
        print(json.dumps(out))
        return 0


def _self_test() -> int:
    if merge_context("INJECT", "ROUTE") != "INJECT\n\nROUTE":
        print("FAIL: merge_context prepend", file=sys.stderr)
        return 1
    if merge_context("", "ROUTE") != "ROUTE":
        print("FAIL: merge_context route-only", file=sys.stderr)
        return 1
    print("PASS: before_submit_skill_router prepend")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    raise SystemExit(main())
