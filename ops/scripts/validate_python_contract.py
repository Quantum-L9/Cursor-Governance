#!/usr/bin/env python3
"""Read-only, fail-closed drift validator for the Python test contract.

This validator proves that the four authorities that describe how
Cursor-Governance's Python tests run cannot silently diverge:

* ``ops/config/python-contract.json`` — declarative suite topology
* ``pyproject.toml`` — exact dependency pins (the version authority)
* ``requirements.txt`` — the verified mirror of the dev pins
* ``.github/workflows/l9-lint-test.yml`` — CI, which must consume the runner

It writes nothing. Every function takes an explicit repository root so the
same logic validates the live repository and the temporary fixture
repositories used by ``test_python_contract.py``. The external
``uv lock --check`` command remains the authoritative lockfile check; this
validator only asserts that ``uv.lock`` exists.

Usage:

    python3 ops/scripts/validate_python_contract.py [--repo-root PATH]

Exit code 0 means no drift. Any nonzero exit lists the drift found.
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

REGISTRY_RELPATH = "ops/config/python-contract.json"
PYPROJECT_RELPATH = "pyproject.toml"
REQUIREMENTS_RELPATH = "requirements.txt"
WORKFLOW_RELPATH = ".github/workflows/l9-lint-test.yml"
WRAPPER_RELPATH = "ops/scripts/run_pytest_suites.sh"
RUNNER_RELPATH = "ops/scripts/run_python_test_suites.py"
LOCKFILE_RELPATH = "uv.lock"

SUPPORTED_SUBSTITUTIONS = {"${PYTHON}", "${REPO_ROOT}"}
SUBSTITUTION_PATTERN = re.compile(r"\$\{[^}]*\}")

ALLOWED_TOP_LEVEL_KEYS = {
    "schema_version",
    "description",
    "import_map",
    "required_dev_distributions",
    "non_test_exclusions",
    "suites",
}
COMMON_SUITE_KEYS = {
    "id",
    "kind",
    "working_directory",
    "owned_paths",
    "environment",
    "allow_exit_5",
    "rationale",
}
KIND_EXTRA_KEYS = {
    "pytest": {"profiles", "append_user_pytest_args", "active_suite_ignores"},
    "command": {"command"},
    "command_sequence": {"commands"},
}
VALID_KINDS = set(KIND_EXTRA_KEYS)
VALID_PROFILES = {"local", "ci"}

# Third-party import root -> a normalized-name that the CI floating-install
# guard forbids re-installing outside uv.lock.
FLOATING_INSTALL_TOKENS = ("pytest-xdist", "pytest-timeout", "pytest_timeout", "xdist")


def _normalize(name: str) -> str:
    """PEP 503 normalization for distribution-name comparison."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def _requirement_name(spec: str) -> str:
    """Extract the distribution name from a requirement string."""
    match = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    return match.group(1) if match else ""


def load_registry(root: Path) -> dict:
    """Load and JSON-parse the registry. Fail closed on any read/parse error."""
    path = root / REGISTRY_RELPATH
    if not path.is_file():
        msg = f"registry not found: {REGISTRY_RELPATH}"
        raise FileNotFoundError(msg)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _confined(root: Path, relpath: str) -> Path | None:
    """Resolve a repo-relative path; return None if it escapes the root."""
    candidate = Path(relpath)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        return None
    return resolved


def _check_substitutions(tokens: list, label: str, errors: list[str]) -> None:
    for token in tokens:
        if not isinstance(token, str):
            errors.append(f"{label}: non-string token {token!r}")
            continue
        for found in SUBSTITUTION_PATTERN.findall(token):
            if found not in SUPPORTED_SUBSTITUTIONS:
                errors.append(f"{label}: unsupported substitution {found!r}")


def _validate_suite(suite: dict, root: Path, errors: list[str]) -> None:
    suite_id = suite.get("id", "<missing id>")
    kind = suite.get("kind")
    if kind not in VALID_KINDS:
        errors.append(f"suite {suite_id!r}: unknown kind {kind!r}")
        return

    allowed = COMMON_SUITE_KEYS | KIND_EXTRA_KEYS[kind]
    for key in suite:
        if key not in allowed:
            errors.append(f"suite {suite_id!r}: unknown field {key!r} for kind {kind!r}")

    required = COMMON_SUITE_KEYS | KIND_EXTRA_KEYS[kind]
    # append_user_pytest_args and active_suite_ignores are optional for pytest.
    if kind == "pytest":
        required = required - {"append_user_pytest_args", "active_suite_ignores"}
    for key in required:
        if key not in suite:
            errors.append(f"suite {suite_id!r}: missing required field {key!r}")

    work_dir = suite.get("working_directory")
    if isinstance(work_dir, str):
        if _confined(root, _strip_subst(work_dir)) is None:
            errors.append(f"suite {suite_id!r}: working_directory escapes root: {work_dir!r}")
    else:
        errors.append(f"suite {suite_id!r}: working_directory must be a string")

    owned = suite.get("owned_paths")
    if not isinstance(owned, list) or not owned:
        errors.append(f"suite {suite_id!r}: owned_paths must be a non-empty list")
    else:
        for owned_path in owned:
            resolved = _confined(root, owned_path) if isinstance(owned_path, str) else None
            if resolved is None:
                errors.append(f"suite {suite_id!r}: owned_path escapes root: {owned_path!r}")
            elif not resolved.exists():
                errors.append(f"suite {suite_id!r}: owned_path does not exist: {owned_path!r}")

    env = suite.get("environment", {})
    if not isinstance(env, dict):
        errors.append(f"suite {suite_id!r}: environment must be an object")
    else:
        _check_substitutions(list(env.values()), f"suite {suite_id!r} environment", errors)

    if not isinstance(suite.get("allow_exit_5", False), bool):
        errors.append(f"suite {suite_id!r}: allow_exit_5 must be a boolean")

    if kind == "pytest":
        _validate_pytest_suite(suite, suite_id, root, errors)
    elif kind == "command":
        command = suite.get("command")
        if not isinstance(command, list) or not command:
            errors.append(f"suite {suite_id!r}: command must be a non-empty argv list")
        else:
            _check_substitutions(command, f"suite {suite_id!r} command", errors)
    elif kind == "command_sequence":
        commands = suite.get("commands")
        if not isinstance(commands, list) or not commands:
            errors.append(f"suite {suite_id!r}: commands must be a non-empty list of argv lists")
        else:
            for index, command in enumerate(commands):
                if not isinstance(command, list) or not command:
                    errors.append(
                        f"suite {suite_id!r}: commands[{index}] must be a non-empty argv list"
                    )
                    continue
                _check_substitutions(command, f"suite {suite_id!r} commands[{index}]", errors)


def _validate_pytest_suite(suite: dict, suite_id: str, root: Path, errors: list[str]) -> None:
    profiles = suite.get("profiles")
    if not isinstance(profiles, dict):
        errors.append(f"suite {suite_id!r}: profiles must be an object")
    else:
        for profile_name in profiles:
            if profile_name not in VALID_PROFILES:
                errors.append(f"suite {suite_id!r}: unknown profile {profile_name!r}")
        for profile_name in VALID_PROFILES:
            profile = profiles.get(profile_name)
            if not isinstance(profile, dict) or not isinstance(profile.get("argv"), list):
                errors.append(f"suite {suite_id!r}: profile {profile_name!r} needs an argv list")
                continue
            _check_substitutions(profile["argv"], f"suite {suite_id!r} {profile_name} argv", errors)

    if "append_user_pytest_args" in suite and not isinstance(
        suite["append_user_pytest_args"], bool
    ):
        errors.append(f"suite {suite_id!r}: append_user_pytest_args must be a boolean")

    for ignore in suite.get("active_suite_ignores", []):
        if not isinstance(ignore, str) or _confined(root, ignore) is None:
            errors.append(f"suite {suite_id!r}: active_suite_ignore escapes root: {ignore!r}")


def _strip_subst(value: str) -> str:
    """Replace supported substitutions with '.' for path-confinement checks."""
    return SUBSTITUTION_PATTERN.sub(".", value)


def _validate_structure(registry: dict, root: Path) -> list[str]:
    errors: list[str] = []

    for key in registry:
        if key not in ALLOWED_TOP_LEVEL_KEYS:
            errors.append(f"registry: unknown top-level key {key!r}")

    if not isinstance(registry.get("schema_version"), str):
        errors.append("registry: schema_version must be a string")

    import_map = registry.get("import_map")
    if not isinstance(import_map, dict):
        errors.append("registry: import_map must be an object")

    required_dev = registry.get("required_dev_distributions")
    if not isinstance(required_dev, list) or not all(isinstance(x, str) for x in required_dev):
        errors.append("registry: required_dev_distributions must be a list of strings")

    exclusions = registry.get("non_test_exclusions")
    if not isinstance(exclusions, list) or not exclusions:
        errors.append("registry: non_test_exclusions must be a non-empty list")
    else:
        for entry in exclusions:
            if not isinstance(entry, dict):
                errors.append("registry: non_test_exclusions entry must be an object")
                continue
            if not entry.get("path"):
                errors.append("registry: non_test_exclusions entry missing 'path'")
            if not entry.get("reason"):
                errors.append(
                    f"registry: non_test_exclusion {entry.get('path')!r} missing a reason"
                )

    suites = registry.get("suites")
    if not isinstance(suites, list) or not suites:
        errors.append("registry: suites must be a non-empty list")
        return errors

    ids = [suite.get("id") for suite in suites]
    seen: set = set()
    for suite_id in ids:
        if suite_id in seen:
            errors.append(f"registry: duplicate suite id {suite_id!r}")
        seen.add(suite_id)

    for suite in suites:
        _validate_suite(suite, root, errors)

    _validate_ignore_ownership(suites, errors)
    return errors


def _validate_ignore_ownership(suites: list, errors: list[str]) -> None:
    """Every active-suite ignore must map to exactly one other suite owner."""
    owners: dict[str, list[str]] = {}
    for suite in suites:
        for owned_path in suite.get("owned_paths", []):
            if isinstance(owned_path, str):
                owners.setdefault(owned_path, []).append(suite.get("id"))

    for suite in suites:
        suite_id = suite.get("id")
        for ignore in suite.get("active_suite_ignores", []):
            matched = [owner for owner in owners.get(ignore, []) if owner != suite_id]
            if len(matched) != 1:
                errors.append(
                    f"suite {suite_id!r}: active_suite_ignore {ignore!r} must be owned by "
                    f"exactly one other suite (found owners: {matched})"
                )


def _read_pyproject(root: Path) -> tuple[list[str], dict[str, str], list[str]]:
    """Return (runtime names, dev name->version, dev raw specs) from pyproject."""
    with (root / PYPROJECT_RELPATH).open("rb") as handle:
        data = tomllib.load(handle)
    project = data.get("project", {})
    runtime = [
        _normalize(_requirement_name(spec))
        for spec in project.get("dependencies", [])
        if _requirement_name(spec)
    ]
    dev_specs = project.get("optional-dependencies", {}).get("dev", [])
    dev_pins: dict[str, str] = {}
    for spec in dev_specs:
        if "==" in spec:
            name, version = spec.split("==", 1)
            dev_pins[_normalize(name)] = version.strip()
    return runtime, dev_pins, dev_specs


def _read_requirements(root: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in (root / REQUIREMENTS_RELPATH).read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if "==" in stripped:
            name, version = stripped.split("==", 1)
            pins[_normalize(name)] = version.strip()
    return pins


def _validate_dependencies(registry: dict, root: Path, errors: list[str]) -> None:
    try:
        runtime, dev_pins, dev_specs = _read_pyproject(root)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"pyproject.toml unreadable: {exc}")
        return
    try:
        req_pins = _read_requirements(root)
    except OSError as exc:
        errors.append(f"requirements.txt unreadable: {exc}")
        return

    # (10) required dev distributions must be present with an exact pin.
    for dist in registry.get("required_dev_distributions", []):
        if _normalize(dist) not in dev_pins:
            errors.append(
                f"dependencies: required dev distribution {dist!r} is not exact-pinned "
                "in [project.optional-dependencies].dev"
            )

    # Every dev entry must be an exact pin (no floating dev tools).
    for spec in dev_specs:
        if "==" not in spec:
            errors.append(f"dependencies: dev entry {spec!r} is not an exact (==) pin")

    # (11) requirements.txt mirrors all exact dev pins by normalized name.
    for name, version in dev_pins.items():
        if name not in req_pins:
            errors.append(
                f"dependencies: dev pin {name}=={version} not mirrored in requirements.txt"
            )
        elif req_pins[name] != version:
            errors.append(
                f"dependencies: pin mismatch for {name}: pyproject=={version} "
                f"requirements=={req_pins[name]}"
            )

    # (12) import_map distributions resolve to a declared runtime or dev dist.
    declared = set(runtime) | set(dev_pins)
    for import_root, distribution in registry.get("import_map", {}).items():
        if _normalize(distribution) not in declared:
            errors.append(
                f"import_map: {import_root!r} -> {distribution!r} is not a declared "
                "runtime or dev distribution"
            )


def _validate_ci_and_runner(root: Path, errors: list[str]) -> None:
    # (6) wrapper delegates to the Python runner and holds no suite topology.
    wrapper_path = root / WRAPPER_RELPATH
    if not wrapper_path.is_file():
        errors.append(f"wrapper missing: {WRAPPER_RELPATH}")
    else:
        wrapper = wrapper_path.read_text(encoding="utf-8")
        if "run_python_test_suites.py" not in wrapper:
            errors.append("wrapper does not delegate to run_python_test_suites.py")
        topology_markers = [
            "environment/claude-code/autonomy",
            "subagent-generated-data",
            "program-execution",
            "-o addopts=",
            "--ignore=",
            "run_wave3",
        ]
        for marker in topology_markers:
            if marker in wrapper:
                errors.append(f"wrapper contains embedded suite topology: {marker!r}")

    workflow_path = root / WORKFLOW_RELPATH
    if not workflow_path.is_file():
        errors.append(f"workflow missing: {WORKFLOW_RELPATH}")
        return
    workflow = workflow_path.read_text(encoding="utf-8")

    # (7) CI invokes the canonical runner exactly once. Count only real
    # invocation lines; comment lines that merely reference the runner by name
    # (documentation) do not count as invocations.
    invocations = sum(
        1
        for line in workflow.splitlines()
        if "run_python_test_suites.py" in line and not line.strip().startswith("#")
    )
    if invocations != 1:
        errors.append(
            f"workflow must invoke run_python_test_suites.py exactly once (found {invocations})"
        )

    # (9) CI bootstraps with the locked environment.
    if "uv sync --locked --extra dev" not in workflow:
        errors.append("workflow does not bootstrap with 'uv sync --locked --extra dev'")

    # (8) no floating fallback installation of CI test tools.
    for line in workflow.splitlines():
        if "pip install" not in line:
            continue
        lowered = line.lower()
        if any(token in lowered for token in FLOATING_INSTALL_TOKENS):
            errors.append(f"workflow contains a forbidden floating install: {line.strip()!r}")


def _validate_lockfile(root: Path, errors: list[str]) -> None:
    # (13) uv.lock must exist; `uv lock --check` remains the authority on freshness.
    if not (root / LOCKFILE_RELPATH).is_file():
        errors.append(f"lockfile missing: {LOCKFILE_RELPATH}")


def run(root: Path) -> list[str]:
    """Run every drift check against ``root`` and return the list of errors."""
    root = Path(root)
    try:
        registry = load_registry(root)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"registry unreadable: {exc}"]

    errors: list[str] = []
    errors += _validate_structure(registry, root)
    _validate_dependencies(registry, root, errors)
    _validate_ci_and_runner(root, errors)
    _validate_lockfile(root, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Python test contract (read-only).")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root to validate (defaults to this script's repository).",
    )
    args = parser.parse_args(argv)

    errors = run(args.repo_root)
    if errors:
        print(f"FAIL: python-contract drift detected ({len(errors)} issue(s)):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: python-contract is internally consistent (no drift).")
    print("NOTE: `uv lock --check` remains the authoritative lockfile freshness check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
