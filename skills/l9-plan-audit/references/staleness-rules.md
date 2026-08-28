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
| *(root)* | Live queue — current unbuilt plans |
| `partially-built/` | Started but not finished (`completed` / `in_progress` todos remain) |
| `backlog/` | Open unbuilt work, parked |
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

`compiled: true` is **not** a skip. A compiled plan with pending todos stays
unbuilt and on the live queue. Donors keep their own shelf until a harvest
receipt stamps `compiled_into`; do not treat a mixed plan as wholly superseded.

## Component verdicts (not pass/fail)

A plan may hold more than one verdict. SessionStart stays display-only.

| Verdict | Meaning |
|---|---|
| `live_invariant` | Success property, pending todo, or compiled packet still in force |
| `stale_wiring` | PE execute heading missing, kernel unfired, or baseline drift |
| `superseded_mission` | Whole-file `status: superseded` or older same-slug |
| `spent` | All todos `completed` / `cancelled` |

`harvestable` is true when at least one `live_invariant` and at least one
`stale_wiring` or `superseded_mission` share the same file. `/l9-audit-plans`
lists those components by concern. It does not auto-compile and does not
`git mv` a mixed plan to `archive/superseded/`.

Harvest of invariants is `scripts/harvest_plan_invariants.py` (Gold Nugget
kernel cited by path; no implementation; not `l9-harvest-pipeline`).

## Staleness flags (additive)

| Flag | When |
|------|------|
| `empty_todos` | `todos` missing or empty |
| `in_progress` | at least one todo `status: in_progress` |
| `baseline_drift` | body contains `immutable_baseline` / `commit_sha` and the SHA ≠ open workspace `HEAD` (when HEAD available) |
| `superseded` | body Metadata `status: superseded`, **or** a newer same-slug `name_M-D-YY.plan.md` (historical ISO `name_YYYY-MM-DD` and `name_<8hex>` still match) exists in the plans dir |
| `missing_execute_section` | **PE-kind only:** body lacks a heading containing `Execute via @environment/program-execution`. PE-kind is the default. Simple-kind (`kind: simple` or `execute_via: cursor-build` in frontmatter, and body has no *live* `make campaign` command / live PE execute heading) must not get this flag. Required prohibition sentences such as `Do not run make campaign` are not live wiring. |
| `kernel_unfired` | `validate_plan_kernel_receipt.py` FAILs on this unbuilt `.plan.md` |
| `harvestable` | Mixed verdicts: live invariants plus stale wiring or a superseded mission |

## Output budget

- Default markdown budget: **1200** characters
- Default limit: **5** plans, newest mtime first
- Soft failures (missing dir, parse errors): exit **0** with an explicit none/skipped line
- SessionStart must remain fail-open; never raise into the bootstrap
