from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from state_store import PipelineStateStore


def redact(value: Any) -> Any:
    sensitive = {
        "token",
        "secret",
        "password",
        "authorization",
        "api_key",
        "private_key",
    }
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if key.lower() in sensitive else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and resolve generated-data dead letters.")
    parser.add_argument("--database", required=True)
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )
    commands.add_parser("list")
    show = commands.add_parser("show")
    show.add_argument("dead_letter_id")
    resolve = commands.add_parser("resolve")
    resolve.add_argument("dead_letter_id")
    resolve.add_argument(
        "--type",
        required=True,
        choices=(
            "discarded",
            "superseded",
            "manually_delivered",
            "configuration_fixed",
        ),
    )
    resolve.add_argument("--reason", required=True)
    resolve.add_argument("--actor", required=True)
    export = commands.add_parser("export")
    export.add_argument("--output", required=True)
    args = parser.parse_args()
    store = PipelineStateStore(args.database)
    if args.command == "list":
        payload = [item.to_dict() for item in store.list_dead_letters()]
    elif args.command == "show":
        matches = [
            item for item in store.list_dead_letters() if item.dead_letter_id == args.dead_letter_id
        ]
        if not matches:
            raise SystemExit("Dead letter not found")
        payload = matches[0].to_dict()
    elif args.command == "resolve":
        payload = store.resolve_dead_letter(
            dead_letter_id=args.dead_letter_id,
            resolution_type=args.type,
            resolution_reason=args.reason,
            actor=args.actor,
        ).to_dict()
    elif args.command == "export":
        payload = [redact(item.to_dict()) for item in store.list_dead_letters()]
        Path(args.output).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(args.output)
        return 0
    else:
        raise SystemExit("Unsupported command")
    print(json.dumps(redact(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
