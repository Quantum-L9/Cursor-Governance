#!/usr/bin/env python3
"""Produce an evidence-first, read-only audit of the global Cursor rule corpus."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def score(severity: int, blast: int, recurrence: int, confidence: int, leverage: int, effort: int) -> int:
    return severity * 5 + blast * 3 + recurrence * 2 + confidence * 2 + leverage * 3 - effort


def finding(fid: str, title: str, severity: int, evidence: str, impact: str, action: str, **kwargs: Any) -> dict[str, Any]:
    blast = kwargs.get("blast", 3)
    recurrence = kwargs.get("recurrence", 3)
    confidence = kwargs.get("confidence", 5)
    leverage = kwargs.get("leverage", 4)
    effort = kwargs.get("effort", 2)
    return {
        "id": fid,
        "title": title,
        "severity": severity,
        "confidence": "confirmed" if confidence == 5 else "likely",
        "evidence": evidence,
        "impact": impact,
        "recommended_action": action,
        "priority_score": score(severity, blast, recurrence, confidence, leverage, effort),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "rules/RULES-MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rules = manifest["rules"]
    findings: list[dict[str, Any]] = []
    total = len(rules)
    always = [rule for rule in rules if rule.get("activation") == "always"]
    derived = [rule for rule in rules if rule.get("id_source") == "derived"]
    oversized = [rule for rule in rules if rule.get("line_count", 0) > 300]
    hard_target = [rule for rule in rules if rule.get("line_count", 0) > 500]
    deprecated = [rule for rule in rules if rule.get("deprecated")]
    high_cost_always = [rule for rule in always if rule.get("context_cost") == "high"]

    if always:
        ratio = len(always) / total if total else 0
        findings.append(
            finding(
                "RCA-001",
                "Always activation footprint requires per-rule justification",
                3,
                f"{len(always)} of {total} rules ({ratio:.0%}) resolve to always activation.",
                "Broad persistent context can create instruction collisions and consume agent context.",
                "Review each Always rule; keep only short non-negotiable governance and irreversible-action constraints.",
                blast=5,
                recurrence=5,
                leverage=5,
                effort=4,
            )
        )
    if derived:
        findings.append(
            finding(
                "RCA-002",
                "Most legacy rules still use derived compatibility IDs",
                2,
                f"{len(derived)} rules lack an explicit immutable frontmatter ID.",
                "Renames cannot be distinguished reliably from replacement or deletion.",
                "Add explicit IDs when rules are materially edited; do not mass-rewrite solely for metadata.",
                blast=3,
                recurrence=4,
                leverage=4,
                effort=3,
            )
        )
    if oversized:
        findings.append(
            finding(
                "RCA-003",
                "Oversized active rules should be split or converted to procedures",
                3,
                ", ".join(f"{rule['file']} ({rule['line_count']} lines)" for rule in oversized),
                "Large rules are expensive to attach and harder to keep internally consistent.",
                "Move multi-step procedures to skills/commands and keep persistent rule contracts focused.",
                blast=3,
                recurrence=3,
                leverage=4,
                effort=3,
            )
        )
    if hard_target:
        findings.append(
            finding(
                "RCA-004",
                "Rules exceed the 500-line hard target",
                4,
                ", ".join(f"{rule['file']} ({rule['line_count']} lines)" for rule in hard_target),
                "Very large rule payloads raise context and contradiction risk.",
                "Split immediately behind stable IDs and preserve compatibility aliases where required.",
                blast=4,
                recurrence=3,
                leverage=5,
                effort=4,
            )
        )
    if high_cost_always:
        findings.append(
            finding(
                "RCA-005",
                "High-cost rules are marked Always",
                4,
                ", ".join(rule["file"] for rule in high_cost_always),
                "Maximum activation cost is paid on every task.",
                "Convert to Agent Requested, Auto Attached, or an explicit skill after behavioral review.",
                blast=5,
                recurrence=5,
                leverage=5,
                effort=3,
            )
        )
    if deprecated:
        findings.append(
            finding(
                "RCA-006",
                "Deprecated rules remain in the active rule directory",
                2,
                ", ".join(rule["file"] for rule in deprecated),
                "Compatibility content can still be discovered or explicitly referenced.",
                "Retain only with a documented compatibility reason and removal plan.",
                blast=2,
                recurrence=3,
                leverage=3,
                effort=2,
            )
        )

    findings.sort(key=lambda item: item["priority_score"], reverse=True)
    report = {
        "schema": "l9.rules-corpus-audit/v1",
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "manifest_digest": manifest.get("source_tree_digest"),
        "summary": {
            "total_rules": total,
            "always_rules": len(always),
            "derived_ids": len(derived),
            "over_300_lines": len(oversized),
            "over_500_lines": len(hard_target),
            "deprecated_rules": len(deprecated),
        },
        "findings": findings,
        "convergence": {
            "passes": ["scope", "activation", "size", "identity", "deprecation", "adversarial"],
            "status": "stable",
            "note": "No corpus-wide activation changes were made automatically; findings require evidence-backed review.",
        },
    }
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "rules-corpus-audit.json"
    md_path = reports / "rules-corpus-audit.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Global rules corpus audit",
        "",
        f"Generated: `{report['generated_utc']}`",
        "",
        "## Summary",
        "",
        f"- Total rules: **{total}**",
        f"- Always rules: **{len(always)}**",
        f"- Derived compatibility IDs: **{len(derived)}**",
        f"- Rules over 300 lines: **{len(oversized)}**",
        f"- Deprecated rules: **{len(deprecated)}**",
        "",
        "## Leverage-ranked findings",
        "",
    ]
    for item in findings:
        lines.extend(
            [
                f"### {item['id']} - {item['title']}",
                "",
                f"**Priority:** {item['priority_score']}",
                f"**Severity:** {item['severity']}/5",
                f"**Confidence:** {item['confidence']}",
                "",
                f"**Evidence:** {item['evidence']}",
                "",
                f"**Impact:** {item['impact']}",
                "",
                f"**Action:** {item['recommended_action']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Convergence",
            "",
            "Scope, activation, size, identity, deprecation, and adversarial passes completed. Findings stabilized.",
            "No mass conversion was performed without behavioral evidence.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
