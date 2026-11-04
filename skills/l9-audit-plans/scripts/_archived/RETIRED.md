# Retired: shelf_plans.py

**Status:** retired 2026-11-03
**Replacement:** none. Plans stay where they are written.

## Why

`shelf_plans.py` moved `.plan.md` files between the plans-store root and
`partially-built/`, `built/`, `stale/`, and `archive/superseded/`. That move
ran whenever `/l9-audit-plans` ran. The plans store is no longer rearranged
by this script.

## What remains

`/l9-audit-plans` still runs `scripts/run_audit_plans.py`, which only refines
leftover todos already sitting in `stale/` or `built/`. It does not import
this module and it does not move files.

Running this file exits 2 and prints the retirement line. `shelf()` raises
the same refusal. Do not restore the mover.
