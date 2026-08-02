from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


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
    raise SystemExit("golden_trace file-path CLI is disabled; call GoldenTraceValidator.validate()")


if __name__ == "__main__":
    raise SystemExit(main())
