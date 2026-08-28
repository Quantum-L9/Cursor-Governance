from __future__ import annotations

import argparse
import io
import json
import os
import sys
import unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from peer_execution.imports import load_module


def _test_files(root: Path) -> list[Path]:
    files = list((root / "conformance").glob("test_*.py"))
    files.extend((root / "tests").glob("test_*.py"))
    files.extend((root / "peer_execution/tests").glob("test_*.py"))
    files.extend((root / "adapters").glob("**/tests/test_*.py"))
    files.extend((root / "integrations").glob("**/tests/test_*.py"))
    files.extend((root / "scripts/tests").glob("test_*.py"))
    return sorted(set(path.resolve() for path in files))


def _load(index: int, path: Path) -> Any:
    """Import one test file under its synthetic module name.

    Several suites import a sibling test module by bare name
    (`from test_run_campaign import ...`). Serially that happened to work once
    any earlier file in the same directory had inserted it on `sys.path`, so
    the imports silently depended on load order. A shard starts with its own
    interpreter, so make every file self-sufficient: its own directory first,
    which is both what pytest does and what those modules already declare they
    need. Own-directory-first also keeps a sibling basename that repeats across
    adapter directories resolving to the file's own neighbour.
    """
    own_dir = str(path.parent)
    if own_dir not in sys.path:
        sys.path.insert(0, own_dir)
    return load_module(path, f"pes_test_module_{index}")


def _classes(suite: unittest.TestSuite) -> list[str]:
    """Test-class names in `suite`, in collection order, without duplicates."""
    seen: dict[str, None] = {}
    for test in _flatten(suite):
        seen.setdefault(type(test).__name__, None)
    return list(seen)


def _flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    tests: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            tests.extend(_flatten(item))
        else:
            tests.append(item)
    return tests


def _run_shard(task: tuple[int, str, str]) -> dict[str, Any]:
    """Load one test file and run exactly one of its test classes.

    Runs in a worker process. A class is the shard unit rather than a file
    because one file (`test_prepare_resumable.py`) was longer than every other
    file put together, so file-level sharding left it as the wall-clock floor.
    Nothing is skipped, filtered, or reordered within a class -- this splits
    the same suite across processes.
    """
    index, path_str, class_name = task
    module = _load(index, Path(path_str))
    suite = unittest.TestLoader().loadTestsFromModule(module)
    selected = unittest.TestSuite(
        test for test in _flatten(suite) if type(test).__name__ == class_name
    )
    stream = unittest.runner._WritelnDecorator(io.StringIO())
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(selected)
    return {
        "index": index,
        "class_name": class_name,
        "output": stream.stream.getvalue(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
    }


def _resolve_jobs(requested: int | None, shard_count: int) -> int:
    """Worker count: explicit flag, then $PES_CONFORMANCE_JOBS, then CPU count.

    Clamped to the shard count, because an idle worker buys nothing.
    """
    if requested is None:
        raw = os.environ.get("PES_CONFORMANCE_JOBS", "").strip()
        requested = int(raw) if raw.isdigit() else 0
    if requested <= 0:
        requested = os.cpu_count() or 1
    return max(1, min(requested, shard_count))


def _plan(files: list[Path]) -> list[tuple[int, str, str]]:
    """One shard per (file, test class), heaviest directory scheduled first.

    Enumerating classes needs the modules imported, which costs ~0.3s for the
    whole tree. The campaign suites under `scripts/tests` hold every shard over
    ten seconds and sort last alphabetically, so a pool that consumed the list
    in order would start the longest shard last and idle three workers waiting
    on it. Reversing the order starts the long poles first; ordering is a
    scheduling hint only and changes no result.
    """
    tasks: list[tuple[int, str, str]] = []
    for index, path in enumerate(files):
        module = _load(index, path)
        suite = unittest.TestLoader().loadTestsFromModule(module)
        tasks.extend((index, str(path), name) for name in _classes(suite))
    return list(reversed(tasks))


def run(root: Path, jobs: int | None = None) -> dict[str, object]:
    files = _test_files(root)
    tasks = _plan(files) if files else []
    if not tasks:
        return {
            "schema": "program-execution-adapter.conformance-report.v1",
            "status": "PASS",
            "tests_run": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "test_files": [path.relative_to(root).as_posix() for path in files],
        }

    worker_count = _resolve_jobs(jobs, len(tasks))
    if worker_count == 1:
        # One process: the shape to debug in when a failure looks like it could
        # be cross-shard.
        shards = [_run_shard(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as pool:
            shards = list(pool.map(_run_shard, tasks))

    # Print in file-then-class order regardless of completion order, so a
    # parallel transcript stays readable and stable between runs.
    # Key on (file, class): a class name can legitimately appear in two files,
    # because one suite imports another's TestCase by name.
    order = {(task[0], task[2]): position for position, task in enumerate(reversed(tasks))}
    for shard in sorted(
        shards,
        key=lambda item: order[(int(item["index"]), str(item["class_name"]))],
    ):
        sys.stderr.write(str(shard["output"]))
    sys.stderr.flush()

    failures = sum(int(shard["failures"]) for shard in shards)
    errors = sum(int(shard["errors"]) for shard in shards)
    return {
        "schema": "program-execution-adapter.conformance-report.v1",
        "status": "PASS" if failures == 0 and errors == 0 else "FAIL",
        "tests_run": sum(int(shard["tests_run"]) for shard in shards),
        "failures": failures,
        "errors": errors,
        "skipped": sum(int(shard["skipped"]) for shard in shards),
        "test_files": [path.relative_to(root).as_posix() for path in files],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Program Execution adapter-layer conformance suite."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="Program Execution root (default: the parent of this script's directory).",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=None,
        help=(
            "Worker processes, one test class per shard. Default: "
            "$PES_CONFORMANCE_JOBS, else the CPU count. 1 runs serially in-process."
        ),
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    report = run(root, jobs=args.jobs)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
