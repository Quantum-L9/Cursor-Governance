import json
import pathlib
import sys

PACK = pathlib.Path(__file__).resolve().parent.parent
REPO = PACK.parent.parent


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path):
    import yaml

    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def contract(name):
    return load_json(PACK / "contracts" / name)


def policy(name):
    return load_yaml(PACK / "policies" / name)


def emit(obj, code=0):
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")
    return code


def fail(msg, code=2):
    sys.stderr.write("BLOCKED/FAIL: " + str(msg) + "\n")
    return code
