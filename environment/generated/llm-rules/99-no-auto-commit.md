---
description: Ask-first git commit/push SSOT with L4 and autonomy-surface precedence
---

# Git mutation gate (ask-first)

**SSOT filename:** `99-no-auto-commit.mdc` · **id:** `l9.rule.git.mutation-gate`

## MUST NOT (Cursor default)

- Run `git commit` or `git push` (any form, including `--force`) without explicit user request
- Chain `git add && git commit` / assume approval from silence or "looks good"

## MAY without asking

- `git status`, `git diff`, `git log`, `git fetch`, `git branch` (read-only)

## Precedence (highest first)

1. **Mechanical gates** — `ops/autonomy/local_execution_gate.py`, L4 receipts, `merge_gate.py`
2. **`88-l4-local-autonomy`** — during an active L4 program: local commits authorized; mid-execution `make pr` and MCP `create_pull_request` / `push_files` denied until `authorize-release`. `git push` / `gh pr create` are off doctrine but not mechanically denied (CANONICAL_LAW §6.2.4)
3. **This rule** — Cursor ask-first for commit/push; waived only when all of:
   - `L9_GOVERNANCE_SURFACE` is an adapter (`claude-code`, `codex`, `gemini`, `manus`) — not `cursor`
   - `L9_AUTONOMY_ENABLED=true`
   - Action is on the Autonomy Surface Profile authorize list (`ops/autonomy/surface_profile.yaml`)
   - Or a campaign packet / `make pr` remediation path applies
4. Force-push, hard-reset, admin-merge, and secrets exfil: **never** waived

Projected override: `zz-autonomy-surface-override.md`.

## Approval phrases

Commit: "commit", "commit this", "commit and push", "save this to git".
Push: "push", "push it", "git push", "push to origin" (separate unless user said commit and push together).

<!-- generated-from: rules/99-no-auto-commit.mdc; do-not-edit -->
