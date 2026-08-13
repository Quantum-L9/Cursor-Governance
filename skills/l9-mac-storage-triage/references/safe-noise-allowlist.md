<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: deletion_allowlist
tags: [macos, storage, caches, docker, trash, safety]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
/L9_META -->

# Safe noise allowlist

## Purpose

Repair and autonomy may delete only regenerating caches and confirmed unused runtime noise. Everything else is diagnose-only or extra HITL.

## Allowed actions (auto-selected)

| Action | What it removes | What it never removes |
|--------|-----------------|------------------------|
| `purge_stale_caches` | Homebrew cache dir only (`$(brew --cache)` when it is `~/Library/Caches/Homebrew` — **not** `brew cleanup`, which also deletes `/opt/homebrew` portable-ruby), npm/yarn/pnpm caches, pip cache, conda tarball/index cache (`conda clean --all --yes`, never `rm -rf` pkgs), uv cache (`uv cache clean` or `~/.cache/uv`), Chrome disk cache (`~/Library/Caches/Google` only), Xcode DerivedData **only if** `XCODE_DERIVED_PURGE=true` | conda **environments**, `/opt/homebrew` Cellar/prefix, `~/Library/Caches` wholesale, `~/Library/Application Support` (including Chrome bookmarks/passwords), cookies, project `node_modules` |
| `docker_prune_unused` | Stopped containers (`docker container prune`), dangling images (`docker image prune`), build cache (`docker builder prune`) | Named images in use, **volumes**, running containers, `docker system prune -a` |
| `empty_trash` | Current user's Trash | Files not in Trash |

## Forbidden in repair/autonomy auto-select

These exist in the playbook for operator-opt-in `.env` use. Repair/autonomy scripts must not add them to `APPROVED_ACTIONS`.

- `mail_cache_remove` — destroys local Mail; needs server-backed + no-local-mailbox confirmations
- `offload_rclone` / `delete_verified_source` — data movement and permanent delete
- `spotlight_reindex_prepare` — opens System Settings; not a deletion
- `spotlight_exclusions` — writes markers, not noise purge

## Forbidden paths (never delete)

- `/`, `$HOME`, `~/Documents`, `~/Desktop`, `~/Downloads` (contents)
- `~/Library/CloudStorage` and File Provider roots
- `~/Library/Mail` unless `mail_cache_remove` is explicitly planned
- `~/Library/Containers` (macOS app sandboxes — not Docker)
- Docker volumes
- Time Machine backups / local snapshots (report only)
- Any path outside `$HOME` except Docker's own prune APIs

## "Old containers" meaning

Docker Engine containers and dangling images. Not `~/Library/Containers`.

## Size gate

Skip an allowlisted action when inventory reports `0` reclaimable KiB for that bucket. Do not run empty no-ops as success theater; omit them from `APPROVED_ACTIONS`.
