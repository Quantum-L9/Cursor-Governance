<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: fix_engine
tags: [pr, fix, code, methodology, local-verify, batch]
owner: igor_beylin
status: active
version: 3.3.0
updated: 2026-08-16
/L9_META -->

# Fix Engine

## Purpose

Apply fixes for classified **codebase** findings. Independent clusters run concurrently (parallel agents/Tasks), then merge into one worktree batch, verify locally, and commit as ONE unit.

## Hard Rules

- MUST classify ownership before editing; never edit CI_PIPELINE surfaces.
- MUST read the target file before editing.
- MUST understand the surrounding context (imports, types, dependencies).
- MUST NOT change code unrelated to the finding.
- MUST NOT introduce new warnings or errors.
- MUST NOT edit until the [remediation plan](remediation-plan.md) has a disposition for every census finding.
- MUST NOT commit or push until ALL planned codebase fixes are applied AND Makefile + every pre-commit hook (when present) passed.
- MUST use the smallest diff that resolves the finding.
- MUST parallelize independent clusters by default; serialize only on conflicting file ownership.
- When a fix would require changes outside the PR's file scope, mark as deferred.
- NEVER push partial fixes — all or nothing per cycle for the codebase batch.

## Lesson Recall (before inventing a fix)

Before proposing a new patch, search the governance learning corpus for a matching known pattern:

```bash
rg -i "<error class or key phrase>" \
  "$HOME/.cursor-governance/learning/failures/repeated-mistakes.md" \
  "$HOME/.cursor-governance/learning/patterns/quick-fixes.md"
```

- If a match is found, apply that template (smallest diff that implements it).
- If no match, proceed with the smallest original fix.
- Do **not** auto-apply unmatched regex patches.
- Do **not** write `memory_log.json` or `session_status.md` (retired; Graphiti is session SSOT).

## Gate Discovery (MANDATORY FIRST STEP)

Before applying any fixes, enumerate ALL CI gates that can fail:

```bash
# Read all workflow files
find .github/workflows -name "*.yml" -o -name "*.yaml" | xargs cat
```

Extract every `run:` command from steps that can produce a non-zero exit. Build the **local verify command list**:

```yaml
local_verify_commands:
  - name: "type-check"
    command: "npx tsc --noEmit"
    source: ".github/workflows/build-and-validate.yml:step:Type check"
  - name: "lint"
    command: "npx eslint . --max-warnings 0"
    source: ".github/workflows/build-and-validate.yml:step:Lint"
  - name: "test"
    command: "npx vitest run"
    source: ".github/workflows/build-and-validate.yml:step:Test"
  - name: "build"
    command: "npm run build"
    source: ".github/workflows/build-and-validate.yml:step:Build"
  - name: "pipeline-dry"
    command: "npm run pipeline:dry"
    source: ".github/workflows/build-and-validate.yml:step:Pipeline dry run"
  - name: "validate"
    command: "node scripts/verify-launch-env.mjs --ci"
    source: ".github/workflows/build-and-validate.yml:step:Verify env"
```

Also check (these outrank ad-hoc command lists when present):
- `Makefile` targets: `agent-check`, `pr-check`, `check`, `ci`, `validate`, `test`
- `.pre-commit-config.yaml` — record hook ids that cover cited/planned paths; all-files pre-commit is not the default
- `package.json` scripts section for `lint`, `typecheck`, `test`, `build`, `validate`
- Any additional hooks in `.husky/` or `.git/hooks/` (must still run; never `--no-verify`)

## Fix Strategies by Type

### Lint Fixes

```bash
# Try auto-fix first
npx eslint --fix {file}        # JS/TS
ruff check --fix {file}         # Python
npx biome check --apply {file}  # Biome
```

If auto-fix fails, read the rule documentation and apply manually.

### Format Fixes

```bash
npx prettier --write {file}
ruff format {file}
```

Format fixes are always safe — apply without further analysis.

### Type-Check Fixes

1. Read the exact error: file, line, expected type vs actual type.
2. Check the type definition source (interface, type alias, imported type).
3. Apply the minimal fix:
   - Missing property → add it with correct type.
   - Wrong type → cast, narrow, or fix the source value.
   - Missing import → add the import.
   - Optional vs required mismatch → add `?` or provide default.
4. NEVER use `any` or `@ts-ignore` as a fix.

### Test Fixes

Priority order:
1. Fix the code under test (if the test caught a real bug).
2. Fix the test assertion (if the test expectation is wrong due to intentional code change).
3. Fix test setup/fixtures (if the test environment is stale).

NEVER delete a failing test unless the feature it tests was intentionally removed in the PR.

### Build Fixes

1. Missing module → add import or install dependency.
2. Syntax error → fix the syntax.
3. Circular dependency → restructure imports.
4. Missing file → check if it should exist (was it deleted accidentally?).

### Security Fixes

1. Dependency vulnerability → update to patched version.
2. Code vulnerability → apply the suggested remediation.
3. NEVER suppress a security finding without explicit user approval.

### Review Comment Fixes

1. **Suggestion block**: Apply the exact suggestion if it's correct on current source.
2. **Bug report**: Read the code, confirm the bug, apply minimal fix.
3. **Property/name correction**: Verify against type definitions, then rename.
4. **Missing null check**: Add the guard.
5. **Performance suggestion**: Apply only if clearly correct and low-risk.
6. **Code-review agent** (`github-code-quality[bot]`, Copilot): inspect the cited code first. Autofix patches are suggestions — apply only when validated. Invalid or already-fixed findings get a Disagreed / Acknowledged reply, not a silent skip. See [code-review-agents.md](code-review-agents.md).

## Local Verification Protocol (BLOCKING GATE)

After applying ALL planned fixes, run the verify stack in [remediation-plan.md](remediation-plan.md). Do not commit on a subset.

```bash
# 1) Makefile primary gate with cached UV_PYTHON (required when Makefile exists)
make pr-check   # or agent-check | check | ci | validate — first discovered

# 2) Cited/planned paths (even if the default toolchain excludes them)
# 3) Leftover workflow run: commands not covered by (1)
```

### Verification Rules

1. **Run ALL gates**, not just the one that was failing. A fix for one gate can break another.
2. **If ANY gate fails** → fix it immediately, then re-run ALL gates from scratch.
3. **Repeat until ALL gates pass.** Only then proceed to commit.
4. **If a fix for gate A breaks gate B** → the fix is wrong. Revert and find a better fix.
5. **If stuck in a loop** (fix A breaks B, fix B breaks A) → mark both as deferred with reason "circular regression".
6. **Maximum local verify iterations**: 5. If not green after 5 attempts, defer the problematic findings.

### What "locally" means

- Run the exact same command CI runs (from workflow YAML `run:` field).
- Use the same Node/Python version if possible.
- If a command requires env vars that are secrets (API keys), check if it has a `--ci` or `--skip-secrets` flag.
- If a command requires external services (database, API), check if it has a dry-run or mock mode.

## Batch Discipline

```text
┌─────────────────────────────────────────────────────────┐
│  ONE-AND-DONE:                                           │
│                                                          │
│  0. RUN_CONTRACT + this PR's plan (no edits)             │
│  1. Apply fix for every planned cluster + companions     │
│  2. make <primary-gate> with cached UV_PYTHON            │
│  3. Verify cited/planned paths                           │
│  4. Fix any new failures from 2-3                        │
│  5. Re-run 2-3 until green                               │
│  6. git add <planned files only>; git commit (hooks ON)  │
│  7. sanctioned publish (ONE) — PR_REMEDIATE=0 make pr    │
│                                                          │
│  ❌ NEVER: edit before the plan is complete              │
│  ❌ NEVER: commit after each fix                         │
│  ❌ NEVER: publish to see what CI says                   │
│  ❌ NEVER: git commit --no-verify                        │
│  ❌ NEVER: raw git push when Makefile pr exists          │
│  ❌ NEVER: git add -u / -A or git reset --hard           │
│  ❌ NEVER: merge this PR because it is now green         │
└─────────────────────────────────────────────────────────┘
```

## Commit Convention

The success path produces exactly ONE commit for the PR:

```
fix(pr-remediation): resolve {count} findings

Fixes:
- {finding-id}: {one-line description}
- {finding-id}: {one-line description}

Local verify: make {target} + pre-commit ({hook ids}) passed
Deferred:
- {finding-id}: {reason}

Remediation-Cycle: {repo}#{pr}/cycle-1
```

## Rollback Protocol

If a fix introduces a NEW CI failure that didn't exist before:

1. `git diff HEAD~1` — identify the problematic change.
2. Revert only that specific change.
3. Mark the original finding as `deferred` with reason: "fix causes regression".
4. Re-run local verify to confirm revert is clean.
5. Continue with remaining fixes.
6. Report the regression in the convergence block.
