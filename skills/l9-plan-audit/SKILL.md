---
name: l9-plan-audit
description: audit ~/.cursor/plans for unbuilt plans from the last 7 days, flag staleness, and surface findings at session start or via /plan-audit. use when session context shows Plan audit, the user asks which plans are unbuilt or stale, or /plan-audit is invoked. do not use to author new plans (use l9-plan-simple, or l9-plan for pe/campaign) or to auto-build plans.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, plan, audit, session-start, staleness, cursor-plans]
  owner: igor_beylin
  status: active
  version: 1.1.0
  updated: 2026-08-21
---

# l9-plan-audit

## Purpose

Deterministically scan the machine-global Cursor plans directory for **unbuilt**
plans modified in the last **7 days**, attach staleness flags, and emit a capped
markdown/JSON report. Scan **top-level** `*.plan.md` only — `built/`,
`backlog/`, and `archive/` are out of session-start. Frontmatter `built: true`
or `status` in `{built, completed, cancelled, superseded}` skips the plan even
when leftover todos are `pending`. SessionStart bootstrap inserts the markdown
under `### Plan audit` in `additional_context`. Findings are **display-only** —
do not auto-Build plans from this skill.

## Authority

1. Explicit user objective.
2. [references/staleness-rules.md](references/staleness-rules.md) (window, unbuilt, flags).
3. Scanner CLI [scripts/audit_plans.py](scripts/audit_plans.py).
4. SessionStart wiring in `ops/hooks/session_start_bootstrap.sh` (fail-open).

## Activation / Reject

**Activate** when session context includes Plan audit findings, the user asks
about unbuilt/stale plans, or `/plan-audit` runs.

**Reject** when the user wants a new plan (`l9-plan-simple` for Cursor Build,
`l9-plan` for PE/campaign), wants to execute a chosen plan (Build, or
`@environment/program-execution` + `/autonomy`), or asks to remediate
unrelated scanner drift outside the plans directory.

## Compact workflow

1. Resolve plans dir (workspace `.cursor/plans` → else `~/.cursor/plans`).
2. Run:

```bash
GOV="${HOME}/.cursor-governance"
[ -f "$GOV/skills/l9-plan-audit/scripts/audit_plans.py" ] || GOV="$(pwd)"
python3 "$GOV/skills/l9-plan-audit/scripts/audit_plans.py" \
  --workspace "${CURSOR_PROJECT_DIR:-$(pwd)}" \
  --window-days 7 \
  --format markdown \
  --budget-chars 1200 \
  --limit 5
```

3. Present findings as listed — do not invent plans the scanner omitted.
4. Optional next step: `/ynp` if the user wants a priority recommendation.

## Resource map

- [references/staleness-rules.md](references/staleness-rules.md)
- [scripts/audit_plans.py](scripts/audit_plans.py)
- [scripts/self_test.py](scripts/self_test.py)
- Slash: `commands/plan-audit.md`
- Hook: `ops/hooks/session_start_bootstrap.sh` → `### Plan audit`

## Validation

```bash
python3 scripts/self_test.py
```

## Failure handling

- Missing plans dir → report `plan audit: no plans dir` (exit 0).
- Parse errors on individual files → skip that file; continue.
- Hook path: stderr discarded; never fail sessionStart.
