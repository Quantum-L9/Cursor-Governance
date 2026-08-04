#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import load_json, safe_cli_path, utc_now, write_json

SEVERITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def summarize(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(findings),
        "by_severity": dict(
            sorted(Counter(item.get("severity", "unknown") for item in findings).items())
        ),
        "by_class": dict(
            sorted(Counter(item.get("class", "unknown") for item in findings).items())
        ),
        "weighted_score": sum(SEVERITY_WEIGHT.get(item.get("severity"), 0) for item in findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare before and after repository audits.")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--json", type=Path, default=Path("renovation-delta.json"))
    parser.add_argument("--markdown", type=Path, default=Path("RENOVATION_DELTA.md"))
    args = parser.parse_args()

    before = load_json(args.before)
    after = load_json(args.after)
    before_by_id = {item["id"]: item for item in before.get("findings", [])}
    after_by_id = {item["id"]: item for item in after.get("findings", [])}
    resolved = [before_by_id[item_id] for item_id in sorted(set(before_by_id) - set(after_by_id))]
    introduced = [after_by_id[item_id] for item_id in sorted(set(after_by_id) - set(before_by_id))]
    remaining = [after_by_id[item_id] for item_id in sorted(set(before_by_id) & set(after_by_id))]
    payload = {
        "schema_version": "renovation-delta-1.0",
        "generated_at": utc_now(),
        "before_audit_id": before.get("audit_id"),
        "after_audit_id": after.get("audit_id"),
        "before": summarize(before.get("findings", [])),
        "after": summarize(after.get("findings", [])),
        "resolved": resolved,
        "remaining": remaining,
        "introduced": introduced,
        "new_high_or_critical": [
            item for item in introduced if item.get("severity") in {"critical", "high"}
        ],
    }
    payload["status"] = "passed" if not payload["new_high_or_critical"] else "failed"
    write_json(safe_cli_path(args.json), payload)

    lines = [
        "# Repository Renovation Delta",
        "",
        f"Status: **{payload['status'].upper()}**",
        "",
        "## Score movement",
        "",
        f"- Findings: {payload['before']['total']} → {payload['after']['total']}",
        f"- Weighted severity: {payload['before']['weighted_score']} → {payload['after']['weighted_score']}",
        f"- Resolved: {len(resolved)}",
        f"- Remaining: {len(remaining)}",
        f"- Introduced: {len(introduced)}",
        "",
        "## Resolved",
        "",
    ]
    lines.extend(
        [f"- `{item['id']}` [{item['severity']}] {item['summary']}" for item in resolved]
        or ["- None"]
    )
    lines.extend(["", "## Remaining", ""])
    lines.extend(
        [f"- `{item['id']}` [{item['severity']}] {item['summary']}" for item in remaining]
        or ["- None"]
    )
    lines.extend(["", "## Introduced", ""])
    lines.extend(
        [f"- `{item['id']}` [{item['severity']}] {item['summary']}" for item in introduced]
        or ["- None"]
    )
    lines.extend(
        [
            "",
            "Finding reduction is supporting evidence only. Contract acceptance criteria and validation evidence remain authoritative.",
            "",
        ]
    )
    safe_cli_path(args.markdown).write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {"status": payload["status"], "resolved": len(resolved), "introduced": len(introduced)},
            indent=2,
        )
    )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
