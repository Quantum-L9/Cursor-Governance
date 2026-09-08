#!/usr/bin/env python3
"""Shared L9 resolver — the gateway's manual fallback and a diagnostics CLI.

Runs the same deterministic pipeline the Cursor hook runs (registry →
route_prompt → materialize) without writing a receipt, or validates the
current receipt for a conversation. Local, deterministic, no network.

    resolve.py --prompt "<request>"            # route + materialize
    resolve.py --conversation-id <id>          # read + validate the receipt
    resolve.py --receipt <path>                # validate a receipt file
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

PACKAGE_NAME = "l9_skill_routing_resolve"


def _plane():
    if __package__:
        from . import materialize, receipt, registry, route_prompt, session_locator

        return registry, route_prompt, materialize, receipt, session_locator
    init = Path(__file__).resolve().parent / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME, init, submodule_search_locations=[str(init.parent)]
    )
    assert spec and spec.loader
    package = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = package
    spec.loader.exec_module(package)
    import importlib as _il

    return tuple(
        _il.import_module(f"{PACKAGE_NAME}.{name}")
        for name in ("registry", "route_prompt", "materialize", "receipt", "session_locator")
    )


def resolve_prompt(prompt: str, root: Path | None = None) -> dict[str, Any]:
    registry, route_prompt, materialize, _, _ = _plane()
    loaded = registry.load_registry(root)
    decision = route_prompt.route_prompt(prompt, loaded.data)
    if decision is None:
        return {"status": "no_route", "registry": loaded.identity()}
    materialized = materialize.materialize_route(decision, loaded)
    return {
        "status": "routed",
        "registry": loaded.identity(),
        "decision": {
            "route_id": decision["route_id"],
            "score": decision["score"],
            "source": decision["source"],
            "primary": materialized["primary"],
            "supporting": materialized["supporting"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=None, help="governance root")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="route and materialize this request")
    group.add_argument("--conversation-id", help="read the current receipt for a conversation")
    group.add_argument("--receipt", type=Path, help="validate this receipt file")
    parser.add_argument("--state-root", type=Path, default=None)
    args = parser.parse_args(argv)

    registry, _, _, receipt, session_locator = _plane()
    try:
        if args.prompt is not None:
            print(json.dumps(resolve_prompt(args.prompt, args.root), indent=2, sort_keys=True))
            return 0
        loaded = registry.load_registry(args.root)
        if args.receipt is not None:
            data = json.loads(args.receipt.read_text(encoding="utf-8"))
            problems = receipt.validate_receipt(
                data,
                conversation_id=str(data.get("conversation_id", "")),
                generation_id=loaded.generation_id,
            )
            print(json.dumps({"valid": not problems, "problems": problems}, indent=2))
            return 0 if not problems else 1
        state_root = args.state_root or session_locator.default_state_root()
        data = receipt.read_receipt(
            args.conversation_id, state_root=state_root, generation_id=loaded.generation_id
        )
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "degraded", "error": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
