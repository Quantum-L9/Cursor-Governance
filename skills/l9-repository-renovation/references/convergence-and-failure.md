<!-- L9_META
layer: reference
role: convergence_and_failure
tags: [validation, rollback, blockers]
status: active
-->
# Convergence and Failure

## Convergence criteria

All must be true:

- contract schema and semantic validation pass;
- changed files remain inside scope;
- every required suite and validator executes through canonical entrypoints;
- local and CI dependency installation use the declared lock authority;
- before/after comparison shows no new high or critical finding;
- no gate was weakened, bypassed, or made advisory without an explicit ratchet decision;
- required PR checks are green or an external blocker is precisely documented;
- rollback is executable.

## Three-cycle limit

For one failure class:

1. reproduce and make the smallest evidence-backed correction;
2. reassess the authority model and hidden coupling;
3. attempt one revised implementation.

A fourth cycle is prohibited. Emit a blocker with command, output, suspected boundary, completed work, and smallest next action.

## Rollback

Prefer commit-level reversion when checkpoints are independently green. For data or schema migration, require a separately proven backward path. Never describe `git reset --hard` as an operator rollback for shared branches.

## Blocked pack

A blocked result must include:

- immutable base and branch state;
- completed files and commits;
- exact blocker and reproduction;
- validation already passed;
- unexecuted gates;
- whether the blocker is local, upstream, downstream, policy, credential, or external provider;
- safest next action.
