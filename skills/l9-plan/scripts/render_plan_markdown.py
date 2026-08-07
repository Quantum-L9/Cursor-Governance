#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def render(plan: dict) -> str:
    lines = [
        f"## PLAN: {plan.get('title', '')}",
        "",
        "### Objective",
        str(plan.get("objective", "")),
        "**Success:**",
    ]
    for c in plan.get("success_criteria") or []:
        lines.append(f"- {c}")
    scope = plan.get("scope") or {}
    lines += [
        "",
        "### Scope",
        f"**In:** {', '.join(scope.get('in') or [])}",
        f"**Out:** {', '.join(scope.get('out') or [])}",
        "",
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
    lines += [
        "",
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
    lines += ["", "### Critical Path", " -> ".join(plan.get("critical_path") or []), ""]
    stress = plan.get("stress_test") or {}
    lines.append("### Stress Test")
    for q in stress.get("disconfirming_questions") or []:
        lines.append(f"- Disconfirming: {q}")
    lines.append(f"- Blast radius: {stress.get('blast_radius')}")
    lines.append(f"- Rollback: {stress.get('rollback')}")
    lev = plan.get("leverage") or {}
    lines += [
        "",
        "### Leverage",
        f"- Ranked: {', '.join(lev.get('ranked_todo_ids') or [])}",
    ]
    conv = plan.get("convergence") or {}
    lines += [
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
    plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(render(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
