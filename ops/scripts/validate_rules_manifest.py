#!/usr/bin/env python3
"""Validate global rule manifests against the active rules directory."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import yaml

sys.dont_write_bytecode = True

LOCAL_ONLY_FILENAMES = {
    "30-odoo-native.mdc",
    "95-plasticos-equipment-policy.mdc",
    "98-odoo-sh-staging.mdc",
}


def load_generator(script_dir: Path):
    path = script_dir / "generate_rules_manifest.py"
    spec = importlib.util.spec_from_file_location("generate_rules_manifest", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_timestamp(data: dict[str, Any]) -> dict[str, Any]:
    copied = dict(data)
    copied.pop("generated_utc", None)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-dir", type=Path, default=Path(__file__).resolve().parents[2] / "rules")
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--yaml", dest="yaml_path", type=Path)
    args = parser.parse_args()

    rules_dir = args.rules_dir.resolve()
    json_path = (args.json_path or rules_dir / "RULES-MANIFEST.json").resolve()
    yaml_path = (args.yaml_path or rules_dir / "RULES-MANIFEST.yaml").resolve()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        json_data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"invalid JSON manifest: {exc}")
        json_data = {}
    try:
        yaml_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"invalid YAML manifest: {exc}")
        yaml_data = {}

    if json_data != yaml_data:
        errors.append("JSON and YAML manifests are not semantically identical")

    generator = load_generator(Path(__file__).resolve().parent)
    generated_utc = json_data.get("generated_utc", "") if isinstance(json_data, dict) else ""
    expected = generator.build_manifest(rules_dir, generated_utc=generated_utc)
    if isinstance(json_data, dict) and strip_timestamp(json_data) != strip_timestamp(expected):
        errors.append("manifest content does not match rules on disk; regenerate it")

    disk_files = {path.name for path in rules_dir.glob("*.mdc")}
    leaked = sorted(disk_files & LOCAL_ONLY_FILENAMES)
    if leaked:
        errors.append(f"repository-local rules remain in global governance: {', '.join(leaked)}")

    records = json_data.get("rules", []) if isinstance(json_data, dict) else []
    names = [record.get("file") for record in records if isinstance(record, dict)]
    if len(names) != len(set(names)):
        errors.append("duplicate rule filenames in manifest")

    for record in records:
        if not isinstance(record, dict):
            errors.append("non-object rule entry in manifest")
            continue
        if not record.get("has_yaml_frontmatter"):
            errors.append(f"missing valid YAML frontmatter: {record.get('file')}")
        if not record.get("description"):
            warnings.append(f"missing description: {record.get('file')}")
        if record.get("always_apply") is True and record.get("globs"):
            warnings.append(
                f"alwaysApply=true with globs may load globally instead of attaching narrowly: {record.get('file')}"
            )

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"RESULT: FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
        return 1
    print(f"RESULT: PASS ({len(records)} rules, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
