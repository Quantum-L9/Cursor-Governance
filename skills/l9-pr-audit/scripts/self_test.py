"""Deterministic regression tests for l9-pr-audit's evidence and Fable handoff gates."""
from __future__ import annotations
import copy
import json
import tempfile
from pathlib import Path
import build_audit_bundle as bab
A = 'a' * 40
B = 'b' * 40
C = 'c' * 40

def evidence(eid: str, etype: str, revision: str, fact: str, properties: list[str], findings: list[str] | None=None, **extra: object) -> dict[str, object]:
    item: dict[str, object] = {'evidence_id': eid, 'evidence_type': etype, 'epistemic_state': 'CONFIRMED', 'repository': 'Quantum-L9/example', 'revision': revision, 'path_or_check': 'synthetic', 'locator': f'fixture:{eid}', 'fact_proven': fact, 'properties_discriminated': properties, 'redaction_state': 'NOT_APPLICABLE', 'findings_using_this_evidence': findings or []}
    item.update(extra)
    return item

def base_audit() -> dict[str, object]:
    shared = [evidence('E-AUTH', 'SOURCE', A, 'canonical rule exists', ['authority_resolution']), evidence('E-GUARD', 'CONTRACT', A, 'repository mutation guard resolved', ['mutation_guard_resolution']), evidence('E-VCMD', 'CONTRACT', A, 'repository validation command is authoritative', ['validation_procedure']), evidence('E-CHECK', 'CONFIGURATION', B, 'required check identity resolved', ['required_check_identity']), evidence('E-REVIEW', 'REVIEW_THREAD', B, 'zero unresolved review threads observed', ['review_thread_coverage']), evidence('E-BYPASS', 'DIFF', B, 'diff inspected for weakening surfaces', ['anti_bypass_coverage'] + [f'anti_bypass:{kind}' for kind in sorted(bab.ANTI_BYPASS_KINDS)]), evidence('E-FIND', 'DIFF', B, 'src/core.py violates canonical rule', ['implementation_surface', 'behavior_mismatch'], ['F1']), evidence('E-TEST', 'TEST', B, 'targeted test fails before remediation', ['closure_property', 'mandatory_validation'], ['F1'], source_head_sha=B, tested_revision_sha=B, validation_result='FAIL', path_or_check='targeted-unit')]
    bypass_checks = [{'kind': kind, 'status': 'PASS', 'evidence_ids': ['E-BYPASS']} for kind in sorted(bab.ANTI_BYPASS_KINDS)]
    return {'schema_version': bab.SCHEMA_VERSION, 'audit_id': 'audit.synthetic.v1', 'generated_at': '2026-09-11T15:00:00Z', 'repository_binding': {'repository': 'Quantum-L9/example', 'default_branch': 'main', 'audited_default_branch_sha': A}, 'audit_coverage': {'status': 'COMPLETE', 'inspection_scope': ['PR #1 full diff', 'directly coupled rule and test surfaces'], 'excluded_or_inaccessible': [], 'applicable_domains': ['INTENT_SCOPE', 'OWNERSHIP_AUTHORITY', 'TESTING_VALIDATION', 'LEVERAGE_SIMPLICITY'], 'completed_domains': ['INTENT_SCOPE', 'OWNERSHIP_AUTHORITY', 'TESTING_VALIDATION', 'LEVERAGE_SIMPLICITY'], 'skipped_domains': []}, 'authority_resolution': {'status': 'RESOLVED', 'sources': [{'authority_id': 'A1', 'kind': 'REPOSITORY_LAW', 'source': 'CANONICAL_LAW.md', 'scope': 'src/core.py behavior and validation', 'precedence': 1, 'evidence_ids': ['E-AUTH', 'E-VCMD']}, {'authority_id': 'A-GUARD', 'kind': 'MUTATION_GUARD', 'source': 'ops/config/mutation-guard.json', 'scope': 'repository mutation admissibility', 'precedence': 2, 'evidence_ids': ['E-GUARD']}], 'conflicts': []}, 'pr_bindings': [{'pr_number': 1, 'url': 'https://github.com/Quantum-L9/example/pull/1', 'state': 'open', 'draft': False, 'base_branch': 'main', 'base_sha': A, 'head_branch': 'feature', 'head_sha': B, 'mergeability': 'MERGEABLE', 'required_check_resolution': {'status': 'RESOLVED', 'checks': ['ci'], 'evidence_ids': ['E-CHECK']}, 'review_thread_coverage': {'unresolved_discovered': 0, 'classified': 0, 'unresolved_remaining': 0, 'status': 'COMPLETE', 'evidence_ids': ['E-REVIEW']}}], 'executive_verdict': {'audit_status': 'SUCCEEDED', 'readiness_status': 'NOT_READY', 'convergence_status': 'CONVERGED', 'summary': 'One confirmed code defect blocks merge.', 'minimum_safe_next_action': {'action': 'Repair F1 within the strict write allowlist.', 'rationale': 'F1 is the only confirmed merge blocker.', 'expected_evidence': 'Targeted closure test passes on the resulting revision.'}}, 'per_pr_verdicts': [{'pr_number': 1, 'completeness': 'FAIL', 'correctness': 'FAIL', 'architecture_alignment': 'FAIL', 'validation_sufficiency': 'PASS', 'mandatory_validation_evidence_ids': ['E-TEST'], 'merge_readiness': 'NOT_READY', 'blocking_finding_ids': ['F1'], 'blocking_unknown_ids': []}], 'findings': [{'finding_id': 'F1', 'finding_class': 'CORRECTNESS', 'severity': 'High', 'confidence': 'Confirmed', 'affected_prs': [1], 'repository_revision': A, 'pr_head_bindings': [{'pr_number': 1, 'head_sha': B}], 'governing_authority': {'authority_id': 'A1', 'rule': 'core behavior must satisfy the canonical contract', 'source': {'path': 'CANONICAL_LAW.md'}, 'enforcement_refs': ['tests/test_core.py']}, 'ownership': {'semantic_owner': 'core', 'execution_owner': 'fable-remediator', 'mutation_guard': 'A-GUARD', 'remediation_owner_class': 'CODEBASE'}, 'evidence_ids': ['E-FIND', 'E-TEST'], 'observed_behavior': 'Current source violates the rule.', 'expected_behavior': 'Current source satisfies the rule.', 'proof_of_mismatch': 'Diff evidence plus targeted failing test proves the mismatch.', 'impact': 'Merge would ship incorrect behavior.', 'root_cause': 'The implementation takes the wrong branch.', 'root_cause_state': 'CONFIRMED', 'behavioral_closure_condition': 'The correct branch is selected for the governed input.', 'closing_validation': [{'property': 'closure_property', 'command_or_check': 'python -m pytest tests/test_core.py -q', 'required_result': 'PASS', 'execution_kind': 'COMMAND', 'authority_id': 'A1', 'evidence_ids': ['E-VCMD']}], 'merge_blocking': True}], 'shared_evidence_index': shared, 'remediation_surface_index': [{'finding_id': 'F1', 'authoritative_surfaces': ['CANONICAL_LAW.md'], 'implementation_surfaces': ['src/core.py'], 'coupled_surfaces': ['tests/test_core.py'], 'excluded_false_leads': [], 'surface_evidence': [{'path': 'src/core.py', 'role': 'IMPLEMENTATION', 'evidence_ids': ['E-FIND'], 'reason': 'Diff evidence locates the incorrect branch.'}]}], 'finding_dependency_graph': [{'finding_id': 'F1', 'depends_on_findings': [], 'shared_root_cause': None, 'affected_prs': [1], 'remediation_order_class': 'ROOT_CAUSE_FIRST'}], 'failed_check_evidence': [{'pr_number': 1, 'source_head_sha': B, 'tested_revision_sha': B, 'check': 'targeted-unit', 'workflow_job': None, 'failing_step': None, 'failure_class': 'CODEBASE', 'local_reproducibility': 'CONFIRMED', 'local_reproduction_command': 'python -m pytest tests/test_core.py -q', 'evidence_ids': ['E-TEST'], 'affected_finding_ids': ['F1']}], 'regression_proof': [{'finding_id': 'F1', 'existing_regression_test': 'tests/test_core.py::test_rule', 'missing_negative_boundary': None, 'reproduction_command': 'python -m pytest tests/test_core.py -q', 'pre_remediation_result': 'FAIL', 'expected_post_remediation_result': 'PASS', 'evidence_ids': ['E-TEST']}], 'preservation_obligations': [], 'anti_bypass_checks': [{'pr_number': 1, 'checks': bypass_checks}], 'cross_pr_evidence_pack': {'status': 'NOT_APPLICABLE', 'relationships': [], 'merge_order': []}, 'residual_unknowns': [], 'combined_merge_readiness': 'NOT_READY'}

def assert_has(errors: list[str], needle: str) -> None:
    if not any((needle in error for error in errors)):
        raise AssertionError(f'expected error containing {needle!r}; got {errors}')

def main() -> int:
    audit = base_audit()
    errors = bab.validate_audit(audit)
    if errors:
        raise AssertionError('positive fixture failed:\n' + '\n'.join(errors))
    handoff = bab.make_handoff(audit)
    unit = handoff['work_units'][0]
    assert unit['mutation_eligible'] is True
    assert unit['write_surfaces'] == ['src/core.py']
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        audit_path = td_path / 'audit.json'
        audit_path.write_text(json.dumps(audit), encoding='utf-8')
        zip_path = bab.build_bundle(audit_path, td_path / 'out')
        assert not bab.verify_zip(zip_path)
        with __import__('zipfile').ZipFile(zip_path) as zf:
            prompt = zf.read('FABLE_REMEDIATION.md').decode('utf-8')
            assert 'SCOPE_EXTENSION_REQUIRED' in prompt
            assert 'strict write allowlist' in prompt
            manifest = json.loads(zf.read('MANIFEST.json'))
            assert manifest['audit_schema_sha256'] == bab.sha256(bab.schema_path())
            assert manifest['canonical_audit_sha256'] == bab.sha256_bytes(zf.read('audit.json'))
            assert manifest['builder_sha256'] == bab.sha256(bab.builder_path())
        import zipfile
        extra_zip = td_path / 'extra-file.zip'
        with zipfile.ZipFile(zip_path, 'r') as source, zipfile.ZipFile(extra_zip, 'w', zipfile.ZIP_DEFLATED) as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
            target.writestr('UNDECLARED.txt', 'not part of the bundle contract')
        assert_has(bab.verify_zip(extra_zip), 'bundle file set mismatch')
        tampered_zip = td_path / 'tampered-audit.zip'
        with zipfile.ZipFile(zip_path, 'r') as source, zipfile.ZipFile(tampered_zip, 'w', zipfile.ZIP_DEFLATED) as target:
            for name in source.namelist():
                payload = source.read(name)
                if name == 'audit.json':
                    tampered = json.loads(payload)
                    tampered['executive_verdict']['summary'] = 'tampered but structurally valid'
                    payload = (json.dumps(tampered, indent=2, sort_keys=True) + '\n').encode()
                target.writestr(name, payload)
        assert_has(bab.verify_zip(tampered_zip), 'canonical_audit_sha256 mismatch')
        projection_zip = td_path / 'tampered-projection.zip'
        with zipfile.ZipFile(zip_path, 'r') as source:
            payloads = {name: source.read(name) for name in source.namelist()}
        payloads['FABLE_REMEDIATION.md'] += b'\nmanual drift\n'
        manifest = json.loads(payloads['MANIFEST.json'])
        manifest['files']['FABLE_REMEDIATION.md'] = {'sha256': bab.sha256_bytes(payloads['FABLE_REMEDIATION.md']), 'bytes': len(payloads['FABLE_REMEDIATION.md'])}
        payloads['MANIFEST.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
        with zipfile.ZipFile(projection_zip, 'w', zipfile.ZIP_DEFLATED) as target:
            for name, payload in payloads.items():
                target.writestr(name, payload)
        assert_has(bab.verify_zip(projection_zip), 'derived projection mismatch: FABLE_REMEDIATION.md')
    bad = copy.deepcopy(audit)
    bad['unexpected'] = True
    assert_has(bab.validate_audit(bad), 'Additional properties are not allowed')
    bad = copy.deepcopy(audit)
    bad['pr_bindings'][0]['required_check_resolution']['evidence_ids'] = []
    assert_has(bab.validate_audit(bad), 'required_check_resolution status RESOLVED requires CONFIRMED evidence')
    bad = copy.deepcopy(audit)
    bad['remediation_surface_index'][0]['surface_evidence'] = []
    assert_has(bab.validate_audit(bad), 'lacks IMPLEMENTATION surface_evidence')
    probable = copy.deepcopy(audit)
    probable['findings'][0]['confidence'] = 'Probable'
    probable['findings'][0]['root_cause_state'] = 'INFERENCE'
    unit = bab.make_handoff(probable)['work_units'][0]
    assert unit['mutation_eligible'] is False
    assert not unit['write_surfaces']
    assert 'confidence=Probable' in unit['mutation_block_reasons']
    secret = copy.deepcopy(audit)
    secret['findings'][0]['impact'] = 'api_key=abcdefghijklmnopqrstuvwx'
    assert_has(bab.validate_audit(secret), 'high-confidence secret material')
    bad = copy.deepcopy(audit)
    for item in bad['shared_evidence_index']:
        if item['evidence_id'] == 'E-FIND':
            item['properties_discriminated'] = ['behavior_mismatch']
    assert_has(bab.validate_audit(bad), 'lacks evidence that discriminates implementation_surface')
    bad = copy.deepcopy(audit)
    for item in bad['shared_evidence_index']:
        if item['evidence_id'] == 'E-VCMD':
            item['properties_discriminated'] = ['authority_resolution']
    assert_has(bab.validate_audit(bad), 'closing validation lacks validation_procedure provenance evidence')
    bad = copy.deepcopy(audit)
    for item in bad['shared_evidence_index']:
        if item['evidence_id'] == 'E-BYPASS':
            item['properties_discriminated'] = ['anti_bypass_coverage']
    assert_has(bab.validate_audit(bad), 'lacks claim-specific discriminating evidence')
    bad_guard = copy.deepcopy(audit)
    bad_guard['findings'][0]['ownership']['mutation_guard'] = 'UNKNOWN'
    assert_has(bab.validate_audit(bad_guard), 'mutation_guard must be NOT_APPLICABLE or a known authority_id')
    unit = bab.make_handoff(bad_guard)['work_units'][0]
    assert unit['mutation_eligible'] is False
    assert 'mutation_guard_unresolved' in unit['mutation_block_reasons']
    bad = copy.deepcopy(audit)
    bad['audit_coverage']['excluded_or_inaccessible'] = [{'surface': 'protected/runtime', 'reason': 'unavailable', 'impact': 'BLOCKS_READINESS'}]
    assert_has(bab.validate_audit(bad), 'COMPLETE cannot contain blocking exclusions')
    bad = copy.deepcopy(audit)
    bad['authority_resolution']['conflicts'] = [{'description': 'two owners conflict', 'authority_ids': ['A1', 'A-GUARD'], 'status': 'BLOCKING'}]
    assert_has(bab.validate_audit(bad), 'RESOLVED cannot retain UNKNOWN/BLOCKING conflicts')
    bad = copy.deepcopy(audit)
    bad['residual_unknowns'] = [{'unknown_id': 'U1', 'description': 'consumer behavior unavailable', 'affected_prs': [1], 'affected_conclusion': 'cross-boundary correctness', 'blocks_readiness': False, 'blocks_convergence': True, 'evidence_needed': 'consumer contract', 'owner_class': 'HUMAN'}]
    assert_has(bab.validate_audit(bad), 'CONVERGED cannot retain convergence-blocking residual Unknowns')
    ready = copy.deepcopy(audit)
    ready['findings'][0]['merge_blocking'] = False
    ready['per_pr_verdicts'][0]['blocking_finding_ids'] = []
    ready['per_pr_verdicts'][0]['merge_readiness'] = 'READY'
    ready['combined_merge_readiness'] = 'READY'
    ready['executive_verdict']['readiness_status'] = 'READY'
    ready['shared_evidence_index'].append(evidence('E-CI', 'CI', B, 'required ci check passed', ['mandatory_validation', 'required_check_result'], source_head_sha=B, tested_revision_sha=C, validation_result='PASS', path_or_check='ci'))
    ready['per_pr_verdicts'][0]['mandatory_validation_evidence_ids'] = ['E-CI']
    if bab.validate_audit(ready):
        raise AssertionError('ready fixture should validate:\n' + '\n'.join(bab.validate_audit(ready)))
    bad = copy.deepcopy(ready)
    bad['pr_bindings'][0]['draft'] = True
    assert_has(bab.validate_audit(bad), 'while draft=true')
    bad = copy.deepcopy(ready)
    bad['pr_bindings'][0]['mergeability'] = 'UNKNOWN'
    assert_has(bab.validate_audit(bad), 'unless mergeability is MERGEABLE')
    bad = copy.deepcopy(ready)
    for item in bad['shared_evidence_index']:
        if item['evidence_id'] == 'E-CI':
            item['validation_result'] = 'FAIL'
    assert_has(bab.validate_audit(bad), "required check 'ci' lacks CONFIRMED PASS evidence")
    bad = copy.deepcopy(ready)
    bad['pr_bindings'][0]['review_thread_coverage']['unresolved_remaining'] = 1
    assert_has(bab.validate_audit(bad), 'unresolved review threads remaining')
    secret = copy.deepcopy(audit)
    secret['findings'][0]['impact'] = 'REDACTED note; api_key=abcdefghijklmnopqrstuvwx'
    assert_has(bab.validate_audit(secret), 'high-confidence secret material')
    cycle = copy.deepcopy(audit)
    f2 = copy.deepcopy(cycle['findings'][0])
    f2['finding_id'] = 'F2'
    f2['evidence_ids'] = ['E-FIND2']
    cycle['findings'].append(f2)
    cycle['shared_evidence_index'].append(evidence('E-FIND2', 'DIFF', B, 'second coupled defect', ['implementation_surface'], ['F2']))
    cycle['remediation_surface_index'].append({'finding_id': 'F2', 'authoritative_surfaces': ['CANONICAL_LAW.md'], 'implementation_surfaces': ['src/other.py'], 'coupled_surfaces': [], 'excluded_false_leads': [], 'surface_evidence': [{'path': 'src/other.py', 'role': 'IMPLEMENTATION', 'evidence_ids': ['E-FIND2'], 'reason': 'Synthetic confirmed location.'}]})
    cycle['finding_dependency_graph'] = [{'finding_id': 'F1', 'depends_on_findings': ['F2'], 'shared_root_cause': 'R1', 'affected_prs': [1], 'remediation_order_class': 'DEPENDENT'}, {'finding_id': 'F2', 'depends_on_findings': ['F1'], 'shared_root_cause': 'R1', 'affected_prs': [1], 'remediation_order_class': 'DEPENDENT'}]
    cycle['per_pr_verdicts'][0]['blocking_finding_ids'] = ['F1', 'F2']
    cycle['executive_verdict']['audit_status'] = 'PARTIALLY_SUCCEEDED'
    cycle['executive_verdict']['convergence_status'] = 'NOT_CONVERGED'
    errors = bab.validate_audit(cycle)
    if errors:
        raise AssertionError('cycle fixture should be representable as non-converged:\n' + '\n'.join(errors))
    units = bab.make_handoff(cycle)['work_units']
    assert all((not unit['mutation_eligible'] for unit in units))
    assert set(bab.make_handoff(cycle)['dependency_blocked_findings']) == {'F1', 'F2'}
    print('PASS: l9-pr-audit self-test passed')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
