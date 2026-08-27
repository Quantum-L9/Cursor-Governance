#!/usr/bin/env python3
# CAPABILITY_CLOSURE: fully deterministic. Replaces the retired zero_stub concept.
import sys, os, datetime
from _common import REPO, policy, emit, fail, load_json

_POL = None
def _pol():
    global _POL
    if _POL is None:
        _POL = policy('capability-closure.yaml')
    return _POL

def _placeholder(text):
    t = text or ''
    return any(m.lower() in t.lower() for m in _pol()['placeholder_markers'])

def _live(repo_root):
    d = os.path.join(repo_root, 'skills')
    if not os.path.isdir(d):
        return set()
    return {n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n, 'SKILL.md'))}

def _reachable(ir):
    nodes = {n['id']: n for n in ir.get('workflow', {}).get('nodes', [])}
    start = ir.get('workflow', {}).get('entrypoint')
    seen, stack = set(), [start] if start in nodes else []
    while stack:
        cur = stack.pop()
        if cur in seen or cur not in nodes:
            continue
        seen.add(cur)
        stack += list(nodes[cur].get('next', []))
    caps = set()
    for nid in seen:
        caps |= set(nodes[nid].get('capabilities', []))
    return seen, caps

def _cycles(caps):
    graph = {c['id']: list((c.get('binding') or {}).get('depends_on', [])) for c in caps}
    found, state = [], {}
    def dfs(n, path):
        state[n] = 1
        for m in graph.get(n, []):
            if state.get(m) == 1 and m in path:
                found.append(path[path.index(m):] + [m])
            elif state.get(m, 0) == 0 and m in graph:
                dfs(m, path + [m])
        state[n] = 2
    for n in graph:
        if state.get(n, 0) == 0:
            dfs(n, [n])
    return found

def check(ir, repo_root=None, live_skills=None):
    repo_root = repo_root or str(REPO)
    live = live_skills if live_skills is not None else _live(repo_root)
    caps = ir.get('capabilities', [])
    dag_nodes = {n['id'] for n in ir.get('workflow', {}).get('nodes', [])}
    _, reach_caps = _reachable(ir)
    checks, rows, unreachable = [], [], []
    kinds = set(_pol()['binding_kinds']) | {'UNKNOWN'}
    runtime_bound = blocked = False
    def add(cid, status, detail=None):
        checks.append({'id': cid, 'status': status, 'detail': detail})

    add('closure_result_is_machine_readable', 'pass', 'emitted per capability-closure.schema.json')
    missing = [c['id'] for c in caps if c.get('required') and not c.get('binding')]
    add('required_capabilities_have_bindings', 'fail' if missing else 'pass', ','.join(missing) or None)
    bad_kind = [c['id'] for c in caps if (c.get('binding') or {}).get('kind') not in kinds]
    add('binding_kind_is_known', 'fail' if bad_kind else 'pass', ','.join(bad_kind) or None)

    local_missing, exec_missing, dag_missing, skill_missing = [], [], [], []
    ext_bad, placeholders, unbounded = [], [], []
    for c in caps:
        b = c.get('binding') or {}
        kind, tgt = b.get('kind'), b.get('target')
        status, detail = 'closed', None
        if kind in ('EXECUTABLE', 'DAG_NODE', 'DELEGATED_SKILL') and not tgt:
            local_missing.append(c['id']); status, detail = 'unresolved', 'no target'
        elif kind == 'EXECUTABLE' and not os.path.exists(os.path.join(repo_root, tgt)):
            exec_missing.append(c['id']); status, detail = 'unresolved', 'missing ' + str(tgt)
        elif kind == 'DAG_NODE' and tgt not in dag_nodes:
            dag_missing.append(c['id']); status, detail = 'unresolved', 'no node ' + str(tgt)
        elif kind == 'DELEGATED_SKILL' and tgt not in live:
            skill_missing.append(c['id']); status, detail = 'unresolved', 'not a live skill: ' + str(tgt)
        elif kind == 'EXTERNAL_CAPABILITY':
            if not b.get('probe') or not b.get('failure_behavior'):
                ext_bad.append(c['id']); status, detail = 'unresolved', 'probe and failure_behavior required'
            else:
                runtime_bound = True; status, detail = 'runtime_bound', 'declared external runtime binding'
        elif kind == 'UNKNOWN':
            if b.get('bounded_unknown'):
                blocked = True; status, detail = 'unresolved', 'bounded UNKNOWN'
            else:
                unbounded.append(c['id']); status, detail = 'unresolved', 'unbounded UNKNOWN'
        if c.get('required') and (_placeholder(b.get('success_condition')) or _placeholder(tgt)):
            placeholders.append(c['id']); status = 'placeholder'
        if c.get('required') and c['id'] not in reach_caps:
            unreachable.append(c['id'])
        rows.append({'id': c['id'], 'binding_kind': kind or 'NONE', 'status': status, 'detail': detail})

    add('local_binding_targets_exist', 'fail' if local_missing else 'pass', ','.join(local_missing) or None)
    add('executable_bindings_resolve', 'fail' if exec_missing else 'pass', ','.join(exec_missing) or None)
    add('DAG_NODE_bindings_resolve_to_real_nodes', 'fail' if dag_missing else 'pass', ','.join(dag_missing) or None)
    add('DELEGATED_SKILL_bindings_resolve_to_live_owned_skills', 'fail' if skill_missing else 'pass', ','.join(skill_missing) or None)
    add('EXTERNAL_CAPABILITY_bindings_define_probe_and_failure_behavior', 'fail' if ext_bad else 'pass', ','.join(ext_bad) or None)
    add('required_capabilities_are_reachable_from_entrypoint', 'fail' if unreachable else 'pass', ','.join(unreachable) or None)
    cycles = _cycles(caps)
    add('dependency_graph_is_acyclic', 'fail' if cycles else 'pass', str(cycles) if cycles else None)
    add('no_required_capability_is_satisfied_by_placeholder', 'fail' if placeholders else 'pass', ','.join(placeholders) or None)
    add('no_unresolved_reference_is_silently_accepted', 'fail' if unbounded else 'pass', ','.join(unbounded) or None)
    add('UNKNOWN_is_only_valid_when_explicitly_bounded', 'block' if blocked else 'pass',
        'bounded UNKNOWN present' if blocked else None)

    if any(c['status'] == 'fail' for c in checks):
        result = 'FAIL'
    elif any(c['status'] == 'block' for c in checks):
        result = 'BLOCKED'
    elif runtime_bound:
        result = 'RUNTIME_BOUND'
    else:
        result = 'CLOSED'
    return {'result': result, 'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'checks': checks, 'capabilities': rows, 'unreachable': unreachable, 'cycles': cycles}

EXIT = {'CLOSED': 0, 'RUNTIME_BOUND': 0, 'BLOCKED': 3, 'FAIL': 2}

def main(argv):
    if len(argv) < 2:
        return fail('usage: check_capability_closure.py <skill-ir.json> [repo_root]')
    res = check(load_json(argv[1]), argv[2] if len(argv) > 2 else None)
    return emit(res, EXIT[res['result']])

if __name__ == '__main__':
    sys.exit(main(sys.argv))
