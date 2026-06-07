---
name: l9-ci-ops
description: ci/cd pipeline status, fix failures, list gates, and author ci regression policies. use when github actions fails, make pr-check fails, or adding an enforceable ci gate.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, ci, github-actions, pr-check, policy, triage]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
disable-model-invocation: true
---

# CI/CD Operations

## Purpose

Operate CI/CD for the current repo: check pipeline status, fix failing gates, enumerate required gates from ground truth, and define new regression-prevention policies (policy-only mode).

## Core Contract

| Mode | Mutates code | Runs CI | Load |
|------|--------------|---------|------|
| status | no | read-only | [ci-fix-workflow.md](references/ci-fix-workflow.md) § Status |
| fix | yes | local verify required | [ci-fix-workflow.md](references/ci-fix-workflow.md) + [parallel-ci-triage.md](references/parallel-ci-triage.md) when multi-job |
| gates | no | no | [plasticos-ci-adapter.md](references/plasticos-ci-adapter.md) or repo `ci.yml` |
| ci-policy | no (config only) | no | [ci-policy-authoring.md](references/ci-policy-authoring.md) |

## Authority Order

1. User request and failing log excerpt / run ID.
2. Repo ground truth: `.github/workflows/ci.yml`, `Makefile` (`pr-check`), `AGENTS.md` CI section if present.
3. This skill's references.
4. `Unknown` — do not invent gate tables.

## Compact Workflow

1. **Detect repo** — PlasticOS loads [plasticos-ci-adapter.md](references/plasticos-ci-adapter.md); else read `ci.yml` + README.
2. **Route mode** — status | fix | gates | ci-policy per Core Contract.
3. **Fix path** — identify → categorize → fix → `make pr-check` (PlasticOS) or repo-equivalent → `make push` (never raw `git push` on PlasticOS).
4. **Policy path** — define → mechanism → scope → register → STOP (no code fixes).

## Resource Map

- [references/ci-fix-workflow.md](references/ci-fix-workflow.md) — status, fix, output format.
- [references/ci-policy-authoring.md](references/ci-policy-authoring.md) — regression policy authoring (no code fixes).
- [references/parallel-ci-triage.md](references/parallel-ci-triage.md) — parallel subagents for independent job failures.
- [references/plasticos-ci-adapter.md](references/plasticos-ci-adapter.md) — `make pr-check`, tier jobs, push workflow.

## Validation

Before declaring fix complete: local command matching the failed gate MUST pass. On PlasticOS: `make pr-check` MUST pass before `make push`.

## Failure Handling

- Missing run ID or logs → STOP; ask user or run `gh run list --limit 5`.
- Single-job failure → fix in main agent; do not spawn parallel triage.
- Policy intent vague → STOP at Phase 1 of ci-policy.
- Ground truth missing → label `Unknown`; do not use generic gate tables.
