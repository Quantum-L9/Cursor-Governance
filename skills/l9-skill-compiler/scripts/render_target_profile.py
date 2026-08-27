#!/usr/bin/env python3
# RENDER_TARGET_PROFILE: deterministic render from validated IR only.
import sys, os
from _common import policy, emit, fail, load_json

def _front(ir, keys):
    auth = ir.get('authority', {})
    src = {'name': ir['identity']['name'], 'version': ir['identity']['version'],
           'updated': ir['identity'].get('updated', ''), 'description': ir['objective'],
           'role': auth.get('role', ir['primary_family'] + '_skill'),
           'tags': '[' + ', '.join(auth.get('tags', ['l9'])) + ']',
           'owner': auth.get('owner', 'unassigned')}
    lines = ['---'] + [k + ': ' + str(src[k]) for k in keys if src.get(k)] + ['---']
    return '\n'.join(lines)

def render(ir, profile_name):
    profiles = policy('target-profiles.yaml')['profiles']
    if profile_name not in profiles:
        raise KeyError('unknown profile ' + profile_name)
    spec = profiles[profile_name]
    if spec.get('status') == 'unverified':
        raise PermissionError('profile ' + profile_name + ' gated: ' + str(spec.get('gate')))
    out = [_front(ir, spec['frontmatter_required']), '',
           '# ' + ir['identity']['name'] + ' v' + ir['identity']['version'], '',
           '## Activate when', '']
    out += ['- ' + a for a in ir['activation']]
    out += ['', '## Do not activate', ''] + ['- ' + a for a in ir['non_activation']]
    out += ['', '## Invariants', ''] + ['- ' + i for i in ir['invariants']]
    if profile_name == 'l9':
        auth = ir.get('authority', {})
        out += ['', '## Runtime', '',
                'Canonical DAG: ' + str(auth.get('canonical_dag')),
                'Registry id: ' + str(auth.get('dag_registry_id'))]
    return '\n'.join(out) + '\n'

def main(argv):
    if len(argv) < 3:
        return fail('usage: render_target_profile.py <skill-ir.json> <profile> [outdir]')
    ir = load_json(argv[1])
    try:
        text = render(ir, argv[2])
    except (KeyError, PermissionError) as exc:
        return emit({'stage': 'RENDER_TARGET_PROFILE', 'status': 'FAIL', 'error': str(exc)}, 2)
    if len(argv) > 3:
        os.makedirs(argv[3], exist_ok=True)
        with open(os.path.join(argv[3], 'SKILL.md'), 'w', encoding='utf-8') as fh:
            fh.write(text)
    return emit({'stage': 'RENDER_TARGET_PROFILE', 'status': 'PASS',
                 'profile': argv[2], 'bytes': len(text)}, 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
