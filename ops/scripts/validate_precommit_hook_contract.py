#!/usr/bin/env python3
"""Fail closed when a pre-commit hook is not declared read_only or writer.

Each hook also declares its locality. ops/scripts/run_pr_precommit.sh runs the
GOVERNANCE catalog with a consumer workspace as cwd, so a hook whose entry is a
governance-tree path dies on a missing file there. ``governance`` marks such a
hook (the runner skips it in consumers); ``any`` marks a hook that runs in every
workspace. A local hook whose entry resolves under this root but is declared
``any`` fails here, so a newly added governance-local hook cannot ship without
a consumer decision.

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
VALID_LOCALITIES = {"governance", "any"}


def load_configured_hook_ids(config_path: Path) -> list[str]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    ids: list[str] = []
    for repo in data.get("repos", []) or []:
        for hook in repo.get("hooks", []) or []:
            hook_id = hook.get("id")
            if hook_id:
                ids.append(str(hook_id))
    return ids


def load_local_hook_entries(config_path: Path) -> dict[str, str]:
    """hook id -> ``entry`` for hooks of ``repo: local``."""
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    entries: dict[str, str] = {}
    for repo in data.get("repos", []) or []:
        if repo.get("repo") != "local":
            continue
        for hook in repo.get("hooks", []) or []:
            if hook.get("id"):
                entries[str(hook["id"])] = str(hook.get("entry", ""))
    return entries


def governance_tree_path(root: Path, entry: str) -> str | None:
    """The first relative entry token that names a file under ``root``."""
    for token in entry.split():
        if "/" in token and not token.startswith("/") and (root / token).is_file():
            return token
    return None


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
    local_entries = load_local_hook_entries(config_path)

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
        locality = entry.get("locality")
        if locality not in VALID_LOCALITIES:
            errors.append(
                f"hook '{hook_id}' has locality {locality!r}; expected one of "
                f"{sorted(VALID_LOCALITIES)}"
            )
            continue
        local_path = governance_tree_path(root, local_entries.get(hook_id, ""))
        if locality == "any" and local_path is not None:
            errors.append(
                f"hook '{hook_id}' entry resolves against the governance tree ({local_path}) "
                "but is declared locality 'any' — it cannot run in a consumer workspace; "
                "declare it 'governance'"
            )

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
    print("OK: every pre-commit hook declares its mode and locality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
