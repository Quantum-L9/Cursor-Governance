---
name: Plan
overview: "Add a `.pre-commit-config.yaml` and adjust the `l9-pre-commit.yml` wrapper so `l9_pre_commit / validate-hook-config` and `pre-commit-passed` pass on PR #16, without pretending this repo has Python code."
todos:
  - id: add-config
    content: Create .pre-commit-config.yaml with pinned pre-commit-hooks v6.0.0 file-hygiene hooks
    status: completed
  - id: wrapper-install-cmd
    content: Override install-command to a no-op in l9-pre-commit.yml wrapper
    status: completed
  - id: fix-whitespace
    content: Strip trailing whitespace from the 6 affected tracked files
    status: completed
  - id: verify-local
    content: Run pre-commit validate-config and pre-commit run --all-files locally, plus npm verify:types/lint/test
    status: completed
  - id: push-verify-ci
    content: "Commit, push to feature/llm-control-plane-phase0-1, confirm the two named checks (and pre-commit-run/hook-version-drift) pass in PR #16"
    status: completed
isProject: false
---

# Fill the `.pre-commit-config.yaml` gap for PR #16

## Root cause (confirmed)

`l9-pre-commit.yml` calls `Quantum-L9/l9-ci-core/.github/workflows/pre-commit-ci.yml`, which has 4 jobs:

- `validate-hook-config` — runs `pre-commit validate-config .pre-commit-config.yaml`. Fails today because that file does not exist.
- `pre-commit-run` — runs `${{ inputs.install-command }}` (default `pip install -e .[dev]`) then `pre-commit run --all-files`.
- `hook-version-drift` — also runs `${{ inputs.install-command }}`, then greps the config for `astral-sh/ruff-pre-commit` / `mirrors-mypy` revs (only ever emits `::warning::`, never fails the job).
- `pre-commit-passed` — gates on `validate-hook-config` and `pre-commit-run` results only (ignores `hook-version-drift`).

Two things are needed, not just the config file: this repo has no `pyproject.toml`, so the default `install-command: pip install -e .[dev]` fails outright in `pre-commit-run`/`hook-version-drift` regardless of what the pre-commit config contains.

## Scope decision

This repo has no Python source, so the config will use **generic, language-agnostic file-hygiene hooks only** (from [pre-commit/pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks) `v6.0.0`) — not fabricated ruff/mypy entries, and not ESLint/tsc duplicated into pre-commit (those already run reliably in [ci.yml](.github/workflows/ci.yml) / [l9-lint-test-node.yml](.github/workflows/l9-lint-test-node.yml); wiring Node into a job that only provisions Python would add complexity for no real gain). `hook-version-drift` will simply warn "ruff/mypy not found" — non-blocking, matches `pre-commit-passed`'s actual gate logic.

## Changes

1. New file `.pre-commit-config.yaml` (repo root): `repo: https://github.com/pre-commit/pre-commit-hooks`, `rev: v6.0.0`, hooks: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-json`, `check-merge-conflict`, `check-added-large-files`, `check-case-conflict`.

2. [.github/workflows/l9-pre-commit.yml](.github/workflows/l9-pre-commit.yml): add `install-command: "true"` under `with:` so `pre-commit-run`/`hook-version-drift` don't try `pip install -e .[dev]` against a repo with no `pyproject.toml`.

3. Pre-fix 6 files with trailing whitespace so `pre-commit run --all-files` passes clean on its first CI run instead of failing on an auto-fix diff (confirmed via `git grep`, no other violations found — no missing-final-newline, no merge-conflict markers, no malformed YAML/JSON, no >500KB tracked files): `CODE_OF_CONDUCT.md`, `src/index.ts`, `src/budget/index.ts`, `src/matrices/general-matrix.ts`, `src/matrices/perplexity-matrix.ts`, `src/vision/index.ts`.

## Verification before push

- `pre-commit validate-config .pre-commit-config.yaml` (local binary at `/Users/ib-mac/Library/Python/3.9/bin/pre-commit`, v4.3.0)
- `pre-commit run --all-files` locally — expect all hooks to pass after the whitespace fix
- `npm run verify:types && npm run lint && npm test` — confirm the whitespace-only edits don't break anything
- Commit on `feature/llm-control-plane-phase0-1`, push, then re-check `gh pr checks 16` for `l9_pre_commit / validate-hook-config` and `pre-commit-passed` (plus `pre-commit-run`, `hook-version-drift`) turning green

## Out of scope (unchanged from prior report)

`l9_governance/*`, `l9_security`, `l9_scorecard`, `l9_pr_pipeline` (blocked by unpublished `l9-ci` package and a bad `ossf/scorecard-action@v2` ref upstream), and `L9 Analysis` remain red for the external reasons already documented in the [PR #16 comment](https://github.com/Quantum-L9/LLM-Router/pull/16#issuecomment-5020001087) — not touched by this plan.
