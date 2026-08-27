#!/usr/bin/env python3
# PACKAGE: deterministic integrity enumeration. Never mutates a registry.
import sys, os, hashlib, datetime
from _common import PACK, emit

EXPECTED = ['SKILL.md', 'contracts', 'policies', 'scripts', 'references', 'tests']

def enumerate_pack(pack=None):
    pack = pack or str(PACK)
    rows = []
    for root, dirs, files in os.walk(pack):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rows.append({'path': os.path.relpath(p, pack),
                         'bytes': os.path.getsize(p),
                         'sha256_16': hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]})
    return sorted(rows, key=lambda r: r['path'])

def integrity(pack=None):
    pack = pack or str(PACK)
    missing = [e for e in EXPECTED if not os.path.exists(os.path.join(pack, e))]
    empty = [r['path'] for r in enumerate_pack(pack) if r['bytes'] == 0]
    return missing, empty

def main(argv):
    pack = argv[1] if len(argv) > 1 else None
    missing, empty = integrity(pack)
    rows = enumerate_pack(pack)
    status = 'FAIL' if (missing or empty) else 'PASS'
    return emit({'stage': 'PACKAGE', 'status': status, 'missing': missing,
                 'empty_files': empty, 'file_count': len(rows),
                 'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
                 'artifacts': rows}, 2 if status == 'FAIL' else 0)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
