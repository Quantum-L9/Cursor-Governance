#!/usr/bin/env python3
"""Inject a high-confidence L9 skill recommendation on UserPromptSubmit.

The hook never blocks a prompt and never invokes a skill itself. Claude's native
Skill tool remains the invocation mechanism and all write-authority rules remain
independent.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("environment/claude-code/generated/skill-registry.json")


def normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9+#./_-]+", " ", text.lower()).split())


def resolve_root() -> Path:
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / REGISTRY_REL).is_file():
            return candidate
    return Path.home() / ".cursor-governance"


def phrase_hit(prompt: str, phrase: str) -> bool:
    return normalize(phrase) in prompt


def route_prompt(prompt: str, registry: dict[str, Any]) -> dict[str, Any] | None:
    routing = registry.get("routing", {})
    normalized = normalize(prompt)
    if not normalized:
        return None
    for pattern in routing.get("trivial_patterns", []):
        if re.search(str(pattern), normalized, flags=re.IGNORECASE):
            return None

    known = {item["name"]: item for item in registry.get("skills", [])}
    explicit = {name for name, item in known.items() if item.get("invocation") == "explicit_only"}
    best: tuple[int, dict[str, Any]] | None = None
    for route in routing.get("routes", []):
        primary = str(route.get("primary", ""))
        if not primary or primary in explicit:
            continue
        if any(phrase_hit(normalized, phrase) for phrase in route.get("negative_signals", [])):
            continue
        positives = [
            phrase for phrase in route.get("positive_signals", []) if phrase_hit(normalized, phrase)
        ]
        score = len(positives) * int(route.get("signal_weight", 4))
        if primary in normalized or primary.removeprefix("l9-").replace("-", " ") in normalized:
            score += 20
        required = route.get("required_any", [])
        if required and not any(phrase_hit(normalized, phrase) for phrase in required):
            score = 0
        if best is None or score > best[0]:
            best = (score, route)

    threshold = int(routing.get("force_threshold", 8))
    if best is None or best[0] < threshold:
        return None
    score, route = best
    max_supporting = int(routing.get("max_supporting", 2))
    supporting = [
        name
        for name in route.get("supporting", [])
        if name in known and name not in explicit and name != route.get("primary")
    ][:max_supporting]
    return {
        "route_id": route.get("id", "unknown"),
        "primary": route["primary"],
        "supporting": supporting,
        "score": score,
    }


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
        registry_path = resolve_root() / REGISTRY_REL
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        recommendation = route_prompt(prompt, registry)
        if recommendation is None:
            return 0
        supporting = recommendation["supporting"]
        support_text = (
            " Supporting candidates: " + ", ".join(f"`{name}`" for name in supporting) + "."
            if supporting
            else ""
        )
        context = (
            "High-confidence L9 skill route: invoke "
            f"`{recommendation['primary']}` through the Skill tool before normal execution."
            f"{support_text} Use at most one primary and two supporting skills. "
            "Do not invoke explicit-only skills automatically. "
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
