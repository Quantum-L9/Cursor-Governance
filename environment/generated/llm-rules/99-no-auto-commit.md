---
description: Never auto-commit or auto-push without explicit user approval
---

# No Auto Commit/Push Rule

## NEVER commit or push without explicit user approval

- **NEVER** run `git commit` without the user explicitly asking
- **NEVER** run `git push` without the user explicitly asking
- **NEVER** run `git add && git commit` chains without approval
- **NEVER** assume the user wants changes committed

## What to do instead

1. Make the code changes
2. Show the user what changed (diff or summary)
3. **WAIT** for the user to say "commit" or "push" or similar

## Acceptable triggers for commit/push

Only proceed with git operations when user says:
- "commit this"
- "push it"
- "commit and push"
- "save this to git"
- Or similar explicit instruction

## NOT acceptable triggers

- Completing a code change
- Fixing a bug
- "That looks good"
- Silence

## Adapter Autonomy Velocity waiver

When **all** of the following are true, this rule is **waived** for scoped
feature-branch `git commit` / `git push` and PR create/update:

1. `L9_GOVERNANCE_SURFACE` is an adapter (`claude-code`, `codex`, `gemini`, `manus`) — **not** `cursor`
2. `L9_AUTONOMY_ENABLED=true`
3. Action is on the Autonomy Surface Profile authorize list (`ops/autonomy/surface_profile.yaml`)

Merge, force-push, hard-reset, admin-merge, and secrets remain forbidden.
Cursor remains ask-first unless a campaign packet or `make pr` remediation path applies.
Projected override: `zz-autonomy-surface-override.md`.

<!-- generated-from: rules/99-no-auto-commit.mdc; do-not-edit -->
