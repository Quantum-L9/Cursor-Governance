# Environment Experience Improvement Pack — Canonical

## What this pack is

A reconciled, provenance-backed canonicalization of the `environment_experience_improvement_pack` family. It consolidates nine unique accessible observations across multiple L9 sessions/repositories, removes two byte-identical duplicate copies, preserves context-specific findings, and merges recurring environment failures/friction/improvements only where the evidence supports shared identity.

## What was reconciled

- **Versions discovered:** 11 accessible archive copies
- **Unique versions included:** 9
- **Duplicate copies removed from the active surface:** 2
- **Source objects processed:** 93
- **Referenced but not independently bound predecessor:** 1 (`environment_experience_improvement_pack.zip` generated 2026-08-24T01:18Z, referenced by Pack 9)

The packs are mostly parallel observations, not nine linear edits. Pack 9 explicitly supersedes the referenced 01:18 predecessor. Accessible Pack 3 is a high-confidence likely representation or neighboring export of that predecessor, but exact identity is left UNKNOWN because the reported byte sizes differ.

## Canonical structure

- `ARCHITECTURE.md` — reconciled control-system boundaries and dependency direction
- `LAWS_AND_INVARIANTS.md` — evidence-derived safety/ownership/freshness invariants
- `EXPERIENCE_REPORT.md` — human synthesis
- `FRICTION_AND_FAILURES.md` — recurring and context-specific defects
- `IMPROVEMENT_PLAN.md` — current dependency-ordered forward work only
- `environment_inventory.yaml` — cross-session environment/capability model
- `experience.yaml`, `failures.yaml`, `friction.yaml`, `improvements.yaml` — canonical machine records
- `OPEN_DECISIONS.yaml` — unresolved decisions/unknowns
- `_reconciliation/` — corpus, lineage, semantic actions, completeness, conflicts, and source map

## Architecture summary

The converged model separates repository ownership, environment authority, bootstrap lifecycle, capability transport, governance execution, safety gates, continuity, and validation. The most damaging recurring seam is coarse state: one-word `READY`/`DEGRADED` or blanket tool claims hide transport-specific and ownership-specific reality.

## Current status

**CANONICAL_PACK_RECONCILED_WITH_OPEN_CONFLICTS.** No conflict was silently resolved. The forward roadmap is current; the one source improvement explicitly marked already applied is retained as completed and not rescheduled.

## Current roadmap

Start with ownership-safe bootstrap projection (`CI-002`), fresh/re-probed bootstrap receipts (`CI-004`), authority-sensitive drift provenance (`CI-006`), project toolchain authority (`CI-009`), and the GitHub REST/GraphQL contract (`CI-001`). Then repair stop-hook semantics, memory continuity, publish-command contract, broker/JWT diagnostics, and gate ergonomics.

## Open decisions

See `OPEN_DECISIONS.yaml`. Re-checked 2026-08-27 against `main@498dcaa`:

- **OD-002, the canonical `make pr` contract — RESOLVED** by PR#307 (CI-008), and neither branch of the original question won: the governance Makefile is the publish authority regardless of the repo worked in, a consumer needs no `pr` target, and there is no raw-push fallback.
- **OD-001, the authoritative `AUTONOMOUS_MERGE` value — NARROWED.** The contradiction that opened it cleared (the live value is now `false`, which is what the verifier expects); what remains is the narrower policy question of whether the variable should exist at all.
- Still open: broker failure cause, missing session JWT cause, memory writeback warning, exact identity of the Pack 9 predecessor, and publish-override origin/lifecycle.

## Provenance

Every final artifact maps back to source versions/paths in `_reconciliation/SOURCE_MAP.yaml`. Every source object has a disposition in `_reconciliation/COMPLETENESS_MATRIX.yaml`. Reconciliation choices and partial supersessions are in `_reconciliation/RECONCILIATION_LEDGER.yaml`; conflicts are in `_reconciliation/CONFLICTS.yaml`.


---

## Progress overlay (2026-08-27)

This is a **revised** pack: every improvement record now carries a `progress` block (done / partial / not_started), assessed against **main@498dcaa (post-#307-merge + 47 commits) + PR#320 open**. See [`PROGRESS.md`](PROGRESS.md) (human) and [`progress.yaml`](progress.yaml) (machine); per-record detail is under each entry's `progress:` key in `improvements.yaml`.

Totals: **3 done · 14 partial · 19 not started** of 36. Two new records (CI-034, CI-035) and one progress-schema change are proposed, not yet adopted — see `PROGRESS.md`. Two new records (CI-034, CI-035) and one progress-schema change are proposed, not yet adopted — see `PROGRESS.md`.
