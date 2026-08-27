#!/usr/bin/env python3
# NORMALIZE_SKILL_IR: deterministic. Source compiles into IR before any render.
import sys, json, datetime
from _common import contract, emit, fail, load_json
from bind_inputs import structural_validate

LIST_KEYS = ['activation','non_activation','inputs','outputs','invariants','capabilities',
             'resources','dependencies','risks','evidence','unknowns','target_profiles',
             'activation_evals','behavior_evals']

def normalize(draft):
    ir = json.loads(json.dumps(draft))
    ir.setdefault('identity', {})
    ir['identity'].setdefault('updated', datetime.date.today().isoformat())
    ir.setdefault('objective', '')
    ir.setdefault('authority', {})
    ir.setdefault('workflow', {'entrypoint': None, 'nodes': []})
    for k in LIST_KEYS:
        ir.setdefault(k, [])
    ir['capabilities'] = sorted(ir['capabilities'], key=lambda c: c.get('id', ''))
    ir['workflow']['nodes'] = sorted(ir['workflow'].get('nodes', []), key=lambda n: n.get('id', ''))
    return ir

def validate(ir):
    return structural_validate(ir, contract('skill-ir.schema.json'))

def round_trip(ir):
    return normalize(json.loads(json.dumps(normalize(ir)))) == normalize(ir)

def main(argv):
    if len(argv) < 2:
        return fail('usage: normalize_skill_ir.py <ir-draft.json> [out.json]')
    ir = normalize(load_json(argv[1]))
    errs = validate(ir)
    if errs:
        return emit({'stage': 'NORMALIZE_SKILL_IR', 'status': 'FAIL', 'errors': errs}, 2)
    if len(argv) > 2:
        with open(argv[2], 'w', encoding='utf-8') as fh:
            json.dump(ir, fh, indent=2, sort_keys=True)
    return emit({'stage': 'NORMALIZE_SKILL_IR', 'status': 'PASS',
                 'round_trip_stable': round_trip(ir),
                 'capability_count': len(ir['capabilities']),
                 'node_count': len(ir['workflow']['nodes'])}, 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
