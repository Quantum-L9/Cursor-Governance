"""The scoped repo-root suite never receives a root its full run ignores.

``run_python_test_suites.py`` hands the dot-owned suite its scoped paths as
explicit pytest arguments, and pytest's ``--ignore`` does not apply to an
explicit argument. A root that the suite ignores in its full run therefore has
to be withheld from the scoped run, or the scoped run collects what the full
run never would.

The withheld set used to be the owned paths of the other *pytest* suites only.
The Program Execution Controller suite is a ``command_sequence`` that runs from
its template directory, where its tests import ``helpers`` as a sibling, so a
PR touching those tests handed the directory to root pytest, where every module
errored on collection with ``No module named 'helpers'`` while the Controller
suite also ran it. Ownership by a non-pytest suite is not the criterion
(``skills`` is owned by one and is still collected by root pytest on purpose);
the repo-root suite's own ``--ignore`` list is.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_python_test_suites import (  # noqa: E402
    REGISTRY_PATH,
    _load_json,
    _load_selector,
    _non_dot_roots,
    _root_suite_paths,
    validate_registry,
)

CONTROLLER_TESTS = (
    "environment/program-execution/core/program-execution-controller-template/scripts/tests"
)


def _suites(root_ignores: list[str]) -> list[dict]:
    argv = [".", *[f"--ignore={root}" for root in root_ignores]]
    return [
        {
            "id": "repo-root",
            "kind": "pytest",
            "owned_paths": ["."],
            "profiles": {"local": {"argv": argv}, "ci": {"argv": [*argv, "-n", "auto"]}},
        },
        {
            "id": "sequence-owner",
            "kind": "command_sequence",
            "owned_paths": ["pkg/scripts/tests"],
            "profiles": {"local": {"argv": [["python", "run.py"]]}},
        },
        {
            "id": "pytest-owner",
            "kind": "pytest",
            "owned_paths": ["other/tests"],
            "profiles": {"local": {"argv": ["."]}},
        },
        {
            "id": "collected-anyway",
            "kind": "command_sequence",
            "owned_paths": ["skills"],
            "profiles": {"local": {"argv": [["python", "check.py"]]}},
        },
    ]


def test_root_suite_ignores_are_withheld_whatever_kind_owns_them() -> None:
    selector = _load_selector()
    roots = _non_dot_roots(_suites(["pkg/scripts/tests"]), selector)
    assert "pkg/scripts/tests" in roots, "ignored by the root suite: withheld"
    assert "other/tests" in roots, "owned by another pytest suite: withheld"
    assert "skills" not in roots, "owned by a command suite the root suite collects: kept"
    scoped = [
        "pkg/scripts/tests",
        "pkg/scripts/tests/test_a.py",
        "other/tests/test_b.py",
        "skills/x/tests/test_c.py",
        "tests/test_d.py",
    ]
    assert _root_suite_paths(scoped, roots, selector) == [
        "skills/x/tests/test_c.py",
        "tests/test_d.py",
    ]


def test_the_registry_withholds_the_controller_tests_from_root_pytest() -> None:
    selector = _load_selector()
    suites = validate_registry(_load_json(REGISTRY_PATH))
    roots = _non_dot_roots(suites, selector)
    assert CONTROLLER_TESTS in roots
    scoped = [CONTROLLER_TESTS, f"{CONTROLLER_TESTS}/test_approval.py", "tests/test_x.py"]
    assert _root_suite_paths(scoped, roots, selector) == ["tests/test_x.py"]
    owners = [s["id"] for s in suites if CONTROLLER_TESTS in s.get("owned_paths", [])]
    assert owners == ["program-execution-controller"], "still owned by its own suite"
