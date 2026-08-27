# Shared deterministic helpers. No LLM work here.
import json, pathlib, sys
PACK = pathlib.Path(__file__).resolve().parent.parent
REPO = PACK.parent.parent
def load_json(p):
    with open(p, 'r', encoding='utf-8') as fh:
        return json.load(fh)
def load_yaml(p):
    import yaml
    with open(p, 'r', encoding='utf-8') as fh:
        return yaml.safe_load(fh)
def contract(name):
    return load_json(PACK / 'contracts' / name)
def policy(name):
    return load_yaml(PACK / 'policies' / name)
def emit(obj, code=0):
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True, default=str) + chr(10))
    return code
def fail(msg, code=2):
    sys.stderr.write('BLOCKED/FAIL: ' + str(msg) + chr(10))
    return code
