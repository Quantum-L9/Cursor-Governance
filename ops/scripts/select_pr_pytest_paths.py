#!/usr/bin/env python3
"""Select local make pr-check pytest paths. Never emit repo-root '.'."""

from __future__ import annotations

import argparse
import json
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


def select_pr_pytest_paths(changed: list[str], *, registry: Path = REGISTRY_PATH) -> list[str]:
    """Return explicit pytest targets for the local pr-check profile."""
    py_changed = [path for path in changed if path.endswith(".py")]
    if not py_changed:
        return []
    suites = _load_suites(registry)
    selected: list[str] = []
    missing: list[str] = []
    for path in py_changed:
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
        tests_dir = str(Path(path).parent / "tests")
        fallback = tests_dir if (REPO_ROOT / tests_dir).is_dir() else str(Path(path).parent)
        if fallback not in selected:
            selected.append(fallback)
        if path not in selected:
            selected.append(path)
        missing.append(path)
    if "." in selected:
        raise SystemExit("select_pr_pytest_paths refused to emit repo-root '.'")
    if missing:
        print(
            "NOTE: no inferred test for "
            + ", ".join(missing)
            + "; scoped to that tests/ directory, not the catalog",
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
