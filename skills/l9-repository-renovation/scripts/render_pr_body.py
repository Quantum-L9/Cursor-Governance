#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import load_json


def command_line(record: dict) -> str:
    command = record.get("command") or []
    if isinstance(command, list):
        return " ".join(str(item) for item in command)
    return str(command)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a renovation pull-request body from verified artifacts."
    )
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--delta", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("PR_BODY.md"))
    args = parser.parse_args()

    contract = load_json(args.contract)
    evidence = load_json(args.evidence)
    delta = load_json(args.delta)
    decisions = contract.get("authority_decisions", [])
    records = evidence.get("records", [])
    lines = [
        "## Operational defect",
        "",
        contract["objective"],
        "",
        "## Renovated authority model",
        "",
    ]
    lines.extend([f"- **{item['concern']}**: {item['target_authority']}" for item in decisions])
    lines.extend(["", "## Scope", ""])
    lines.append(f"- Base commit: `{contract['repository'].get('base_commit')}`")
    lines.append(f"- Target branch: `{contract['repository'].get('target_branch')}`")
    lines.append(f"- Implementation phases: {len(contract.get('phases', []))}")
    lines.extend(["", "### Preserved behavior", ""])
    lines.extend([f"- {item}" for item in contract.get("scope", {}).get("preserved_behavior", [])])
    lines.extend(["", "## Validation", ""])
    for record in records:
        mark = "✅" if record.get("exit_code") == 0 else "❌"
        lines.append(f"- {mark} `{command_line(record)}` ({record.get('duration_seconds', 0)}s)")
    lines.extend(
        [
            "",
            "## Before and after",
            "",
            f"- Findings: {delta.get('before', {}).get('total')} → {delta.get('after', {}).get('total')}",
            f"- Weighted severity: {delta.get('before', {}).get('weighted_score')} → {delta.get('after', {}).get('weighted_score')}",
            f"- Resolved: {len(delta.get('resolved', []))}",
            f"- Remaining: {len(delta.get('remaining', []))}",
            f"- Introduced: {len(delta.get('introduced', []))}",
            "",
            "## Risk and rollback",
            "",
            f"- Rollback: {contract.get('rollback', {}).get('strategy')}",
            "- Merge remains a separate human-authorized action.",
            "",
            "## Review checklist",
            "",
            "- [ ] Changed files stay inside the renovation contract",
            "- [ ] No local/CI authority duplication remains",
            "- [ ] Every active isolated suite executes through a canonical entrypoint",
            "- [ ] Lockfile movement matches declared dependency changes",
            "- [ ] Required checks are green",
            "",
        ]
    )
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"pr body: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
