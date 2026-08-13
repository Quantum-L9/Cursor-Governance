<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: kernel
tags: [diagnose-first, macos, storage]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
/L9_META -->

# Diagnose-first kernel (storage)

## Purpose

No write, plan, or reclaim command until current disk state is inspected and summarized from this machine.

## Principles

1. **Diagnosis before execution** — `.state/diagnosis.complete` unlocks env, plan, and apply.
2. **Zero placeholders** — paths and remotes are copy-paste facts from diagnosis, never `<PATH>`.
3. **No inference of missing state** — `UNKNOWN` stays `UNKNOWN`; ask or skip.
4. **Deletion is a separate plan from copy/offload.**

## Allowed before a plan

- `df`, `diskutil`, `tmutil listlocalsnapshots`, `mdutil -sa` (read)
- Bounded `du -sk` of allowlisted cache/trash paths
- `docker system df` / `docker ps -a` (read)
- `conda clean --all --dry-run`
- Saved `ncdu` scan excluding CloudStorage
- Sparse-file allocated-block inspect

## Forbidden before diagnosis + plan + confirmation

- `rm`, `brew cleanup`, `npm cache clean`, `conda clean --yes`, Docker prune, Trash empty
- `mdutil -E`
- Mail data removal
- rclone copy/delete
- Writing `.metadata_never_index` except as a planned `spotlight_exclusions` action

## Enforcement sequence

1. Read state → diagnosis receipt
2. Plan changes → hashed plan bound to `.env` digest
3. Write changes → only actions listed in the plan, after the mode's confirmation value
