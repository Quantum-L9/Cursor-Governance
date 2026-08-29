---
name: Stop generated merge conflicts
overview: "Scope pull_request self-check to changed sources, keep the full snapshot on main, and stop stack_safe_merge from deleting a parent ref a child still uses."
todos:
  - id: scope-pr-self-check
    content: "pull_request uses --changed-file; add --pe-manifest only when PE sources listed; push to main keeps --force --pe-manifest"
    status: pending
    phase: implement
    depends_on: []
  - id: keep-parent-ref
    content: "stack_safe_merge.py skips DELETE / omits --delete-branch when selection.children is nonempty"
    status: pending
    phase: implement
    depends_on: []
  - id: janitor-main-generated
    content: "Add --force --pe-manifest step to lint-autofix.yml; reuse create-pull-request; never push to main"
    status: pending
    phase: implement
    depends_on: [scope-pr-self-check]
  - id: generated-heal-law
    content: "Align run-contract generated_output_overlap with INVENTORY_GATE; confirm generated-heal.md"
    status: pending
    phase: implement
    depends_on: [scope-pr-self-check]
  - id: doctrine-owners
    content: "Append-only AGENTS stamp plus named-fragment ownership; do not rewrite session_start_block"
    status: pending
    phase: implement
    depends_on: [keep-parent-ref]
  - id: tests-docs
    content: "Scoped self-check fixture + parent-ref test; make pr-check; no merge from this path"
    status: pending
    phase: verify
    depends_on: [scope-pr-self-check, keep-parent-ref]
isProject: false
kind: pe
execute_via: pe_autonomy
status: executable
plan_id: stop_generated_merge_conflicts_b8e41c2a
schema_version: 1.0.0
kernel_pass:
  bound_path: docs/plans/stop_generated_merge_conflicts_b8e41c2a.plan.md
  improve:
    ran_at: "2026-08-28T22:10:00+00:00"
    deltas:
      - "Bound execute_via to PE+autonomy; INVENTORY_GATE owns generated-only overlap"
      - "Locked pull_request --changed-file vs push --force --pe-manifest"
  validate_repair:
    ran_at: "2026-08-28T22:12:00+00:00"
    body_sha256: "e1b2b443f0b96e3348fc3a4aa12852000826c2da3687bbcd9e3a4dea71e38190"
    deltas:
      - "Removed unresolved exclusive locks; kernel receipt bound to this stem"
      - "Confirmed rollback is revert-the-one-PR"
---

# PLAN: Stop generated merge conflicts

## Metadata

- plan_id: `stop_generated_merge_conflicts_b8e41c2a`
- schema_version: `1.0.0`
- status: executable
- Lock: origin/main = `59f03a5d4460b939360bc2fd5dd85239d47416a5`
- autonomous_merge: false

## Architect framing

Sibling PRs go CONFLICTING after any land because `governance-self-check.yml` forces every PR to commit the full generated snapshot. A second defect: `stack_safe_merge.py` DELETEs a parent ref that a child still uses (proven: #343 deleted `claude/dag-skill-consolidation-5ne7g1` and GitHub closed #349).

## Immutable baseline

- `sync_generated_artifacts.py` already has `--changed-file` and `should_run()`. `--force` runs every generator. `--pe-manifest` is opt-in for `environment/program-execution/MANIFEST.json`.
- `lint-autofix.yml` already opens a draft cleanup PR and never pushes to protected `main`.
- GitHub has no `l9-generated` merge driver. Do not pursue `.gitattributes` as a GitHub fix.

## Objective + success properties

Open sibling PRs that do not share **source** files stay MERGEABLE after one of them lands. Parent refs survive while a child still bases on them.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Two sibling PRs that do not share source files do not both list PE `MANIFEST.json` or `skill-registry.json` | quality_gate | fixture file lists + `should_run` | true |
| SP-02 | A PR that only changes `ops/scripts/foo.py` does not fail self-check because PE `MANIFEST.json` is stale | quality_gate | scoped self-check fixture | true |
| SP-03 | A PR that changes `environment/program-execution/**` still fails if `MANIFEST.json` is omitted | quality_gate | PE-source fixture + `--pe-manifest` | true |
| SP-04 | `push` to `main` is the only `--force` snapshot check; lint-autofix is the only generated janitor | repository_state | workflow YAML | true |
| SP-05 | `stack_safe_merge.py --run` of a parent with an open child does not DELETE the parent ref | unit_test | `test_stack_safe_merge.py` | true |

## Capability preflight

- Worktree: `/Users/ib-mac/.l9/gov-worktrees/cursor__stop-gen-snap-v2` on `agent/cursor/stop-gen-snap-v2` from fetched `origin/main`.
- Interpreter: worktree `.venv` after `uv sync --locked --extra dev`.
- No merge from this path. Campaign / `make pr` end green + merge-ready.

## Execution envelope

In: self-check split, lint-autofix generated heal, `stack_safe_merge` parent-ref keep, remediator generated-heal wording, AGENTS append-only stamp, two test modules.

Out: GitHub merge drivers; weakening self-check on `main`; folding AGENTS / CANONICAL_LAW; ceremony rewrite; remediator merge-timing rewrite; mixing onto the dirty primary checkout.

## Side effects + idempotency

Scoped regen writes only generators whose prefixes match the PR file list. Re-running the same list is a no-op when content already matches. Janitor opens a cleanup PR only when `--force --pe-manifest` dirties generated content.

## Architecture impact

CI authority split: PR checks the changed-source snapshot; `main` still fail-closes on the full snapshot. Merge helper keeps a parent ref while `selection.children` is nonempty.

## Rollback

Revert the one PR. Self-check returns to `--force --pe-manifest` on every event. `stack_safe_merge` returns to always-delete.

## Complexity and uncertainty

U1 resolved accept_bounded: reuse `lint-autofix.yml`; do not add a second workflow.

## Execution DAG

1. `scope-pr-self-check` and `keep-parent-ref` in parallel.
2. `janitor-main-generated` and `generated-heal-law` after the self-check split.
3. `doctrine-owners` after parent-ref keep (AGENTS stamp only).
4. `tests-docs` then `PR_BASE=origin/main make pr-check`. No merge.

## Property evidence matrix

| id | how observed | pass |
|----|--------------|------|
| SP-01 | non-PE file list does not dirty PE `MANIFEST.json` or `skill-registry.json` | fixture |
| SP-02 | same | fixture |
| SP-03 | PE-source list plus `--pe-manifest` requires `MANIFEST.json` in the check set | fixture |
| SP-04 | YAML review: PR path has no `--force`; push path keeps it; one janitor workflow | inspect |
| SP-05 | parent-with-children omits `--delete-branch` and skips DELETE | unit |

## Stress and disconfirm

- A PE-source PR that omits `MANIFEST.json` must still fail.
- Janitor and scoped PR check must not fight: `main` holds the full snapshot; PRs omit unrelated generated files.
- After the last child retargets or lands, the parent ref may be deleted. Do not keep it forever.
- `kernel_gate` must still require `kernel_pass` when a `.plan.md` is actually in the PR.

## Out of scope

- GitHub merge drivers / `.gitattributes` as a GitHub fix
- Weakening self-check on `main`
- Folding AGENTS.md / CANONICAL_LAW.md
- Ceremony / `make pr` rewrite
- Remediator merge-timing rewrite
- Mixing onto the dirty primary checkout

## Convergence

- status: executable
- next_skill: `/autonomy` + `@environment/program-execution`
- stop_reason: law holds; implement on this worktree

## Execute via @environment/program-execution + autonomy

`.plan.md` → `@environment/program-execution` (Blueprint → Program Lock → Controller) → `@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter `cursor-foreground`.

Do not free-form execute from this markdown alone after the kernel receipt PASSes: follow the DAG on the dedicated worktree.
