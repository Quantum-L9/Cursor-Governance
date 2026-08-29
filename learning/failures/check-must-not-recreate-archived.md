# Lesson: a check must not recreate an archived or absent file

**Date:** 2026-08-28
**Donor:** `integrity/hash-verifier.py` `update_meta_audit` (deleted with the
Suite-6 healer)
**Owners today:** `sync_generated_artifacts.py`, sessionStart reconcilers,
`check_governance_wiring.sh`. Not a new integrity tool.

## Rule

A verifier, reporter, or health probe may read. It may write a gitignored
report. It must not create a path that is missing because it was archived,
retired, or never seeded.

## Why

`hash-verifier.py` used to append to `intelligence/meta-audit.md`. That file
was archived in the Suite-6 → L9 migration. Recreating it as a side effect of
an integrity check would have reintroduced governed-tree drift — the check
becoming the defect.

Existence of a checker is not permission to restore its old outputs.

## Wrong

- `mkdir` / write a retired `memory-bank/`, `meta-audit.md`, or Suite-6 log
  because a script still names the path
- Treat “file missing” as “seed the file” inside a verify path

## Right

- If the target is absent, skip or report `absent` / `not_seeded` and stop
- Restore retired content only through git / `governance_activate_fresh.sh`
- Generated artifacts are a different class: `sync_generated_artifacts.py`
  may rewrite **declared derived** files. It must not invent archived sources
