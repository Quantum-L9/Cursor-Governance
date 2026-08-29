---
name: l9-git-work-preserve
description: diagnose-first audit extract harvest and prune-propose for unpushed dirty orphan stale stash and leftover worktree dirt. use when cleaning branches worktrees or stashes or harvesting misplaced dirty/untracked/WIP across worktrees into a PR. never lose unique commits without receipts and auth.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, git, worktree, stash, diagnose-first, preserve, prune, harvest, hygiene]
  owner: igor_beylin
  status: active
  version: 1.2.0
  updated: 2026-08-28
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
| `extract` | Local only | Dedicated worktree + path-union of allowlisted path-absent files; never cherry-picks a mixed leftover ref; never deletes source ref |
| `harvest` | Report, then local extract | Classify leftover dirty/untracked/WIP across sibling worktrees; port unique paths onto a fresh `origin/main` worktree |
| `triage-preserved` | No | Classify the refs `/ff` parked; **deletes nothing** |
| `prune-propose` | No | Delete candidates + required receipts + copy-paste commands |
| `prune-execute` | Yes | Only with user auth **and** `L9_GIT_PRUNE_AUTHORIZED=<reason>` |

Load detail: [references/audit-workflow.md](references/audit-workflow.md), [references/value-diagnosis.md](references/value-diagnosis.md), [references/extract-workflow.md](references/extract-workflow.md), [references/harvest-workflow.md](references/harvest-workflow.md), [references/triage-handoff.md](references/triage-handoff.md), [references/prune-policy.md](references/prune-policy.md), [references/stash-deep-analysis.md](references/stash-deep-analysis.md).

## Novelty is evidence, not a commit count

A branch whose work already landed still reports commits ahead, so counting them
calls redundant work unique and stale work worthless. Diagnosis instead asks
`git cherry` whether each patch id is already upstream, and whether every line
the ref touched has been absorbed. `redundancy_basis` records which answered:
`patch_id` is exact and may authorise a prune, `content_superset` is a heuristic
that may only be reported. See [references/value-diagnosis.md](references/value-diagnosis.md).

## `/ff` handoff

`/ff` is **`l9-repo-sync`'s** command and stays there: it catches a clone up to
`origin/main` in place and *parks* unique work instead of deleting it. Those
preserve refs then accumulate unread. This pack is the other half — it triages
what `/ff` parked, and it deletes nothing either:

```bash
python3 scripts/triage_preserved_refs.py --repo "$(pwd)" --fetch
```

Buckets: `novel` (still unlanded), `superseded` (`patch_id` — eligible for a
later prune-execute), `review` (`content_superset` — human reads it), `merged`,
`unproven`. Contract: [references/triage-handoff.md](references/triage-handoff.md).

## Authority Order

1. Explicit user objective and auth env flags.
2. [references/diagnose-first-binding.md](references/diagnose-first-binding.md) + CANONICAL_LAW §11.
3. `ops/autonomy/worktree_isolation_gate.py` / rule `49-shared-worktree-isolation` (consume; do not weaken).
4. This skill's scripts and receipt schema.
5. `Unknown` — keep the ref; do not delete.

## Compact Workflow

1. **Discovery (RO)** — `scripts/inventory_git_work.py --repo <path> --fetch`.
2. **Diagnosis (RO)** — `scripts/diagnose_ref_value.py --fetch` for each stale/orphan
   candidate. Judge against a *fetched* baseline: a stale `origin/main` overstates
   how much work is unpushed.
2a. **Triage (RO)** — `scripts/triage_preserved_refs.py` when `/ff` preserve refs
   have piled up (see `/ff` handoff above).
3. **Harvest classify (RO)** — when leftover worktree dirt / WIP is in scope:
   `scripts/harvest_worktree_dirt.py --repo <path> --include-wip --json`.
4. **Plan** — harvest/extract and/or prune-propose with rollback (reflog SHA in receipt).
5. **Execute** — harvest or extract first (fresh `origin/main` worktree). Extract leftover refs with `scripts/extract_path_union.py` (path-union through the allowlist; never mixed-branch cherry-pick). Prune-execute last and auth-gated; stash drop only with `L9_GIT_STASH_DROP_AUTHORIZED`.

## Forbidden

- `git stash drop` / `clear` without deep-analysis receipt + `L9_GIT_STASH_DROP_AUTHORIZED`
- `git branch -D` / `git push --delete` without prune-execute + `L9_GIT_PRUNE_AUTHORIZED`
- Age ⇒ worthless
- Broad `git add -A` / checkout thrash on dirty shared clone
- Deleting a worktree that still has unique dirty paths
- Applying a stale (behind-`main`) worktree dirty tree wholesale
- Copying `WIP/` through `/tmp`
- Scooping foreign dirt on a shared primary `main` checkout
- Mixed-branch cherry-pick of a leftover ref that deletes or overwrites a baseline path

## Resource Map

- [references/diagnose-first-binding.md](references/diagnose-first-binding.md)
- [references/harvest-workflow.md](references/harvest-workflow.md)
- [references/triage-handoff.md](references/triage-handoff.md)
- [references/output-receipt.schema.yaml](references/output-receipt.schema.yaml)
- [scripts/inventory_git_work.py](scripts/inventory_git_work.py)
- [scripts/diagnose_ref_value.py](scripts/diagnose_ref_value.py)
- [scripts/git_fetch.py](scripts/git_fetch.py)
- [references/extract-workflow.md](references/extract-workflow.md)
- [scripts/harvest_worktree_dirt.py](scripts/harvest_worktree_dirt.py)
- [scripts/extract_path_union.py](scripts/extract_path_union.py)
- [scripts/triage_preserved_refs.py](scripts/triage_preserved_refs.py)
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

`make clean` ships **this** workspace. `harvest` scans **sibling worktrees**
for misplaced unique dirt (including `WIP/`). `repo_hygiene.py` only deletes
landed residue at sessionEnd — it is not harvest.
