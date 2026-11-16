import hashlib
from evaluate_behavior import evaluate
CASES=[{'id':'X'}]
def run():
    assert evaluate(CASES,[])['cases'][0]['status']=='NOT_RUN'
    r={'case_id':'X','actual_response':'text','run_context':'isolated session','observed_positive':True,'observed_forbidden':False,'reviewer_verdict':'PASS'}
    assert evaluate(CASES,[r])['cases'][0]['status']=='REVIEW_REQUIRED'
    r.update(independent_reviewer='reviewer-1',evidence_refs=['response:1'],run_id='run1',skill_sha256='a'*64,source_snapshot_refs=['snapshot:1'],reviewer_identity='reviewer',executor_identity='executor',reviewer_evidence_refs=['review:1'],actual_response_sha256=hashlib.sha256(b'text').hexdigest(),artifact_sha256_by_path={})
    assert evaluate(CASES,[r])['behavioral_acceptance']=='RECORDED_PASS_NOT_INDEPENDENTLY_AUTHENTICATED'
    r['actual_response_sha256']='b'*64
    assert evaluate(CASES,[r])['cases'][0]['status']=='INCOMPLETE'
    r['actual_response_sha256']=hashlib.sha256(b'text').hexdigest();r['observed_forbidden']=True
    assert evaluate(CASES,[r])['cases'][0]['status']=='FAIL'
    try:evaluate(CASES,[r,r]);raise AssertionError('duplicate accepted')
    except ValueError:pass
    print('PASS 6 evaluator unit checks; no independent model behavior tested')
if __name__=='__main__':run()
