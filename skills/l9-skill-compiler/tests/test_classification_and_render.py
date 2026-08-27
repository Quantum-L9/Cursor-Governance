import json, os, sys, pytest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
import classify_skill_profile as cls
import render_target_profile as rtp
import normalize_skill_ir as nsi

def ir():
    with open(os.path.join(HERE, 'fixtures', 'self-ir.json'), encoding='utf-8') as fh:
        return json.load(fh)

def test_compiler_family_is_deterministic():
    p = cls.classify('rebuild a compiler that renders skill artifacts')
    assert p['primary_family'] == 'compiler' and p['decided_by'] == 'deterministic_rule'

def test_diagnostic_family_is_deterministic():
    p = cls.classify('audit and inspect the repository for drift')
    assert p['primary_family'] == 'diagnostic'

def test_ambiguity_escalates_to_bounded_llm():
    p = cls.classify('audit and then deploy and also compile things')
    assert p['primary_family'] is None and p['decided_by'] == 'bounded_llm'

def test_no_match_escalates():
    p = cls.classify('xyzzy plugh frobnicate')
    assert p['decided_by'] == 'bounded_llm'

def test_dag_trait_requires_registration():
    p = cls.classify('rebuild a compiler that renders skill artifacts')
    assert 'canonical_dag_registration' in cls.apply_trait_implications(p)

def test_render_is_deterministic():
    d = nsi.normalize(ir())
    assert rtp.render(d, 'portable') == rtp.render(d, 'portable')

def test_l9_profile_carries_dag_metadata_portable_does_not():
    d = nsi.normalize(ir())
    assert 'Canonical DAG' in rtp.render(d, 'l9')
    assert 'Canonical DAG' not in rtp.render(d, 'portable')

def test_unverified_profiles_are_gated():
    d = nsi.normalize(ir())
    for prof in ('cursor', 'claude_code', 'openai'):
        with pytest.raises(PermissionError):
            rtp.render(d, prof)

def test_ir_round_trips_and_validates():
    d = nsi.normalize(ir())
    assert nsi.validate(d) == []
    assert nsi.round_trip(d)
