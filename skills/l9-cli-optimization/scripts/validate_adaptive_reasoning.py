#!/usr/bin/env python3
"""Validate adaptive routing, evidence ledger, schemas, and pack integration."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from route_optimize import route
from validate_decision_ledger import validate_decision_contract

ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    errors=[]
    required=[
        'references/adaptive-optimize-router.yaml',
        'references/evidence-decision-ledger-contract.yaml',
        'references/adaptive-convergence.md',
        'scripts/route_optimize.py',
        'scripts/validate_decision_ledger.py',
        'schemas/pack-spec.schema.json',
        'schemas/pack-manifest.schema.json',
        'assets/adaptive-route-cases.json',
    ]
    for rel in required:
        if not (ROOT/rel).is_file(): errors.append(f'missing {rel}')
    skill=(ROOT/'SKILL.md').read_text(encoding='utf-8')
    for snippet in ('Adaptive Execution Router','Evidence and Decision Ledger','proof obligation','DECISION_LEDGER.json','EXECUTION_ROUTE.json','A fourth cycle is prohibited'):
        if snippet.lower() not in skill.lower(): errors.append(f'SKILL.md missing adaptive doctrine: {snippet}')
    cases=json.loads((ROOT/'assets'/'adaptive-route-cases.json').read_text(encoding='utf-8'))
    for case in cases:
        if not isinstance(case, dict) or 'input' not in case or 'expect' not in case or 'name' not in case:
            errors.append(f'malformed route case: {case!r}'); continue
        try: result=route(case['input'])
        except Exception as exc:
            errors.append(f"route case {case['name']} raised: {exc}")
            continue
        expect=case['expect']
        for key in ('reasoning_depth','initial_action','write_action_allowed'):
            if result.get(key)!=expect.get(key): errors.append(f"route case {case['name']} {key}: {result.get(key)} != {expect.get(key)}")
        proofs={item['id'] for item in result['proof_obligations']}
        for proof in expect.get('proofs', []):
            if proof not in proofs: errors.append(f"route case {case['name']} missing {proof}")
        for key in ('docs_code_divergence','latent_capability','output_mode'):
            if key not in result: errors.append(f"route case {case['name']} dropped classification {key}")
    example=json.loads((ROOT/'assets'/'pack-spec.example.json').read_text(encoding='utf-8'))
    errors.extend(f'example: {item}' for item in validate_decision_contract(example))
    schema=json.loads((ROOT/'schemas'/'pack-spec.schema.json').read_text(encoding='utf-8'))
    for field in ('execution_route','decision_ledger'):
        if field not in schema.get('required',[]): errors.append(f'pack schema does not require {field}')
    manifest=json.loads((ROOT/'schemas'/'pack-manifest.schema.json').read_text(encoding='utf-8'))
    for field in ('reasoning_depth','initial_action','final_action','proof_obligation_count','satisfied_proof_obligation_count','unresolved_material_unknowns','decision_convergence_status'):
        if field not in manifest.get('required',[]): errors.append(f'manifest schema does not require {field}')
    builder=(ROOT/'scripts'/'build_commit_pack.py').read_text(encoding='utf-8')
    validator=(ROOT/'scripts'/'validate_commit_pack.py').read_text(encoding='utf-8')
    for snippet in ('EXECUTION_ROUTE.json','DECISION_LEDGER.json','DECISION_RECORD.md','validate_decision_contract'):
        if snippet not in builder or snippet not in validator: errors.append(f'builder/validator missing {snippet}')
    if errors:
        for error in errors: print(f'FAIL: {error}',file=sys.stderr)
        return 1
    print(f'PASS: adaptive reasoning integration and {len(cases)} route cases are valid')
    return 0

if __name__=='__main__': raise SystemExit(main())
