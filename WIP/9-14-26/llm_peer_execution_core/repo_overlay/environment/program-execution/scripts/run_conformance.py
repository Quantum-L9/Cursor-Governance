from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from peer_execution.imports import load_module


def _test_files(root: Path) -> list[Path]:
    files = list((root / "conformance").glob("test_*.py"))
    files.extend((root / "tests").glob("test_*.py"))
    files.extend((root / "peer_execution/tests").glob("test_*.py"))
    files.extend((root / "adapters").glob("**/tests/test_*.py"))
    files.extend((root / "integrations").glob("**/tests/test_*.py"))
    return sorted(set(path.resolve() for path in files))


def run(root: Path) -> dict[str, object]:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    files = _test_files(root)
    for index, path in enumerate(files):
        module = load_module(path, f"pes_test_module_{index}")
        suite.addTests(loader.loadTestsFromModule(module))
    stream = unittest.runner._WritelnDecorator(sys.stderr)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return {
        "schema": "program-execution-adapter.conformance-report.v1",
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "test_files": [path.relative_to(root).as_posix() for path in files],
    }


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    report = run(root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
