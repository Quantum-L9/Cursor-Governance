# Supported action identifiers

## Repair / autonomy allowlist

- `purge_stale_caches`: Homebrew, npm/yarn/pnpm, pip, conda package caches, uv cache, and Chrome disk cache (`~/Library/Caches/Google` only). Conda environments and Chrome Application Support are kept. Xcode DerivedData only if `XCODE_DERIVED_PURGE=true`.
- `docker_prune_unused`: Stopped containers, dangling images, and build cache. Never volumes or `docker system prune -a`.
- `empty_trash`: Current user's Trash only.

## Extra HITL (never auto-selected)

- `spotlight_exclusions`: Create `.metadata_never_index` on ordinary local directories and report File Provider paths for manual Search Privacy handling.
- `spotlight_reindex_prepare`: Verify free-space and indexing-state prerequisites, then open System Settings for the privacy-toggle rebuild procedure.
- `mail_cache_remove`: Remove the current user's Apple Mail local data only after explicit server-backed and local-only-mailbox confirmations.
- `offload_rclone`: Stream a configured local directory directly to a configured rclone remote and verify the copy.
- `delete_verified_source`: Delete a local source only when a successful offload receipt matches the configured source and destination.
