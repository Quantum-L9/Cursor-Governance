# CTO owner runbook: dependency graph, safe concurrency and integration

## Preparation and authority

Read `00_LAUNCH_IN_CTO_MODE.md` first; treat its access header as the complete maximum campaign universe. Freeze the latest main SHA and open PRs in each writable repo, then consult `CAMPAIGN.yaml` for the actual lane DAG. Existing main baseline values are evidence only and are intentionally refreshed, never force-reset. Resolve upstream authority and current source/receipt with actual owners. A tool's ability to write is not authorization to edit.

The user is the single human owner. L9-ORG-007 explicitly permits an authenticated owner to authorize their own exact governance change, and may accept attributable chat instruction. Do not require a second human where current law does not. Do not treat this general campaign launch as an exact approved candidate after code changes are made. Agent can autonomously implement and propose; only exact owner-only admissions, unauthorized privilege or genuine blocked ambiguity cause escalation.

## Parallelism schedule

```text
S: four read-only pool Tasks, no new lane files
|
A: CTO session opens the .github PR
|
+-- B: CTO session stacks on A's head immediately
|    |-- C: pool stacks on B's head, and on any overlapping Cursor PR
|    `-- M: pool stacks on B's head, and on any overlapping Ops PR
|
`-- E: pool opens against l9-ci-core main, pinned to A's or B's head

F: CTO session stacks on B's head once B, C, M, and E have a disposition.
```

The pool is four coding agents, cap five, launched once and reused. A, B, and F are not pool slots. See `09_EXECUTION_BINDING.md`. B starts when A's head exists. E, C, and M start when that head, or B's head, can be pinned. They push pin updates to their own open pull requests. The CTO never merges. An unmerged pull request does not pause a lane. A signature or owner gap is recorded and the other lanes continue. Do not call a blocked lane passed.

Lock files via `repo + branch + path` and one mutating agent per worktree. Stack on the predecessor or overlapping open pull request. `PR_STACK=auto` fail-closes while Cursor-Governance has several sibling pull requests against `main`, so name that parent head. CTO alone reconciles cross-repository contracts. No shared `.github` writers. Recheck #1036, #1037, and #1038 when C chooses its base, and L9-Ops-MCP #44 when M chooses its base.

## Per-lane execution discipline

1. Reconfirm exact upstream and local authority and toolchain currentness.
2. Inspect the owning source and actual affected code, including tests, before deriving edits and commands. Never use guessed script names as execution instructions.
3. Reconcile paths, scope, one-writer and prior PR overlap; branch from current correct integration base or exact predecessor head for a real stack.
4. Implement only bounded finding set. Verify native schema/contract + minimal relevant positive/negative paths. Avoid accidental large full-corpus reruns when current ownership already supplies tested output.
5. For each completed code lane, invoke one Cursor-Governance publication ceremony with `WS` at its exact target worktree: `PR_REMEDIATE=0 OPEN_PR=1 make -C "$HOME/.cursor-governance" pr WS="$WT"`, with `PR_BASE` set to the predecessor or overlapping open pull request head. Run `l4_local.py begin` and `authorize-release` in that worktree first. Do not call `kernel_gate.py`; that file is absent at the pinned governance SHA. No `OPEN_PR=0 make pr` rehearsal and no raw push or `gh pr create`. The stack rule is in `09_EXECUTION_BINDING.md`. The CTO does not merge.
6. Independently check the created PR, checks, reviewability, exact user owner authorization and merge SHA. Fix in-scope defects at the real owning repo and revalidate affected interfaces, not hidden downstream patches.
7. CTO binds integration on exact release SHA and gathers live required-check evidence. A green PR is neither policy admission nor organization-wide enforcement.

## Known collision and risk checklist

- `.github` policy and ruleset authoring both mutate the same owner: A, B, F serialized.
- `Cursor-Governance #1036` may change governance files or generated references: diff current worktrees before C.
- Org ruleset 21895545's live `strict=false` and always-bypass admin vs committed expected config must be reconciled; never blindly apply stale JSON.
- `.github` may be excluded from its own org ruleset. Prove its separate platform protection.
- Core `Analyze (central Core)` check must run even when PR title/body changes, ref retargets or a metadata waiver tries to skip; preserve non-skippable semantics.
- Cursor's existing v4.0.0 sibling hardcoded canonical paths will silently sabotage a mirror if only `ORG_INVARIANTS.yaml` is moved.
- L9-Ops-MCP's mirror is not a v4 policy clone; preserve its small `org_invariants` adapter.
- Signed release/in-toto and exact authorization are real gates. No ability to sign is not permission to remove signing requirements.

## Final owner handoff

Aggregate D01-D16 evidence, each source/PR URL, actual merge SHA, signed release verification, live ruleset scope, good/bad required-job test, exceptions and remaining unknowns. Output PASS only when mandatory evidence actually exists. An unresolved prerequisite is BLOCKED with exact owner and single next action. No automatic Phase 2 improvements or edits to unlisted repositories.
