# VALIDATION — GitHub-Centric Governance Migration

**Date:** 2026-06-30 · **Branch:** `claude/governance-github-migration-23mh38`
**Kernels:** L9 Validation Evidence Kernel · L9 Recursive Improvement Kernel
**Skill:** `l9-recursive-optimization` (optimize)
**Final status:** `APPROVED_WITH_FINDINGS` (execution-ready; non-blocking pre-existing defects logged)

---

## Scope

Migrate the governance Single Source of Truth from Dropbox to a local GitHub clone at
`$HOME/.cursor-governance`, with guarded auto-sync, preserved Graphiti tunnel/scaffold, and
stateful-memory isolation. **The whole repo IS GlobalCommands** (repo-root layout): so
`$GLOBAL_COMMANDS == $GOV_ROOT == $HOME/.cursor-governance` — no nested `GlobalCommands/`.

## Hard-gate results

| Gate | Method | Result | Evidence |
|------|--------|--------|----------|
| Path resolution (SSOT) | `source resolve_governance_paths.sh; resolve_governance_paths` against simulated `~/.cursor-governance` | **PASS** | `GOV_ROOT == GLOBAL_COMMANDS == ~/.cursor-governance` |
| No-hardcoded-paths lint | `validate_governance_no_hardcoded_paths.sh` (simulated clone) | **PASS** | exit 0; 5 wiring files clean of `/Users/`,`/home/`,CloudStorage |
| Symlink wiring | `validate_governance_symlinks.sh` via full `setup_workspace_symlinks.sh` | **PASS** | `.cursor-commands`, `.cursor/rules`, `CANONICAL_LAW.md` all → `~/.cursor-governance` |
| Fresh-machine setup | full `setup_workspace_symlinks.sh` in empty `$HOME` + new repo | **PASS** | bootstrap installed+exec; hooks.json sessionStart wired; memory-bank scaffolded |
| Guarded sync — dirty tree | `governance_sync.sh` with uncommitted edit + untracked sentinel | **PASS** | upstream ff-applied AND local edit + sentinel preserved (no data loss) |
| Guarded sync — clean tree | `governance_sync.sh` clean tree | **PASS** | fast-forwarded to upstream HEAD, no spurious changes |
| Guarded sync — concurrency | two concurrent runs (flock) | **PASS** | both complete, no corruption |
| Bootstrap self-heal | stale installed copy + changed source | **PASS** | installed hook re-copied to new version |
| Global-ignore isolation | `ensure_global_git_ignores` (idempotent) | **PASS** | `core.excludesfile` gets `memory-bank/`, `.workflow_state_*.json`, fallback log; re-run no-op |
| Syntax (changed `.sh`) | `bash -n` on all modified shell | **PASS** | all clean |
| Syntax (changed `.py`) | `py_compile` on all modified python | **PASS except 2 pre-existing** | see findings |
| JSON/YAML validity | parse changed `.json`/`.yaml` | **PASS** | RULES-MANIFEST.{json,yaml}, start-session.yaml valid |

## Findings

| # | Sev | Type | Description | Disposition |
|---|-----|------|-------------|-------------|
| F1 | medium | pre-existing | `ops/scripts/closed_loop_improvement.py:431` and `prevention_effectiveness_tracker.py:500` fail `py_compile` (f-string-with-backslash). **Confirmed present at HEAD before this change** — not a regression. | Out of scope (no scope creep). Logged as Unknown/pre-existing. |
| F2 | low | non-blocking | `check_governance_wiring.sh` emits WARN (sessionEnd deep-wiring) in the bare test harness; final symlink gate still PASS. | Resolves once `/wire governance` runs in a real session. |
| F3 | n/a | carve-out | Immutable provenance NOT modified: `foundation/security/_archived/**`, `reports/GMP-*`, `current_work/harvested/**`, `*.sig.json`, `learning/**` (historical lessons), `C_GOV_FILES/**` (snapshot bundle). | Intentional — see DELTA_REPORT. |

## Regression safety
- Dropbox retained as ordered fallback in every resolver → zero-downtime cutover.
- Sync is ff-only/stash; `reset --hard` only via explicit `GOVERNANCE_SYNC_HARD_RESET=1`.
- Graphiti tunnel agent + memory-bank scaffold functions preserved byte-for-byte.
- No tracked file untracked; immutable provenance untouched.

## Smallest next action
Confirm SSOT origin owner (Open Item) and run, on each machine:
`git clone <origin>/Cursor-Governance.git "$HOME/.cursor-governance"` then
`bash "$HOME/.cursor-governance/ops/scripts/setup_workspace_symlinks.sh"` from any project root.
