#!/usr/bin/env python3
# SCAN_SKILL_TOPOLOGY: deterministic. Creation is never the default outcome.
import sys, os, re
from _common import REPO, emit, fail, load_json

def parse_skill_metadata(skill_md):
    meta, lines, inside = {}, [], False
    with open(skill_md, 'r', encoding='utf-8') as fh:
        for line in fh:
            if line.strip() == '---':
                if inside:
                    break
                inside = True
                continue
            if inside:
                lines.append(line.rstrip('\n'))
    key = None
    for line in lines:
        m = re.match(r'^([a-z_]+):\s*(.*)$', line)
        if m:
            key = m.group(1)
            meta[key] = m.group(2).strip()
        elif key and line.startswith(' '):
            meta[key] = (meta.get(key, '') + ' ' + line.strip()).strip()
    return meta

def enumerate_live_skills(skills_dir=None):
    root = skills_dir or os.path.join(str(REPO), 'skills')
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if name.startswith('_') or name.startswith('.'):
            continue
        md = os.path.join(root, name, 'SKILL.md')
        if os.path.isfile(md):
            out[name] = parse_skill_metadata(md)
    return out

def tokens(text):
    return set(re.findall(r'[a-z0-9]+', (text or '').lower()))

def candidates(subject, live):
    want = tokens(subject.get('proposed_name', '')) | tokens(subject.get('domain', '')) \
        | tokens(subject.get('stated_objective', ''))
    scored = []
    for name, meta in live.items():
        trig = tokens(meta.get('description', ''))
        cap = tokens(meta.get('role', '')) | tokens(name)
        t_ov, c_ov = len(want & trig), len(want & cap)
        if t_ov or c_ov:
            scored.append({'skill': name, 'trigger_overlap': t_ov,
                           'capability_overlap': c_ov, 'specificity': len(cap)})
    scored.sort(key=lambda r: (-r['capability_overlap'], -r['specificity'], -r['trigger_overlap']))
    return scored

def decide(subject, live):
    existing = subject.get('existing_skill')
    cands = candidates(subject, live)
    ev = ['live_skills_enumerated=' + str(len(live))]
    if existing and existing in live:
        ev.append('existing_skill_present=' + existing)
        return 'REPLACE_EXISTING', ev, cands, 'deterministic_rule'
    if cands and cands[0]['capability_overlap'] >= 2:
        ev.append('nearest_owner=' + cands[0]['skill'] + ' capability_overlap=' +
                  str(cands[0]['capability_overlap']))
        return 'EXTEND_EXISTING', ev, cands, 'deterministic_rule'
    if len(cands) >= 3:
        ev.append('multiple_partial_owners=' + ','.join(c['skill'] for c in cands[:3]))
        return 'ESCALATE_TO_BOUNDED_LLM', ev, cands, 'bounded_llm'
    if cands and cands[0]['trigger_overlap'] and not cands[0]['capability_overlap']:
        ev.append('trigger_overlap_only=' + cands[0]['skill'])
        return 'CREATE_NEW', ev, cands, 'deterministic_rule'
    if not cands:
        ev.append('no_ownership_candidates')
        return 'CREATE_NEW', ev, cands, 'deterministic_rule'
    ev.append('weak_overlap_nearest=' + cands[0]['skill'])
    return 'ESCALATE_TO_BOUNDED_LLM', ev, cands, 'bounded_llm'

def main(argv):
    if len(argv) < 2:
        return fail('usage: scan_skill_topology.py <compile-request.json> [skills_dir]')
    req = load_json(argv[1])
    live = enumerate_live_skills(argv[2] if len(argv) > 2 else None)
    d, ev, cands, by = decide(req.get('subject', {}), live)
    return emit({'stage': 'SCAN_SKILL_TOPOLOGY', 'decision': d, 'decided_by': by,
                 'evidence': ev, 'candidates': cands[:10]}, 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
