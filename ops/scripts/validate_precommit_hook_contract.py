#!/usr/bin/env python3
"""Fail closed when a pre-commit hook is not declared read_only or writer.

pre-commit attributes "files were modified by this hook" to whichever hook was
running when the tracked worktree changed, regardless of who actually wrote
(pre_commit/commands/run.py ``_run_single_hook``). Without a declaration there
is no mechanical way to exonerate a validator, so an agent chases the wrong
script. This validator keeps ops/config/precommit-hook-contract.json in lockstep
with .pre-commit-config.yaml so ops/scripts/attribute_tree_writers.sh always has
a ground truth to reason from.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

VALID_MODES = {"read_only", "writer"}


def load_configured_hook_ids(config_path: Path) -> list[str]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    ids: list[str] = []
    for repo in data.get("repos", []) or []:
        for hook in repo.get("hooks", []) or []:
            hook_id = hook.get("id")
            if hook_id:
                ids.append(str(hook_id))
    return ids


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    config_path = root / ".pre-commit-config.yaml"
    contract_path = root / "ops" / "config" / "precommit-hook-contract.json"

    if not config_path.is_file():
        return [f"missing {config_path}"]
    if not contract_path.is_file():
        return [f"missing {contract_path}"]

    contract: dict[str, Any] = json.loads(contract_path.read_text(encoding="utf-8"))
    declared: dict[str, Any] = contract.get("hooks") or {}
    configured = load_configured_hook_ids(config_path)

    for hook_id in configured:
        entry = declared.get(hook_id)
        if entry is None:
            errors.append(
                f"hook '{hook_id}' is configured in .pre-commit-config.yaml but undeclared in "
                "ops/config/precommit-hook-contract.json — declare it read_only or writer"
            )
            continue
        mode = entry.get("mode")
        if mode not in VALID_MODES:
            errors.append(
                f"hook '{hook_id}' has mode {mode!r}; expected one of {sorted(VALID_MODES)}"
            )
            continue
        if mode == "writer" and not isinstance(entry.get("output_prefixes"), list):
            errors.append(f"writer hook '{hook_id}' must declare an output_prefixes list")

    for hook_id in declared:
        if hook_id not in configured:
            errors.append(
                f"hook '{hook_id}' is declared in the contract but no longer configured in "
                ".pre-commit-config.yaml — remove the stale declaration"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()

    errors = validate(args.root.resolve())
    if errors:
        print("FAIL: pre-commit hook contract drift")
        for error in errors:
            print(f"  {error}")
        return 1
    print("OK: every pre-commit hook is declared read_only or writer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
