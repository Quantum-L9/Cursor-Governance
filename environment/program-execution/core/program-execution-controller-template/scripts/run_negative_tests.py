#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], success: bool) -> subprocess.CompletedProcess[str]:
    r = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if (r.returncode == 0) != success:
        raise SystemExit(f"unexpected result: {cmd}\n{r.stdout}\n{r.stderr}")
    return r


def main() -> int:
    run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_controller.py"),
            str(ROOT),
            "--mode",
            "template",
        ],
        True,
    )
    policy = (ROOT / "policy/autonomy.yaml").read_text()
    if "push: denied" not in policy or "pull_request: denied" not in policy:
        raise SystemExit("remote denial missing")
    print(
        json.dumps(
            {"status": "PASS", "fixtures": ["controller_structure", "remote_authority_denial"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
