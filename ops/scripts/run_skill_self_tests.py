#!/usr/bin/env python3
"""Validate and execute the canonical skill self-test surface.

`ops/config/python-contract.json` owns the registered skill roots. This adapter
proves that every live `skills/*/scripts/*self_test.py` belongs to one of those
roots and executes every discovered script in a fresh Python process from its
skill root. New self-tests in an unregistered skill fail closed instead of
silently falling out of CI.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = REPO_ROOT / "ops" / "config" / "python-contract.json"
SELF_TEST_GLOB = "skills/*/scripts/*self_test.py"
TIMEOUT_SECONDS = 900


class ContractError(RuntimeError):
    """The declared skill self-test topology does not match repository reality."""


def load_contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ContractError("python contract must be a JSON object")
    return data


def registered_roots(contract: dict[str, Any]) -> list[str]:
    raw = contract.get("skill_self_test_roots")
    if not isinstance(raw, list) or not raw:
        raise ContractError("skill_self_test_roots must be a non-empty list")
    roots: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.startswith("skills/") or item.count("/") != 1:
            raise ContractError(f"invalid skill_self_test_roots entry: {item!r}")
        if item in roots:
            raise ContractError(f"duplicate skill_self_test_roots entry: {item}")
        roots.append(item)
    return roots


def discover_self_tests(root: Path) -> list[Path]:
    return sorted(path for path in root.glob(SELF_TEST_GLOB) if path.is_file())


def validate_contract(root: Path, contract: dict[str, Any]) -> list[Path]:
    roots = registered_roots(contract)
    registered = set(roots)
    tests = discover_self_tests(root)
    if not tests:
        raise ContractError("no live skill self-tests discovered")

    discovered_roots = {test.parent.parent.relative_to(root).as_posix() for test in tests}
    unregistered = sorted(discovered_roots - registered)
    missing = sorted(registered - discovered_roots)
    if unregistered:
        raise ContractError("unregistered skill self-test roots: " + ", ".join(unregistered))
    if missing:
        raise ContractError("registered skill roots have no *self_test.py: " + ", ".join(missing))

    for skill_root in roots:
        skill_dir = root / skill_root
        if not (skill_dir / "SKILL.md").is_file():
            raise ContractError(f"registered self-test root has no SKILL.md: {skill_root}")

    suites = contract.get("suites")
    if not isinstance(suites, list):
        raise ContractError("python contract suites must be a list")
    matches = [
        suite
        for suite in suites
        if isinstance(suite, dict) and suite.get("id") == "skill-contracts"
    ]
    if len(matches) != 1:
        raise ContractError("python contract must define exactly one skill-contracts suite")
    suite = matches[0]
    if suite.get("kind") != "command_sequence":
        raise ContractError("skill-contracts must use command_sequence")
    owned = suite.get("owned_paths")
    if not isinstance(owned, list) or "skills" not in owned:
        raise ContractError("skill-contracts must own skills/ so new self-tests select the suite")

    return tests


def run_self_tests(root: Path, tests: list[Path]) -> int:
    base_env = dict(os.environ)
    base_env["PYTHONDONTWRITEBYTECODE"] = "1"
    for test in tests:
        skill_root = test.parent.parent
        relative = test.relative_to(skill_root).as_posix()
        label = test.relative_to(root).as_posix()
        print(f"[skill-contracts] RUN {label}", flush=True)
        try:
            completed = subprocess.run(
                [sys.executable, relative],
                cwd=skill_root,
                env=base_env,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"[skill-contracts] TIMEOUT {label}", file=sys.stderr)
            return 124
        if completed.returncode != 0:
            print(
                f"[skill-contracts] FAIL {label} exit={completed.returncode}",
                file=sys.stderr,
            )
            return completed.returncode
    print(f"[skill-contracts] PASS {len(tests)} fresh-process self-tests")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    root = args.repo_root.resolve()
    try:
        contract = load_contract(args.contract.resolve())
        tests = validate_contract(root, contract)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"[skill-contracts] CONTRACT ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"[skill-contracts] contract PASS: {len(tests)} self-tests across registered skill roots")
    if args.check_only:
        return 0
    return run_self_tests(root, tests)


if __name__ == "__main__":
    raise SystemExit(main())
