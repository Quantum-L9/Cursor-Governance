#!/usr/bin/env python3
# Compiler self-host validation. Runs the compiler against its own pack.
import sys, os, json
from _common import PACK, emit
import static_validate, check_capability_closure, evaluate_activation
import normalize_skill_ir, render_target_profile, classify_skill_profile, scan_skill_topology

IR = os.path.join(str(PACK), 'tests', 'fixtures', 'self-ir.json')
REPO_FIXTURE = os.path.join(str(PACK), 'tests', 'fixtures', 'repo', 'skills')

def run():
    steps = []
    ir = normalize_skill_ir.normalize(json.load(open(IR, encoding='utf-8')))
    steps.append(('normalize_skill_ir.validate', not normalize_skill_ir.validate(ir)))
    steps.append(('normalize_skill_ir.round_trip', normalize_skill_ir.round_trip(ir)))
    sv = static_validate.main(['x', IR, str(PACK)])
    steps.append(('static_validate', sv == 0))
    cc = check_capability_closure.check(ir, str(PACK.parent.parent),
                                       live_skills={'l9-wire-skill-into-repo',
                                                    'l9-dag-authoring',
                                                    'l9-structured-reasoning'})
    steps.append(('capability_closure', cc['result'] in ('CLOSED', 'RUNTIME_BOUND'))
    ae = evaluate_activation.evaluate(ir, live_skills={'l9-wire-skill-into-repo',
                                                       'l9-dag-authoring',
                                                       'l9-structured-reasoning'})
    steps.append(('activation_eval', ae['status'] == 'PASS'))
    p = render_target_profile.render(ir, 'portable')
    l = render_target_profile.render(ir, 'l9')
    steps.append(('deterministic_render', p == render_target_profile.render(ir, 'portable')))
    steps.append(('profile_specific_validation', 'Canonical DAG' in l and 'Canonical DAG' not in p))
    gated = False
    try:
        render_target_profile.render(ir, 'cursor')
    except PermissionError:
        gated = True
    steps.append(('unverified_profile_is_gated', gated))
    prof = classify_skill_profile.classify('rebuild a compiler that renders skill artifacts')
    steps.append(('classification_compiler', prof['primary_family'] == 'compiler'))
    live = scan_skill_topology.enumerate_live_skills(REPO_FIXTURE) if os.path.isdir(REPO_FIXTURE) else {}
    d, ev, _, _ = scan_skill_topology.decide({'proposed_name': 'l9-skill-compiler',
                                              'existing_skill': 'l9-skill-compiler'}, live)
    steps.append(('topology_replace_existing', d == 'REPLACE_EXISTING'))
    return steps, cc, ae

def main(argv):
    steps, cc, ae = run()
    failed = [n for n, ok in steps if not ok]
    return emit({'stage': 'SELF_TEST', 'status': 'FAIL' if failed else 'PASS',
                 'checks': [{'id': n, 'status': 'pass' if ok else 'fail'} for n, ok in steps],
                 'failed': failed, 'capability_closure_result': cc['result'],
                 'activation_status': ae['status']}, 2 if failed else 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
