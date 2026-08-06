from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[1]


def run_suite(
    directory: Path,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(directory),
        "-p",
        "test_*.py",
        "-v",
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return {
        "directory": str(directory),
        "command": command,
        "exit_code": completed.returncode,
        "output": completed.stdout,
        "passed": completed.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all Wave 3 test suites.")
    parser.add_argument(
        "--json",
        action="store_true",
    )
    args = parser.parse_args()
    suites = [
        BASE / "tests" / "conformance",
        BASE / "tests" / "routing",
        BASE / "tests" / "negative",
        BASE / "tests" / "golden",
    ]
    results = [run_suite(directory) for directory in suites]
    if args.json:
        print(
            json.dumps(
                {
                    "passed": all(result["passed"] for result in results),
                    "results": results,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for result in results:
            print(f"\n=== {result['directory']} ===")
            print(result["output"])
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
