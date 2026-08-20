---
name: Align checker pins
overview: Apply the scoped SAST/checker lockstep (Pyright no longer requires .venv; pin ruff/semgrep/mypy in requirements-dev; pin advisory semgrep; fix the pre-commit comment) and locally commit only three safe files so the rest of the dirty tree stays unstaged.
todos:
  - id: preflight-stage-guard
    content: Confirm HEAD SHA, current branch, and that make commit is forbidden; list allowed stage set (3 files) vs l9-analysis.yml edit-only
    status: completed
  - id: keep-pyright-no-venv
    content: Keep pyproject.toml [tool.pyright] without venvPath/venv; do not reintroduce those keys
    status: completed
  - id: pin-requirements-dev
    content: Add ruff==0.15.5, semgrep==1.164.0, mypy==1.14.0 to requirements-dev.txt to match ci.yml
    status: completed
  - id: fix-precommit-comment
    content: Change .pre-commit-config.yaml lockstep comment from (>=0.15,<0.16) to ==0.15.5
    status: completed
  - id: pin-l9-analysis-untracked
    content: Pin semgrep==1.164.0 in l9-analysis.yml; leave the file untracked (needs sibling .github/governance/)
    status: completed
  - id: verify-then-local-commit
    content: git add exactly the 3 allowed paths, verify cached name-only, commit locally with conventional message; no push; no make commit
    status: completed
isProject: false
---

# Align SAST checker pins (local commit only)

**l9-plan:** skill loaded from `~/.claude/skills/l9-plan` (already installed globally; do not copy it into this repo). Depth **standard** (risk=low, evidence=sufficient). Execute later via this plan — do not free-form widen scope.

**Branch now:** `docs/agent-docs-refresh-and-repo-index` @ `169d9d5358b23de02ad9b07d186f9985e9ac9b5f`

**User lock:** settings-optimization files only. Unrelated dirty tree stays unstaged. No push. No PR. No `make venv`. No L9-managed `.vscode` keys.

## Objective

Stop Cursor Pyright from failing workspace settings when `.venv` is missing, and make the checker version pins one list instead of three implicit sites — then snapshot that slice in a local commit before other agents overwrite it.

## Immutable constraint: do not use `make commit`

[`Makefile`](Makefile) `commit` runs `git add -u` plus every untracked file except `.cursor-commands`. That would commit the entire dirty tree (deleted workflows, agent-docs, untracked `.claude/skills/*`, `memory-bank/`, etc.).

Execution must `git add` **exact paths only**, then `git commit`.

## What to change

### 1. Already done — include in commit

[`pyproject.toml`](pyproject.toml) `[tool.pyright]`: `venvPath` / `venv` removed. Keep mode `basic` and reporters. Working-tree diff vs HEAD is only this slice (6 lines).

### 2. Add pins to [`requirements-dev.txt`](requirements-dev.txt)

Today this file pins pytest only. CI already uses:

- `ruff==0.15.5` ([`.github/workflows/ci.yml`](.github/workflows/ci.yml) lint job)
- `semgrep==1.164.0` and `mypy==1.14.0` (static-checks job)

Add those three lines (with a one-line comment that they match `ci.yml`). Do not touch `pr-repair` or pytest pins. Do not edit [`requirements.txt`](requirements.txt) (Odoo.sh).

### 3. Comment-only in [`.pre-commit-config.yaml`](.pre-commit-config.yaml)

Line 18 still says `required-version (>=0.15,<0.16)`. Change the comment to `==0.15.5`. Leave `rev: v0.15.5` unchanged.

### 4. Pin advisory Semgrep — edit, do not stage

[`.github/workflows/l9-analysis.yml`](.github/workflows/l9-analysis.yml) line 89 is `pip install --upgrade pip semgrep` (unpinned). Change to `pip install --upgrade pip semgrep==1.164.0`.

This file is **untracked** and its job reads untracked [`.github/governance/`](.github/governance/). Staging it alone would land a broken workflow. Apply the pin in the working tree; leave the file untracked with its sibling governance WIP.

## Allowed staged set (exactly these three)

- `pyproject.toml`
- `requirements-dev.txt`
- `.pre-commit-config.yaml`

Pre-commit hook: if it auto-modifies any of those three, create a **new** commit (do not amend). If it stages anything else, unstage the extras before committing.

## Success properties (falsifiable)

- `grep -n 'venvPath\\|venv =' pyproject.toml` has no `[tool.pyright]` hits
- `requirements-dev.txt` contains `ruff==0.15.5`, `semgrep==1.164.0`, `mypy==1.14.0`
- `.pre-commit-config.yaml` comment says `==0.15.5` and `rev: v0.15.5`
- `l9-analysis.yml` has `semgrep==1.164.0` and `git status` still shows it untracked
- `git diff --cached --name-only` equals the three allowed paths
- `git log -1` is a new local commit; `git status -sb` still shows the rest of the dirty tree
- no `git push`

## Out of scope

- `make venv`, `.envrc`, `odools.toml`, `.vscode/settings.json` (L9-managed keys)
- `Makefile` `venv` target (already pins the same versions as a second pip line)
- `ci.yml` pins (already correct)
- Promoting l9-analysis rules to blocking
- Pyright/mypy as a CI gate
- `biome.json`, `.editorconfig`, `pyrightconfig.json`
- Committing `.claude/skills/l9-plan` or any other untracked skill
- Push, PR, merge, `make push`
- Full `make pr-check` on this dirty tree (non-diagnostic; unrelated WIP would fail-closed)

## Stress and disconfirm

- If `make commit` is used, the whole dirty tree lands — **blocked by explicit path add**.
- If `l9-analysis.yml` is staged without `.github/governance/`, CI gains a broken advisory workflow — **blocked by do-not-stage**.
- If pre-commit reformats more than the three files, extras must be unstaged.
- Rollback: `git reset --soft HEAD~1` if the commit is still local and unpushed.

## Leverage

Shared cause: checker versions lived in CI/Makefile comments but not in `requirements-dev.txt`, so a missing `.venv` plus PATH Ruff 0.14.11 looked like a settings bug. One pin list is the fix. Pyright `venv` keys were a second hard dependency on that missing env.

## Doc / root surface

N/A for AGENTS.md / LOCAL_DEV_SETUP this slice — lockstep text already names `==0.15.5`. Do not refresh agent docs in this commit.

## Execute via program-execution + autonomy

When Build is approved: attach `@environment/program-execution` + `/autonomy` under a Program lease, or a single Cursor agent that stays inside this envelope. `autonomous_merge: false`. No network except none required (pin strings are already in `ci.yml`).

Campaign packet stub: local-only, `fs` write = the four paths above, `git add` = the three allowed paths, `git commit` allowed, `git push` forbidden.

## Validation (execution, not plan mode)

```bash
# after edits, before commit
git add -- pyproject.toml requirements-dev.txt .pre-commit-config.yaml
git diff --cached --name-only
# must print exactly those three paths
```

Do not run full `make pr-check` until the unrelated dirty tree is isolated. Pin grep is the quality gate for this slice.
