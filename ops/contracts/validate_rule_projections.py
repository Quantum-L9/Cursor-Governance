#!/usr/bin/env python3
"""Independent assurance for generated contract-first Cursor rule projections."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = Path(__file__).resolve().parent / "adapters"
if str(ADAPTERS) not in sys.path:
    sys.path.insert(0, str(ADAPTERS))
from cursor_rules import (  # noqa: E402
    RuleBinding,
    discover_cursor_rules,
    discover_rule_bindings,
)
from render_cursor_rule import (  # noqa: E402
    enforce_context_budget,
    render_cursor_rule,
)
from resolve_rule_contracts import (  # noqa: E402
    load_contract_index,
    resolve_binding,
)

GENERATED_MARKER = "<!-- GENERATED FILE — DO NOT EDIT -->"
PROVENANCE_RE = re.compile(r"`\[(?P<contract>[A-Z][A-Z0-9_.]+):(?P<clause>[A-Za-z0-9_.-]+)\]`")
HARD_GUIDANCE_RE = re.compile(
    r"\b(?:MUST(?:\s+NOT)?|NEVER|PROHIBITED|FORBIDDEN|"
    r"REQUIRED|MANDATORY|STOP|FAIL[-\s]+CLOSED|SSOT|SOURCE\s+OF\s+TRUTH)\b",
    re.IGNORECASE,
)
NORMATIVE_SECTIONS = {
    "Required",
    "Prohibited",
    "Constraints",
    "Permissions",
    "Routing",
    "Evidence",
}


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.path}: {self.message}"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _section_lines(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1)
            sections.setdefault(current, [])
            continue
        if current:
            sections.setdefault(current, []).append(line)
    return sections


def _binding_expected(
    binding: RuleBinding,
    index: Any,
) -> tuple[dict[str, Any], str]:
    resolution = resolve_binding(binding, index)
    rendered = render_cursor_rule(resolution)
    metrics = enforce_context_budget(resolution, rendered)
    resolution["context"] = metrics
    return resolution, rendered


def validate_projection_set(
    root: Path = ROOT,
    registry_path: Path | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    bindings = discover_rule_bindings(root)
    index = load_contract_index(root, registry_path)
    expected_outputs: dict[str, tuple[RuleBinding, dict[str, Any], str]] = {}
    for binding in bindings:
        if binding.migration_state != "generated":
            continue
        try:
            resolution, rendered = _binding_expected(binding, index)
        except ValueError as exc:
            findings.append(
                Finding(
                    "RULE-PROJ-RESOLUTION",
                    binding.relative_path,
                    str(exc),
                )
            )
            continue
        expected_outputs[binding.output_path] = (
            binding,
            resolution,
            rendered,
        )
    actual_rules = {rule.relative_path: rule for rule in discover_cursor_rules(root)}
    for output_path, (binding, resolution, rendered) in expected_outputs.items():
        actual = actual_rules.get(output_path)
        if actual is None:
            findings.append(
                Finding(
                    "RULE-PROJ-MISSING",
                    output_path,
                    f"generated binding {binding.binding_id} has no tracked output",
                )
            )
            continue
        if GENERATED_MARKER not in actual.text:
            findings.append(
                Finding(
                    "RULE-PROJ-MARKER",
                    output_path,
                    "generated rule is missing generated-file marker",
                )
            )
        if actual.text != rendered:
            findings.append(
                Finding(
                    "RULE-PROJ-DRIFT",
                    output_path,
                    f"tracked digest {_sha256(actual.text)} differs from "
                    f"expected {_sha256(rendered)}",
                )
            )
        sections = _section_lines(actual.text)
        for section in NORMATIVE_SECTIONS:
            for line in sections.get(section, []):
                stripped = line.strip()
                if not stripped.startswith("- "):
                    continue
                match = PROVENANCE_RE.search(stripped)
                if match is None:
                    findings.append(
                        Finding(
                            "RULE-PROJ-PROVENANCE",
                            output_path,
                            f"{section} directive lacks contract-clause provenance: "
                            f"{stripped[:120]}",
                        )
                    )
                    continue
                contract_id = match.group("contract")
                clause_id = match.group("clause")
                record = index.records.get(contract_id)
                if record is None or clause_id not in record.clauses:
                    findings.append(
                        Finding(
                            "RULE-PROJ-PROVENANCE-UNRESOLVED",
                            output_path,
                            f"unresolved provenance {contract_id}:{clause_id}",
                        )
                    )
        for line in sections.get("Guidance", []):
            stripped = line.strip()
            if stripped.startswith("- ") and HARD_GUIDANCE_RE.search(stripped):
                findings.append(
                    Finding(
                        "RULE-PROJ-GUIDANCE-NORMATIVE",
                        output_path,
                        f"advisory guidance contains hard doctrine: {stripped[:120]}",
                    )
                )
        expected_binding = f"<!-- binding: {resolution['binding_id']} -->"
        expected_binding_digest = f"<!-- binding-sha256: {resolution['binding_digest']} -->"
        expected_bundle_digest = f"<!-- contract-bundle-sha256: {resolution['bundle_digest']} -->"
        for marker in (
            expected_binding,
            expected_binding_digest,
            expected_bundle_digest,
        ):
            if marker not in actual.text:
                findings.append(
                    Finding(
                        "RULE-PROJ-INTEGRITY-MARKER",
                        output_path,
                        f"missing or stale marker {marker}",
                    )
                )
    bound_outputs = set(expected_outputs)
    for rule in actual_rules.values():
        if GENERATED_MARKER in rule.text and rule.relative_path not in bound_outputs:
            findings.append(
                Finding(
                    "RULE-PROJ-ORPHAN",
                    rule.relative_path,
                    "generated rule has no active generated binding",
                )
            )
    return sorted(
        findings,
        key=lambda item: (item.path.casefold(), item.code, item.message),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    args = parser.parse_args()
    try:
        findings = validate_projection_set(args.root.resolve(), args.registry)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"RULE_PROJECTION_VALIDATION_ERROR: {exc}", file=sys.stderr)
        return 2
    if findings:
        print(f"FAIL ({len(findings)})")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("PASS: generated Cursor rule projections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
