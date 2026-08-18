#!/usr/bin/env python3
"""Regenerate autonomy/policy_loader.py from its JSON sources.

`autonomy/policy_loader.py` embeds the autonomy control-plane policies,
examples, and golden specs as literal JSON so the runtime performs no
filesystem I/O (Sonar pythonsecurity:S8707). The JSON files under
`autonomy/policies`, `autonomy/examples`, and `autonomy/tests/golden` remain
the source of truth; this script re-embeds them.

Usage:
    python3 ops/scripts/regenerate_autonomy_policy_loader.py            # write
    python3 ops/scripts/regenerate_autonomy_policy_loader.py --check    # drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIRECTORY = Path("autonomy/policies")
EXAMPLE_DIRECTORY = Path("autonomy/examples")
GOLDEN_DIRECTORY = Path("autonomy/tests/golden")
TARGET = Path("autonomy/policy_loader.py")

HEADER = """from __future__ import annotations

import copy
import json
from typing import Any

# Embedded payloads — no filesystem I/O (Sonar pythonsecurity:S8707).
# Edit autonomy/{policies,examples,tests/golden} JSON, then regenerate this module.
# Regenerate: python3 ops/scripts/regenerate_autonomy_policy_loader.py
"""

FOOTER = """

def load_policy(name: str) -> Any:
    try:
        return copy.deepcopy(_POLICIES[name])
    except KeyError as exc:
        raise KeyError(f"Unknown policy: {name}") from exc


def load_example(name: str) -> Any:
    try:
        return copy.deepcopy(_EXAMPLES[name])
    except KeyError as exc:
        raise KeyError(f"Unknown example: {name}") from exc


def load_golden_spec(name: str) -> Any:
    try:
        return copy.deepcopy(_GOLDEN[name])
    except KeyError as exc:
        raise KeyError(f"Unknown golden spec: {name}") from exc
"""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_policies(root: Path) -> dict[str, Any]:
    directory = root / POLICY_DIRECTORY
    return {path.stem: read_json(path) for path in sorted(directory.glob("*.json"))}


def collect_examples(root: Path) -> dict[str, Any]:
    directory = root / EXAMPLE_DIRECTORY
    return {
        path.relative_to(directory).as_posix(): read_json(path)
        for path in sorted(directory.rglob("*.json"))
    }


def collect_golden(root: Path) -> dict[str, Any]:
    directory = root / GOLDEN_DIRECTORY
    return {path.name: read_json(path) for path in sorted(directory.glob("*.json"))}


def render_block(name: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, indent=2, sort_keys=True)
    if '"""' in body:
        raise SystemExit(f"{name} payload contains a triple quote and cannot be embedded")
    return f'{name}: dict[str, Any] = json.loads(\n    """\n{body}\n"""\n)\n'


def render_module(root: Path) -> str:
    blocks = [
        render_block("_POLICIES", collect_policies(root)),
        render_block("_EXAMPLES", collect_examples(root)),
        render_block("_GOLDEN", collect_golden(root)),
    ]
    return HEADER + "\n" + "\n".join(blocks) + FOOTER


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when the embedded module is stale instead of rewriting it",
    )
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    target = root / TARGET
    rendered = render_module(root)
    current = target.read_text(encoding="utf-8") if target.is_file() else ""
    if rendered == current:
        print(f"OK: {TARGET} matches its JSON sources")
        return 0
    if arguments.check:
        print(
            f"FAIL: {TARGET} is stale; run "
            "python3 ops/scripts/regenerate_autonomy_policy_loader.py",
            file=sys.stderr,
        )
        return 1
    target.write_text(rendered, encoding="utf-8")
    print(f"WROTE: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
