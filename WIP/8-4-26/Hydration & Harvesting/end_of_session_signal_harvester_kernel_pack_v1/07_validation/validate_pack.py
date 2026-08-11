#!/usr/bin/env python3
import pathlib, sys, yaml
root = pathlib.Path(__file__).resolve().parents[1]
errors = []
for path in root.rglob("*.yaml"):
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: {exc}")
required = [
    "00_manifest/MANIFEST.yaml",
    "01_spec/end_of_session_signal_harvester.canonical_spec.v1.yaml",
    "03_signal_schemas/session_signal_packet.v1.schema.yaml",
    "05_rules/promotion_rules.v1.yaml",
    "05_rules/fuel_scoring_model.v1.yaml",
]
for rel in required:
    if not (root / rel).exists():
        errors.append(f"missing {rel}")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print("validation_passed")
