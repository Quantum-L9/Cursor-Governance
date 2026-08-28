#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> None:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, *args], text=True, capture_output=True, env=env)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    print(result.stdout.strip())


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    run(str(root / "scripts" / "validate_skill.py"))
    run(str(root / "scripts" / "evaluate_fixtures.py"))
    run(str(root / "scripts" / "validate_ledger.py"), str(root / "fixtures" / "sample_ledger.json"))
    run(str(root / "scripts" / "evaluate_confidence_cases.py"))
    run(str(root / "scripts" / "validate_exemplary_skill.py"), str(root))
    print("PASS: all self-tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
