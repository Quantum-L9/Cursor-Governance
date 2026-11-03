#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from paths import safe_cli_path


def _bullets(items: list) -> list[str]:
    return [f"- {item}" for item in items]


def _pre_validation_table(plan: dict) -> list[str]:
    lines = [
        "### Pre-Validation (mandatory)",
        "| Check | Command / action | Pass criteria | Status |",
        "|-------|------------------|---------------|--------|",
    ]
    for row in plan.get("pre_validation") or []:
        lines.append(
            "| {id} | {action} | {criteria} | {status} |".format(
                id=row.get("id"),
                action=row.get("command_or_action"),
                criteria=row.get("pass_criteria"),
                status=row.get("status"),
            )
        )
    return lines


def _todo_table(plan: dict) -> list[str]:
    lines = [
        "### TODO Plan",
        "| # | Task | Files | Effort | Risk | Deps | Leverage |",
        "|---|------|-------|--------|------|------|----------|",
    ]
    for t in plan.get("todos") or []:
        lines.append(
            f"| {t.get('id')} | {t.get('task')} | {', '.join(t.get('files') or [])} | "
            f"{t.get('effort')} | {t.get('risk')} | {', '.join(t.get('dependencies') or [])} | "
            f"{t.get('leverage_rank')} |"
        )
    return lines


def _stress_section(plan: dict) -> list[str]:
    stress = plan.get("stress_test") or {}
    lines = ["### Stress Test"]
    lines.extend(
        _bullets(f"Disconfirming: {q}" for q in stress.get("disconfirming_questions") or [])
    )
    lines.append(f"- Blast radius: {stress.get('blast_radius')}")
    lines.append(f"- Rollback: {stress.get('rollback')}")
    return lines


def render(plan: dict) -> str:
    scope = plan.get("scope") or {}
    lev = plan.get("leverage") or {}
    conv = plan.get("convergence") or {}
    lines = [
        f"## PLAN: {plan.get('title', '')}",
        "",
        "### Objective",
        str(plan.get("objective", "")),
        "**Success:**",
        *_bullets(plan.get("success_criteria") or []),
        "",
        "### Scope",
        f"**In:** {', '.join(scope.get('in') or [])}",
        f"**Out:** {', '.join(scope.get('out') or [])}",
        "",
        *_pre_validation_table(plan),
        "",
        *_todo_table(plan),
        "",
        "### Critical Path",
        " -> ".join(plan.get("critical_path") or []),
        "",
        *_stress_section(plan),
        "",
        "### Leverage",
        f"- Ranked: {', '.join(lev.get('ranked_todo_ids') or [])}",
        "",
        "### Convergence",
        f"- status: {conv.get('status')}",
        f"- next_skill: {conv.get('next_skill')}",
        f"- stop_reason: {conv.get('stop_reason')}",
        "",
        "_Projection of PLAN_DOCUMENT — validate JSON before treating as ready._",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: render_plan_markdown.py <plan.json>", file=sys.stderr)
        return 2
    plan = json.loads(safe_cli_path(sys.argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(render(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
