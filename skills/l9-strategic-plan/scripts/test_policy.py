import json
from validate_working_plan import check_policy,check_unchanged,verify_policy

def run():
    good={'graph.json':json.dumps({'edges':[{'source':'a','target':'b','relation':'requires'}],'priority':['a']}).encode(),'dashboard.json':json.dumps({'priority':['a']}).encode(),'protected.json':b'fixed'}
    rules={'authority_ref':'test:operator','assertions':[{'id':'right','kind':'edge_exists','file':'graph.json','source':'a','target':'b'},{'id':'reverse','kind':'edge_absent','file':'graph.json','source':'b','target':'a'},{'id':'sync','kind':'matches_file','file':'graph.json','pointer':'/priority','other_file':'dashboard.json','other_pointer':'/priority'}],'must_remain_unchanged':['protected.json'],'allowed_changed_paths':['graph.json','dashboard.json']}
    verify_policy(rules)
    assert len(check_policy(good,rules))==3
    bad=dict(good);bad['graph.json']=json.dumps({'edges':[{'source':'b','target':'a','relation':'requires'}],'priority':['a']}).encode()
    try:check_policy(bad,rules);raise AssertionError('reversed edge accepted')
    except ValueError as e:assert 'POLICY_ASSERTION_FAILED' in str(e)
    bad=dict(good);bad['dashboard.json']=json.dumps({'priority':['b']}).encode()
    try:check_policy(bad,rules);raise AssertionError('stale projection accepted')
    except ValueError as e:assert 'POLICY_ASSERTION_FAILED' in str(e)
    bad=dict(good);bad['protected.json']=b'changed'
    try:check_unchanged(good,bad,rules);raise AssertionError('protected file changed')
    except ValueError as e:assert 'PROTECTED_PATH_CHANGED' in str(e) or 'UNEXPECTED_CHANGED_PATH' in str(e)
    bad=dict(good);bad['new.json']=b'new'
    assert check_unchanged(good,bad,rules)==[]
    print('PASS 5 policy checks including negative controls')
if __name__=='__main__':run()
