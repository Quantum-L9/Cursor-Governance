<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [ci, fix, status, github-actions]
status: active
/L9_META -->

# CI Fix Workflow

## Status

```bash
gh run list --limit 5
gh run view {RUN_ID} --json status,conclusion,jobs
```

Output: gate table with pass/fail per job.

## Fix (sequential)

### 1. Identify failures

```bash
gh run view {RUN_ID} --log-failed
```

If `gh` unavailable, use pasted log from UI.

### 2. Categorize

| Type | Typical fix |
|------|-------------|
| Lint | `ruff check --fix .` + `ruff format .` |
| Format | `ruff format .` |
| Static / XML / wiring | repo-specific scripts (see plasticos-ci-adapter) |
| Test | fix code or test fixture |
| Security | address finding; do not suppress |

### 3. Fix and verify

Run the **same command** the CI job ran, locally. PlasticOS: `make pr-check`.

### 4. Push (PlasticOS)

```bash
make push
```

Do NOT use raw `git push` on PlasticOS repos.

## Output format

```markdown
## CI STATUS

| Gate | Status | Details |
|------|--------|---------|
| lint | pass/fail | ... |

### Failures
| Test/Job | Error |
|----------|-------|

### Fix Plan
1. {action}
```
