# DELTA REPORT — GitHub-Centric Governance Migration

**Date:** 2026-06-30 · **Branch:** `claude/governance-github-migration-23mh38`

## Before → After

| Dimension | Before | After |
|-----------|--------|-------|
| SSOT root | `$HOME/Dropbox/Cursor Governance/` | `$HOME/.cursor-governance` (GitHub clone) |
| GlobalCommands | nested `Dropbox/.../GlobalCommands/` | clone root (`$GLOBAL_COMMANDS == $GOV_ROOT`) |
| GitHub role | off-site backup only | Single Source of Truth |
| Auto-sync | none (manual) | `governance_sync.sh` guarded ff-only on session start |
| Dropbox | required | optional transition fallback |

## Functional changes

- **`ops/scripts/resolve_governance_paths.sh`** — rewritten: `~/.cursor-governance` first (repo-root layout → `GLOBAL_COMMANDS=GOV_ROOT`), Dropbox nested layout as fallback.
- **`ops/scripts/recursive_learning_orchestrator.py`** — `get_global_commands_path()` mirrors the same 3-tier ordering.
- **`ops/hooks/session_start_bootstrap.sh`** — resolver updated; **backgrounded guarded sync injected** (replaces the proposed unsafe `reset --hard`).
- **`ops/scripts/governance_sync.sh`** — NEW. ff-only + stash-around-dirty + `flock` single-flight + installed-bootstrap self-heal. Opt-in hard reset via `GOVERNANCE_SYNC_HARD_RESET=1`.
- **`ops/scripts/setup_workspace_symlinks.sh`** — `ensure_global_git_ignores()` added (isolates runtime state via `core.excludesfile`); **fresh-machine blocker fixed** (bootstrap `cp` no longer precedes `mkdir ~/.cursor/hooks`); stale Dropbox error text updated.
- **`intelligence/workspace/setup-new-workspace.py`** — `GLOBAL_COMMANDS` resolves dynamically (`~/.cursor-governance` → Dropbox).
- **`rules/97-governance-ssot-paths.mdc`** — canonical SSOT contract rewritten to declare `~/.cursor-governance`; Dropbox = legacy fallback; auto-sync row added.
- **`.gitignore`** — runtime-isolation block (`memory-bank/`, `.workflow_state_*.json`, `*.fallback.log`); `memory-bank-template/` deliberately not matched.

## Non-functional changes
- Active docs/rules/skills + wrapper scripts: 63 files, 358 path-string replacements (Dropbox/Library `GlobalCommands` → `~/.cursor-governance`); `/Users/...` hardcodes de-machined (satisfies rule 97 "forbidden" list).

## Preserved (anti-regression)
- `install_graphiti_tunnel_agent()` and memory-bank scaffold loop — unchanged.
- Dropbox fallback in all resolvers.
- `backup_to_github.sh` push/rebase logic (reframed as SSOT push side, not rewritten).

## Removed / rejected
- **Rejected:** `git reset --hard origin/main` background sync (data-loss + race) → replaced by guarded sync.
- **Rejected:** creating a nested `GlobalCommands/` subfolder → evidence shows repo root *is* GlobalCommands (zero-churn).

## Out of scope (carve-outs, with reason)
| Path | Reason |
|------|--------|
| `foundation/security/_archived/**`, `*.sig.json` | Immutable signed provenance — editing corrupts signatures. |
| `reports/GMP-*`, `current_work/harvested/**` | Historical declarations/snapshots — not live instructions. |
| `learning/**` (e.g. `repeated-mistakes.md`) | Historical lessons; rewriting "Dropbox-not-Library" inverts the recorded lesson. |
| `C_GOV_FILES/**` | Snapshot/export bundle; high-churn, low value. |
| 2 pre-existing `py_compile` failures | Present at HEAD; fixing = scope creep. |
