#!/usr/bin/env python3
import pathlib, yaml, sys
root=pathlib.Path(__file__).resolve().parents[1]
errors=[]
for p in root.rglob("*.yaml"):
    try: yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e: errors.append(f"{p}: {e}")
for r in ["00_manifest/MANIFEST.yaml","01_strategy/session_hydration_strategy.canonical_spec.v1.yaml","02_runtime_contracts/mobile_hydration_system_prompt.md","04_playbook/PLAYBOOK.md","05_skill/l9-mobile-session-hydrator/SKILL.md"]:
    if not (root/r).exists(): errors.append(f"missing {r}")
if errors:
    print("\n".join(errors)); sys.exit(1)
print("validation_passed")
