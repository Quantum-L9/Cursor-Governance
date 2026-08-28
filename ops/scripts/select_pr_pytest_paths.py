#!/usr/bin/env python3
"""Select local make pr-check pytest paths. Never emit repo-root '.'."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "ops" / "config" / "python-contract.json"


def _load_suites(registry: Path) -> list[dict]:
    data = json.loads(registry.read_text(encoding="utf-8"))
    suites = data.get("suites") or []
    if not isinstance(suites, list):
        raise SystemExit("python-contract.json suites must be a list")
    return [item for item in suites if isinstance(item, dict)]


def is_dot_owned(suite: dict) -> bool:
    owned = [str(path) for path in (suite.get("owned_paths") or [])]
    return "." in owned


def path_under(path: str, root: str) -> bool:
    if root in {".", ""}:
        return False
    return path == root or path.startswith(root.rstrip("/") + "/")


def infer_test_path(changed: str, *, repo_root: Path = REPO_ROOT) -> str | None:
    name = Path(changed).name
    if not changed.endswith(".py"):
        return None
    if name.startswith("test_") or "/tests/" in changed:
        return changed
    stem = Path(changed).stem
    parent = Path(changed).parent
    candidates = [
        Path("tests") / parent / f"test_{stem}.py",
        parent / "tests" / f"test_{stem}.py",
        parent / f"test_{stem}.py",
    ]
    for candidate in candidates:
        if (repo_root / candidate).is_file():
            return candidate.as_posix()
    return None


def root_collect_ignores(repo_root: Path = REPO_ROOT) -> list[str]:
    """`collect_ignore` from the root conftest — what the repo-root suite never collects.

    Read rather than restated so there is one list, not two that drift. The
    conftest assigns a literal, so the value is taken from the AST instead of
    importing the module.
    """
    conftest = repo_root / "conftest.py"
    if not conftest.is_file():
        return []
    try:
        tree = ast.parse(conftest.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if not any(isinstance(item, ast.Name) and item.id == "collect_ignore" for item in targets):
            continue
        try:
            value = ast.literal_eval(node.value)
        except ValueError:
            return []
        return [str(item) for item in value if isinstance(item, str)]
    return []


def _has_pytest_owner(path: str, suites: list[dict]) -> bool:
    return any(
        not is_dot_owned(suite)
        and any(
            path_under(path, str(root)) or path_under(str(root), path) or path == str(root)
            for root in (suite.get("owned_paths") or [])
        )
        for suite in suites
    )


def _drop_unrunnable(selected: list[str], suites: list[dict]) -> tuple[list[str], list[str]]:
    """Split off targets no pytest suite can actually collect.

    A path the root conftest excludes belongs to a non-pytest loader (the
    Program Execution adapter layer runs under `make program-execution-conformance`).
    Handing it to the repo-root suite as an explicit argument overrides that
    exclusion and fails on import, so it is not a valid pr-check target unless a
    non-root suite owns it.
    """
    ignores = root_collect_ignores()
    keep: list[str] = []
    dropped: list[str] = []
    for path in selected:
        ignored = any(path_under(path, root) or path == root for root in ignores)
        if ignored and not _has_pytest_owner(path, suites):
            dropped.append(path)
        else:
            keep.append(path)
    return keep, dropped


def tests_referencing(changed: str, tests_dir: Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Test files that actually name this module.

    A source file with no `test_<stem>.py` twin used to pull in its entire
    sibling tests/ directory. One unmatched file under
    environment/program-execution/scripts/ therefore selected every PE script
    test — smoke campaigns and worker lifecycles included — for a change that
    touched none of them. Tests that mention the module by name are the ones
    that can plausibly break; when none do, the caller keeps the whole
    directory, so this only ever narrows a guess, never a certainty.
    """
    stem = Path(changed).stem
    if not stem:
        return []
    # Leading boundary only. A trailing \b would miss `campaign_input_module`,
    # which is exactly how the tests that exercise `campaign_input` name it —
    # and missing them is what sends the whole directory back into the run.
    needle = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(stem)}")
    found: list[str] = []
    for path in sorted(tests_dir.rglob("test_*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if needle.search(text):
            found.append(path.relative_to(repo_root).as_posix())
    return found


def tests_naming_path(changed: str, *, repo_root: Path = REPO_ROOT) -> list[str]:
    """Test files that name a non-Python changed file.

    A shell script, workflow, or config file has no `test_<stem>.py` twin, so
    stem inference finds nothing and the file used to contribute no targets at
    all. Tests still assert *about* such files by naming them — the swallowed
    failure ratchet keys SWALLOW_BASELINE on 'ops/scripts/run_pr_gate.sh', and
    a change to that script is exactly what it exists to catch. Scanning the
    295 test modules for the literal name costs ~20ms, so the whole tree is
    searched rather than a guessed subdirectory.

    Both the repository-relative path and the bare filename count as naming the
    file: a test that says `run_pr_gate.sh` asserts about it just as much as one
    that spells the full path, and dropping the second kind loses real coverage.
    Path matches are listed first only so the most specific targets lead.
    """

    target = changed.strip()
    if not target:
        return []
    basename = Path(target).name
    by_path: list[str] = []
    by_name: list[str] = []
    for path in sorted(repo_root.rglob("test_*.py")):
        if any(part in {".venv", ".git", "node_modules"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative = path.relative_to(repo_root).as_posix()
        if target in text:
            by_path.append(relative)
        elif basename and basename in text:
            by_name.append(relative)
    return by_path + [item for item in by_name if item not in by_path]


def select_pr_pytest_paths(changed: list[str], *, registry: Path = REGISTRY_PATH) -> list[str]:
    """Return explicit pytest targets for the local pr-check profile."""
    py_changed = [path for path in changed if path.endswith(".py")]
    # A non-Python change is not an untested change. Shell scripts, workflows
    # and config files are asserted about by name, so they select the tests
    # that name them; without this a `.sh` edit selected nothing and shipped
    # straight to CI.
    other_changed = [path for path in changed if not path.endswith(".py")]
    if not py_changed and not other_changed:
        return []
    suites = _load_suites(registry)
    selected: list[str] = []
    missing: list[str] = []
    for path in other_changed:
        for target in tests_naming_path(path):
            if target not in selected:
                selected.append(target)
    for path in py_changed:
        if Path(path).name == "conftest.py":
            # Fixture module, not a collectable test. Passing it as an explicit
            # target collides with tests/**/conftest.py (import file mismatch).
            continue
        inferred = infer_test_path(path)
        if inferred:
            if inferred not in selected:
                selected.append(inferred)
            continue
        owners = [
            suite
            for suite in suites
            if not is_dot_owned(suite)
            and any(path_under(path, str(root)) for root in (suite.get("owned_paths") or []))
        ]
        if owners:
            for suite in owners:
                for root in suite.get("owned_paths") or []:
                    text = str(root)
                    if text and text != "." and text not in selected:
                        selected.append(text)
            continue
        tests_dir = Path(path).parent / "tests"
        if (REPO_ROOT / tests_dir).is_dir():
            referencing = tests_referencing(path, REPO_ROOT / tests_dir)
            fallbacks = referencing or [tests_dir.as_posix()]
        else:
            fallbacks = [str(Path(path).parent)]
        for target in fallbacks:
            if target not in selected:
                selected.append(target)
        # The source file itself is not a pytest target: collecting a
        # non-test module yields nothing and only lengthens the command.
        missing.append(path)
    if "." in selected:
        raise SystemExit("select_pr_pytest_paths refused to emit repo-root '.'")
    # A directory target already collects everything beneath it; listing the
    # files too just makes the command longer than the work it describes.
    directories = [item for item in selected if not item.endswith(".py")]
    selected = [
        item
        for item in selected
        if item in directories or not any(path_under(item, root) for root in directories)
    ]
    selected, unrunnable = _drop_unrunnable(selected, suites)
    if missing:
        still_missing = [path for path in missing if path not in unrunnable]
        if still_missing:
            print(
                "NOTE: no inferred test for "
                + ", ".join(still_missing)
                + "; scoped to that tests/ directory, not the catalog",
                file=sys.stderr,
            )
    if unrunnable:
        print(
            "NOTE: not a repo-root pytest target (excluded by root conftest, owned by a "
            "non-pytest loader): " + ", ".join(unrunnable),
            file=sys.stderr,
        )
    return selected


def _read_changed(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed-file", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    args = parser.parse_args(argv)
    for item in select_pr_pytest_paths(_read_changed(args.changed_file), registry=args.registry):
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
