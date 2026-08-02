#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def manifest_ok(root: Path) -> bool:
    m = yaml.safe_load((root / "MANIFEST.yaml").read_text())
    expected = {x["path"]: x["sha256"] for x in m.get("files", [])}
    actual = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
        and p.name != "MANIFEST.yaml"
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    }
    return expected == actual


def compatible(root: Path) -> bool:
    c = yaml.safe_load((root / "COMPATIBILITY.yaml").read_text())
    p = yaml.safe_load((root / "program-execution-blueprint-template/PROGRAM.yaml").read_text())[
        "program"
    ]
    r = yaml.safe_load(
        (root / "program-execution-controller-template/CONTROLLER.yaml").read_text()
    )["controller"]
    return (
        p["contracts"]["blueprint"] == c["blueprint_contract"]
        and p["contracts"]["pair"] == c["pair_contract"]
        and r["contracts"]
        == {
            "controller": c["controller_contract"],
            "blueprint": c["blueprint_contract"],
            "pair": c["pair_contract"],
        }
    )


def main() -> int:
    if not manifest_ok(ROOT) or not compatible(ROOT):
        raise SystemExit("positive pair fixture failed")
    with tempfile.TemporaryDirectory() as raw:
        copy = Path(raw) / "pair"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (copy / "README.md").write_text((copy / "README.md").read_text() + "\ntamper\n")
        if manifest_ok(copy):
            raise SystemExit("manifest tamper falsely passed")
    with tempfile.TemporaryDirectory() as raw:
        copy = Path(raw) / "pair"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        path = copy / "COMPATIBILITY.yaml"
        v = yaml.safe_load(path.read_text())
        v["controller_contract"] = "program-execution-controller.v99"
        path.write_text(yaml.safe_dump(v, sort_keys=False))
        if compatible(copy):
            raise SystemExit("contract mismatch falsely passed")
    print(
        json.dumps(
            {
                "status": "PASS",
                "fixtures": ["positive_pair", "root_manifest_tamper", "contract_version_mismatch"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
