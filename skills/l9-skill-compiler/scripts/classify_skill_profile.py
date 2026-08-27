#!/usr/bin/env python3
# CLASSIFY_SKILL_PROFILE: deterministic rules first; bounded LLM only on ambiguity.
import sys, re
from _common import policy, emit, fail, load_json

RULES = [
    ('compiler',     r'compil|render|transform|codegen'),
    ('orchestrator', r'orchestrat|coordinate coordinat|\bdag\b'),
    ('lifecycle',    r'lifecycle|durable state|resume|checkpoint'),
    ('adapter',      r'adapter|bind external|third-party|connector'),
    ('operator',     r'mutate|deploy|remediat|migrat'),
    ('diagnostic',   r'diagnos|audit|inspect|triage'),
    ('advisory',     r'advis|guidance|recommend|doctrine|methodolog'),
]

def classify(objective):
    text = (objective or '').lower()
    hits = [(fam, rid) for fam, rid in RULES if re.search(rid, text)]
    fams = policy('skill-families.yaml')['families']
    if len(hits) == 1:
        fam = hits[0][0]
        return {'primary_family': fam, 'traits': fams[fam]['default_traits'],
                'evidence': ['deterministic_rule_matched:' + hits[0][1]],
                'decided_by': 'deterministic_rule', 'rule_id': hits[0][1]}
    reason = 'no_deterministic_rule_matched' if not hits else \
        'ambiguous_multi_family_match:' + ','.join(f for f, _ in hits)
    return {'primary_family': None, 'traits': None, 'evidence': [reason],
            'decided_by': 'bounded_llm', 'rule_id': None}

def apply_trait_implications(profile):
    reqs = []
    if not profile.get('traits'):
        return reqs
    for rule in policy('skill-families.yaml').get('trait_implications', []):
        if all(profile['traits'].get(k) == v for k, v in rule.get('if', {}).items()):
            reqs += rule.get('then_required', [])
    return sorted(set(reqs))

def main(argv):
    if len(argv) < 2:
        return fail('usage: classify_skill_profile.py <compile-request.json>')
    req = load_json(argv[1])
    prof = classify(req.get('subject', {}).get('stated_objective', ''))
    return emit({'stage': 'CLASSIFY_SKILL_PROFILE', 'profile': prof,
                 'derived_requirements': apply_trait_implications(prof),
                 'status': 'ESCALATE_TO_BOUNDED_LLM' if prof['primary_family'] is None else 'PASS'}, 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
