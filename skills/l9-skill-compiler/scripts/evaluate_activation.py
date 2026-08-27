#!/usr/bin/env python3
# ACTIVATION_EVAL: deterministic fixture execution against the declared trigger surface.
import sys, re
from _common import emit, fail, load_json

def _hit(prompt, terms):
    return any(re.search(re.escape(t), prompt, re.I) for t in terms)

def evaluate(ir, live_skills=None):
    auth = ir.get('authority', {})
    pos = auth.get('activation_triggers', [])
    neg = auth.get('non_activation_triggers', [])
    results = []
    for fx in ir.get('activation_evals', []):
        p = fx['prompt']
        fired = _hit(p, pos) and not _hit(p, neg)
        if fx['expect'] == 'activate':
            ok = fired
        elif fx['expect'] == 'no_activate':
            ok = not fired
        else:
            ok = (not fired) and bool(fx.get('route_to'))
            if ok and live_skills is not None and fx['route_to'] not in live_skills:
                ok = False
        results.append({'class': fx['class'], 'prompt': p, 'expect': fx['expect'],
                        'route_to': fx.get('route_to'), 'fired': fired,
                        'deterministic': True, 'status': 'pass' if ok else 'fail'})
    classes = {r['class'] for r in results}
    gaps = [c for c in ('positive', 'negative', 'sibling_collision') if c not in classes]
    failed = [r for r in results if r['status'] == 'fail']
    return {'stage': 'ACTIVATION_EVAL', 'status': 'FAIL' if (failed or gaps) else 'PASS',
            'results': results, 'missing_classes': gaps, 'failed_count': len(failed)}

def main(argv):
    if len(argv) < 2:
        return fail('usage: evaluate_activation.py <skill-ir.json>')
    res = evaluate(load_json(argv[1]))
    return emit(res, 2 if res['status'] == 'FAIL' else 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
