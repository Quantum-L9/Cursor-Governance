---
name: l9-git-work-preserve
description: diagnose-first audit extract and prune-propose for unpushed dirty orphan stale and stash git work. use when cleaning branches worktrees or stashes never lose unique commits without receipts and auth.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, git, worktree, stash, diagnose-first, preserve, prune]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-08-14
disable-model-invocation: true
---

# Git Work Preserve (L9)

## Purpose

Inventory git work with evidence receipts; extract unique value safely; propose prune only after Diagnose-First. Default is **report-only**. Never treat age as worthlessness.

## Core Contract

| Mode | Mutates? | Output |
|------|----------|--------|
| `audit` (default) | No | JSON + summary: unpushed, dirty, worktrees, orphans, stale, stashes |
| `diagnose-value` | No | Per-ref diagnosis receipt vs `origin/main` |
| `extract` | Local only | New branch/worktree + surgical commits; never deletes source ref |
| `prune-propose` | No | Delete candidates + required receipts + copy-paste commands |
| `prune-execute` | Yes | Only with user auth **and** `L9_GIT_PRUNE_AUTHORIZED=<reason>` |

Load detail: [references/audit-workflow.md](references/audit-workflow.md), [references/value-diagnosis.md](references/value-diagnosis.md), [references/extract-workflow.md](references/extract-workflow.md), [references/prune-policy.md](references/prune-policy.md), [references/stash-deep-analysis.md](references/stash-deep-analysis.md).

## Authority Order

1. Explicit user objective and auth env flags.
2. [references/diagnose-first-binding.md](references/diagnose-first-binding.md) + CANONICAL_LAW §11.
3. `ops/autonomy/worktree_isolation_gate.py` / rule `49-shared-worktree-isolation` (consume; do not weaken).
4. This skill's scripts and receipt schema.
5. `Unknown` — keep the ref; do not delete.

## Compact Workflow

1. **Discovery (RO)** — `scripts/inventory_git_work.py --repo <path>`.
2. **Diagnosis (RO)** — `scripts/diagnose_ref_value.py` for each stale/orphan candidate.
3. **Plan** — extract and/or prune-propose with rollback (reflog SHA in receipt).
4. **Execute** — extract first; prune-execute last and auth-gated; stash drop only with `L9_GIT_STASH_DROP_AUTHORIZED`.

## Forbidden

- `git stash drop` / `clear` without deep-analysis receipt + `L9_GIT_STASH_DROP_AUTHORIZED`
- `git branch -D` / `git push --delete` without prune-execute + `L9_GIT_PRUNE_AUTHORIZED`
- Age ⇒ worthless
- Broad `git add -A` / checkout thrash on dirty shared clone
- Deleting a worktree that still has unique dirty paths

## Resource Map

- [references/diagnose-first-binding.md](references/diagnose-first-binding.md)
- [references/output-receipt.schema.yaml](references/output-receipt.schema.yaml)
- [scripts/inventory_git_work.py](scripts/inventory_git_work.py)
- [scripts/diagnose_ref_value.py](scripts/diagnose_ref_value.py)
- [scripts/validate_pack_structure.py](scripts/validate_pack_structure.py)
- [scripts/pack_self_test.py](scripts/pack_self_test.py)

## Validation

```bash
python3 scripts/validate_pack_structure.py
python3 scripts/pack_self_test.py
```

## Failure Handling

- Inventory fails → stop; report git error; no prune.
- Diagnosis confidence unknown → classify `keep_push` / keep ref.
- Auth env missing on prune-execute → refuse and emit prune-propose only.
