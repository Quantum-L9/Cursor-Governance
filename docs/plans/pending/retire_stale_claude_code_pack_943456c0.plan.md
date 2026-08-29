---
name: Retire stale Claude Code pack
overview: Confirm WIP/l9-claude-code-env-pack has zero content that isn't already merged into environment/claude-code/, then remove the stale WIP copy under explicit deletion approval.
todos:
  - id: reverify
    content: Re-run diff -rq against environment/claude-code/ immediately before deletion to confirm no new drift
    status: pending
  - id: confirm-delete
    content: Show the exact file list and get explicit user approval to delete (governance requires this every time)
    status: pending
  - id: delete
    content: rm -rf WIP/l9-claude-code-env-pack/ after approval
    status: pending
  - id: verify-clean
    content: Confirm git status shows a clean state with no residual references to the folder
    status: pending
isProject: false
---

# Retire stale Claude Code pack (WIP/l9-claude-code-env-pack)

## Finding (already verified in this session)

`WIP/l9-claude-code-env-pack/` is a hand-made distributable snapshot that fed [PR #23](https://github.com/Quantum-L9/Cursor-Governance/pull/23), already merged to `main`. Its own [`START_HERE.md`](WIP/l9-claude-code-env-pack/START_HERE.md) states:

> **Canonical source:** `environment/claude-code/` in `Quantum-L9/Cursor-Governance`. This pack is a copy of that directory plus this guide. If they ever disagree, the repo wins.

A full recursive diff (`diff -rq WIP/l9-claude-code-env-pack environment/claude-code`) shows exactly two differences, both already accounted for:

- `START_HERE.md` — pack-only copy-paste guide for the `claude.ai/code` account-environment UI fields. Not applicable outside a "pack" distribution context.
- `web/setup.sh` — the pack's copy predates the 4-line SonarCloud security hardening I applied on PR #23 (`curl --proto '=https' --tlsv1.2`, `pip install --only-binary :all:` x3, `--ignore-scripts` x2). The merged copy in `environment/claude-code/web/setup.sh` is the current, secure version.

There is no content in the WIP pack to "move to a new home" — everything it contains is already at its home. Re-integrating it as-is would silently reintroduce the 8 vulnerability findings already fixed and merged.

## Plan

1. **Re-verify no drift immediately before deletion** (repo may have moved since this check)
   - `diff -rq WIP/l9-claude-code-env-pack environment/claude-code`
   - Expect exactly the same two known differences (`START_HERE.md` only-in-pack, `web/setup.sh` pre-fix). If anything else differs, STOP and re-open this plan rather than deleting.

2. **Show the exact deletion target and get explicit approval** (per repo's destructive-operation governance — deletion requires explicit "yes, delete it" every time, no exceptions)
   - List the 11 files under `WIP/l9-claude-code-env-pack/` (`README.md`, `START_HERE.md`, `mcp.template.json`, `render.claude.json`, `settings.template.json`, `validate_claude_env.py`, `adapters/claude-code.md`, `hooks/session_start_claude_governance.sh`, `web/README.md`, `web/environment.env.example`, `web/network-policy.md`, `web/setup.sh`)
   - State plainly: this folder was never git-tracked (confirmed via `git log --all -- WIP/l9-claude-code-env-pack` returning empty), so deletion is filesystem-only — no git history is lost, nothing to revert.
   - Wait for explicit approval before running `rm -rf WIP/l9-claude-code-env-pack`.

3. **Delete** `WIP/l9-claude-code-env-pack/` (untracked directory; `rm -rf` has no git-revert path, which is exactly why step 2's explicit approval gate exists).

4. **Confirm clean state**
   - `git status --porcelain=v1` in the repo root should show no changes related to this folder (it was never tracked, so removing it produces no diff — just confirms the untracked-files listing no longer shows it).

## Explicitly out of scope

- No changes to `environment/claude-code/` (it is already correct and current).
- No new export/regeneration tooling for future "packs" — the user selected the minimal "it's dead weight, delete it" option, not the "formalize export" or "fold START_HERE.md into the canonical README" alternatives that were offered and declined.
- No git commit/push — this is an untracked directory, so there is nothing to stage; no repo history changes.
