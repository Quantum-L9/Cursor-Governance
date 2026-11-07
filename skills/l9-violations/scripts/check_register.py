#!/usr/bin/env python3
"""Fail when the violation register and its briefs disagree."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

STATUSES = {"open", "acknowledged", "addressed"}
SEVERITIES = {"critical", "high", "medium"}
ID_RE = re.compile(r"^V-(\d{4}-\d{2}-\d{2})-(\d{3})$")


def check(root: Path) -> list[str]:
    """Return one error string per broken register invariant."""
    errors: list[str] = []
    register_path = root / "records" / "register.yaml"
    if not register_path.is_file():
        return ["missing records/register.yaml"]
    data = yaml.safe_load(register_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return ["records/register.yaml must be a mapping"]
    records = data.get("records")
    if not isinstance(records, list) or not records:
        errors.append("records must be a non-empty list")
        records = []
    seen: set[str] = set()
    for row in records:
        if not isinstance(row, dict):
            errors.append("record row is not a mapping")
            continue
        record_id = str(row.get("id", ""))
        brief = str(row.get("brief", ""))
        status = str(row.get("status", ""))
        severity = str(row.get("severity", ""))
        match = ID_RE.fullmatch(record_id)
        if match is None:
            errors.append(f"bad id: {record_id}")
        elif str(row.get("date", "")) != match.group(1):
            errors.append(f"{record_id}: date does not match the id")
        if record_id in seen:
            errors.append(f"duplicate id: {record_id}")
        seen.add(record_id)
        if status not in STATUSES:
            errors.append(f"{record_id}: status {status} is not open, acknowledged, or addressed")
        if severity not in SEVERITIES:
            errors.append(f"{record_id}: severity {severity} is not critical, high, or medium")
        if not str(row.get("type", "")).strip():
            errors.append(f"{record_id}: type is empty")
        if brief != f"records/{record_id}.md":
            errors.append(f"{record_id}: brief must be records/{record_id}.md")
            continue
        path = (root / brief).resolve()
        if path.parent != (root / "records").resolve():
            errors.append(f"{record_id}: brief leaves records/")
            continue
        if not path.is_file():
            errors.append(f"{record_id}: missing {brief}")
            continue
        if record_id not in path.read_text(encoding="utf-8"):
            errors.append(f"{record_id}: brief does not contain its id")
    on_disk = {path.name[: -len(".md")] for path in (root / "records").glob("V-*.md")}
    missing = on_disk - seen
    if missing:
        errors.append("briefs missing from the register: " + ", ".join(sorted(missing)))
    fixtures = data.get("fixtures")
    if not isinstance(fixtures, dict):
        errors.append("fixtures must be a mapping")
    else:
        rel = str(fixtures.get("file", ""))
        if rel != "records/fixtures.yaml":
            errors.append("fixtures.file must be records/fixtures.yaml")
        else:
            path = root / rel
            if not path.is_file():
                errors.append("missing records/fixtures.yaml")
            else:
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
                entries = payload.get("entries") if isinstance(payload, dict) else None
                expected = fixtures.get("count")
                if not isinstance(entries, list) or not entries:
                    errors.append("fixtures entries must be a non-empty list")
                elif expected != len(entries):
                    errors.append(f"fixtures count {expected} != {len(entries)} entries")
                else:
                    for entry in entries:
                        label = entry.get("violation_id") if isinstance(entry, dict) else None
                        if not label:
                            errors.append("fixture entry missing violation_id")
                        elif entry.get("class") != "tracker_self_test":
                            errors.append(f"{label}: class must be tracker_self_test")
    return errors


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errors = check(root)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: violation register ({root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
