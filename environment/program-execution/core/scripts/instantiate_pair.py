#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Instantiate aligned Blueprint and Controller siblings")
    p.add_argument("--program-name", required=True)
    p.add_argument("--program-id", required=True)
    p.add_argument("--program-version", required=True)
    p.add_argument("--program-owner", required=True)
    p.add_argument("--controller-name", required=True)
    p.add_argument("--controller-id", required=True)
    p.add_argument("--controller-owner", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--target", required=True, type=Path)
    a = p.parse_args()
    target = a.target.resolve()
    if target.exists():
        raise SystemExit(f"target already exists: {target}")
    target.mkdir(parents=True)
    bp = target / "program-execution-blueprint"
    ct = target / "program-execution-controller"
    run(
        [
            sys.executable,
            str(ROOT / "program-execution-blueprint-template/scripts/instantiate.py"),
            "--name",
            a.program_name,
            "--id",
            a.program_id,
            "--version",
            a.program_version,
            "--owner",
            a.program_owner,
            "--date",
            a.date,
            "--target",
            str(bp),
        ]
    )
    run(
        [
            sys.executable,
            str(ROOT / "program-execution-controller-template/scripts/instantiate.py"),
            "--name",
            a.controller_name,
            "--id",
            a.controller_id,
            "--owner",
            a.controller_owner,
            "--date",
            a.date,
            "--target",
            str(ct),
        ]
    )
    pair = {
        "schema": "program-execution-system.pair.v2",
        "pair_contract": "program-execution-system.v2",
        "program_id": a.program_id,
        "blueprint": "program-execution-blueprint",
        "controller": "program-execution-controller",
        "definition_status": "draft_until_blueprint_placeholders_and_runtime_bindings_are_completed",  # noqa: E501
    }
    (target / "PAIR.yaml").write_text(yaml.safe_dump(pair, sort_keys=False), encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
