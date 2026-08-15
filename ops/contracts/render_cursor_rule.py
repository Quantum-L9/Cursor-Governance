#!/usr/bin/env python3
"""Deterministically render a resolved contract bundle into Cursor .mdc."""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "ops" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from lib.rule_frontmatter import emit_native_frontmatter  # noqa: E402

SECTION_BY_EFFECT = {
    "require": "Required",
    "prohibit": "Prohibited",
    "constrain": "Constraints",
    "stop": "Required",
    "permit": "Permissions",
    "route": "Routing",
    "attest": "Evidence",
}
SECTION_ORDER = (
    "Required",
    "Prohibited",
    "Constraints",
    "Permissions",
    "Routing",
    "Evidence",
)


def _human(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text)


def render_directive(directive: dict[str, Any]) -> str:
    parameters = directive.get("parameters")
    if isinstance(parameters, dict):
        projection_text = parameters.get("projection_text")
        if isinstance(projection_text, str) and projection_text.strip():
            sentence = projection_text.strip()
        else:
            sentence = ""
    else:
        sentence = ""
    if not sentence:
        subject = _human(directive.get("subject")) or "The governed actor"
        action = _human(directive.get("action"))
        obj = _human(directive.get("object"))
        tail = " ".join(part for part in (action, obj) if part).strip()
        effect = str(directive.get("effect") or "")
        if effect == "require":
            sentence = f"{subject} MUST {tail}."
        elif effect == "prohibit":
            sentence = f"{subject} MUST NOT {tail}."
        elif effect == "permit":
            sentence = f"{subject} MAY {tail}."
        elif effect == "constrain":
            sentence = f"{subject} MUST satisfy this constraint: {tail}."
        elif effect == "stop":
            sentence = f"STOP when {subject} would {tail}."
        elif effect == "route":
            sentence = f"{subject} MUST route through {tail}."
        elif effect == "attest":
            sentence = f"{subject} MUST provide evidence for {tail}."
        else:
            raise ValueError(
                f"unsupported normative effect {effect!r} for "
                f"{directive.get('contract_id')}:{directive.get('clause_id')}"
            )
    conditions = [_human(item) for item in directive.get("conditions") or [] if _human(item)]
    exceptions = [_human(item) for item in directive.get("exceptions") or [] if _human(item)]
    additions: list[str] = []
    if conditions:
        additions.append("Conditions: " + "; ".join(conditions))
    if exceptions:
        additions.append("Exceptions: " + "; ".join(exceptions))
    if additions:
        sentence = f"{sentence} {' '.join(additions)}"
    provenance = f"[{directive['contract_id']}:{directive['clause_id']}]"
    return f"- {sentence} `{provenance}`"


def _frontmatter(resolution: dict[str, Any]) -> str:
    identity = resolution["rule_identity"]
    activation = resolution["activation"]
    mode = str(activation.get("mode") or "")
    metadata: dict[str, Any] = {
        "description": str(activation.get("description") or identity.get("description") or ""),
        "alwaysApply": mode == "always",
    }
    if mode == "auto_attached":
        metadata["globs"] = activation.get("globs") or []
    native = emit_native_frontmatter(metadata)
    native_lines = native.splitlines()
    extended = [
        f"id: {identity['rule_id']}",
        f"version: {identity['rule_version']}",
        f"scope: {identity['scope']}",
        f"activation: {mode}",
        f"domain: {identity['domain']}",
        "authority: reference_only",
    ]
    return "\n".join(
        [
            native_lines[0],
            *native_lines[1:-1],
            *extended,
            native_lines[-1],
            "",
        ]
    )


def render_cursor_rule(resolution: dict[str, Any]) -> str:
    identity = resolution["rule_identity"]
    directives = resolution["directives"]
    grouped: dict[str, list[str]] = {section: [] for section in SECTION_ORDER}
    for directive in directives:
        effect = str(directive.get("effect") or "")
        section = SECTION_BY_EFFECT.get(effect)
        if section is None:
            raise ValueError(f"unsupported directive effect: {effect!r}")
        grouped[section].append(render_directive(directive))
    lines = [
        _frontmatter(resolution).rstrip(),
        "",
        "<!-- GENERATED FILE — DO NOT EDIT -->",
        f"<!-- binding: {resolution['binding_id']} -->",
        f"<!-- binding-sha256: {resolution['binding_digest']} -->",
        f"<!-- contract-bundle-sha256: {resolution['bundle_digest']} -->",
        "",
        f"# {identity['title']}",
        "",
        "## Governing contracts",
        "",
    ]
    for contract in resolution["resolved_contracts"]:
        clause_list = ", ".join(contract["clauses"])
        lines.append(
            f"- `{contract['contract_id']}@{contract['version']}` — clauses `{clause_list}`"
        )
    for section in SECTION_ORDER:
        values = grouped[section]
        if not values:
            continue
        lines.extend(["", f"## {section}", "", *values])
    guidance = resolution.get("guidance")
    if isinstance(guidance, dict):
        inline = guidance.get("inline")
        refs = guidance.get("refs")
        if inline:
            lines.extend(["", "## Guidance", ""])
            for item in inline:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if text:
                    lines.append(f"- {text}")
        if refs:
            lines.extend(["", "### Guidance references", ""])
            for reference in refs:
                lines.append(f"- `{reference}`")
    rendered = "\n".join(lines).rstrip() + "\n"
    return rendered


def measure_rendered_rule(text: str) -> dict[str, int]:
    byte_count = len(text.encode("utf-8"))
    return {
        "measured_bytes": byte_count,
        "token_estimate": math.ceil(byte_count / 4),
    }


def enforce_context_budget(
    resolution: dict[str, Any],
    rendered: str,
) -> dict[str, int]:
    metrics = measure_rendered_rule(rendered)
    render = resolution.get("render")
    if not isinstance(render, dict):
        raise ValueError("resolution missing render configuration")
    budget = render.get("context_budget_bytes")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
        raise ValueError("context_budget_bytes must be a positive integer")
    if metrics["measured_bytes"] > budget:
        raise ValueError(
            f"{resolution['binding_id']}: rendered rule is "
            f"{metrics['measured_bytes']} bytes, exceeding budget {budget}"
        )
    return {
        **metrics,
        "budget_bytes": budget,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("resolution", type=Path)
    args = parser.parse_args()
    try:
        loaded = yaml.safe_load(args.resolution.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("resolution must be a mapping")
        rendered = render_cursor_rule(loaded)
        enforce_context_budget(loaded, rendered)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"RULE_RENDER_ERROR: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
