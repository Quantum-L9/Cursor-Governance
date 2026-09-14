# RETIRED — Python origin/HEAD binder duplicate

**Retired:** 2026-09-13
**Replacement:** [`ops/scripts/lib/git_remote_head.sh`](../../lib/git_remote_head.sh)

`ops/scripts/repo_hygiene.py` previously contained a second implementation of
remote default-branch discovery, bounded default-ref fetch, and
`refs/remotes/origin/HEAD` binding. That implementation was removed from the
live Python path so the shell helper is now the sole executable authority.

The live `sync_remote_refs()` function still owns the caller-specific
**prune** and the fail-soft hygiene report. When it needs to repair a missing
`origin/HEAD`, it invokes the helper’s sealed CLI. It must not recreate
`ls-remote --symref`, `check-ref-format`, default-ref fetch, or
`remote set-head` logic.

This archive record intentionally preserves provenance only. The removed
implementation remains recoverable from Git history but is not copied here as
executable code. `_archived` is excluded from active formatting, type-checking,
test collection, and pre-commit discovery.

Restoring inline binding logic in Python would reintroduce a competing
implementation and violate the single-path contract.
