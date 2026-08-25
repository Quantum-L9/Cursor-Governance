---
name: l9-plan-audit
description: sessionStart scanner for unbuilt plans in the last 7 days under the live plans-store root. use when session context shows Plan audit. do not use to author plans (l9-plan-simple / l9-plan) or to shelf the store (that is /l9-audit-plans). do not auto-build plans.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, plan, audit, session-start, staleness, cursor-plans]
  owner: igor_beylin
  status: active
  version: 1.1.0
  updated: 2026-08-23
---

# l9-plan-audit

## Purpose

Deterministically scan the machine-global Cursor plans directory for **unbuilt**
plans modified in the last **7 days**, attach staleness flags, and emit a capped
markdown/JSON report. Scan **top-level** `*.plan.md` only — `built/`,
`partially-built/`, `backlog/`, and `archive/` are out of session-start. Frontmatter `built: true`
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

**Activate** when session context includes Plan audit findings, or the user
asks which **live-queue** (root) plans are unbuilt or stale.

**Reject** when the user wants `/l9-audit-plans` or store organize (that
protocol is `commands/l9-audit-plans.md`), wants a new plan (`l9-plan-simple`
/ `l9-plan`), wants to execute a chosen plan (Build or PE+autonomy), or asks
to remediate scanner drift outside the plans directory.

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
- Slash (store organize, not this skill): `commands/l9-audit-plans.md`
- Hook: `ops/hooks/session_start_bootstrap.sh` → `### Plan audit`

## Validation

```bash
python3 scripts/self_test.py
```

## Failure handling

- Missing plans dir → report `plan audit: no plans dir` (exit 0).
- Parse errors on individual files → skip that file; continue.
- Hook path: stderr discarded; never fail sessionStart.
