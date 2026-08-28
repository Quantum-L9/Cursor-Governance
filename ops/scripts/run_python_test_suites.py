#!/usr/bin/env python3
"""Canonical, fail-closed orchestrator for Cursor-Governance Python test suites.

This is the single implementation of suite orchestration. It reads the declarative
registry at ops/config/python-contract.json, strictly validates it, and executes the
declared suites in order under two profiles:

    --profile local   forwards operator pytest arguments (default)
    --profile ci      applies the locked coverage / xdist / timeout arguments

Guarantees:
  * repository root is resolved from this script's location, never the caller's cwd
  * working directories and owned paths are confined under the repository root
  * PYTHONPATH collisions between the root autonomy/ package and the Claude Code
    environment/program-execution/peer_execution/autonomy/ package are isolated per suite
  * pytest, opaque command, and fresh-process command_sequence suites are supported
  * user pytest arguments are appended only to suites that explicitly permit it
  * exit status is propagated exactly; the first nonzero suite result is preserved
  * cancellation, timeout, missing command, malformed registry, and unknown state
    are never reinterpreted as success

The registry is topology only. Exact dependency versions live in pyproject.toml and
are mirrored in requirements.txt; this runner never edits repository files.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Default: the governance root this script was loaded from. That is correct when
# the tree being tested is the tree the runner lives in, which is every consumer
# publish and every CI run.
#
# It is wrong in exactly one shape, and that shape is supported doctrine (rule 49
# §7): publishing from a second clone of the governance repo. There `make pr`
# runs the Makefile from $GOV while the changed files -- and their tests -- live
# in $WS. Selection then reads one tree and execution runs in another, so a test
# added in the workspace is reported as "no tests ran" and the gate fails on work
# that is present and passing. Measured 2026-08-27: three selected test files,
# repo_root=$GOV, exit 4.
#
# --repo-root closes that gap by letting the caller name the tree, the same way
# sync_generated_artifacts.py already takes --root "$WS" from the same gate.
REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "ops" / "config" / "python-contract.json"


def _rebind_repo_root(root: Path) -> str | None:
    """Point the runner at `root`. Returns an error string, or None on success.

    Fails closed rather than falling back: a caller that names a root which is
    not a governance tree has a wiring bug, and silently testing a different
    tree than the one requested is the failure mode this whole change exists to
    remove.
    """
    global REPO_ROOT, REGISTRY_PATH  # noqa: PLW0603 - module-level contract, set once at startup

    resolved = root.expanduser().resolve()
    if not resolved.is_dir():
        return f"--repo-root is not a directory: {resolved}"
    registry = resolved / "ops" / "config" / "python-contract.json"
    if not registry.is_file():
        return (
            f"--repo-root is not a governance root (no ops/config/python-contract.json): {resolved}"
        )

    REPO_ROOT = resolved
    REGISTRY_PATH = registry
    return None


PROFILES = ("local", "ci")
SUITE_KINDS = ("pytest", "command", "command_sequence")
ALLOWED_ENV_SUBSTITUTIONS = {"REPO_ROOT"}
ALLOWED_ARGV_SUBSTITUTIONS = {"REPO_ROOT", "PYTHON"}
REQUIRED_SUITE_FIELDS = (
    "id",
    "kind",
    "working_directory",
    "owned_paths",
    "env",
    "append_user_pytest_args",
    "allow_exit_5",
    "profiles",
)
REQUIRED_TOP_LEVEL = (
    "schema_version",
    "import_map",
    "required_dev_distributions",
    "non_test_exclusions",
    "suites",
)

_SUBSTITUTION_RE = re.compile(r"\$\{([A-Z_]+)\}")

# Bounded timeout for a single subprocess. A safety net only: the CI job and the
# per-test pytest --timeout already bound normal execution well below this.
SUITE_TIMEOUT_SECONDS = 1800


class RegistryError(Exception):
    """Raised when the registry is structurally invalid. Always fail closed."""


def _load_json(path: Path) -> Any:
    import json

    if not path.is_file():
        msg = f"registry not found: {path}"
        raise RegistryError(msg)
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        msg = f"registry is not valid JSON: {exc}"
        raise RegistryError(msg) from exc


def _confined(relative: str) -> Path:
    """Resolve a repository-relative path and prove it stays under REPO_ROOT."""
    if os.path.isabs(relative):
        msg = f"path must be repository-relative, not absolute: {relative!r}"
        raise RegistryError(msg)
    resolved = (REPO_ROOT / relative).resolve()
    if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
        msg = f"path escapes repository root: {relative!r}"
        raise RegistryError(msg)
    return resolved


def _check_substitutions(value: str, allowed: set[str], context: str) -> None:
    for name in _SUBSTITUTION_RE.findall(value):
        if name not in allowed:
            msg = f"unsupported substitution ${{{name}}} in {context}"
            raise RegistryError(msg)


def _substitute(value: str, mapping: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in mapping:
            msg = f"unsupported substitution ${{{name}}}"
            raise RegistryError(msg)
        return mapping[name]

    return _SUBSTITUTION_RE.sub(replace, value)


def _validate_argv_tokens(tokens: Any, context: str) -> None:
    if not isinstance(tokens, list) or not tokens:
        msg = f"{context} must be a non-empty argv list"
        raise RegistryError(msg)
    for token in tokens:
        if not isinstance(token, str) or token == "":
            msg = f"{context} contains a non-string or empty argv token"
            raise RegistryError(msg)
        _check_substitutions(token, ALLOWED_ARGV_SUBSTITUTIONS, context)


def validate_registry(registry: Any) -> list[dict[str, Any]]:
    """Strictly validate the registry and return the ordered suite list."""
    if not isinstance(registry, dict):
        msg = "registry root must be a JSON object"
        raise RegistryError(msg)
    for key in REQUIRED_TOP_LEVEL:
        if key not in registry:
            msg = f"registry missing required top-level key: {key}"
            raise RegistryError(msg)

    suites = registry["suites"]
    if not isinstance(suites, list) or not suites:
        msg = "registry 'suites' must be a non-empty list"
        raise RegistryError(msg)

    seen_ids: set[str] = set()
    for index, suite in enumerate(suites):
        if not isinstance(suite, dict):
            msg = f"suite #{index} is not an object"
            raise RegistryError(msg)
        for field in REQUIRED_SUITE_FIELDS:
            if field not in suite:
                msg = f"suite #{index} missing required field: {field}"
                raise RegistryError(msg)

        suite_id = suite["id"]
        if not isinstance(suite_id, str) or not suite_id:
            msg = f"suite #{index} has an invalid id"
            raise RegistryError(msg)
        if suite_id in seen_ids:
            msg = f"duplicate suite id: {suite_id}"
            raise RegistryError(msg)
        seen_ids.add(suite_id)

        kind = suite["kind"]
        if kind not in SUITE_KINDS:
            msg = f"suite {suite_id} has unknown kind: {kind}"
            raise RegistryError(msg)

        if not isinstance(suite["allow_exit_5"], bool):
            msg = f"suite {suite_id} allow_exit_5 must be a boolean"
            raise RegistryError(msg)
        if not isinstance(suite["append_user_pytest_args"], bool):
            msg = f"suite {suite_id} append_user_pytest_args must be a boolean"
            raise RegistryError(msg)
        if kind != "pytest" and suite["append_user_pytest_args"]:
            msg = f"suite {suite_id} may not append user pytest args to a {kind} suite"
            raise RegistryError(msg)

        _confined(suite["working_directory"])

        owned = suite["owned_paths"]
        if not isinstance(owned, list) or not owned:
            msg = f"suite {suite_id} owned_paths must be a non-empty list"
            raise RegistryError(msg)
        for owned_path in owned:
            if not isinstance(owned_path, str) or not owned_path:
                msg = f"suite {suite_id} has an invalid owned_path"
                raise RegistryError(msg)
            _confined(owned_path)

        env = suite["env"]
        if not isinstance(env, dict):
            msg = f"suite {suite_id} env must be an object"
            raise RegistryError(msg)
        for env_key, env_value in env.items():
            if not isinstance(env_key, str) or not isinstance(env_value, str):
                msg = f"suite {suite_id} env entries must be strings"
                raise RegistryError(msg)
            _check_substitutions(env_value, ALLOWED_ENV_SUBSTITUTIONS, f"{suite_id} env")

        profiles = suite["profiles"]
        if not isinstance(profiles, dict):
            msg = f"suite {suite_id} profiles must be an object"
            raise RegistryError(msg)
        for profile in PROFILES:
            if profile not in profiles:
                msg = f"suite {suite_id} missing profile: {profile}"
                raise RegistryError(msg)
            argv = profiles[profile].get("argv") if isinstance(profiles[profile], dict) else None
            context = f"{suite_id}:{profile}"
            if kind == "command_sequence":
                if not isinstance(argv, list) or not argv:
                    msg = f"{context} command_sequence argv must be a non-empty list of commands"
                    raise RegistryError(msg)
                for command in argv:
                    _validate_argv_tokens(command, context)
            elif kind == "command":
                _validate_argv_tokens(argv, context)
            else:  # pytest
                if not isinstance(argv, list):
                    msg = f"{context} pytest argv must be a list"
                    raise RegistryError(msg)
                for token in argv:
                    if not isinstance(token, str):
                        msg = f"{context} pytest argv contains a non-string token"
                        raise RegistryError(msg)

    return suites


# Host `make pr` may export these. A poisoned parent must not skip overlap
# tests or change remediates/stacking mid-suite. Empty is not unset: the
# checker treats empty PR_OVERLAP as block, but ignore must be dropped.
CEREMONY_KNOBS: tuple[str, ...] = (
    "PR_OVERLAP",
    "PR_OVERLAP_TELEMETRY",
    "PR_STACK",
    "PR_REMEDIATE",
)


def strip_ceremony_knobs(env: dict[str, str]) -> dict[str, str]:
    """Return a copy with publish-path knobs removed (not set empty)."""
    out = dict(env)
    for key in CEREMONY_KNOBS:
        out.pop(key, None)
    return out


def _suite_env(suite: dict[str, Any], mapping: dict[str, str]) -> dict[str, str]:
    env = strip_ceremony_knobs(os.environ)
    for key, value in suite["env"].items():
        env[key] = _substitute(value, mapping)
    return env


def _run_subprocess(argv: list[str], cwd: Path, env: dict[str, str]) -> int:
    try:
        completed = subprocess.run(  # noqa: S603 - argv is a validated list, never a shell string
            argv,
            cwd=str(cwd),
            env=env,
            timeout=SUITE_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        print(f"[runner] ERROR: command not found: {argv[0]}", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired:
        print(f"[runner] ERROR: timed out after {SUITE_TIMEOUT_SECONDS}s: {argv}", file=sys.stderr)
        return 124
    return completed.returncode


def _normalize_exit(code: int, allow_exit_5: bool, suite_id: str) -> int:
    if code == 5 and allow_exit_5:
        print(f"[runner] NOTICE: suite {suite_id} collected zero tests (exit 5, allowed)")
        return 0
    return code


def _load_selector() -> Any:
    script = Path(__file__).with_name("select_pr_pytest_paths.py")
    spec = importlib.util.spec_from_file_location("select_pr_pytest_paths", script)
    if spec is None or spec.loader is None:
        msg = f"pytest path selector missing: {script}"
        raise RegistryError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_changed(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _non_dot_roots(suites: list[dict[str, Any]], selector: Any) -> list[str]:
    roots: list[str] = []
    for suite in suites:
        if selector.is_dot_owned(suite):
            continue
        for root in suite.get("owned_paths") or []:
            text = str(root)
            if text and text != "." and text not in roots:
                roots.append(text)
    return roots


def _suite_intersects(
    suite: dict[str, Any],
    selected: list[str],
    changed: list[str],
    selector: Any,
) -> bool:
    if selector.is_dot_owned(suite):
        return True
    owned = [str(root) for root in (suite.get("owned_paths") or [])]
    candidates = [*selected, *changed]
    return any(
        selector.path_under(item, root) or item == root or selector.path_under(root, item)
        for item in candidates
        for root in owned
    )


def _root_suite_paths(selected: list[str], non_dot_roots: list[str], selector: Any) -> list[str]:
    return [
        path
        for path in selected
        if not any(selector.path_under(path, root) or path == root for root in non_dot_roots)
    ]


def run_suite(
    suite: dict[str, Any],
    profile: str,
    user_args: list[str],
    mapping: dict[str, str],
    *,
    scoped_paths: list[str] | None = None,
    selector: Any | None = None,
    non_dot_roots: list[str] | None = None,
) -> int:
    suite_id = suite["id"]
    kind = suite["kind"]
    cwd = _confined(suite["working_directory"])
    env = _suite_env(suite, mapping)
    argv_spec = suite["profiles"][profile]["argv"]

    print(
        f"[runner] START suite={suite_id} kind={kind} "
        f"profile={profile} cwd={suite['working_directory']}"
    )

    if kind == "pytest":
        tokens = [_substitute(a, mapping) for a in argv_spec]
        extra_args = list(user_args)
        if scoped_paths is not None:
            tokens = [token for token in tokens if token != "."]
            if selector is not None and selector.is_dot_owned(suite):
                paths = _root_suite_paths(scoped_paths, non_dot_roots or [], selector)
                if not paths:
                    print(f"[runner] SKIP  suite={suite_id} reason=no_scoped_root_paths")
                    return 0
                extra_args = [*user_args, *paths]
            elif not extra_args:
                extra_args = list(user_args)
        argv = [mapping["PYTHON"], "-m", "pytest", *tokens]
        if suite["append_user_pytest_args"] and extra_args:
            argv.extend(extra_args)
        code = _run_subprocess(argv, cwd, env)
    elif kind == "command":
        argv = [_substitute(token, mapping) for token in argv_spec]
        code = _run_subprocess(argv, cwd, env)
    else:  # command_sequence
        code = 0
        for command in argv_spec:
            argv = [_substitute(token, mapping) for token in command]
            code = _run_subprocess(argv, cwd, env)
            if code != 0:
                # Stop on the first failed command; preserve its exact exit status.
                break

    result = _normalize_exit(code, suite["allow_exit_5"], suite_id)
    label = "PASS" if result == 0 else f"FAIL(exit={result})"
    print(f"[runner] END   suite={suite_id} result={label}")
    return result


def _run_drift_validator() -> int:
    """Run the fail-closed drift validator before any suite. Missing = fail closed."""
    validator_path = REPO_ROOT / "ops" / "scripts" / "validate_python_contract.py"
    if not validator_path.is_file():
        print(f"[runner] FATAL: drift validator missing: {validator_path}", file=sys.stderr)
        return 2
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [sys.executable, str(validator_path)],
            timeout=SUITE_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"[runner] FATAL: drift validator did not complete: {exc}", file=sys.stderr)
        return 2
    return completed.returncode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the canonical Cursor-Governance Python test suites.",
    )
    parser.add_argument("--profile", choices=PROFILES, default="local")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help=(
            "Repository root to test. Defaults to the tree this script lives in. "
            "Pass the workspace when publishing from a second governance clone, "
            "so suite selection and suite execution name the same tree."
        ),
    )
    parser.add_argument(
        "--changed-file",
        type=Path,
        default=None,
        help="changed-file selector for local make pr and pull_request CI. Never emits '.'.",
    )
    parser.add_argument("pytest_args", nargs="*", help="pytest args after --")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Before the drift validator, the registry read, or any path confinement --
    # all of which resolve against REPO_ROOT.
    if args.repo_root is not None:
        rebind_error = _rebind_repo_root(args.repo_root)
        if rebind_error is not None:
            print(f"[runner] FATAL: {rebind_error}", file=sys.stderr)
            return 2

    profile, user_args = args.profile, args.pytest_args
    if args.changed_file is not None and profile != "local":
        print("[runner] FATAL: --changed-file is valid only with --profile local", file=sys.stderr)
        return 2

    # Fail-closed drift gate before any suite runs. This is why make test,
    # make pr-full, and CI all receive the drift check through this one runner.
    drift_code = _run_drift_validator()
    if drift_code != 0:
        print("[runner] FATAL: python contract drift check failed; suites not run", file=sys.stderr)
        return drift_code

    try:
        registry = _load_json(REGISTRY_PATH)
        suites = validate_registry(registry)
    except RegistryError as exc:
        print(f"[runner] FATAL: {exc}", file=sys.stderr)
        return 2

    mapping = {"REPO_ROOT": str(REPO_ROOT), "PYTHON": sys.executable}
    scoped_paths: list[str] | None = None
    selector: Any | None = None
    non_dot_roots: list[str] = []
    changed: list[str] = []
    if args.changed_file is not None:
        if not args.changed_file.is_file():
            print(f"[runner] FATAL: changed-file missing: {args.changed_file}", file=sys.stderr)
            return 2
        try:
            selector = _load_selector()
            changed = _read_changed(args.changed_file)
            scoped_paths = selector.select_pr_pytest_paths(changed)
        except (OSError, SystemExit, RegistryError) as exc:
            print(f"[runner] FATAL: scoped pytest selection failed: {exc}", file=sys.stderr)
            return 2
        if "." in scoped_paths:
            print("[runner] FATAL: selector emitted repo-root '.'", file=sys.stderr)
            return 2
        non_dot_roots = _non_dot_roots(suites, selector)
        print(
            f"[runner] scoped_pr_check paths={scoped_paths or ['<none>']} "
            f"never_pass_repo_root_dot=true"
        )

    print(f"[runner] profile={profile} suites={len(suites)} repo_root={REPO_ROOT}")
    return run_suites(
        suites,
        profile,
        user_args,
        mapping,
        scoped_paths=scoped_paths,
        selector=selector,
        changed=changed,
        non_dot_roots=non_dot_roots,
    )


def run_suites(
    suites: list[dict[str, Any]],
    profile: str,
    user_args: list[str],
    mapping: dict[str, str],
    *,
    scoped_paths: list[str] | None = None,
    selector: Any | None = None,
    changed: list[str] | None = None,
    non_dot_roots: list[str] | None = None,
) -> int:
    """Run declared suites. Local profile stops at the first red suite."""
    results: list[tuple[str, int]] = []
    first_nonzero = 0
    for suite in suites:
        if scoped_paths is not None and selector is not None:
            if not _suite_intersects(suite, scoped_paths, changed or [], selector):
                print(
                    f"[runner] SKIP  suite={suite['id']} "
                    "reason=owned_paths_do_not_intersect_changed"
                )
                results.append((suite["id"], 0))
                continue
        try:
            code = run_suite(
                suite,
                profile,
                user_args,
                mapping,
                scoped_paths=scoped_paths,
                selector=selector,
                non_dot_roots=non_dot_roots,
            )
        except RegistryError as exc:
            print(f"[runner] FATAL: {exc}", file=sys.stderr)
            code = 2
        results.append((suite["id"], code))
        if code != 0 and first_nonzero == 0:
            first_nonzero = code
            if profile == "local":
                break

    print("[runner] ===== summary =====")
    for suite_id, code in results:
        status = "PASS" if code == 0 else f"FAIL(exit={code})"
        print(f"[runner]   {suite_id}: {status}")
    overall = "PASS" if first_nonzero == 0 else f"FAIL(exit={first_nonzero})"
    print(f"[runner] overall: {overall}")
    return first_nonzero


if __name__ == "__main__":
    raise SystemExit(main())
