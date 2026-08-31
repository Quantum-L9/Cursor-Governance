<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: ownership_boundary
tags: [pr, ownership, codebase, ci-pipeline, edit-axis]
owner: igor_beylin
status: active
version: 3.3.0
updated: 2026-08-30
/L9_META -->

# Ownership Boundary

Classify before any edit. This skill repairs **codebase** defects only.

**This file is the edit axis and nothing else.** Ownership answers one question:
may I patch this file? It never decides what happens to the pull request. That
verdict — `merge` / `fix` / `wait` / `leftover` — comes from
`ops/autonomy/pr_board.py`, which reads required-check identity and conflicted
paths. `edit=CI_PIPELINE` is not `board=leftover`: a pipeline you may not patch
can still be a PR GitHub will merge, and reading these classes as PR outcomes is
what parked six mergeable PRs on 2026-08-30.

## CODEBASE

Defect in source, tests, fixtures, package dependencies, or normal runtime artifacts.

Examples: type errors, implementation bugs, stale fixtures, missing imports, lint/format violations in source, dependency bumps that do not change CI policy, build failures caused by repo code.

## CI_PIPELINE

Repair would change CI orchestration, infra, or enforcement — not compliant code.

Read-only surfaces (never edit here):

- `.github/workflows/**`, `.github/actions/**`, reusable workflows
- action pins, runners, permissions, secrets, OIDC, environments
- branch protection, required-check names, merge queue, check wiring
- CI-only scripts, caches, service containers, centralized CI templates
- contradictory lint/type config when the needed change alters enforcement rather than code
- missing secrets / provisioning / third-party outages

**Action:** cite evidence in the cycle status. Do not edit. Do not emit issue-file bundles or tarballs. Continue every independent codebase cluster. Then let the board decide the PR: if the failing check is **required** and cannot be fixed without editing CI, declare it (`pr_board.py --unfixable-check "{name}"`) and that PR is `leftover`. If the check is not in the required set, it never blocked merge.

## ENVIRONMENT

Interpreter, arch, ABI, or venv failure (cryptography native-ext import, Rosetta miniconda on arm64, broken SSOT `.venv`). Not a source defect.

**Action:** run the venv preflight once ([run-contract.md](run-contract.md)). Export `UV_PYTHON` to uv-managed **native** CPython. Do not use `uv python find --system` (conda `base` wins). Do not edit source. Do not unpin lock pins. Do not symlink a failing SSOT venv. Do not edit the Makefile from this skill. Continue every independent codebase cluster.

## HUMAN

Needs product, architecture, legal, or security-exception judgment.

**Action:** name the decision in the reply (linked issue if Deferred), resolve the thread, finish all independent codebase work, then pass the decision to `pr_board.py --human-decision "{decision}"` so that PR is `leftover` on a named decision rather than on a hunch. An unnamed "feels like a human call" is not a decision and does not park a PR. GitHub conversation resolution is itself a merge blocker — do not leave `isResolved: false`.

## Code-review agents

Validated `github-code-quality[bot]` / Copilot findings that are real source defects are **CODEBASE**. They are review comments, not a separate scanner class and not skippable chatter. See [code-review-agents.md](code-review-agents.md).

## FALSE_POSITIVE

Current evidence disproves the signal on the evaluated head.

**Action:** reply with evidence; resolve when appropriate. Code-review agent false positives still require a Disagreed reply — do not drop the thread.

## Decision Test

1. Fixable by changing normal source/tests/fixtures/deps without changing how CI is orchestrated?
2. Would the fix touch a CI_PIPELINE surface or policy?
3. Does the same source command fail locally for the same code reason?
4. Is the failure CI-environment / credentials / workflow-expression specific?

Edit only when (1) yes and (2) no. Unknown ownership → do not edit that cluster.

## Mixed Jobs

Split one failed job into multiple root causes. Repair codebase pieces; note pipeline pieces. Never modify CI to expose or bypass a code failure.
