---
name: Group-resolver retry hardening
overview: "Adopt the already-merged PR #201 group-resolver retry (fast-forward local clones), then close the remaining regression-test and behavior gaps for the multi-repo `/home/user` shape — without touching the hardened override/fail-closed semantics."
todos:
  - id: w0-ff-sync
    content: Fast-forward both governance clones to origin/main via governance_sync.sh; verify _git_toplevel retry and upstream test are present; run existing resolver suite
    status: pending
  - id: w1-branch
    content: Create new branch from origin/main tip (no unrelated WIP)
    status: pending
  - id: w1-tests
    content: "Add regression tests: multi-child ambiguity stays readonly, explicit override selects within child set, toplevel retry from clone subdir"
    status: pending
  - id: w2-validate
    content: Run resolver + memory-enforcement suites with locked venv python, then make pr-check
    status: pending
  - id: w2-publish
    content: Publish via make pr (single small PR against origin/main)
    status: pending
isProject: false
---

# Group-resolver retry — adopt PR #201 + close remaining gaps

## Ground truth (verified, changes the scope)

The fix you asked to "land" is **already merged to `origin/main`** as PR #201 (`46bdf5c`, feat(secrets): shared Infisical plane):

- `ops/graphiti/group_resolver.py` — `_git_toplevel()` retry when the path match misses, then `_child_git_roots()` scan of immediate child git repos
- `environment/agents/adapters/claude-code/memory/memory_state.py` — `workspace_root()` env-var / walk-up fix (lock half)
- `ops/graphiti/graphiti_memory_client.py` — `cmd_conflicts` freshness + group scoping (`_fresh_conflicts`, `_conflicts_in_scope`)
- `ops/graphiti/test_group_resolver.py` — one new test (`test_child_git_repo_does_not_collapse_to_workspace`)
- `group_registry.yaml` on main already has `llm-router`, `seo-bot`, `website-bot` rows

The local workspace checkout is at `b62147a`, **behind** the tip; `git merge-base --is-ancestor` confirms a clean fast-forward. So the plan is: sync, verify, then close the two genuine remaining gaps.

## Remaining gaps (the actual new work)

1. **No test for the many-children case.** At a real `/home/user` with 9 registered child repos, the child scan produces multiple hits → `ambiguous group match` → readonly, `group_id=None`. That is the intended honest-degraded behavior, but it is untested, and it silently changed the failure mode from `fallback_readonly igor-workspace` to `ambiguous`. A regression test must pin it so a future "fix" doesn't collapse a multi-repo root into one product group.
2. **No test that an explicit override selects within the child set.** A Claude cloud session at `/home/user` pinned via `GRAPHITI_GROUP_ID=llm-router` must resolve (override is a member of the ambiguous child set) — this is the sanctioned escape hatch for that environment and mirrors the existing `test_explicit_member_of_ambiguous_set_allowed`.

## Invariants that must not move (collision guards)

- Explicit override contradicting a resolved match **fails closed** (readonly, no write)
- Path hints match **whole segments only**
- Direct `write` to `igor-workspace` stays rejected; `forbidden_groups` unchanged
- **No `/home/user` registry row, no `path_hints: [user]`** — the umbrella never becomes a group
- `on_failure: abort_write_allow_readonly` fallback stays; DEGRADED at an unresolvable root is correct, not a bug

## Steps

### W0 — Sync to tip (no code)
- Fast-forward both clones to `origin/main` via the sanctioned path: `bash ~/.cursor-governance/ops/scripts/governance_sync.sh` (ff-only; never hard-reset). Workspace clone has uncommitted edits in unrelated files (`AGENTS.md`, claude-code web/*) — ff-only pull is commit-preserving; stop and report if any modified file conflicts.
- Verify adoption: `_git_toplevel` present in [ops/graphiti/group_resolver.py](ops/graphiti/group_resolver.py), upstream test present, resolver suite green.

### W1 — Regression tests (new branch from origin/main)
Branch per `KERNEL_PACK_NEW_BRANCH_DEFAULT_V1`: new branch from ff-only tip, no unrelated WIP.
- Extend [ops/graphiti/test_group_resolver.py](ops/graphiti/test_group_resolver.py):
  - `test_multi_child_repos_stay_ambiguous_readonly` — tmp workspace with two registered child git dirs → `group_id=None`, `readonly=True`, `"ambiguous"` in error
  - `test_explicit_override_selects_within_child_set` — same shape + `explicit="cursor-governance"` → resolves, `readonly=False`
  - `test_toplevel_retry_from_registered_clone_subdir` — subdir of a git repo whose toplevel segment matches a hint (env `GRAPHITI_GROUP_ID` unset, `_git_toplevel` monkeypatched) → registry match
- Tests only; no resolver behavior change expected. If a test exposes a real defect, fix minimally in `group_resolver.py` and keep all existing 14 tests green.

### W2 — Validate + publish
- `.venv/bin/python -m pytest ops/graphiti/test_group_resolver.py environment/agents/adapters/claude-code/tests/test_memory_enforcement.py`
- `make pr-check`, then publish via `make pr` (never raw push). Single small PR; no campaign branch needed.

## Explicitly out of scope
- Any change to `l9-graphiti-memory` (server repo — wrong plane, per ADR-0006)
- Registry row for `/home/user` or other umbrella folders
- Relocating `memory_state.py`; SessionStart hook changes (hydrate already passes the harness project dir; honest DEGRADED at an unresolved umbrella is by design)
