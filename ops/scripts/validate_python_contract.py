#!/usr/bin/env python3
"""Read-only, fail-closed drift validator for the Python test contract.

Proves that the four authorities that must move together have not silently
diverged:

  * ops/config/python-contract.json   (test-suite topology)
  * pyproject.toml                     (exact dependency pins + pytest addopts)
  * requirements.txt                   (verified mirror of the dev pins)
  * .github/workflows/l9-lint-test.yml (CI bootstrap + runner invocation)
  * ops/scripts/run_pytest_suites.sh   (compatibility wrapper, no topology)

It NEVER edits repository files. Every check fails closed: a missing file,
malformed registry, unproven claim, or unknown state is a failure, not a pass.
The authoritative lockfile check remains the external `uv lock --check`; this
validator only proves uv.lock exists.

Exit code 0 = all checks pass. Nonzero = at least one check failed.

The individual check_* functions accept an explicit `root` so they can be
exercised against temporary fixture repositories (see ops/scripts/test_python_contract.py)
without touching the real tree.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

REGISTRY_RELPATH = "ops/config/python-contract.json"
PYPROJECT_RELPATH = "pyproject.toml"
REQUIREMENTS_RELPATH = "requirements.txt"
WORKFLOW_RELPATH = ".github/workflows/l9-lint-test.yml"
WRAPPER_RELPATH = "ops/scripts/run_pytest_suites.sh"
UV_LOCK_RELPATH = "uv.lock"
RUNNER_INVOCATION = "run_python_test_suites.py"

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

# Suite-shell topology that must NEVER reappear in the compatibility wrapper.
FORBIDDEN_WRAPPER_TOKENS = (
    "--ignore=",
    "--cov",
    "unittest",
    "run_wave3_tests.py",
    "autonomy/tests",
    "-o addopts=",
    "-n auto",
)

# Floating CI installs that must never bypass uv.lock.
_FLOATING_INSTALL_RE = re.compile(
    r"pip\s+install\s+.*pytest[-_](?:xdist|timeout)",
)

_SUBSTITUTION_RE = re.compile(r"\$\{([A-Z_]+)\}")
_PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;#]+)")


class ContractError(Exception):
    """A drift check failed. Always fail closed."""


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def _read_text(root: Path, relpath: str) -> str:
    path = root / relpath
    if not path.is_file():
        msg = f"required file missing: {relpath}"
        raise ContractError(msg)
    return path.read_text(encoding="utf-8")


def _confined(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute():
        msg = f"path must be repository-relative, not absolute: {relative!r}"
        raise ContractError(msg)
    resolved = (root / relative).resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        msg = f"path escapes repository root: {relative!r}"
        raise ContractError(msg)
    return resolved


def load_registry(root: Path) -> dict[str, Any]:
    text = _read_text(root, REGISTRY_RELPATH)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"registry is not valid JSON: {exc}"
        raise ContractError(msg) from exc
    if not isinstance(data, dict):
        msg = "registry root must be a JSON object"
        raise ContractError(msg)
    return data


def _check_substitutions(value: str, allowed: set[str], context: str) -> None:
    for name in _SUBSTITUTION_RE.findall(value):
        if name not in allowed:
            msg = f"unsupported substitution ${{{name}}} in {context}"
            raise ContractError(msg)


def _validate_argv_tokens(tokens: Any, context: str) -> None:
    if not isinstance(tokens, list) or not tokens:
        msg = f"{context} must be a non-empty argv list"
        raise ContractError(msg)
    for token in tokens:
        if not isinstance(token, str) or token == "":
            msg = f"{context} contains a non-string or empty token"
            raise ContractError(msg)
        _check_substitutions(token, ALLOWED_ARGV_SUBSTITUTIONS, context)


def check_structure(registry: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    """Check 1 + 2: structural validity, repo-confined paths, unique/ordered ids."""
    for key in REQUIRED_TOP_LEVEL:
        if key not in registry:
            msg = f"registry missing required top-level key: {key}"
            raise ContractError(msg)

    suites = registry["suites"]
    if not isinstance(suites, list) or not suites:
        msg = "registry 'suites' must be a non-empty list"
        raise ContractError(msg)

    seen: set[str] = set()
    for index, suite in enumerate(suites):
        if not isinstance(suite, dict):
            msg = f"suite #{index} is not an object"
            raise ContractError(msg)
        for field in REQUIRED_SUITE_FIELDS:
            if field not in suite:
                msg = f"suite #{index} missing required field: {field}"
                raise ContractError(msg)

        suite_id = suite["id"]
        if not isinstance(suite_id, str) or not suite_id:
            msg = f"suite #{index} has an invalid id"
            raise ContractError(msg)
        if suite_id in seen:
            msg = f"duplicate suite id: {suite_id}"
            raise ContractError(msg)
        seen.add(suite_id)

        if suite["kind"] not in SUITE_KINDS:
            msg = f"suite {suite_id} has unknown kind: {suite['kind']}"
            raise ContractError(msg)
        if not isinstance(suite["allow_exit_5"], bool):
            msg = f"suite {suite_id} allow_exit_5 must be a boolean"
            raise ContractError(msg)
        if not isinstance(suite["append_user_pytest_args"], bool):
            msg = f"suite {suite_id} append_user_pytest_args must be a boolean"
            raise ContractError(msg)
        if suite["kind"] != "pytest" and suite["append_user_pytest_args"]:
            msg = f"suite {suite_id} cannot forward pytest args to a {suite['kind']} suite"
            raise ContractError(msg)

        _confined(root, suite["working_directory"])
        owned = suite["owned_paths"]
        if not isinstance(owned, list) or not owned:
            msg = f"suite {suite_id} owned_paths must be a non-empty list"
            raise ContractError(msg)
        for owned_path in owned:
            if not isinstance(owned_path, str) or not owned_path:
                msg = f"suite {suite_id} has an invalid owned_path"
                raise ContractError(msg)
            _confined(root, owned_path)

        env = suite["env"]
        if not isinstance(env, dict):
            msg = f"suite {suite_id} env must be an object"
            raise ContractError(msg)
        for env_key, env_value in env.items():
            if not isinstance(env_key, str) or not isinstance(env_value, str):
                msg = f"suite {suite_id} env entries must be strings"
                raise ContractError(msg)
            _check_substitutions(env_value, ALLOWED_ENV_SUBSTITUTIONS, f"{suite_id} env")

        profiles = suite["profiles"]
        if not isinstance(profiles, dict):
            msg = f"suite {suite_id} profiles must be an object"
            raise ContractError(msg)
        for profile in PROFILES:
            if profile not in profiles or not isinstance(profiles[profile], dict):
                msg = f"suite {suite_id} missing profile: {profile}"
                raise ContractError(msg)
            argv = profiles[profile].get("argv")
            context = f"{suite_id}:{profile}"
            if suite["kind"] == "command_sequence":
                if not isinstance(argv, list) or not argv:
                    msg = f"{context} command_sequence argv must be a non-empty command list"
                    raise ContractError(msg)
                for command in argv:
                    _validate_argv_tokens(command, context)
            elif suite["kind"] == "command":
                _validate_argv_tokens(argv, context)
            else:
                if not isinstance(argv, list):
                    msg = f"{context} pytest argv must be a list"
                    raise ContractError(msg)
                for token in argv:
                    if not isinstance(token, str):
                        msg = f"{context} pytest argv contains a non-string token"
                        raise ContractError(msg)
    return suites


def _root_ignore_paths(suites: list[dict[str, Any]]) -> list[str]:
    ignores: list[str] = []
    for suite in suites:
        if suite["kind"] != "pytest":
            continue
        for profile in PROFILES:
            for token in suite["profiles"][profile]["argv"]:
                if token.startswith("--ignore="):
                    ignores.append(token[len("--ignore=") :])
    return ignores


def _paths_related(a: str, b: str) -> bool:
    a_norm = a.rstrip("/")
    b_norm = b.rstrip("/")
    if a_norm == b_norm:
        return True
    return a_norm.startswith(b_norm + "/") or b_norm.startswith(a_norm + "/")


def check_ignore_ownership(suites: list[dict[str, Any]]) -> None:
    """Check 3: every separately ignored active suite has exactly one registry owner."""
    ignores = _root_ignore_paths(suites)
    if not ignores:
        msg = "no active-suite ignores declared on any pytest suite"
        raise ContractError(msg)
    for ignore in dict.fromkeys(ignores):
        # The ignoring root suite owns "." (whole tree); exclude that self-claim so
        # each ignored active suite resolves to exactly one non-root owner.
        owners = [
            suite["id"]
            for suite in suites
            if suite["owned_paths"] != ["."]
            and any(_paths_related(ignore, owned) for owned in suite["owned_paths"])
        ]
        if len(owners) != 1:
            msg = f"ignored active suite {ignore!r} has {len(owners)} owners (expected 1): {owners}"
            raise ContractError(msg)


def check_owned_paths_exist(suites: list[dict[str, Any]], root: Path) -> None:
    """Check 4: every registered owned path exists."""
    for suite in suites:
        for owned in suite["owned_paths"]:
            if not (root / owned).exists():
                msg = f"suite {suite['id']} owned_path does not exist: {owned}"
                raise ContractError(msg)


def check_non_test_exclusions(registry: dict[str, Any], root: Path) -> None:
    """Check 5: non-test exclusions exist and carry a reason."""
    exclusions = registry["non_test_exclusions"]
    if not isinstance(exclusions, list) or not exclusions:
        msg = "non_test_exclusions must be a non-empty list"
        raise ContractError(msg)
    for entry in exclusions:
        if not isinstance(entry, dict) or "path" not in entry or "reason" not in entry:
            msg = "each non_test_exclusion needs a path and a reason"
            raise ContractError(msg)
        path = _confined(root, entry["path"])
        if not path.exists():
            msg = f"non_test_exclusion path does not exist: {entry['path']}"
            raise ContractError(msg)
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            msg = f"non_test_exclusion {entry['path']} has an empty reason"
            raise ContractError(msg)


def check_wrapper(root: Path) -> None:
    """Check 6: run_pytest_suites.sh delegates to the runner and holds no topology."""
    text = _read_text(root, WRAPPER_RELPATH)
    if RUNNER_INVOCATION not in text:
        msg = "run_pytest_suites.sh does not delegate to run_python_test_suites.py"
        raise ContractError(msg)
    for token in FORBIDDEN_WRAPPER_TOKENS:
        if token in text:
            msg = f"run_pytest_suites.sh contains embedded suite topology: {token!r}"
            raise ContractError(msg)


def _noncomment_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def check_ci_workflow(root: Path) -> None:
    """Checks 7, 8, 9: single canonical runner invocation, no floating installs, locked sync."""
    text = _read_text(root, WORKFLOW_RELPATH)
    active = _noncomment_lines(text)
    active_text = "\n".join(active)

    invocations = sum(line.count(RUNNER_INVOCATION) for line in active)
    if invocations != 1:
        msg = f"CI must invoke the canonical runner exactly once, found {invocations}"
        raise ContractError(msg)

    for line in active:
        if _FLOATING_INSTALL_RE.search(line):
            msg = f"CI contains a forbidden floating test-tool install: {line.strip()!r}"
            raise ContractError(msg)

    if "uv sync --locked --extra dev" not in active_text:
        msg = "CI does not bootstrap with 'uv sync --locked --extra dev'"
        raise ContractError(msg)


def _pyproject(root: Path) -> dict[str, Any]:
    path = root / PYPROJECT_RELPATH
    if not path.is_file():
        msg = "pyproject.toml missing"
        raise ContractError(msg)
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _dev_pins(root: Path) -> dict[str, str]:
    data = _pyproject(root)
    optional = data.get("project", {}).get("optional-dependencies", {})
    dev = optional.get("dev", [])
    pins: dict[str, str] = {}
    for spec in dev:
        match = _PIN_RE.match(str(spec))
        if match:
            pins[_normalize(match.group(1))] = match.group(2)
    return pins


def _runtime_distributions(root: Path) -> set[str]:
    data = _pyproject(root)
    names: set[str] = set()
    for spec in data.get("project", {}).get("dependencies", []):
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", str(spec))
        if match:
            names.add(_normalize(match.group(1)))
    return names


def check_dev_extra_pins(registry: dict[str, Any], root: Path) -> None:
    """Check 10: the dev extra contains the required test distributions at exact pins."""
    required = registry["required_dev_distributions"]
    if not isinstance(required, list) or not required:
        msg = "required_dev_distributions must be a non-empty list"
        raise ContractError(msg)
    pins = _dev_pins(root)
    for name in required:
        if _normalize(str(name)) not in pins:
            msg = f"required dev distribution not exact-pinned in pyproject dev extra: {name}"
            raise ContractError(msg)


def _requirements_pins(root: Path) -> dict[str, str]:
    text = _read_text(root, REQUIREMENTS_RELPATH)
    pins: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _PIN_RE.match(stripped)
        if match:
            pins[_normalize(match.group(1))] = match.group(2)
    return pins


def check_requirements_mirror(root: Path) -> None:
    """Check 11: requirements.txt mirrors every exact dev pin by normalized name."""
    dev = _dev_pins(root)
    req = _requirements_pins(root)
    for name, version in dev.items():
        if name not in req:
            msg = f"dev pin {name}=={version} is not mirrored in requirements.txt"
            raise ContractError(msg)
        if req[name] != version:
            msg = f"version mismatch for {name}: pyproject=={version} requirements=={req[name]}"
            raise ContractError(msg)


def check_import_map(registry: dict[str, Any], root: Path) -> None:
    """Check 12: import_map roots resolve to declared runtime or dev distributions."""
    import_map = registry["import_map"]
    if not isinstance(import_map, dict):
        msg = "import_map must be an object"
        raise ContractError(msg)
    declared = _runtime_distributions(root) | set(_dev_pins(root))
    for import_root, distribution in import_map.items():
        if not isinstance(import_root, str) or not isinstance(distribution, str):
            msg = "import_map entries must be strings"
            raise ContractError(msg)
        if _normalize(distribution) not in declared:
            msg = (
                f"import_map root {import_root!r} maps to undeclared distribution "
                f"{distribution!r} (not in runtime deps or dev extra)"
            )
            raise ContractError(msg)


def check_uv_lock(root: Path) -> None:
    """Check 13: uv.lock exists (external `uv lock --check` remains authoritative)."""
    if not (root / UV_LOCK_RELPATH).is_file():
        msg = "uv.lock is missing"
        raise ContractError(msg)


CHECKS: tuple[str, ...] = (
    "registry structure + confinement",
    "unique/ordered suite ids",
    "ignore -> single owner mapping",
    "owned paths exist",
    "non-test exclusions have reasons",
    "wrapper delegates, no topology",
    "CI invokes canonical runner once",
    "CI has no floating test installs",
    "CI bootstraps uv sync --locked --extra dev",
    "dev extra pins required test tools",
    "requirements mirrors dev pins",
    "import_map resolves to declared distributions",
    "uv.lock present",
)


def run_all(root: Path) -> list[tuple[str, bool, str]]:
    """Run every check against `root`. Returns (name, ok, detail) per check group."""
    results: list[tuple[str, bool, str]] = []

    def record(name: str, fn: Any) -> None:
        try:
            fn()
            results.append((name, True, ""))
        except ContractError as exc:
            results.append((name, False, str(exc)))

    try:
        registry = load_registry(root)
        suites = check_structure(registry, root)
    except ContractError as exc:
        return [("registry structure + confinement", False, str(exc))]

    results.append(("registry structure + confinement", True, ""))
    results.append(("unique/ordered suite ids", True, ""))
    record("ignore -> single owner mapping", lambda: check_ignore_ownership(suites))
    record("owned paths exist", lambda: check_owned_paths_exist(suites, root))
    record("non-test exclusions have reasons", lambda: check_non_test_exclusions(registry, root))
    record("wrapper delegates, no topology", lambda: check_wrapper(root))
    record("CI runner / no floating installs / locked sync", lambda: check_ci_workflow(root))
    record("dev extra pins required test tools", lambda: check_dev_extra_pins(registry, root))
    record("requirements mirrors dev pins", lambda: check_requirements_mirror(root))
    record("import_map -> declared distributions", lambda: check_import_map(registry, root))
    record("uv.lock present", lambda: check_uv_lock(root))
    return results


def main(root: Path | None = None) -> int:
    target = root if root is not None else REPO_ROOT
    results = run_all(target)
    failures = 0
    print(f"[validate] python contract drift check — root={target}")
    for name, ok, detail in results:
        if ok:
            print(f"[validate]   PASS  {name}")
        else:
            failures += 1
            print(f"[validate]   FAIL  {name}: {detail}")
    if failures:
        print(f"[validate] FAILED: {failures} check group(s) failed")
        return 1
    print("[validate] OK: all drift checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
