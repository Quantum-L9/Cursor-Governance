#!/usr/bin/env python3
"""Deterministic validation for the shared Peer Execution autonomy runtime."""

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
REPO_ROOT = HERE.parents[2]

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


# Concurrency-policy truthfulness: every declared limit must be runtime
# enforced (ConcurrencyBudget lanes, or exclusive target-lineage write locks),
# or the policy is rejected here — silent no-op fields are forbidden.
ENFORCED_CONCURRENCY_LIMITS = frozenset(
    {
        "max_active_dispatches",
        "max_mutating_dispatches",
        "max_mutating_dispatches_per_target_lineage",
    }
)


def _concurrency_policy_failures() -> list[str]:
    policy_path = HERE.parents[1] / "registry" / "EXECUTION_CONCURRENCY_POLICY.yaml"
    if not policy_path.is_file():
        return [f"missing concurrency policy: {policy_path}"]
    try:
        import yaml

        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — a broken registry file is one finding
        return [f"unreadable concurrency policy {policy_path}: {exc}"]
    limits = dict(policy.get("limits") or {})
    failures: list[str] = []
    unsupported = sorted(set(limits) - ENFORCED_CONCURRENCY_LIMITS)
    if unsupported:
        failures.append(
            "concurrency policy declares limits nothing enforces "
            f"(silent no-op fields are forbidden): {unsupported}"
        )
    lineage = limits.get("max_mutating_dispatches_per_target_lineage")
    if lineage is not None and int(lineage) != 1:
        failures.append(
            "max_mutating_dispatches_per_target_lineage is enforced by exclusive "
            f"target-lineage write locks; only 1 is enforceable, got {lineage}"
        )
    return failures


def main() -> int:
    failures: list[str] = []
    print("=== Peer Execution autonomy runtime validation ===")
    failures.extend(_concurrency_policy_failures())
    for rel in REQUIRED_FILES:
        path = HERE / rel
        if not path.is_file():
            failures.append(f"missing required file: {rel}")
    for path in sorted(HERE.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"invalid JSON {path.relative_to(HERE)}: {exc}")
    with tempfile.TemporaryDirectory() as compile_tmp:
        compile_root = Path(compile_tmp)
        for path in sorted(HERE.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            cfile = compile_root / path.relative_to(HERE).with_suffix(".pyc")
            cfile.parent.mkdir(parents=True, exist_ok=True)
            try:
                py_compile.compile(str(path), cfile=str(cfile), doraise=True)
            except py_compile.PyCompileError as exc:
                failures.append(f"compile failed {path.relative_to(HERE)}: {exc.msg}")
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path.suffix not in {".py", ".md", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in UNFINISHED_MARKERS:
            if marker in text and path.name != Path(__file__).name:
                failures.append(f"unfinished marker {marker!r} in {path.relative_to(HERE)}")
    hook = REPO_ROOT / ".claude/hooks/session_start_claude_governance.sh"
    if hook.is_file():
        result = subprocess.run(
            ["bash", "-n", str(hook)], capture_output=True, text=True, check=False, timeout=30
        )
        if result.returncode != 0:
            failures.append(f"Claude compatibility hook syntax failed: {result.stderr.strip()}")
    sys.path.insert(0, str(HERE.parent))
    suite = unittest.defaultTestLoader.discover(str(HERE / "tests"), pattern="test_*.py")
    test_result = unittest.TextTestRunner(verbosity=1).run(suite)
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
            timeout=120,
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
            if result.returncode != 0 or payload.get("status") != "no_active_campaign":
                failures.append(f"bootstrap smoke failed: rc={result.returncode} payload={payload}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"RESULT: FAIL - {len(failures)} issue(s)")
        return 1
    print("RESULT: PASS - shared Peer Execution autonomy runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
