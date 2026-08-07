<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: fix_engine
tags: [pr, codebase-only, fix, local-verify, batch, rollback]
owner: igor_beylin
status: active
version: 3.5.0
updated: 2026-07-28
/L9_META -->

# Fix Engine

## Purpose

Apply only accepted `CODEBASE_REPAIR` findings. Batch, verify, and commit codebase fixes as one unit per cycle. Never repair a `CI_PIPELINE_SIGNAL`.

## Hard Scope Gate

Before editing, assert all are true:

- finding ownership is `CODEBASE_REPAIR`;
- target is normal source, test, fixture, package dependency, or codebase-owned artifact;
- change does not alter CI orchestration, infrastructure, permissions, secrets, policy, shared CI, or required-check definitions;
- change is inside resolved PR scope;
- current source and evidence support the repair.

If any assertion fails, do not edit. Route to CI signal, deferment, human decision, or false-positive handling.

## Forbidden Mutation Surfaces

Never modify in this Skill:

- `.github/workflows/**`;
- `.github/actions/**`;
- reusable workflow definitions or call contracts;
- action pins or workflow permissions;
- runner labels/images or CI environment provisioning;
- branch protection, check names, merge queue, repository settings;
- secrets, OIDC, environments, external scanner integration;
- CI-only scripts, caches, service orchestration, or shared CI packages;
- quality-tool configuration when the purpose is changing or bypassing enforcement.

Read these surfaces only to diagnose and produce evidence.

## Codebase Fix Strategies

### Lint and Format

Run the configured formatter or linter against affected code. Apply automated source fixes only when they do not change CI configuration.

```bash
npx eslint --fix {file}
ruff check --fix {file}
npx biome check --write {file}
npx prettier --write {file}
ruff format {file}
```

### Type Check

Read the exact error and type source. Fix annotations, interfaces, imports, narrowing, defaults, and implementation values. Never use `any`, `@ts-ignore`, or configuration weakening as a shortcut.

### Tests

Fix implementation first, then stale fixtures or assertions only when current intended behavior proves they are wrong. Never delete a failing test to obtain green status.

### Build

Fix source imports, syntax, module declarations, package metadata, and generated artifacts when they are normal codebase responsibilities. Missing runner tools, workflow paths, or CI environment setup are signals, not build fixes.

### Security

Update a vulnerable dependency or repair vulnerable source when it is a normal codebase change. Scanner configuration, policy, token, permissions, or service failures are CI signals.

### Review Comments

Apply only current-code-valid codebase suggestions. Route comments requesting workflow, action, runner, policy, secret, or CI configuration changes to `SIGNAL_CI`.

## Local Verification Protocol

Run every locally reproducible required command without editing its CI definition:

1. run all codebase gates, not only the previously failing one;
2. classify every failure by ownership;
3. repair only `CODEBASE_REPAIR` failures;
4. render issue files for `CI_PIPELINE_SIGNAL` failures;
5. rerun all codebase gates after changes;
6. allow no more than three local verification iterations;
7. push only when every locally reproducible codebase gate is green.

A local failure caused by an invalid CI wrapper does not authorize changing the wrapper. Run the underlying trustworthy code command when discoverable and signal the wrapper defect separately.

## Batch Discipline

```text
WITHIN ONE CYCLE:
  1. classify all findings by ownership
  2. render all CI issue files
  3. apply all accepted codebase fixes
  4. run all locally reproducible codebase gates
  5. repeat codebase repair and verification up to three iterations
  6. commit codebase changes once, or make no commit
  7. push once, or make no push
```

Never include generated issue files in the PR commit. They belong only in the run deliverable.

## Commit Convention

```text
fix(pr-remediation): cycle {N} - resolve {count} codebase findings

Codebase fixes:
- {finding-id}: {description}

CI signals routed:
- {signal-id}: {issue-file-path}

Local verify: {passed}/{total} reproducible codebase gates passed
Remediation-Cycle: {repo}#{pr}/cycle-{N}
```

The `Remediation-Cycle:` trailer is the commit idempotency key.

## Rollback Protocol

If a codebase fix introduces a new failure:

1. identify the exact change;
2. classify the new failure by ownership;
3. revert the codebase change when it caused the regression;
4. if the new failure is pipeline-owned, keep the valid codebase fix and emit a CI signal;
5. rerun all codebase gates;
6. record the regression and outcome.
