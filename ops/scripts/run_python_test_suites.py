#!/usr/bin/env python3
"""Canonical, fail-closed Python test-suite runner for Cursor-Governance.

This is the single implementation of suite orchestration. It reads the
declarative registry at ``ops/config/python-contract.json``, runs the
read-only drift validator (``validate_python_contract.py``) as a pre-suite
gate, then executes every registered suite in order.

Design guarantees:

* The repository root is resolved from this script's location, never from the
  caller's current working directory.
* Working directories and owned paths are confined under the repository root.
* argv arrays are executed with ``subprocess.run`` (never ``shell=True``),
  with bounded timeouts and exact exit-code propagation.
* The first nonzero suite exit code is preserved as the process exit code.
* Cancellation, timeout, a missing command, a malformed registry, or any
  unknown state is never reinterpreted as success.
* ``pytest`` exit code 5 (no tests collected) is tolerated only for suites
  whose registry entry sets ``allow_exit_5`` and the runner prints a notice.
* A final summary lists every suite and its status.

Invoke directly, or via the ``ops/scripts/run_pytest_suites.sh`` wrapper:

    python3 ops/scripts/run_python_test_suites.py --profile local -- <pytest args>
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_python_contract as contract  # noqa: E402  (needs sys.path setup)

# Wall-clock ceiling for a single suite invocation. Per-test timeouts are
# supplied separately through pytest's --timeout in the CI profile; this bound
# only exists so a wedged subprocess fails closed instead of hanging forever.
SUITE_TIMEOUT_SECONDS = 1800

PYTEST_EXIT_NO_TESTS_COLLECTED = 5
EXIT_TIMEOUT = 124
EXIT_MISSING_COMMAND = 127


def _subst(value: str, python: str) -> str:
    """Resolve supported ``${...}`` substitutions in a single token."""
    return value.replace("${PYTHON}", python).replace("${REPO_ROOT}", str(REPO_ROOT))


def _confined(path: Path) -> Path:
    """Resolve ``path`` and fail closed if it escapes the repository root."""
    resolved = path.resolve()
    root = REPO_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        msg = f"path escapes repository root: {path}"
        raise ValueError(msg)
    return resolved


def resolve_work_dir(suite: dict) -> Path:
    """Resolve a suite's working directory, confined under the repo root."""
    raw = _subst(str(suite["working_directory"]), sys.executable)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / raw
    return _confined(candidate)


def build_env(suite: dict) -> dict[str, str]:
    """Build the subprocess environment for a suite (PYTHONPATH confined)."""
    env = os.environ.copy()
    for key, raw_value in suite.get("environment", {}).items():
        value = _subst(str(raw_value), sys.executable)
        if key == "PYTHONPATH":
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = REPO_ROOT / value
            value = str(_confined(candidate))
        env[key] = value
    return env


def build_pytest_argv(suite: dict, profile: str, user_args: list[str]) -> list[str]:
    """Construct the full pytest argv for a suite/profile (no execution)."""
    profile_argv = suite["profiles"][profile]["argv"]
    argv = [sys.executable, "-m", "pytest"]
    argv += [_subst(str(token), sys.executable) for token in profile_argv]
    for ignore in suite.get("active_suite_ignores", []):
        argv.append(f"--ignore={ignore}")
    if suite.get("append_user_pytest_args", False) and user_args:
        argv += user_args
    return argv


def build_command_argv(suite: dict) -> list[str]:
    """Construct the argv for a command suite (no execution)."""
    return [_subst(str(token), sys.executable) for token in suite["command"]]


def build_sequence_argvs(suite: dict) -> list[list[str]]:
    """Construct the ordered argv lists for a command_sequence suite."""
    return [
        [_subst(str(token), sys.executable) for token in command] for command in suite["commands"]
    ]


def _run(argv: list[str], cwd: Path, env: dict[str, str]) -> int:
    printable = " ".join(argv)
    print(f"    $ {printable}  (cwd={cwd})")
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=env,
            timeout=SUITE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after {SUITE_TIMEOUT_SECONDS}s: {printable}")
        return EXIT_TIMEOUT
    except FileNotFoundError as exc:
        print(f"    MISSING COMMAND: {exc}")
        return EXIT_MISSING_COMMAND
    return completed.returncode


def _run_pytest(suite: dict, profile: str, user_args: list[str]) -> int:
    argv = build_pytest_argv(suite, profile, user_args)
    rc = _run(argv, resolve_work_dir(suite), build_env(suite))
    if rc == PYTEST_EXIT_NO_TESTS_COLLECTED and suite.get("allow_exit_5", False):
        print(
            f"    NOTICE: suite '{suite['id']}' collected zero tests "
            "(pytest exit 5); tolerated by registry."
        )
        return 0
    return rc


def _run_command(suite: dict) -> int:
    return _run(build_command_argv(suite), resolve_work_dir(suite), build_env(suite))


def _run_command_sequence(suite: dict) -> int:
    env = build_env(suite)
    cwd = resolve_work_dir(suite)
    for argv in build_sequence_argvs(suite):
        rc = _run(argv, cwd, env)
        if rc != 0:
            return rc
    return 0


def _run_suite(suite: dict, profile: str, user_args: list[str]) -> int:
    kind = suite["kind"]
    if kind == "pytest":
        return _run_pytest(suite, profile, user_args)
    if kind == "command":
        return _run_command(suite)
    if kind == "command_sequence":
        return _run_command_sequence(suite)
    # The validator rejects unknown kinds before we ever get here; treat any
    # residual unknown state as a failure rather than success.
    print(f"    UNKNOWN suite kind: {kind!r}")
    return 2


def _parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    if "--" in argv:
        split = argv.index("--")
        flag_args, user_args = argv[:split], argv[split + 1 :]
    else:
        flag_args, user_args = argv, []
    parser = argparse.ArgumentParser(
        description="Run the canonical Python test suites declared in "
        "ops/config/python-contract.json.",
    )
    parser.add_argument(
        "--profile",
        choices=["local", "ci"],
        default="local",
        help="Suite argv profile to run (default: local).",
    )
    return parser.parse_args(flag_args), user_args


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:]) if argv is None else list(argv)
    args, user_args = _parse_args(raw)

    print(f"[run_python_test_suites] repo root: {REPO_ROOT}")
    print(f"[run_python_test_suites] profile: {args.profile}")

    # Fail-closed drift gate BEFORE any suite runs. This is how make test,
    # make pr-full, and CI all receive the contract drift check through the
    # existing shell wrapper without changing the Makefile.
    try:
        registry = contract.load_registry(REPO_ROOT)
    except Exception as exc:  # noqa: BLE001 - fail closed on any load error
        print(f"FAIL: cannot load python-contract registry: {exc}")
        return 1

    errors = contract.run(REPO_ROOT)
    if errors:
        print("FAIL: python-contract validation failed; not executing suites:")
        for error in errors:
            print(f"  - {error}")
        return 1

    results: list[tuple[str, int, str]] = []
    first_nonzero = 0
    for suite in registry["suites"]:
        suite_id = suite["id"]
        print(f">>> suite start: {suite_id} ({suite['kind']}, profile={args.profile})")
        rc = _run_suite(suite, args.profile, user_args)
        status = "PASS" if rc == 0 else f"FAIL(rc={rc})"
        print(f"<<< suite end:   {suite_id} -> {status}")
        results.append((suite_id, rc, status))
        if rc != 0 and first_nonzero == 0:
            first_nonzero = rc

    print("=== suite summary ===")
    for suite_id, _rc, status in results:
        print(f"  {suite_id}: {status}")
    overall = "PASS" if first_nonzero == 0 else "FAIL"
    print(f"=== overall: {overall} (exit {first_nonzero}) ===")
    return first_nonzero


if __name__ == "__main__":
    raise SystemExit(main())
