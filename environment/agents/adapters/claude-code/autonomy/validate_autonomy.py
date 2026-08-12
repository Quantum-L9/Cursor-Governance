#!/usr/bin/env python3
"""Deterministic validation for the Claude Code autonomy runtime."""

from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent

REQUIRED_FILES = (
    "README.md",
    "__init__.py",
    "models.py",
    "readiness.py",
    "resource_locks.py",
    "scheduler.py",
    "state_store.py",
    "claim_lease.py",
    "worker_lane.py",
    "join_controller.py",
    "merge_coordinator.py",
    "bootstrap.py",
    "cli.py",
    "action-graph.schema.json",
    "resource-contract.schema.json",
    "join-barrier.schema.json",
    "profiles/pr-convergence.json",
    "examples/pr-convergence-campaign.json",
)

UNFINISHED_MARKERS = ("TODO", "FIXME", "NotImplementedError", "raise NotImplemented")


def main() -> int:
    failures: list[str] = []
    print("=== Claude Code autonomy runtime validation ===")

    for rel in REQUIRED_FILES:
        path = HERE / rel
        if path.is_file():
            print(f"  OK: present {rel}")
        else:
            failures.append(f"missing required file: {rel}")

    for path in sorted(HERE.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            print(f"  OK: json {path.relative_to(HERE)}")
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"invalid JSON {path.relative_to(HERE)}: {exc}")

    with tempfile.TemporaryDirectory() as compile_tmp:
        compile_root = Path(compile_tmp)
        for path in sorted(HERE.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(HERE).with_suffix(".pyc")
            cfile = compile_root / relative
            cfile.parent.mkdir(parents=True, exist_ok=True)
            try:
                py_compile.compile(str(path), cfile=str(cfile), doraise=True)
                print(f"  OK: compile {path.relative_to(HERE)}")
            except py_compile.PyCompileError as exc:
                failures.append(f"compile failed {path.relative_to(HERE)}: {exc.msg}")

    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path.suffix not in {".py", ".md", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in UNFINISHED_MARKERS:
            if marker in text and path.name != Path(__file__).name:
                failures.append(f"unfinished marker {marker!r} in {path.relative_to(HERE)}")

    hook = PARENT / "hooks" / "session_start_claude_governance.sh"
    if hook.is_file():
        result = subprocess.run(
            ["bash", "-n", str(hook)], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("  OK: bash syntax hooks/session_start_claude_governance.sh")
        else:
            failures.append(f"hook bash syntax failed: {result.stderr.strip()}")

    sys.path.insert(0, str(PARENT))
    suite = unittest.defaultTestLoader.discover(str(HERE / "tests"), pattern="test_*.py")
    test_result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not test_result.wasSuccessful():
        failures.append(
            f"unittest failures={len(test_result.failures)} errors={len(test_result.errors)}"
        )

    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [sys.executable, str(HERE / "bootstrap.py"), "--workspace", tmp, "--json"],
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "L9_AUTONOMY_ENABLED": "true",
                "L9_AUTONOMY_STATE_DIR": ".l9/autonomy",
            },
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            failures.append(f"bootstrap did not emit JSON: {exc}: {result.stdout!r}")
        else:
            if result.returncode == 0 and payload.get("status") == "no_active_campaign":
                print("  OK: bootstrap no-active-campaign smoke test")
            else:
                failures.append(f"bootstrap smoke failed: rc={result.returncode} payload={payload}")

    print()
    if failures:
        for failure in failures:
            print(f"  FAIL: {failure}")
        print(f"RESULT: FAIL - {len(failures)} issue(s)")
        return 1
    print("RESULT: PASS - concurrent autonomy runtime is structurally and behaviorally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
