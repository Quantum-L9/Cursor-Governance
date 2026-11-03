---
description: Review ergonomics, PR size guidance, and checklists for L9.
paths:
- .github/PULL_REQUEST_TEMPLATE*
- .github/ISSUE_TEMPLATE*
- '**/*.md'
---

# Review ergonomics (L9)

## PR size and scope

- Prefer **small, focused PRs** over large mixed changes.
- Target **≤400 LOC** per PR when practical; split larger work into reviewable chunks.
- If a change grows beyond a reasonable diff size, consider splitting into separate, reviewable chunks.

---

## Commit message format

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`

| Type | Use for |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Tests only |
| `refactor` | Code change, no behavior change |
| `ci` | CI/CD changes |
| `chore` | Maintenance |

- Breaking changes: `type!:` prefix or `BREAKING CHANGE:` footer.
- Commit messages describe **intent** only — they do not authorize `git push` (see `99-no-auto-commit.mdc`).

---

## Review checklist

- For each PR, reviewers should confirm:
  - Scope is clearly described and limited.
  - Critical invariants (safety, memory, protected-core, infra) are respected.
  - Appropriate tests were added or updated (see `50-qa-testing.mdc`).
  - Risk and rollback plan are briefly described for high-impact changes.

---

## Templates and documentation

- Keep PR and issue templates aligned with these review rules.
- Use documentation (`*.md`) to clarify intent and risks for non-trivial changes.

---

## GMP reports

Optional — never required, never forbidden. Location (`reports/gmp/`) and name
(`GMP-Report-<NNN>-<Description>.md`) are defined once in `81-gmp-audit.mdc`.

---


## Cursor Brief Policy

**Path for Cursor-generated briefs:** `/docs/cursor-briefs/`

**When to create a brief:**
- Analysis summaries that don't warrant a full GMP report
- Status snapshots during exploration
- Temporary reference docs during debugging

**When a GMP report fits better than a brief (reports are optional):**
- Any change that modifies code — `reports/gmp/GMP-Report-<NNN>-<Description>.md`
- Any execution with TODO plan — use GMP report
- Post-deployment verification — use GMP report

**NEVER CREATE BOTH:** for one piece of work, a GMP report or a brief, not both.

**Anti-patterns:**
- ❌ Saving briefs to `/docs/` root (contaminates user docs)
- ❌ Creating brief AND report for same work
- ❌ Creating briefs without clear purpose

**User docs folder (`/docs/`):** Reserved for Igor's documentation. Cursor should not save files here directly.

---

## workflow_state.md Update Protocol

**Path:** `/workflow_state.md` (project root)

**MANDATORY:** Update `workflow_state.md` after:
- Every GMP or `/gmp` execution (add to Recent Changes)
- Any code change that modifies repository structure
- Major architectural decisions (add to Decision Log)
- Phase transitions (update PHASE section)
- Test runs with results (update Test Status)
- TODO completion (update Active TODO Plan)

**DO NOT update for:**
- Informational queries that change nothing
- Read-only analysis or exploration
- Simple clarification questions

### Required Sections

| Section | When to Update |
|---------|----------------|
| `## PHASE` | On phase transitions |
| `## Active TODO Plan` | When TODOs added/completed |
| `## Files in Scope` | When working on new files |
| `## Test Status` | After test runs |
| `## Recent Changes` | **EVERY change** (prepend newest at top) |
| `## Decision Log` | Major decisions only |
| `## Open Questions` | When blockers identified |
| `## Next Steps` | At session end or priority change |
| `## Recent Sessions` | At session end (7-day window) |

### Recent Changes Format

```
- [DATE] [PHASE] Files: file1.py, file2.py | Action: Brief description | Tests: pass/fail/not run
```

### Recent Sessions Format

```
- ✅ YYYY-MM-DD: Brief session summary with key outcomes
```

- Mark completed sessions with `✅`
- Keep only 7 days of history
- Add new entries at TOP (newest first)

### Anti-patterns

- ❌ Skipping update after GMP execution
- ❌ Verbose descriptions (keep entries concise)
- ❌ Updating for read-only queries
- ❌ Forgetting to mark sessions with ✅

---

<!-- generated-from: rules/72-review-ergonomics.mdc; do-not-edit -->
