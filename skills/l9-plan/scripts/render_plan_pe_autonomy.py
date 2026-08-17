#!/usr/bin/env python3
"""Project PLAN_DOCUMENT JSON into a Cursor .plan.md (PE + autonomy template).

Keeps scripts/render_plan_markdown.py as the legacy GMP-section renderer.
Default for l9-plan / /plan is this projector + first-class SSOT
environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md
(skill references/executable-plan.pe-autonomy.template.md is a symlink).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from paths import safe_cli_path

# Skill path is a symlink; prefer resolving the first-class git SSOT.
TEMPLATE_REL = Path("references/executable-plan.pe-autonomy.template.md")
SSOT_REL = Path(
    "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
)


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "plan").strip().lower()).strip("-")
    return cleaned or "plan"


def _hex8(plan: dict) -> str:
    raw = json.dumps(plan, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:8]


def _todo_rows(plan: dict) -> list[dict]:
    rows: list[dict] = []
    for t in plan.get("todos") or []:
        tid = str(t.get("id") or "todo")
        content = str(t.get("task") or t.get("content") or tid)
        deps = t.get("dependencies") or t.get("depends_on") or []
        if not isinstance(deps, list):
            deps = []
        rows.append(
            {
                "id": tid,
                "content": content,
                "status": "pending",
                "depends_on": [str(d) for d in deps],
                "phase": str(t.get("phase") or "execute"),
            }
        )
    return rows


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def _frontmatter(plan: dict) -> str:
    title = str(plan.get("title") or "Untitled plan")
    overview = str(plan.get("objective") or title).replace("\n", " ").strip()
    if len(overview) > 400:
        overview = overview[:397] + "..."
    todos = _todo_rows(plan)
    lines = [
        "---",
        f"name: {title}",
        f'overview: "{overview.replace(chr(34), chr(39))}"',
        "todos:",
    ]
    if not todos:
        lines.append("  []")
    for t in todos:
        lines.append(f"  - id: {t['id']}")
        content = t["content"].replace('"', "'")
        lines.append(f'    content: "{content}"')
        lines.append("    status: pending")
        lines.append(f"    phase: {t['phase']}")
        lines.append(f"    depends_on: {_yaml_list(t['depends_on'])}")
    lines.append("isProject: false")
    lines.append("---")
    return "\n".join(lines)


def _success_table(plan: dict) -> list[str]:
    lines = [
        "| id | property | evidence_type | proof | blocking |",
        "|----|----------|---------------|-------|----------|",
    ]
    criteria = plan.get("success_criteria") or []
    for i, c in enumerate(criteria, start=1):
        lines.append(
            f"| SP-{i:02d} | {c} | quality_gate | observe during PE verify / make pr | true |"
        )
    if not criteria:
        lines.append(
            "| SP-01 | REPLACE | repository_state | git rev-parse HEAD == locked SHA | true |"
        )
    return lines


def _scope_out(plan: dict) -> list[str]:
    scope = plan.get("scope") or {}
    out = list(scope.get("out") or [])
    if not out:
        out = ["Adjacent work not listed in execution envelope"]
    return [f"- {item}" for item in out]


def render(plan: dict, template_text: str) -> str:
    """Fill a minimal executable head from JSON; append template body as fill guide."""
    title = str(plan.get("title") or "Untitled plan")
    scope = plan.get("scope") or {}
    conv = plan.get("convergence") or {}
    stress = plan.get("stress_test") or {}
    critical = " → ".join(
        plan.get("critical_path") or [t.get("id", "") for t in (plan.get("todos") or [])]
    )

    body = template_text
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].lstrip("\n")

    body = re.sub(r"^# PLAN:.*$", f"# PLAN: {title}", body, count=1, flags=re.M)

    head = [
        _frontmatter(plan),
        "",
        f"# PLAN: {title}",
        "",
        "> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.",
        "> **Template SSOT:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`",
        "> **Execute:** `@environment/program-execution` → Program Lock/Controller → `@autonomy` (subordinate).",
        f"> **Suggested filename:** `{_slug(title)}_{_hex8(plan)}.plan.md`",
        "",
        "## Objective (from PLAN_DOCUMENT)",
        "",
        str(plan.get("objective") or ""),
        "",
        "### Success properties (seed — complete evidence_type/proof in template sections)",
        "",
        *_success_table(plan),
        "",
        "## Scope (from PLAN_DOCUMENT)",
        "",
        f"**In:** {', '.join(scope.get('in') or [])}",
        "",
        "**Out:**",
        *_scope_out(plan),
        "",
        "## Critical path (seed)",
        "",
        critical or "_fill from execution_DAG_",
        "",
        "## Stress (seed from PLAN_DOCUMENT)",
        "",
        f"- Blast radius: {stress.get('blast_radius', '_fill_')}",
        f"- Rollback: {stress.get('rollback', '_fill_')}",
        "",
        "## Convergence (seed)",
        "",
        f"- status: {conv.get('status', 'draft')}",
        f"- next_skill: {conv.get('next_skill', '/autonomy + @environment/program-execution')}",
        f"- stop_reason: {conv.get('stop_reason', '')}",
        "- execute_via: @environment/program-execution → @autonomy",
        "",
        "---",
        "",
        "## Template body (complete every required section before status=executable)",
        "",
        body,
    ]
    return "\n".join(head) + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: render_plan_pe_autonomy.py <plan.json> [template.md]",
            file=sys.stderr,
        )
        return 2
    plan_path = safe_cli_path(sys.argv[1])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_root = Path(__file__).resolve().parents[1]
    repo_root = skill_root.parents[1]
    if len(sys.argv) > 2:
        template_path = safe_cli_path(sys.argv[2])
    else:
        ssot = (repo_root / SSOT_REL).resolve()
        if ssot.is_file() and repo_root.resolve() in ssot.parents:
            template_path = ssot
        else:
            # Symlink under skill pack (confined to cwd when run from skill root)
            template_path = safe_cli_path(str(TEMPLATE_REL))
    template_text = template_path.read_text(encoding="utf-8")
    sys.stdout.write(render(plan, template_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
