#!/usr/bin/env python3
# STATIC_VALIDATE: structural, partition, graph, eval-coverage and reference checks.
import sys, os, re
from _common import PACK, contract, policy, emit, fail, load_json
from bind_inputs import structural_validate

def check_partition(ir):
    pol = policy('runtime-routing.yaml')
    det, llm = set(pol['deterministic_code']), set(pol['bounded_llm'])
    errs = []
    for n in ir.get('workflow', {}).get('nodes', []):
        impl = n.get('impl') or ''
        if n['kind'] == 'bounded_llm' and impl in det:
            errs.append('node ' + n['id'] + ': deterministic work routed to an LLM node')
        if n['kind'] == 'deterministic' and impl in llm:
            errs.append('node ' + n['id'] + ': semantic work routed to a deterministic node')
        if n['kind'] == 'deterministic' and not impl:
            errs.append('node ' + n['id'] + ': deterministic node has no impl')
    return errs

def check_graph(ir):
    nodes = {n['id']: n for n in ir.get('workflow', {}).get('nodes', [])}
    errs = []
    if ir.get('workflow', {}).get('entrypoint') not in nodes:
        errs.append('workflow.entrypoint does not resolve to a node')
    for n in nodes.values():
        for nx in n.get('next', []):
            if nx not in nodes:
                errs.append('node ' + n['id'] + ': dangling next -> ' + nx)
    if not any(n['kind'] == 'terminal' for n in nodes.values()):
        errs.append('workflow has no terminal node')
    return errs

def check_evals(ir):
    errs = []
    classes = {e['class'] for e in ir.get('activation_evals', [])}
    for req in ('positive', 'negative', 'sibling_collision'):
        if req not in classes:
            errs.append('activation_evals: missing required class ' + req)
    fam = ir.get('primary_family')
    required = {e['id'] for e in policy('behavior-evals.yaml').get(fam, [])}
    have = {e['id'] for e in ir.get('behavior_evals', [])}
    for miss in sorted(required - have):
        errs.append('behavior_evals: missing family-required eval ' + miss)
    return errs

def check_pack_files(pack=None):
    pack = pack or str(PACK)
    errs = []
    cdir = os.path.join(pack, 'contracts')
    for fn in sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []:
        if fn.endswith('.json'):
            try:
                load_json(os.path.join(cdir, fn))
            except Exception as exc:
                errs.append('contracts/' + fn + ': parse error: ' + str(exc))
    pdir = os.path.join(pack, 'policies')
    import yaml
    for fn in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if fn.endswith('.yaml'):
            try:
                with open(os.path.join(pdir, fn), encoding='utf-8') as fh:
                    yaml.safe_load(fh)
            except Exception as exc:
                errs.append('policies/' + fn + ': parse error: ' + str(exc))
    sdir = os.path.join(pack, 'scripts')
    for fn in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        if fn.endswith('.py'):
            src = open(os.path.join(sdir, fn), encoding='utf-8').read()
            try:
                compile(src, fn, 'exec')
            except SyntaxError as exc:
                errs.append('scripts/' + fn + ': syntax error: ' + str(exc))
    md = os.path.join(pack, 'SKILL.md')
    if os.path.isfile(md):
        text = open(md, encoding='utf-8').read()
        if re.search(r'zero[-_ ]?stub', text, re.I):
            errs.append('SKILL.md: retired term zero_stub is present')
        for ref in re.findall(r'`([A-Za-z0-9_./-]+\.(?:json|yaml|py|md))`', text):
            if '/' in ref and not ref.startswith('workflows/') \
               and not os.path.exists(os.path.join(pack, ref)):
                errs.append('SKILL.md: dangling reference ' + ref)
    return errs

def main(argv):
    errs = []
    if len(argv) > 1 and argv[1] != '-':
        ir = load_json(argv[1])
        errs += structural_validate(ir, contract('skill-ir.schema.json'))
        errs += check_partition(ir) + check_graph(ir) + check_evals(ir)
    errs += check_pack_files(argv[2] if len(argv) > 2 else None)
    return emit({'stage': 'STATIC_VALIDATE', 'status': 'FAIL' if errs else 'PASS',
                 'error_count': len(errs), 'errors': errs}, 2 if errs else 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
