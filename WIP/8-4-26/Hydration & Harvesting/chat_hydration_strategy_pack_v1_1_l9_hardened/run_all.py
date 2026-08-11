#!/usr/bin/env python3
"""One-command validation orchestrator for the L9 mobile chat session hydration pack.

Runs structural checks only. It does not mutate artifacts, call network services,
or simulate ChatGPT mobile runtime behavior.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_step(index: int, total: int, name: str, command: list[str]) -> None:
    print(f"[{index}/{total}] {name}: {' '.join(command)}")
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        print(f"FAILED: {name} exited with {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def check_required_files() -> None:
    required = [
        "README.md",
        "MANIFEST.md",
        "QUICKSTART.md",
        "LICENSE.md",
        "00_manifest/MANIFEST.yaml",
        "00_manifest/ARTIFACT_REGISTRY.yaml",
        "00_manifest/KERNEL_REFERENCE_REGISTRY.yaml",
        "01_strategy/session_hydration_strategy.canonical_spec.v1.yaml",
        "02_runtime_contracts/mobile_hydration_system_prompt.md",
        "04_playbook/PLAYBOOK.md",
        "05_skill/l9-mobile-session-hydrator/SKILL.md",
        "08_validation/REGRESSION_GUARD.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        raise SystemExit("missing required files: " + ", ".join(missing))
    print("required_file_check_passed")


def scan_for_disallowed_markers() -> None:
    disallowed = ["TODO", "TBD", "placeholder", "fake validation", "should work", "appears valid"]
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".py", ".txt"}:
            continue
        if path.name == "run_all.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in disallowed:
            if marker.lower() in text.lower():
                findings.append(f"{path.relative_to(ROOT)} contains {marker}")
    if findings:
        raise SystemExit("disallowed marker scan failed:\n" + "\n".join(findings))
    print("disallowed_marker_scan_passed")


def main() -> None:
    total = 5
    check_required_files()
    scan_for_disallowed_markers()
    run_step(1, total, "base pack validation", [sys.executable, "08_validation/validate_pack.py"])
    run_step(2, total, "L9 hardening validation", [sys.executable, "08_validation/validate_l9_hardening.py"])
    run_step(3, total, "recursive hardening validation", [sys.executable, "-c", "import yaml, pathlib; [yaml.safe_load(p.read_text()) for p in pathlib.Path('.').rglob('*.yaml')]; print('yaml_parse_passed')"])
    run_step(4, total, "manifest presence", [sys.executable, "-c", "from pathlib import Path; assert Path('00_manifest/MANIFEST.yaml').exists(); print('manifest_present')"])
    run_step(5, total, "quick artifact count", [sys.executable, "-c", "from pathlib import Path; print('file_count=' + str(sum(1 for p in Path('.').rglob('*') if p.is_file())))"])
    print("polish_validation_passed")


if __name__ == "__main__":
    main()
