#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import load_json, run, safe_cli_path, utc_now, write_json
from validate_contract import validate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute a renovation contract validation matrix and capture evidence."
    )
    parser.add_argument("contract", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("validation-evidence.json"))
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args()

    contract = load_json(args.contract)
    errors = validate(contract)
    if errors:
        print(json.dumps({"valid_contract": False, "errors": errors}, indent=2))
        return 2
    repo = args.repo.resolve()
    records = []
    for item in contract["validation_matrix"]:
        record = run(
            [str(token) for token in item["command"]],
            cwd=repo,
            timeout=int(item.get("timeout_seconds", 600)),
            env={str(key): str(value) for key, value in (item.get("env") or {}).items()},
        )
        record["id"] = item["id"]
        record["required"] = bool(item.get("required", True))
        records.append(record)
        print(f"{record['status'].upper()}: {record['id']} ({record['duration_seconds']}s)")
        if record["required"] and record["exit_code"] != 0 and not args.continue_on_failure:
            break
    required_failed = [
        record for record in records if record["required"] and record["exit_code"] != 0
    ]
    expected_ids = {
        item["id"] for item in contract["validation_matrix"] if item.get("required", True)
    }
    executed_ids = {record["id"] for record in records}
    missing_required = sorted(expected_ids - executed_ids)
    payload = {
        "schema_version": "validation-evidence-1.0",
        "generated_at": utc_now(),
        "contract_id": contract["contract_id"],
        "repository": str(repo),
        "status": "passed" if not required_failed and not missing_required else "failed",
        "required_failures": [record["id"] for record in required_failed],
        "missing_required": missing_required,
        "records": records,
    }
    output = safe_cli_path(args.output)
    write_json(output, payload)
    print(f"evidence: {output}")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
