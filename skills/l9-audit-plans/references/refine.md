<!-- L9_META
l9_schema: 1
parent: l9-audit-plans
tags: [audit-plans, refine, status, harvested]
status: active
version: 1.0.0
/L9_META -->

# Plans-store refine

Invoke path (this skill only): shelf → refine → shelf → README live-queue.
SessionStart must not call refine. Kill switch: `L9_AUDIT_PLANS_REFINE=0`
(diagnose: shelf + display only).

`l9-intelligence-harvest` stays read-only. `scripts/refine_plans.py` is the
only fold/compile writer.

## Status (closed set)

Every `.plan.md` frontmatter must have `status`:

- `current` — live root only
- `partially-built` — `partially-built/`
- `built` — `built/` (same folder as `BUILT/` on macOS)
- `stale` — `stale/`
- `superseded` — `archive/superseded/`

`/l9-plan-simple` writes `status: current` on first draft. Shelf heals a root
file missing `status` to `current`. Leave-root rewrites `status` to the dest
folder. Do not write a parked status onto a live root file. Do not write
`status: harvested`.

## Harvested (tag, not a status)

After fold or compile: keep the folder `status`, set `harvested: true`, set
`compiled_into` to the plan survivor. Later invokes **omit** `harvested: true`
donors. `keep-started` is a slug merge, not harvest — do not tag the survivor
`harvested`. `other-repo` stays `stale` and is not tagged harvested.

## Dispositions (one per leftover todo on a non-harvested donor)

- `keep-started` — same slug already in `partially-built/`
- `fold` — append unique leftover todos onto an existing same-concern root or
  `partially-built` beneficiary
- `compile` — no beneficiary: one new `compiled: true` root packet per concern,
  `status: current`
- `other-repo` — stay `stale`, no harvested tag
- `drop-ident` — identical sibling (same todo content)

No `absorb`. Never drop a leftover todo because `AGENTS.md` already states it.
`uncategorized` never folds and never compiles.

## Live-queue rewrite

Replace only the numbered `` `name` `` lines under `## Live queue` from remaining
root `.plan.md` files (exclude `_TEMPLATE.plan.md`). Do not restack live store
files during a Build that only changes this skill pack.
