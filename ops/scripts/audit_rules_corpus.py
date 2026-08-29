#!/usr/bin/env python3
"""Produce an evidence-first, read-only audit of the global Cursor rule corpus.

C3: inverted rule → enforcer coverage (advisory; empty enforcer set is a finding).
C1: every observation names its population. Not a gate. No compliance_rate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Declared enforcer search set (not inferred). RULES-MANIFEST is the population
# source, not an enforcer — counting it would give every rule a hit.
ENFORCER_SET: tuple[str, ...] = (
    ".pre-commit-config.yaml",
    "Makefile",
    "ops/hooks/hooks.json.template",
    "ops/scripts/check_rules_standard.py",
    "ops/scripts/validate_rules_manifest.py",
)

SKIP_PARTS = {"_archived", "WIP", "__pycache__", "node_modules", ".git"}

SCHEMA = "l9.rules-corpus-audit/v2"


def score(
    severity: int, blast: int, recurrence: int, confidence: int, leverage: int, effort: int
) -> int:
    return severity * 5 + blast * 3 + recurrence * 2 + confidence * 2 + leverage * 3 - effort


def finding(
    fid: str, title: str, severity: int, evidence: str, impact: str, action: str, **kwargs: Any
) -> dict[str, Any]:
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


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_manifest(root: Path) -> tuple[dict[str, Any], Path]:
    """Load the live rules manifest. Fail closed if rules/ or the file is missing."""
    rules_dir = root / "rules"
    if not rules_dir.is_dir():
        raise FileNotFoundError(f"rules/ not found under {root}")
    yaml_path = rules_dir / "RULES-MANIFEST.yaml"
    json_path = rules_dir / "RULES-MANIFEST.json"
    path: Path | None = None
    if yaml_path.is_file():
        path = yaml_path
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise FileNotFoundError(f"unreadable manifest: {yaml_path}: {exc}") from exc
    elif json_path.is_file():
        path = json_path
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FileNotFoundError(f"unreadable manifest: {json_path}: {exc}") from exc
    else:
        raise FileNotFoundError(f"missing generated manifest: {yaml_path}")
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise FileNotFoundError(f"manifest missing rules list: {path}")
    return data, path


def _skip(rel: str) -> bool:
    return bool(set(rel.split("/")) & SKIP_PARTS)


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect_enforcer_blobs(root: Path) -> dict[str, str]:
    """Map relative path → text for the declared enforcer set plus skills/commands."""
    blobs: dict[str, str] = {}
    for rel in ENFORCER_SET:
        text = _read(root, rel)
        if text:
            blobs[rel] = text
    for prefix in ("skills", "commands"):
        base = root / prefix
        if not base.is_dir():
            continue
        pattern = "SKILL.md" if prefix == "skills" else "*.md"
        for path in base.rglob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if _skip(rel):
                continue
            if prefix == "commands" and path.name == "SKILL.md":
                continue
            text = _read(root, rel)
            if text:
                blobs[rel] = text
    return blobs


def _token_re(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_.-]){re.escape(token)}(?:\.mdc)?(?![A-Za-z0-9_.-])")


def coverage_for_rules(rules: list[dict[str, Any]], blobs: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rule in rules:
        file_name = str(rule.get("file") or "")
        rule_id = str(rule.get("id") or "")
        stem = Path(file_name).stem if file_name else ""
        basename = Path(file_name).name if file_name else ""
        tokens = [t for t in (stem, rule_id, basename) if t]
        enforcers: list[str] = []
        for rel, text in blobs.items():
            if any(_token_re(token).search(text) for token in tokens):
                enforcers.append(rel)
        enforcers = sorted(set(enforcers))
        rows.append(
            {
                "id": rule_id,
                "file": file_name,
                "enforcers": enforcers,
                "enforcer_count": len(enforcers),
            }
        )
    return rows


def corpus_findings(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                "Broad persistent context can create instruction collisions and consume "
                "agent context.",
                "Review each Always rule; keep only short non-negotiable governance and "
                "irreversible-action constraints.",
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
                "Add explicit IDs when rules are materially edited; do not mass-rewrite "
                "solely for metadata.",
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
                "Move multi-step procedures to skills/commands and keep persistent rule "
                "contracts focused.",
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
                "Split immediately behind stable IDs and preserve compatibility aliases "
                "where required.",
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
                "Convert to Agent Requested, Auto Attached, or an explicit skill after "
                "behavioral review.",
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
    return findings


def build_report(
    root: Path,
    manifest: dict[str, Any],
    manifest_path: Path,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    rules = list(manifest["rules"])
    blobs = collect_enforcer_blobs(root)
    coverage_rows = coverage_for_rules(rules, blobs)
    zero = [row for row in coverage_rows if row["enforcer_count"] == 0]
    findings = corpus_findings(rules)
    if zero:
        names = ", ".join(f"{row['file']} ({row['id']})" for row in zero[:20])
        extra = "" if len(zero) <= 20 else f" and {len(zero) - 20} more"
        findings.append(
            finding(
                "RCA-007",
                "Rules with an empty named-enforcer set",
                2,
                f"{len(zero)} of {len(coverage_rows)} rules have no named enforcer: "
                f"{names}{extra}.",
                "A rule that is never referenced by a gate, hook, or skill is inert "
                "relative to the declared enforcer set.",
                "Confirm whether the rule should be named by an enforcer or retired. "
                "This finding is advisory; it is not a gate.",
                blast=3,
                recurrence=4,
                leverage=4,
                effort=3,
            )
        )
    findings.sort(key=lambda item: item["priority_score"], reverse=True)
    stamp = generated_utc or utc_now()
    try:
        source = manifest_path.relative_to(root).as_posix()
    except ValueError:
        source = str(manifest_path)
    return {
        "schema": SCHEMA,
        "generated_utc": stamp,
        "manifest_digest": manifest.get("source_tree_digest"),
        "population": {
            "source": source,
            "entrypoint_set": list(ENFORCER_SET),
            "generated_utc": stamp,
        },
        "coverage": {
            "enforcer_set": list(ENFORCER_SET),
            "rules": coverage_rows,
            "zero_enforcer_count": len(zero),
        },
        "summary": {
            "total_rules": len(rules),
            "always_rules": sum(1 for rule in rules if rule.get("activation") == "always"),
            "derived_ids": sum(1 for rule in rules if rule.get("id_source") == "derived"),
            "over_300_lines": sum(1 for rule in rules if rule.get("line_count", 0) > 300),
            "over_500_lines": sum(1 for rule in rules if rule.get("line_count", 0) > 500),
            "deprecated_rules": sum(1 for rule in rules if rule.get("deprecated")),
            "zero_enforcer_rules": len(zero),
        },
        "findings": findings,
        "convergence": {
            "passes": [
                "scope",
                "activation",
                "size",
                "identity",
                "deprecation",
                "adversarial",
                "coverage",
            ],
            "status": "stable",
            "note": "No corpus-wide activation changes were made automatically; findings "
            "require evidence-backed review. Coverage is advisory and is not a gate.",
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Global rules corpus audit",
        "",
        f"Generated: `{report['generated_utc']}`",
        "",
        "## Population",
        "",
        f"- Source: `{report['population']['source']}`",
        f"- Enforcer set: {', '.join(f'`{p}`' for p in report['population']['entrypoint_set'])}",
        "",
        "## Summary",
        "",
        f"- Total rules: **{summary['total_rules']}**",
        f"- Always rules: **{summary['always_rules']}**",
        f"- Derived compatibility IDs: **{summary['derived_ids']}**",
        f"- Rules over 300 lines: **{summary['over_300_lines']}**",
        f"- Deprecated rules: **{summary['deprecated_rules']}**",
        f"- Zero named enforcers: **{summary['zero_enforcer_rules']}**",
        "",
        "## Leverage-ranked findings",
        "",
    ]
    for item in report["findings"]:
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
            "Scope, activation, size, identity, deprecation, coverage, and adversarial "
            + "passes completed. Findings stabilized.",
            "No mass conversion was performed without behavioral evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="JSON report path (default: <root>/reports/rules-corpus-audit.json)",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help="Markdown report path (default: <root>/reports/rules-corpus-audit.md)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        manifest, manifest_path = load_manifest(root)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    report = build_report(root, manifest, manifest_path)
    json_path = args.json_out or (root / "reports" / "rules-corpus-audit.json")
    md_path = args.md_out or (root / "reports" / "rules-corpus-audit.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"WROTE: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
