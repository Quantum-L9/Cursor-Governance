#!/usr/bin/env python3
"""Fail closed when a live pointer-stack file lacks declared headings/pointers.

Read-only. Never creates or overwrites documentation files.
A mapped path that does not exist is Unknown (bind-before-write), not a create cue.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

PACK = Path(__file__).resolve().parents[1]
MAP_PATH = PACK / "references" / "pointer-heading-map.yaml"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def normalize_heading(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "", cleaned).lower()


def load_map() -> dict:
    return yaml.safe_load(MAP_PATH.read_text(encoding="utf-8"))


def headings_in(text: str) -> set[str]:
    return {normalize_heading(match.group(2)) for match in HEADING_RE.finditer(text)}


def check_file(root: Path, rel: str, spec: dict) -> tuple[str, list[str]]:
    path = root / rel
    if not path.is_file():
        return "Unknown", [f"{rel}: missing on disk (Unknown; do not create)"]
    text = path.read_text(encoding="utf-8")
    found = headings_in(text)
    errors: list[str] = []
    for heading in spec.get("required_headings") or []:
        if normalize_heading(heading) not in found:
            errors.append(f"{rel}: missing required heading {heading!r}")
    for pointer in spec.get("required_pointers") or []:
        if pointer not in text:
            errors.append(f"{rel}: missing required pointer {pointer!r}")
    return ("Failed" if errors else "Passed"), errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root to inspect")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    mapping = load_map()
    forbidden = {normalize_heading(name) for name in mapping.get("forbidden_donor_sections") or []}
    errors: list[str] = []
    unknowns: list[str] = []
    for rel, spec in (mapping.get("files") or {}).items():
        for heading in spec.get("required_headings") or []:
            if normalize_heading(heading) in forbidden:
                errors.append(f"map {rel}: donor section {heading!r} must not be required")
        status, findings = check_file(root, rel, spec)
        if status == "Unknown":
            unknowns.extend(findings)
        else:
            errors.extend(findings)
        print(f"{rel}: {status}")
    for item in unknowns:
        print(f"Unknown: {item}")
    if errors:
        print("FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
