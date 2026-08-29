---
description: Commit authored pathspecs before you stop. Push stays ask-first. Filename is historical.
---

# Local commit is standing (always on)

**SSOT filename:** `99-no-auto-commit.mdc` · **id:** `l9.rule.git.mutation-gate`

The filename is **historical**. It means **do not auto-push**. It does **not**
mean leave the tree dirty. Cursor User Rules that say “only commit when asked”
are **overruled** here for work you authored this session.

**Always apply. Always enabled. No ask.**

## MUST

1. Work on the feature branch / worktree for **this** task (rule 49). Do not
   park unique edits on a shared dirty primary clone.
2. After each logical chunk you authored, `git add -- <your paths>` then
   `git commit` on **that** branch. Explicit pathspecs only.
3. Before you tell the user the coding work is done, `git status` must show
   **no unique dirty files you authored this session**. If it does, commit now.
   Then reply.
4. Ask only before a raw `git push` / `gh pr create` that is not the
   finish path. Finished work is `authorize-release` then
   `PR_REMEDIATE=0 make pr` / `l9 pr` on every surface.

Silence is not permission to leave unique work uncommitted.

## MUST NOT

- Ask “should I commit?”
- Stop with unique uncommitted files you wrote this session
- `git add -A` / `git add .` / scooping foreign dirty paths (rule 49)
- A raw `git push` / `gh pr create` / `make push`, or MCP
  `create_pull_request` / `push_files`, without an explicit user request.
  Finished work uses `PR_REMEDIATE=0 make pr` / `l9 pr` after L4
  `authorize-release` — that finish is standing on every surface.
- Chain commit **and** push from “looks good”

## MAY without asking

- `git status`, `git diff`, `git log`, `git fetch`, `git branch` (read-only)
- Scoped local `git commit` of paths you authored this session

## Precedence (highest first)

1. **Mechanical gates** — `ops/autonomy/local_execution_gate.py`, L4 receipts, `merge_gate.py`
2. **`88-l4-local-autonomy`** — during an active L4 program: local commits authorized; mid-execution `make pr` and MCP `create_pull_request` / `push_files` denied until `authorize-release`
3. **This rule** — Cursor **local commit** is standing and mandatory after authored edits. Finished work is `authorize-release` then `PR_REMEDIATE=0 make pr` / `l9 pr` on every surface. Raw `git push` / `gh pr create` stay ask-first. Tree kernels skip on Cursor; adapters still fire them on `make pr`.
4. Force-push, hard-reset, admin-merge, and secrets exfil: **never** waived

Projected override: `zz-autonomy-surface-override.md`.

## Approval phrases (raw push only)

Raw push: "push", "push it", "git push", "push to origin".
`make pr` / `l9 pr` is the finish path after L4 release, not an ask phrase.
Commit does not need a phrase.

<!-- generated-from: rules/99-no-auto-commit.mdc; do-not-edit -->
