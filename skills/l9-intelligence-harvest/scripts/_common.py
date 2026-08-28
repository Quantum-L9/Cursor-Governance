import json
from pathlib import Path

import yaml

PACK = Path(__file__).resolve().parent.parent


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(obj, path=None):
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def schema(name):
    return load_json(PACK / "contracts" / name)


def policy(name):
    return yaml.safe_load((PACK / "policies" / name).read_text(encoding="utf-8"))
