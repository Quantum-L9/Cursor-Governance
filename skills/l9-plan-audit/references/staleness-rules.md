<!-- L9_META
l9_schema: 1
parent: l9-plan-audit
tags: [plan, audit, staleness, session-start]
status: active
version: 1.1.0
updated: 2026-08-21
/L9_META -->

# Plan audit staleness rules

Authoritative rules for `scripts/audit_plans.py` and its self-test.

## Scan root

1. If `--plans-dir` is set, use it.
2. Else if `<workspace>/.cursor/plans` exists, use it (usually a symlink to `~/.cursor/plans`).
3. Else `$HOME/.cursor/plans`.

Always exclude `_TEMPLATE.plan.md`. Scan **top-level** `*.plan.md` only.
Subfolders are out of the session-start set (see `docs/plans/README.md`):

| Folder | Meaning |
|---|---|
| *(root)* | Live queue — last-7-day unbuilt plans |
| `backlog/` | Open work, parked |
| `built/` | Executed plans |
| `archive/` | Non-plan harvest and other dead weight |
| `archive/superseded/` | Older same-slug copies or body `status: superseded` |

## Window

Include a plan only when filesystem **mtime** is within `--window-days` (default **7**).
Body `created_at` / `updated_at` are ignored (almost never filled in the live corpus).

## Unbuilt

A plan is **unbuilt** when any of:

- frontmatter `todos` is missing or `[]`
- any todo has `status` in `{pending, in_progress}`

Skip when every todo is `completed` or `cancelled` (and todos is non-empty).

Skip (treat as built/stale, do not highlight) when frontmatter has `built: true`
or `status` in `{built, completed, cancelled, superseded}`. These markers win
over todo inference so a Built plan with leftover `pending` todos, or a
superseded copy, does not appear in session-start Plan audit.

## Staleness flags (additive)

| Flag | When |
|------|------|
| `empty_todos` | `todos` missing or empty |
| `in_progress` | at least one todo `status: in_progress` |
| `baseline_drift` | body contains `immutable_baseline` / `commit_sha` and the SHA ≠ open workspace `HEAD` (when HEAD available) |
| `superseded` | body Metadata `status: superseded`, **or** a newer same-slug `name_M-D-YY.plan.md` (historical ISO `name_YYYY-MM-DD` and `name_<8hex>` still match) exists in the plans dir |
| `missing_execute_section` | body lacks a heading containing `Execute via @environment/program-execution` |

## Output budget

- Default markdown budget: **1200** characters
- Default limit: **5** plans, newest mtime first
- Soft failures (missing dir, parse errors): exit **0** with an explicit none/skipped line
- SessionStart must remain fail-open; never raise into the bootstrap
