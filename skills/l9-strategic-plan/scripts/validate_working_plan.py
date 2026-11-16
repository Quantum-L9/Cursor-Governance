#!/usr/bin/env python3
"""Generic structural and optionally graph-coherence checks for a working plan package.

Never claims strategic admission, authoritative provenance, semantic correctness,
source freshness or runtime verification. Graph JSON schema is supplied by caller.
"""
import argparse, hashlib, json, zipfile, sys
from pathlib import PurePosixPath

def digest(b): return hashlib.sha256(b).hexdigest()
def read_zip(path):
    with zipfile.ZipFile(path) as z:
        infos=[i for i in z.infolist() if not i.is_dir()]
        if not infos: raise ValueError('empty archive')
        if sum(i.file_size for i in infos)>250_000_000: raise ValueError('oversized archive')
        names=[i.filename for i in infos]
        if len(names)!=len(set(names)): raise ValueError('duplicate member')
        for i in infos:
            n=i.filename
            if n.startswith('/') or '\\' in n or any(p in ('.','..','') for p in n.split('/')): raise ValueError('unsafe path '+n)
            if i.external_attr>>16 & 0o170000 == 0o120000: raise ValueError('symlink')
        roots={PurePosixPath(n).parts[0] for n in names}
        if len(roots)!=1: raise ValueError('multiple roots')
        data={'/'.join(PurePosixPath(n).parts[1:]):z.read(n) for n in names}
        if '' in data: raise ValueError('root file not allowed')
        if 'SHA256SUMS.json' in data:
            m=json.loads(data['SHA256SUMS.json'])['sha256_by_path']
            if set(m)!=set(data)-{'SHA256SUMS.json'}: raise ValueError('checksum coverage')
            for k,v in m.items():
                if digest(data[k])!=v: raise ValueError('checksum mismatch '+k)
        return data

def check_graph(data, path, node_key, edge_key, id_key, source_key, target_key, relation_key, allowed_relations):
    if path not in data: raise ValueError('graph missing '+path)
    graph=json.loads(data[path]); nodes=graph[node_key]; edges=graph[edge_key]
    ids=[n[id_key] for n in nodes]
    if len(ids)!=len(set(ids)): raise ValueError('duplicate graph node id')
    known=set(ids)
    for i,e in enumerate(edges):
        if e[source_key] not in known or e[target_key] not in known: raise ValueError('dangling graph edge '+str(i))
        if allowed_relations and e[relation_key] not in allowed_relations: raise ValueError('unknown relation '+str(i))
    return {'nodes':len(ids),'edges':len(edges),'edge_endpoint_integrity':'PASS'}

def json_pointer(document, pointer):
    if not pointer.startswith('/'):
        raise ValueError('invalid JSON pointer')
    value = document
    for part in pointer[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value

def check_policy(data, policy):
    """Caller-authored domain-specific assertions, not invented semantic inference."""
    results = []
    for rule in policy.get('assertions', []):
        kind = rule['kind']
        doc = json.loads(data[rule['file']])
        if kind == 'equals':
            ok = json_pointer(doc, rule['pointer']) == rule['value']
        elif kind == 'matches_file':
            other = json.loads(data[rule['other_file']])
            ok = json_pointer(doc, rule['pointer']) == json_pointer(other, rule['other_pointer'])
        elif kind in ('edge_exists', 'edge_absent'):
            edges = json_pointer(doc, rule.get('edges_pointer', '/edges'))
            src, dst = rule['source'], rule['target']
            found = any(e.get(rule.get('source_key','source')) == src and
                        e.get(rule.get('target_key','target')) == dst and
                        (not rule.get('relation') or e.get(rule.get('relation_key','relation')) == rule['relation'])
                        for e in edges)
            ok = found if kind == 'edge_exists' else not found
        elif kind == 'unique_field':
            records = json_pointer(doc, rule['pointer'])
            vals = [r[rule['field']] for r in records]
            ok = len(vals) == len(set(vals))
        else:
            raise ValueError('unsupported policy assertion: '+kind)
        if not ok:
            raise ValueError('POLICY_ASSERTION_FAILED: '+str(rule.get('id',kind)))
        results.append(rule.get('id',kind))
    return results

def check_unchanged(predecessor, successor, policy):
    changed = {k for k in set(predecessor)&set(successor) if predecessor[k]!=successor[k]}
    allowed = set(policy.get('allowed_changed_paths',[]))
    if 'allowed_changed_paths' in policy and changed-allowed:
        raise ValueError('UNEXPECTED_CHANGED_PATH: '+','.join(sorted(changed-allowed)))
    for name in policy.get('must_remain_unchanged',[]):
        if name not in predecessor or name not in successor or predecessor[name]!=successor[name]:
            raise ValueError('PROTECTED_PATH_CHANGED: '+name)
    return sorted(changed)

def verify_policy(policy):
    if not isinstance(policy,dict) or not isinstance(policy.get('assertions',[]),list):
        raise ValueError('INVALID_POLICY')
    if not policy.get('authority_ref'):
        raise ValueError('POLICY_AUTHORITY_REQUIRED')


def main():
    a=argparse.ArgumentParser();a.add_argument('successor');a.add_argument('--predecessor');a.add_argument('--allow-removed',action='append',default=[]);a.add_argument('--graph');a.add_argument('--node-key',default='nodes');a.add_argument('--edge-key',default='edges');a.add_argument('--id-key',default='id');a.add_argument('--source-key',default='source');a.add_argument('--target-key',default='target');a.add_argument('--relation-key',default='relation');a.add_argument('--allowed-relation',action='append',default=[]);a.add_argument('--policy',help='Caller-authored semantic assertions JSON');args=a.parse_args()
    out={'status':'FAIL','structural':'NOT_RUN','semantic':'NOT_TESTED','source_freshness':'NOT_TESTED','runtime':'NOT_TESTED'}
    try:
        new=read_zip(args.successor);out['structural']='PASS';out['successor_sha256']=digest(open(args.successor,'rb').read());out['file_count']=len(new)
        if args.policy:
            policy=json.loads(open(args.policy,encoding='utf-8').read());verify_policy(policy)
            out['policy_authority_ref']=policy['authority_ref']
            out['assertions_passed']=check_policy(new,policy)
            out['policy_assertions']='PASS'
        if args.predecessor:
            old=read_zip(args.predecessor);missing=set(old)-set(new)
            if missing!=set(args.allow_removed):raise ValueError('undocumented or stale removal exemption: '+str(sorted(missing^set(args.allow_removed))))
            if args.policy:out['changed_paths']=check_unchanged(old,new,policy)
            out['predecessor_sha256']=digest(open(args.predecessor,'rb').read());out['preserved_files']=len(old)-len(missing)
        elif args.allow_removed: raise ValueError('predecessor required')
        if args.graph:out['graph']=check_graph(new,args.graph,args.node_key,args.edge_key,args.id_key,args.source_key,args.target_key,args.relation_key,set(args.allowed_relation))
        out['status']='PASS_POLICY_ASSERTIONS_AND_STRUCTURE' if args.policy else 'PASS_STRUCTURAL_ONLY'
    except (ValueError,KeyError,OSError,zipfile.BadZipFile,json.JSONDecodeError) as exc:out['error']=str(exc)
    print(json.dumps(out,indent=2,sort_keys=True));return 0 if out['status'] in ('PASS_STRUCTURAL_ONLY','PASS_POLICY_ASSERTIONS_AND_STRUCTURE') else 1
if __name__=='__main__':sys.exit(main())
