#!/usr/bin/env python3
"""Validate generated rule manifests against the live rules filesystem."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_rules_manifest import SCHEMA, build_manifest  # noqa: E402

REPO_SPECIFIC_PATTERNS = {
    "plasticos module name": re.compile(r"\bplasticos_", re.I),
    "PlasticOS repository name": re.compile(r"\bPlasticOS\b|\bIB-Odoo", re.I),
    "Odoo deployment endpoint": re.compile(r"\.dev\.odoo\.com|cryptoxdog-ib-odoo", re.I),
    "Odoo model fixture": re.compile(
        r"\baccount\.(?:journal|move)\b|\bres\.(?:company|partner|currency)\b|\bproduct\.product\b",
        re.I,
    ),
    "Odoo version policy": re.compile(r"\bOdoo\s+(?:18|19)\b", re.I),
}
MACHINE_PATH_PATTERNS = (
    re.compile(r"/Users/(?!<|\$|\{)[^/\s]+/"),
    re.compile(r"/home/(?!<|\$|\{)[^/\s]+/"),
)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load(path: Path) -> Any:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    rules_dir = root / "rules"
    json_path = rules_dir / "RULES-MANIFEST.json"
    yaml_path = rules_dir / "RULES-MANIFEST.yaml"
    md_path = rules_dir / "RULES-MANIFEST.md"
    for path in (json_path, yaml_path, md_path):
        if not path.is_file():
            fail(errors, f"missing generated manifest: {path.relative_to(root)}")
    if errors:
        return errors

    actual = build_manifest(root)
    json_data = load(json_path)
    yaml_data = load(yaml_path)
    if json_data != yaml_data:
        fail(errors, "JSON and YAML manifests differ")
    if json_data.get("$schema") != SCHEMA:
        fail(errors, f"unexpected schema: {json_data.get('$schema')}")

    # Timestamps may differ from a fresh in-memory build; compare the source model.
    for volatile in ("generated_utc",):
        actual.pop(volatile, None)
        json_data.pop(volatile, None)
    if json_data != actual:
        fail(errors, "manifest content does not match rules filesystem; regenerate it")

    entries = json_data.get("rules", [])
    files = [entry.get("file") for entry in entries]
    ids = [entry.get("id") for entry in entries]
    if len(files) != len(set(files)):
        fail(errors, "duplicate filenames in manifest")
    if len(ids) != len(set(ids)):
        fail(errors, "duplicate rule IDs in manifest")

    disk_files = sorted(path.name for path in rules_dir.glob("*.mdc"))
    if sorted(files) != disk_files:
        fail(errors, "manifest file set differs from rules/*.mdc")

    summary = json_data.get("summary", {})
    if summary.get("total_mdc_files") != len(entries):
        fail(errors, "summary total does not equal entry count")
    true_count = sum(entry.get("always_apply") is True for entry in entries)
    false_count = sum(entry.get("always_apply") is False for entry in entries)
    none_count = len(entries) - true_count - false_count
    if summary.get("always_apply_true") != true_count:
        fail(errors, "alwaysApply true count is stale")
    if summary.get("always_apply_false") != false_count:
        fail(errors, "alwaysApply false count is stale")
    if summary.get("no_boolean_always_apply") != none_count:
        fail(errors, "non-boolean alwaysApply count is stale")

    for entry in entries:
        path = rules_dir / entry["file"]
        digest = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        if entry.get("content_digest") != digest:
            fail(errors, f"digest mismatch: {entry['file']}")
        activation = entry.get("activation")
        if activation == "agent_requested" and not entry.get("description"):
            fail(errors, f"Agent Requested rule lacks description: {entry['file']}")
        if activation == "auto_attached" and not entry.get("globs"):
            fail(errors, f"Auto Attached rule lacks usable globs: {entry['file']}")
        if entry.get("deprecated") and not (entry.get("replacement") or entry.get("removal_plan")):
            fail(errors, f"deprecated rule lacks replacement/removal plan: {entry['file']}")
        content = path.read_text(encoding="utf-8")
        for pattern in MACHINE_PATH_PATTERNS:
            if pattern.search(content):
                fail(errors, f"hardcoded machine path in {entry['file']}")
        for label, pattern in REPO_SPECIFIC_PATTERNS.items():
            if pattern.search(content):
                fail(errors, f"global domain leakage ({label}) in {entry['file']}")

    md = md_path.read_text(encoding="utf-8")
    expected_total = json_data["summary"]["total_mdc_files"]
    if f"| Total MDC files | **{expected_total}** |" not in md:
        fail(errors, "Markdown summary is not generated from the JSON model")
    for filename in disk_files:
        if f"`{filename}`" not in md:
            fail(errors, f"Markdown manifest omits {filename}")

    path_validator = root / "ops/scripts/validate_governance_no_hardcoded_paths.sh"
    if path_validator.is_file():
        result = subprocess.run(["bash", str(path_validator)], cwd=root, capture_output=True, text=True)
        if result.returncode != 0:
            fail(errors, "validate_governance_no_hardcoded_paths.sh failed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        print(f"RESULT: FAIL ({len(errors)} errors)", file=sys.stderr)
        return 1
    print("RESULT: PASS - manifests match filesystem and rule contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
