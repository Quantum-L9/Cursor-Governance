from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def validate(spec_path: Path, schema_path: Path) -> list[str]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return [error.message for error in Draft202012Validator(schema).iter_errors(spec)]


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print("usage: validate_target_adapter.py SPEC.json", file=sys.stderr)
        return 2
    path = Path(args[0]).resolve()
    schema = Path(__file__).with_name("target-adapter-spec.schema.json")
    errors = validate(path, schema)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
