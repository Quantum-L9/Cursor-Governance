#!/usr/bin/env python3
"""Capture a machine-readable preflight for the two-repository rule cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MOVES_TO_GLOBAL = [
    ".cursor/rules/05-recursive-execution-kernel.mdc",
    ".cursor/rules/96-output-discipline.mdc",
]
MOVES_TO_CONSUMER = [
    "rules/30-odoo-native.mdc",
    "rules/95-plasticos-equipment-policy.mdc",
    "rules/98-odoo-sh-staging.mdc",
]


def run(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.rstrip("\n")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_state(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        return {
            "type": "symlink",
            "target": os.readlink(path),
            "realpath": str(path.resolve()),
        }
    if path.is_dir():
        return {"type": "directory", "realpath": str(path.resolve())}
    if path.exists():
        return {"type": "other", "realpath": str(path.resolve())}
    return {"type": "missing"}


def repo_state(repo: Path) -> dict[str, Any]:
    return {
        "path": str(repo),
        "head": run(repo, "rev-parse", "HEAD"),
        "branch": run(repo, "branch", "--show-current"),
        "status_porcelain_v2": run(repo, "status", "--porcelain=v2"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("governance", type=Path)
    parser.add_argument("consumer", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    governance = args.governance.resolve()
    consumer = args.consumer.resolve()
    output_dir = (args.output_dir or governance / "reports").resolve()

    try:
        gov_state = repo_state(governance)
        consumer_state = repo_state(consumer)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    if not args.allow_dirty:
        if gov_state["status_porcelain_v2"]:
            errors.append("governance repository is dirty")
        if consumer_state["status_porcelain_v2"]:
            errors.append("consumer repository is dirty")

    rules_path = consumer / ".cursor/rules"
    tracked_rules = run(consumer, "ls-tree", "-r", "--name-only", "HEAD", "--", ".cursor/rules")
    tracked_rule_files = [line for line in tracked_rules.splitlines() if line.endswith(".mdc")]
    global_rules = sorted(path.name for path in (governance / "rules").glob("*.mdc"))

    moves: list[dict[str, Any]] = []
    for source_rel in MOVES_TO_GLOBAL:
        source = consumer / source_rel
        destination = governance / "rules" / source.name
        moves.append(
            {
                "direction": "consumer_to_global",
                "source": source_rel,
                "destination": f"rules/{source.name}",
                "source_sha256": sha256(source),
                "destination_exists": destination.exists() or destination.is_symlink(),
            }
        )
    for source_rel in MOVES_TO_CONSUMER:
        source = governance / source_rel
        destination = consumer / ".cursor/rules" / source.name
        moves.append(
            {
                "direction": "global_to_consumer",
                "source": source_rel,
                "destination": f".cursor/rules/{source.name}",
                "source_sha256": sha256(source),
                "destination_exists": destination.exists() or destination.is_symlink(),
            }
        )
    for item in moves:
        if item["source_sha256"] is None:
            errors.append(f"missing move source: {item['source']}")
        if item["destination_exists"]:
            errors.append(f"destination collision: {item['destination']}")

    manifest_summary: dict[str, Any] | None = None
    manifest_path = governance / "rules/RULES-MANIFEST.json"
    if manifest_path.is_file():
        try:
            manifest_summary = json.loads(manifest_path.read_text(encoding="utf-8")).get("summary")
        except json.JSONDecodeError:
            errors.append("existing JSON manifest is invalid")

    report = {
        "schema": "l9.rules-cleanup-preflight/v1",
        "captured_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "governance": gov_state,
        "consumer": consumer_state,
        "consumer_rules_object": object_state(rules_path),
        "consumer_tracked_rule_count": len(tracked_rule_files),
        "consumer_tracked_rules": tracked_rule_files,
        "global_rule_count": len(global_rules),
        "global_rules": global_rules,
        "existing_manifest_summary": manifest_summary,
        "moves": moves,
        "errors": errors,
        "gate": "PASS" if not errors else "FAIL",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "rules-cleanup-preflight.json"
    md_path = output_dir / "rules-cleanup-preflight.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Rules cleanup preflight",
        "",
        f"**Gate:** {report['gate']}",
        f"**Captured:** {report['captured_utc']}",
        "",
        "## Repositories",
        "",
        f"- Governance: `{gov_state['head']}` on `{gov_state['branch']}`",
        f"- Consumer: `{consumer_state['head']}` on `{consumer_state['branch']}`",
        f"- Consumer `.cursor/rules`: `{report['consumer_rules_object']['type']}`",
        f"- Consumer tracked MDC files: **{len(tracked_rule_files)}**",
        f"- Global MDC files: **{len(global_rules)}**",
        "",
        "## Cross-repository moves",
        "",
        "| Direction | Source | Destination | Source digest | Collision |",
        "|---|---|---|---|---|",
    ]
    for item in moves:
        digest = (item["source_sha256"] or "MISSING")[:12]
        lines.append(
            f"| {item['direction']} | `{item['source']}` | `{item['destination']}` | "
            f"`{digest}` | {item['destination_exists']} |"
        )
    lines.extend(["", "## Gate findings", ""])
    if errors:
        lines.extend(f"- FAIL: {error}" for error in errors)
    else:
        lines.append("- PASS: sources are recoverable, destinations are collision-free, and both trees are clean.")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE: {md_path}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
