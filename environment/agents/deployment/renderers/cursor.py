# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/deployment/renderers/cursor.py
#   layer: library
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-12
"""Deterministic Cursor-native renderer for governed subagent roles.

Frontmatter is restricted to Cursor-supported fields. L9 provenance lives in a
managed HTML-comment block in the body (custom frontmatter is not used).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any

RENDERER_VERSION = "1.0.0"
MANAGED_MARKER = "L9_MANAGED_SUBAGENT"

ROLE_FILENAMES: dict[str, str] = {
    "recon": "l9-recon.md",
    "pr_remediation": "l9-pr-remediation.md",
    "test": "l9-test.md",
    "documentation": "l9-documentation.md",
    "verifier_reviewer": "l9-verifier-reviewer.md",
}

ROLE_AGENT_NAMES: dict[str, str] = {
    "recon": "l9-recon",
    "pr_remediation": "l9-pr-remediation",
    "test": "l9-test",
    "documentation": "l9-documentation",
    "verifier_reviewer": "l9-verifier-reviewer",
}

_PROVENANCE_RE = re.compile(
    rf"<!--\s*{MANAGED_MARKER}\n(?P<body>.*?)\n-->",
    re.DOTALL,
)


def content_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_managed(text: str) -> bool:
    return parse_managed_provenance(text) is not None


def parse_managed_provenance(text: str) -> dict[str, str] | None:
    match = _PROVENANCE_RE.search(text)
    if match is None:
        return None
    result: dict[str, str] = {}
    for line in match.group("body").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    if result.get("managed") != "true":
        return None
    return result


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _bool_yaml(value: bool) -> str:
    return "true" if value else "false"


def _description_for(role_key: str, role: Mapping[str, Any]) -> str:
    responsibilities = role.get("responsibilities") or []
    focus = ", ".join(str(item).replace("_", " ") for item in responsibilities[:3])
    mutation = role.get("mutation")
    mutation_note = {
        False: "read-only",
        True: "mutating",
        "bounded": "bounded mutation",
    }.get(mutation, str(mutation))
    base = f"L9 governed {role_key.replace('_', '-')} subagent ({mutation_note}). Use for: {focus}."
    if role.get("must_be_independent_from_subject_agent"):
        base += " Must remain independent from the subject agent under review."
    return base


def _format_mutation(value: Any) -> str:
    if value is False:
        return "false"
    if value is True:
        return "true"
    return str(value)


def _system_prompt(role_key: str, role: Mapping[str, Any]) -> str:
    lines = [
        f"You are the L9 governed Cursor subagent role `{role_key}`.",
        "",
        "Authority boundaries:",
        f"- autonomy_role: {role.get('autonomy_role')}",
        f"- cursor_subagent_type: {role.get('cursor_subagent_type')}",
        f"- mutation: {_format_mutation(role.get('mutation'))}",
        f"- result_kind: {role.get('result_kind')}",
        f"- generated_data_role: {role.get('generated_data_role')}",
        "",
        "Responsibilities:",
    ]
    for item in role.get("responsibilities") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Prohibited:")
    for item in role.get("prohibited") or []:
        lines.append(f"- {item}")
    if role.get("must_be_independent_from_subject_agent"):
        lines.extend(
            [
                "",
                "Independence: you must not review your own work and must name the subject agent.",
            ]
        )
    lines.extend(
        [
            "",
            "Return exactly one structured result document matching the role's result_kind.",
            "Do not schedule work, accept peer results, or mutate Program Execution state.",
        ]
    )
    return "\n".join(lines)


def render_role(
    role_key: str,
    role: Mapping[str, Any],
    *,
    source_rel: str,
    role_schema: str,
    source_digest: str,
    renderer_version: str = RENDERER_VERSION,
) -> str:
    """Render one Cursor agent markdown definition deterministically."""
    if role_key not in ROLE_FILENAMES:
        raise KeyError(f"unsupported role key: {role_key}")

    name = ROLE_AGENT_NAMES[role_key]
    readonly = role.get("mutation") is False
    is_background = bool(role.get("default_background", True))
    description = _description_for(role_key, role)

    frontmatter = "\n".join(
        [
            "---",
            f"name: {name}",
            f"description: {_yaml_quote(description)}",
            "model: inherit",
            f"readonly: {_bool_yaml(readonly)}",
            f"is_background: {_bool_yaml(is_background)}",
            "---",
        ]
    )

    provenance = "\n".join(
        [
            f"<!-- {MANAGED_MARKER}",
            "managed: true",
            f"role: {role_key}",
            f"source: {source_rel}",
            f"role_schema: {role_schema}",
            f"source_digest: {source_digest}",
            f"renderer_version: {renderer_version}",
            "-->",
        ]
    )

    body = _system_prompt(role_key, role)
    return f"{frontmatter}\n\n{provenance}\n\n{body}\n"


def expected_definitions(
    roles: Mapping[str, Any],
    *,
    source_rel: str,
    role_schema: str,
    source_digest: str,
    renderer_version: str = RENDERER_VERSION,
) -> dict[str, str]:
    """Map filename -> rendered markdown for every role in the manifest."""
    out: dict[str, str] = {}
    for role_key in sorted(ROLE_FILENAMES):
        if role_key not in roles:
            raise KeyError(f"roles manifest missing required role: {role_key}")
        filename = ROLE_FILENAMES[role_key]
        out[filename] = render_role(
            role_key,
            roles[role_key],
            source_rel=source_rel,
            role_schema=role_schema,
            source_digest=source_digest,
            renderer_version=renderer_version,
        )
    return out
