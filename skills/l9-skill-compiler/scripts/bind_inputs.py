#!/usr/bin/env python3
# BIND_INPUTS: deterministic. Validates a CompileRequest with no external deps.
import sys

from _common import contract, emit, fail, load_json


def structural_validate(obj, schema, path="$"):
    errs = []
    schema_type = schema.get("type")
    types = schema_type if isinstance(schema_type, list) else [schema_type] if schema_type else []
    if "object" in types and not isinstance(obj, dict):
        return [path + ": expected object"]
    if "array" in types and not isinstance(obj, list):
        return [path + ": expected array"]
    if "enum" in schema and obj not in schema["enum"]:
        errs.append(path + ": value not in enum " + str(schema["enum"]))
    if isinstance(obj, dict):
        for required in schema.get("required", []):
            if required not in obj:
                errs.append(path + "." + required + ": required field missing")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in obj:
                if key not in props:
                    errs.append(path + "." + key + ": additional property not allowed")
        for key, value in obj.items():
            if key in props and isinstance(props[key], dict):
                errs += structural_validate(value, props[key], path + "." + key)
    if isinstance(obj, list):
        if "minItems" in schema and len(obj) < schema["minItems"]:
            errs.append(path + ": fewer than minItems=" + str(schema["minItems"]))
        item = schema.get("items")
        if isinstance(item, dict):
            for index, value in enumerate(obj):
                errs += structural_validate(value, item, path + "[" + str(index) + "]")
    if isinstance(obj, str) and "minLength" in schema and len(obj) < schema["minLength"]:
        errs.append(path + ": shorter than minLength")
    return errs


def bind(req):
    errs = structural_validate(req, contract("compile-request.schema.json"))
    profiles = req.get("target_profiles", []) if isinstance(req, dict) else []
    for required in ("portable", "l9"):
        if required not in profiles:
            errs.append("target_profiles: missing required initial profile " + required)
    return errs


def main(argv):
    if len(argv) < 2:
        return fail("usage: bind_inputs.py <compile-request.json>")
    req = load_json(argv[1])
    errs = bind(req)
    if errs:
        return emit({"stage": "BIND_INPUTS", "status": "FAIL", "errors": errs}, 2)
    return emit(
        {
            "stage": "BIND_INPUTS",
            "status": "PASS",
            "request_id": req["request_id"],
            "intent": req["intent"],
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
