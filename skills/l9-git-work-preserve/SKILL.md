---
name: l9-git-work-preserve
description: diagnose-first audit extract fast-forward and prune for unpushed dirty orphan stale and stash git work. proves novelty by patch id and absorption, not commit counts. use when cleaning branches worktrees stashes or fast-forwarding a clone.
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
| `ff` (`/ff`) | Local only | Fetch → classify every branch → fast-forward the baseline → safe-delete the proven-redundant. Never pushes; publishing is `make pr` |

**Novelty is proved, not counted.** A branch whose work already landed still
reports commits ahead, so `unique_commits` alone will call it unique forever.
Two signals settle it: `git cherry` patch ids (exact, sees cherry-picks and
rebases) and line absorption vs the merge base (heuristic, sees work that landed
reimplemented). Both are judged against a **fetched** baseline — see
[references/value-diagnosis.md](references/value-diagnosis.md).

Load detail: [references/audit-workflow.md](references/audit-workflow.md), [references/value-diagnosis.md](references/value-diagnosis.md), [references/extract-workflow.md](references/extract-workflow.md), [references/prune-policy.md](references/prune-policy.md), [references/stash-deep-analysis.md](references/stash-deep-analysis.md).

## Authority Order

1. Explicit user objective and auth env flags.
2. [references/diagnose-first-binding.md](references/diagnose-first-binding.md) + CANONICAL_LAW §11.
3. `ops/autonomy/worktree_isolation_gate.py` / rule `49-shared-worktree-isolation` (consume; do not weaken).
4. This skill's scripts and receipt schema.
5. `Unknown` — keep the ref; do not delete.

## Compact Workflow

1. **Discovery (RO)** — `scripts/inventory_git_work.py --repo <path> --fetch`.
2. **Diagnosis (RO)** — `scripts/diagnose_ref_value.py --fetch` for each stale/orphan candidate.
3. **Plan** — extract and/or prune-propose with rollback (reflog SHA in receipt).
4. **Execute** — extract first; prune-execute last and auth-gated; stash drop only with `L9_GIT_STASH_DROP_AUTHORIZED`.

Whole-repo sweep: `scripts/ff_pipeline.py --mode plan` classifies every branch in
one pass and `--mode apply` fast-forwards then safe-deletes. It refuses a dirty
tree (that is `/clean`'s job) and never force-deletes — anything `git branch -d`
rejects lands in `needs_human[]` with its tip SHA.

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
- [scripts/git_fetch.py](scripts/git_fetch.py)
- [scripts/ff_pipeline.py](scripts/ff_pipeline.py)
- [scripts/validate_pack_structure.py](scripts/validate_pack_structure.py)
- [scripts/pack_self_test.py](scripts/pack_self_test.py)

Commands that load this skill: `/git-work-preserve` (audit / extract / prune),
`/ff` (fetch → prove → publish-handoff → fast-forward → prune).

## Validation

```bash
python3 scripts/validate_pack_structure.py
python3 scripts/pack_self_test.py
```

## Failure Handling

- Inventory fails → stop; report git error; no prune.
- Diagnosis confidence unknown → classify `keep_push` / keep ref.
- Auth env missing on prune-execute → refuse and emit prune-propose only.

## make clean (ship + reset)

Orchestrator (does not replace this skill's report-only default):

```bash
make -C "$HOME/.cursor-governance" clean WS="$(pwd)"
# preview: CLEAN_MODE=plan
```

`ops/scripts/workspace_clean.py` classifies dirty/untracked paths with
`ops/config/workspace-clean-routing.yaml`, extracts each destination into its
own worktree, opens a scoped PR, prunes only ancestor-of-`origin/main` locals
that are not checked out elsewhere, and primes `$HOME/.l9/primed/<dest>`.
Ambiguous paths block apply. Secrets and machine-local files are never shipped.
