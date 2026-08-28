#!/usr/bin/env python3
import sys

from _common import dump, load_json, schema
from jsonschema import Draft202012Validator

DEFAULTS = {
    "access_mode": "read-only",
    "depth": "exhaustive",
    "secrets_policy": "redact",
    "language": "as-donor",
    "brief": False,
}


def bind(req):
    out = dict(DEFAULTS)
    out.update(req)
    errs = sorted(
        Draft202012Validator(schema("harvest-request.schema.json")).iter_errors(out),
        key=lambda e: list(e.path),
    )
    return out, [e.message for e in errs]


def main():
    req = load_json(sys.argv[1])
    out, errs = bind(req)
    if errs:
        dump({"status": "FAIL", "errors": errs})
        return 2
    if len(sys.argv) > 2:
        dump(out, sys.argv[2])
    dump({"status": "PASS", "request": out})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
