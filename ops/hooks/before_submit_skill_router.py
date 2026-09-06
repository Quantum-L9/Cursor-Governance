#!/usr/bin/env python3
"""Cursor beforeSubmitPrompt adapter for the L9 Virtual Skill Plane.

I/O adapter only (CANONICAL_LAW §2.1). Every concern is delegated:

  root resolution / registry schema   ops/skill_routing/registry.py
  scoring                              ops/skill_routing/route_prompt.py
  skill lookup / path validation       ops/skill_routing/materialize.py
  receipt scope / encoding / atomics   ops/skill_routing/receipt.py
  conversation identity                ops/skill_routing/session_locator.py

Contract (hard invariants):
  * every prompt event writes exactly one conversation-scoped receipt state:
    routed | no_route | disabled | degraded — a no-route prompt can never
    inherit the previous prompt's route
  * stdout is always {"continue": true}; prompt submission fails open
  * no additional_context (unsupported on beforeSubmitPrompt), no global
    state file, no rediscovery of selected skills, no network, no LLM, no MCP
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from typing import Any

PACKAGE_REL = Path("ops/skill_routing")
PACKAGE_NAME = "l9_skill_routing"


def _package_roots() -> list[Path]:
    roots: list[Path] = []
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        roots.append(Path(configured).expanduser())
    roots.append(Path.home() / ".cursor-governance")
    roots.extend(Path(__file__).resolve().parents)
    return roots


def load_plane() -> types.SimpleNamespace:
    """Import the shared routing package as ``l9_skill_routing`` from disk."""
    cached = sys.modules.get(PACKAGE_NAME)
    if cached is not None and getattr(cached, "__l9_plane__", None) is not None:
        return cached.__l9_plane__
    for root in _package_roots():
        init = root / PACKAGE_REL / "__init__.py"
        if not init.is_file():
            continue
        spec = importlib.util.spec_from_file_location(
            PACKAGE_NAME, init, submodule_search_locations=[str(init.parent)]
        )
        if not spec or not spec.loader:
            continue
        package = importlib.util.module_from_spec(spec)
        sys.modules[PACKAGE_NAME] = package
        spec.loader.exec_module(package)
        plane = types.SimpleNamespace(
            registry=importlib.import_module(f"{PACKAGE_NAME}.registry"),
            route_prompt=importlib.import_module(f"{PACKAGE_NAME}.route_prompt"),
            materialize=importlib.import_module(f"{PACKAGE_NAME}.materialize"),
            receipt=importlib.import_module(f"{PACKAGE_NAME}.receipt"),
            session_locator=importlib.import_module(f"{PACKAGE_NAME}.session_locator"),
        )
        package.__l9_plane__ = plane
        return plane
    raise RuntimeError("ops/skill_routing package not found (L9_GOVERNANCE_DIR?)")


def extract_prompt(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_message", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def proactive_enabled() -> bool:
    return os.environ.get("L9_PROACTIVE_SKILLS", "true").lower() == "true"


def _usage_log(receipt: dict[str, Any], state_root: Path) -> None:
    if os.environ.get("L9_SKILL_USAGE_LOGGING", "true").lower() != "true":
        return
    if receipt.get("status") != "routed":
        return
    try:
        decision = receipt["decision"]
        event = {
            "event": "cursor_skill_route",
            "conversation_key": receipt.get("conversation_key", ""),
            "issued_at": receipt.get("issued_at"),
            "route_id": decision.get("route_id"),
            "primary": decision["primary"]["name"],
            "supporting": [item["name"] for item in decision.get("supporting", [])],
            "score": decision.get("score"),
            "source": decision.get("source"),
        }
        log_path = state_root.parent / "skill-usage.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except (OSError, KeyError, TypeError) as exc:
        # Usage logging is observability only: never let it change the
        # receipt or block the prompt, but say why it was skipped.
        print(f"WARN: Cursor L9 skill router: usage log skipped: {exc}", file=sys.stderr)


def route_event(payload: dict[str, Any], plane: types.SimpleNamespace) -> dict[str, Any] | None:
    """Resolve scope, route, materialize, and persist one receipt state."""
    locator = plane.session_locator.locator_from_payload(payload)
    if locator is None:
        print("WARN: Cursor L9 skill router: payload has no conversation_id", file=sys.stderr)
        return None
    state_root = Path(locator.state_root)
    prompt = extract_prompt(payload)
    registry = None
    generation_id = ""
    identity: dict[str, str] = {}

    def emit(status: str, **fields: Any) -> dict[str, Any]:
        receipt = plane.receipt.build_receipt(
            status=status,
            locator=locator,
            generation_id=generation_id,
            registry_identity=identity,
            prompt=prompt or None,
            **fields,
        )
        plane.receipt.write_receipt(receipt, state_root)
        _usage_log(receipt, state_root)
        return receipt

    try:
        if not proactive_enabled():
            try:
                registry = plane.registry.load_registry()
                generation_id, identity = registry.generation_id, registry.identity()
            except plane.registry.RegistryError as exc:
                # Registry identity is optional on a disabled receipt: the
                # receipt must still be written so no prior route stays live.
                registry = None
                print(f"WARN: Cursor L9 skill router: registry unavailable: {exc}", file=sys.stderr)
            return emit("disabled", reason="L9_PROACTIVE_SKILLS is not true")
        registry = plane.registry.load_registry()
        generation_id, identity = registry.generation_id, registry.identity()
        if not prompt.strip():
            return emit("no_route", reason="empty prompt")
        decision = plane.route_prompt.route_prompt(prompt, registry.data)
        if decision is None:
            return emit("no_route", reason="no recommendation")
        materialized = plane.materialize.materialize_route(decision, registry)
        return emit("routed", decision=decision, materialized=materialized)
    except Exception as exc:  # routing infrastructure failure → degraded, never stale
        print(f"WARN: Cursor L9 skill router degraded: {exc}", file=sys.stderr)
        try:
            return emit("degraded", reason=f"{type(exc).__name__}: {exc}"[:500])
        except Exception as inner:  # best effort only
            print(f"WARN: degraded receipt not written: {inner}", file=sys.stderr)
            return None


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload: dict[str, Any] = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    try:
        route_event(payload, load_plane())
    except Exception as exc:  # fail-open: prompt submission is never blocked
        print(f"WARN: Cursor L9 skill router unavailable: {exc}", file=sys.stderr)
    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
