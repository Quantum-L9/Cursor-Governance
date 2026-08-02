from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from autonomy.io import confined_path, load_json


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


def read_receipts_jsonl(
    path: str | Path, *, root: str | Path | None = None
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    source = confined_path(path, root=root, label="events path")
    with open(source, encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an autonomy event trace.")
    parser.add_argument("--events", required=True)
    parser.add_argument("--spec", required=True)
    args = parser.parse_args()
    events = read_receipts_jsonl(args.events)
    specification = load_json(args.spec)
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
