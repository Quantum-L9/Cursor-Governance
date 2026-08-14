#!/usr/bin/env python3
"""Keep the generated-artifact allowlist honest.

`ops/scripts/classify_generated_dirtiness.sh` decides whether gate dirtiness is
tolerable by asking `is_generated_path`. That allowlist
(``GENERATED_PATH_PREFIXES``) is hand-maintained and decoupled from the
generators it describes, so a new generator output would be classified as a
non-generated autofix and hard-fail `make pr` for no good reason.

Two checks, both cheap:

1. Every path a forced ``sync()`` reports writing is matched by
   ``is_generated_path``. The sync is idempotent — it rewrites nothing that is
   already current — so this is safe to run on a live tree.
2. The writer declaration for ``sync-generated-artifacts`` in
   ops/config/precommit-hook-contract.json covers the same prefixes, so the two
   lists cannot drift apart silently.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from sync_generated_artifacts import (  # noqa: E402
    GENERATED_PATH_PREFIXES,
    is_generated_path,
    sync,
)


def check_contract_prefixes(root: Path) -> list[str]:
    contract_path = root / "ops" / "config" / "precommit-hook-contract.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read {contract_path}: {exc}"]

    entry = (contract.get("hooks") or {}).get("sync-generated-artifacts") or {}
    declared = set(entry.get("output_prefixes") or [])
    missing = set(GENERATED_PATH_PREFIXES) - declared
    return [
        f"prefix {prefix!r} is in GENERATED_PATH_PREFIXES but not declared as an "
        "output_prefix of sync-generated-artifacts in the hook contract"
        for prefix in sorted(missing)
    ]


def check_forced_sync(root: Path) -> list[str]:
    result = sync(root, force=True)
    # A generator that could not run proves nothing; report it rather than
    # passing vacuously (the generators need the project interpreter, not
    # whatever python3 happens to be first on PATH).
    errors = [
        f"forced sync could not complete: {message}" for message in result.get("errors", [])
    ]
    errors.extend(
        f"forced sync wrote {path!r}, which is_generated_path() does not match — "
        "add it to GENERATED_PATH_PREFIXES or the gate will hard-fail on it"
        for path in result.get("wrote", [])
        if not is_generated_path(path)
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SCRIPTS.parents[1])
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="only compare the declared prefix lists; do not run generators",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    errors = check_contract_prefixes(root)
    if not args.no_sync:
        errors.extend(check_forced_sync(root))

    if errors:
        print("FAIL: generated-artifact allowlist drift")
        for error in errors:
            print(f"  {error}")
        return 1
    print("OK: generated outputs are all covered by GENERATED_PATH_PREFIXES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
