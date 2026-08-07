#!/usr/bin/env python3
"""Back-compat wrapper → reconcile_llm_rule_adapters.py.

Historically this pointed `.claude/rules` at raw `rules/` (.mdc). That mount is
wrong for Claude (expects `.md`). The multi-adapter ingress now symlinks peers
to `environment/generated/llm-rules/`. Prefer calling
`reconcile_llm_rule_adapters.py` directly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from reconcile_llm_rule_adapters import reconcile_adapters  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    import json

    try:
        payload = reconcile_adapters(
            args.root.resolve(),
            workspace=(args.workspace or Path.cwd()).resolve(),
            check=args.check,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(payload, indent=2, sort_keys=True))

    bad = any(r["status"] in {"error", "drift"} for r in payload["results"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
