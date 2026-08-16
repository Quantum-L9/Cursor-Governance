<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: finding_classifier
tags: [pr, classification, triage, severity]
owner: igor_beylin
status: active
version: 3.2.0
updated: 2026-08-16
/L9_META -->

# Finding Classifier

## Purpose

Classify each ingested finding by **ownership first**, then severity and fix strategy. Determines what may be edited and what runs in parallel this cycle.

## Ownership (before severity)

| Class | Edit? | Action |
|-------|-------|--------|
| **CODEBASE** | yes | Fix in the concurrent batch |
| **CI_PIPELINE** | no | Note in status; continue other clusters |
| **HUMAN** | no | Name the decision; continue other clusters |
| **FALSE_POSITIVE** | no | Reply with evidence |

See [ownership-boundary.md](ownership-boundary.md). Unknown ownership → do not edit that cluster.

## Severity Classification

| Severity | Definition | Action |
|----------|-----------|--------|
| **blocking** | CI gate failure that prevents merge | Fix immediately, cycle 1 priority |
| **actionable** | Review comment with a clear, implementable suggestion | Fix after blocking items resolved |
| **discussion** | Review comment asking a question or proposing alternatives | Do not fix; **still reply**. Code-review agent comments in this bucket are never silently dropped. |
| **deferred** | Requires human decision, architectural change, or external dependency | Do not fix; **still reply** with reason |

## CI Failure Classification

| Gate Type | Indicators | Fix Strategy |
|-----------|-----------|--------------|
| lint | `ruff`, `eslint`, `biome`, lint rule violations | Auto-fix with linter's `--fix` flag, then manual for unfixable |
| format | `prettier`, `ruff format`, formatting diff | Run formatter |
| type-check | `tsc`, `mypy`, `pyright`, type errors | Fix type annotations, add missing types, correct interfaces |
| test | `jest`, `pytest`, `vitest`, assertion failures | Fix code or update test expectations (prefer fixing code) |
| build | `tsc --noEmit`, `vite build`, compilation errors | Fix imports, missing modules, syntax errors |
| security | `npm audit`, `snyk`, `trivy`, vulnerability reports | Update dependencies or apply patches |

## Review Comment Classification

**Code-review agents** (`github-code-quality[bot]`, Copilot — [code-review-agents.md](code-review-agents.md)) skip none of the steps. Severity **Error** / **Warning** that validates on current source is `actionable`. **Note** and discussion-shaped member comments still get inspect + reply (Acknowledged / Disagreed / Deferred). `skip_bot_discussions` does not apply.

### Actionable Indicators

A review comment is **actionable** when it:
- Contains a specific code suggestion (GitHub suggestion block or inline code)
- Points to a concrete bug ("this will throw because X is undefined")
- Identifies a type mismatch with the fix implied
- References a missing import, wrong property name, or incorrect API usage
- Says "should be X" or "change Y to Z"

### Discussion Indicators

A review comment is **discussion** when it:
- Asks "have you considered..." or "what about..."
- Proposes an architectural alternative without a concrete fix
- Questions a design decision without asserting it's wrong
- Uses "nit:" prefix (unless the nit has a clear one-line fix)
- Requests explanation rather than change

### Deferred Indicators

A review comment is **deferred** when it:
- Requires adding a new dependency or service
- Suggests a refactor spanning multiple files not in the PR diff
- Conflicts with another review comment
- Requires user/owner decision on direction
- References external systems not accessible to the agent

## Execution Priority

```text
1. blocking (CI failures) — ordered by: build > type-check > lint > test > security
2. actionable (review comments, including validated code-review agent findings) — file proximity to CI failures first, then top-to-bottom
3. discussion — no code change; reply required (especially code-review agents)
4. deferred — no code change; reply required with reason
```

## Conflict Resolution

When findings conflict:
- CI requirement wins over review suggestion (CI blocks merge).
- Later review comment wins over earlier one from same author.
- Human reviewer wins over bot reviewer when they conflict.
- When two humans conflict → defer to user.

## Output

After classification, produce:

```yaml
classified_findings:
  blocking: [{finding}...]
  actionable: [{finding}...]
  discussion: [{finding}...]
  deferred: [{finding, reason}...]

execution_plan:
  cycle_scope: [list of finding IDs to fix this cycle]
  estimated_files: [list of files to modify]
  local_verify_commands: [Makefile target + every pre-commit hook + leftover workflow commands]
```

Promote this object into the full ledger in [remediation-plan.md](remediation-plan.md) (`disposition` + `status` on every finding) before any edit.

## Batch Planning Rule

The plan MUST include ALL findings from the census. Do NOT plan to fix one finding at a time, and do not edit until every finding has a disposition.
1. Fix all blocking findings.
2. Fix all actionable findings (including validated code-review agent items).
3. Run Makefile + every `.pre-commit-config.yaml` hook + leftover local commands.
4. Commit once. Push once. Remote CI is confirmation, not a second planning loop.
