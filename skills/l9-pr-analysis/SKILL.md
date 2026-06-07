---
name: l9-pr-analysis
description: analyze pull requests, review comments, merge blockers, gap status, and adoption strategy. use when the user asks about a PR, merge decision, review findings, or PR readiness.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, pr, review, merge, gap-analysis, blockers]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
---

# PR Analysis

## Purpose

Analyze pull requests with intelligence mode: review comments, file deltas, alignment, gap/deep eval, merge blockers, and git-native adoption recommendation. Present findings inline — no file generation unless the user requests a report.

## Core Contract

| Mode | Mutates code | Adoption | Load |
|------|--------------|----------|------|
| analyze | no | recommend only | [references/pr-analysis-workflow.md](references/pr-analysis-workflow.md) |
| babysit | yes (CI/fixes) | merge loop | [references/pr-babysitting.md](references/pr-babysitting.md) |

**Critical:** Adoption = merge via git. NEVER manually write PR files from a diff.

## Authority Order

1. Explicit PR number or URL and user merge intent.
2. GitHub ground truth — `gh pr view`, diff, review comments, CI status.
3. Repo policies — merge policy YAML, protected files, `AGENTS.md` CI rules when present.
4. This skill's references.
5. `Unknown` — do not invent alignment scores or blockers without evidence.

## Compact Workflow

1. **Memory + config** — lessons search; load merge policy, protected files, review config.
2. **Discovery** — PR metadata, diff, review comments (mandatory).
3. **Index scan** — class/function/import/test catalog when indexes exist.
4. **Intelligence** — size, protected surface, LOC delta, alignment, impact, regression.
5. **Gap + deep eval** — dimensional coverage on touched files; auto-fix classification.
6. **Blockers** — synthesize verdict: MERGE | MERGE WITH CONDITIONS | BLOCKED.
7. **Present inline** — v12 format; load `l9-ynp` for yes/no/proceed.
8. **Execute** — only after user confirms; git-native merge methods per workflow ref.

## Resource Map

- [references/pr-analysis-workflow.md](references/pr-analysis-workflow.md) — gated phases 0–9, inline output format, enforcement, CI handling.
- [references/pr-babysitting.md](references/pr-babysitting.md) — keep PR merge-ready loop.
- [references/pr-review-angles.md](references/pr-review-angles.md) — security, perf, tests, architecture lenses.
- [references/pr-template-github.md](references/pr-template-github.md) — PR body structure.

## Validation

Review comments MUST be read before verdict. Gap analysis and merge blocker assessment are mandatory. Manual file write from PR diff = CRITICAL violation — revert and re-merge via git.

## Failure Handling

- PR number missing → STOP; ask or list open PRs.
- Skip review comments → BLOCK analysis; fetch comments first.
- Protected file touched without approval → BLOCKED verdict.
- CI infra failure (steps: 0) → may proceed with local rebase merge per workflow ref.
- CI code failure → fix before merge; load `l9-ci-ops` or babysitting ref.
