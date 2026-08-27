import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
import evaluate_activation as ea
import bind_inputs as bi

LIVE = {'l9-wire-skill-into-repo', 'l9-dag-authoring', 'l9-structured-reasoning'}

def load(name):
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as fh:
        return json.load(fh)

def test_all_activation_fixtures_pass():
    res = ea.evaluate(load('self-ir.json'), live_skills=LIVE)
    assert res['status'] == 'PASS', res['results']

def test_required_fixture_classes_present():
    res = ea.evaluate(load('self-ir.json'), live_skills=LIVE)
    assert res['missing_classes'] == []

def test_sibling_collision_routes_elsewhere():
    res = ea.evaluate(load('self-ir.json'), live_skills=LIVE)
    coll = [r for r in res['results'] if r['class'] == 'sibling_collision']
    assert coll and all(r['status'] == 'pass' and not r['fired'] for r in coll)

def test_missing_class_is_reported():
    d = load('self-ir.json')
    d['activation_evals'] = [e for e in d['activation_evals'] if e['class'] != 'sibling_collision']
    res = ea.evaluate(d, live_skills=LIVE)
    assert 'sibling_collision' in res['missing_classes'] and res['status'] == 'FAIL'

def test_valid_compile_request_binds():
    assert bi.bind(load('compile-request.valid.json')) == []

def test_invalid_compile_request_is_rejected():
    errs = bi.bind(load('compile-request.invalid.json'))
    assert errs and any('portable' in e for e in errs)
