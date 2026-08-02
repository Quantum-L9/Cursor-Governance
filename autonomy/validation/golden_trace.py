from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from typing import Any

from autonomy.cli_fs import load_json_cli, read_jsonl_cli


class GoldenTraceValidator:
    def validate(
        self,
        *,
        events: Iterable[Mapping[str, Any]],
        specification: Mapping[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        event_list = list(events)
        event_types = [str(event["event_type"]) for event in event_list]
        for forbidden in specification.get("forbidden_events", []):
            if forbidden in event_types:
                errors.append(f"Forbidden event observed: {forbidden}")
        for required in specification.get("required_events", []):
            if required not in event_types:
                errors.append(f"Required event missing: {required}")
        sequence = specification.get("required_sequence", [])
        position = -1
        for required in sequence:
            try:
                position = event_types.index(required, position + 1)
            except ValueError:
                errors.append(f"Required sequence is not satisfied at event {required!r}")
                break
        maximum_counts = specification.get("maximum_counts", {})
        for event_type, maximum in maximum_counts.items():
            observed = event_types.count(event_type)
            if observed > int(maximum):
                errors.append(
                    f"Event {event_type!r} observed {observed} times; maximum is {maximum}"
                )
        return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an autonomy event trace.")
    parser.add_argument("--events", required=True)
    parser.add_argument("--spec", required=True)
    args = parser.parse_args()
    events = read_jsonl_cli(args.events)
    specification = load_json_cli(args.spec)
    errors = GoldenTraceValidator().validate(
        events=events,
        specification=specification,
    )
    print(
        json.dumps(
            {"valid": not errors, "errors": errors},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
