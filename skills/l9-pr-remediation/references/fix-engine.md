<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: fix_engine
tags: [pr, fix, code, methodology, local-verify, batch]
owner: igor_beylin
status: active
version: 3.5.0
updated: 2026-08-18
/L9_META -->

# Fix Engine

## Purpose

Apply fixes for classified **codebase** findings. Independent clusters run concurrently (parallel agents/Tasks), then merge into one worktree batch, verify locally, and commit as ONE unit.

## Hard Rules

- MUST classify ownership before editing; never edit CI_PIPELINE surfaces.
- MUST read the target file before editing.
- MUST understand the surrounding context (imports, types, dependencies).
- MUST NOT change code unrelated to the finding.
- MUST NOT invent a fix when `root_cause` is `Unknown` or confidence is `low`.
- MUST NOT introduce new warnings or errors.
- MUST NOT edit until the [remediation plan](remediation-plan.md) has a disposition for every census finding.
- MUST NOT commit or push until ALL planned codebase fixes are applied AND `make precommit-repo` passed.
- MUST use the smallest diff that resolves the finding.
- MUST parallelize independent clusters by default; serialize only on conflicting file ownership.
  Launch each cluster as Task type `l9-pr-remediation` with
  `L9_ADMISSION_TOKEN=…` from `mint_admission.py`. Do not spawn generic
  `explore` / `generalPurpose` for remediator work.
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

When a Makefile exists, the public local gate **is** `pr-check`. Do not build a second suite from every workflow `run:`.

```bash
# PUBLIC verbs
test -f Makefile && { grep -E '^(pr-check|pr|improve):' Makefile || true; }
```

```yaml
local_verify_commands:
  - name: "pr-check"
    command: "PR_BASE=origin/main make precommit-repo"
    source: "Makefile:pr-check"
```

Also record (do not all-run unless no Makefile `pr-check`):
- `.pre-commit-config.yaml` hook ids that cover **cited/planned** paths; all-files pre-commit is not the default and is not the public gate
- `package.json` scripts only as leftover fallback when no `pr-check`
- Workflow `run:` commands only when no Makefile `pr` / `pr-check` exists (see [run-contract.md](run-contract.md))

Never `--no-verify`. Never `pre-commit install`. Never `make precommit` as shipping verify.

## Fix Strategies by Type

### Lint Fixes

```bash
# Try auto-fix first — use the repo's owned formatter only
npx eslint --fix {file}        # JS/TS when eslint owns the file
ruff check --fix {file}         # Python
npx biome check --write {file}  # JS/TS/JSON when biome owns the file
```

If auto-fix fails, read the rule documentation and apply manually.

### Format Fixes

Use the workspace formatter owner (see `AGENTS.md` formatter table). Do not reformat a file with a competing tool. Format-on-save for Markdown is off in this host so governance docs do not churn — do not `prettier --write` Markdown unless the finding is a Markdown format gate.

```bash
ruff format {file}              # Python only
npx biome check --write {file}  # when biome owns the language
```

Format fixes are **not** always safe. A cross-owner reformat is a protocol violation.

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
# 1) Makefile public gate with cached UV_PYTHON (required when Makefile exists)
PR_BASE=origin/main make precommit-repo

# 2) Cited/planned paths (even if the default toolchain excludes them)
# 3) Workflow run: leftover ONLY when no Makefile pr-check exists
```

### Verification Rules

1. **Run ALL gates**, not just the one that was failing. A fix for one gate can break another.
2. **If ANY gate fails** → fix it immediately, then re-run ALL gates from scratch.
3. **Repeat until ALL gates pass.** Only then proceed to commit.
4. **If a fix for gate A breaks gate B** → the fix is wrong. Revert and find a better fix.
5. **If stuck in a loop** (fix A breaks B, fix B breaks A) → mark both as deferred with reason "circular regression".
6. **Maximum local verify iterations**: 5. If not green after 5 attempts, defer the problematic findings.

### What "locally" means

- Run `make precommit-repo` — not a reconstructed list of CI `run:` lines. Do not run `make pr-check`.
- Use the locked `.venv` interpreter / cached native `UV_PYTHON`.
- If a command requires env vars that are secrets (API keys), check if it has a `--ci` or `--skip-secrets` flag.
- If a command requires external services (database, API), check if it has a dry-run or mock mode.

## Batch Discipline

```text
┌─────────────────────────────────────────────────────────┐
│  ONE-AND-DONE:                                           │
│                                                          │
│  0. RUN_CONTRACT + this PR's plan (no edits)             │
│  1. Apply fix for every planned cluster + companions     │
│  2. make precommit-repo (hooks plus ruff)                │
│  3. Verify cited/planned paths                           │
│  4. Fix any new failures from 2-3                        │
│  5. Re-run 2-3 until green                               │
│  6. git add <planned files only>; git commit (hooks ON)  │
│  7. remediator sanctioned publish (ONE) — git push       │
│                                                          │
│  ❌ NEVER: edit before the plan is complete              │
│  ❌ NEVER: commit after each fix                         │
│  ❌ NEVER: publish to see what CI says                   │
│  ❌ NEVER: git commit --no-verify                        │
│  ❌ NEVER: make pr / make pr-check (ceremony)            │
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

Local verify: make precommit-repo passed
Deferred:
- {finding-id}: {reason}

Remediation-Cycle: {repo}#{pr}/cycle-1
```

## Rollback Protocol

If a fix introduces a NEW local-verify failure that didn't exist before (still uncommitted):

1. `git diff` (working tree vs HEAD) — identify the problematic hunk. Do not use `HEAD~1` unless that commit was this cycle's single remediation commit.
2. Revert only that specific change.
3. Mark the original finding as `deferred` with reason: "fix causes regression".
4. Re-run `make precommit-repo` to confirm revert is clean.
5. Continue with remaining planned fixes.
6. Report the regression in the convergence block. Never `--no-verify`. Never invent a passing result.
