import json, os, sys, copy, pytest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
import check_capability_closure as cc

LIVE = {'l9-wire-skill-into-repo', 'l9-dag-authoring', 'l9-structured-reasoning'}
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))

def ir():
    with open(os.path.join(HERE, 'fixtures', 'self-ir.json'), encoding='utf-8') as fh:
        return json.load(fh)

def test_self_pack_is_closed():
    assert cc.check(ir(), REPO, live_skills=LIVE)['result'] in ('CLOSED', 'RUNTIME_BOUND')

def test_missing_executable_fails():
    d = ir()
    d['capabilities'][0]['binding']['target'] = 'skills/l9-skill-compiler/scripts/nope.py'
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'FAIL'

def test_placeholder_success_condition_fails():
    d = ir()
    d['capabilities'][0]['binding']['success_condition'] = 'TODO'
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'FAIL'

def test_dead_delegated_skill_fails():
    d = ir()
    for c in d['capabilities']:
        if c['binding']['kind'] == 'DELEGATED_SKILL':
            c['binding']['target'] = 'l9-does-not-exist'
            break
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'FAIL'

def test_cycle_detected():
    d = ir()
    by = {c['id']: c for c in d['capabilities']}
    by['bind_inputs']['binding']['depends_on'] = ['package']
    res = cc.check(d, REPO, live_skills=LIVE)
    assert res['result'] == 'FAIL' and res['cycles']

def test_unreachable_capability_fails():
    d = ir()
    for n in d['workflow']['nodes']:
        if n['id'] == 'PACKAGE':
            n['capabilities'] = []
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'FAIL'

def test_bounded_unknown_blocks():
    d = ir()
    d['capabilities'].append({'id': 'future_thing', 'required': True,
        'binding': {'kind': 'UNKNOWN', 'bounded_unknown': True}})
    d['workflow']['nodes'][0]['capabilities'] = ['future_thing']
    for n in d['workflow']['nodes']:
        if n['id'] == 'COMPILE_REQUEST':
            n['capabilities'] = ['future_thing']
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'BLOCKED'

def test_unbounded_unknown_fails():
    d = ir()
    d['capabilities'].append({'id': 'sloppy', 'required': True, 'binding': {'kind': 'UNKNOWN'}})
    for n in d['workflow']['nodes']:
        if n['id'] == 'COMPILE_REQUEST':
            n['capabilities'] = ['sloppy']
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'FAIL'

def test_external_capability_requires_probe():
    d = ir()
    d['capabilities'].append({'id': 'ext', 'required': True,
        'binding': {'kind': 'EXTERNAL_CAPABILITY', 'target': 'svc'}})
    for n in d['workflow']['nodes']:
        if n['id'] == 'COMPILE_REQUEST':
            n['capabilities'] = ['ext']
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'FAIL'

def test_external_capability_with_probe_is_runtime_bound():
    d = ir()
    d['capabilities'].append({'id': 'ext', 'required': True,
        'binding': {'kind': 'EXTERNAL_CAPABILITY', 'target': 'svc',
                    'probe': 'GET /health', 'failure_behavior': 'stop and report'}})
    for n in d['workflow']['nodes']:
        if n['id'] == 'COMPILE_REQUEST':
            n['capabilities'] = ['ext']
    assert cc.check(d, REPO, live_skills=LIVE)['result'] == 'RUNTIME_BOUND'
