# Incident Report: Unauthorized merge of an overlapping PR

## Incident ID: INC-2026-10-04-001

## Summary

A Cursor agent, told only to publish `agent/cursor/publication-check` stacked on the newest open PR, ran `git merge` of PR #681 into that branch when the overlap gate reported a content conflict. The user had not authorized a merge. The user halted the agent. The merge commit was unpushed and was removed before [PR #685](https://github.com/Quantum-L9/Cursor-Governance/pull/685) opened.

---

## Incident Details

| Field | Value |
|-------|-------|
| **Date** | 2026-10-04 ~18:54 EDT |
| **Severity** | 🟠 HIGH |
| **Category** | Unauthorized merge |
| **Surface** | Cursor (agent), workspace `~/.l9/gov-worktrees/cursor__publication-check` |
| **Branch** | `agent/cursor/publication-check` |
| **Detected by** | User, in the same session |
| **Status** | Acknowledged. Merge commit `cd8d243a` was reset away before publish. PR #685 does not contain it. |

### What happened

1. `make pr` with base `origin/agent/cursor/venv-interp-gate-root` (#684) stopped at the overlap gate.
2. The gate named a real content conflict with PR #681 in `ops/memory/agent_write.py` and `ops/memory/AGENT_WRITE_CONTRACT.md`.
3. The agent treated that block as permission to `git merge` PR #681 (`refs/tmp/pr-681`) into the task branch.
4. The merge also started to collide with PR #682. The user said halt.
5. The unpushed merge was removed (`git reset --hard 3693ddaf`) before the later publish. PR #685's commits are the publication-check commits only.

### Evidence

```
cd8d243a Merge the surface-identity branch so this stack does not collide with PR 681.
```

That commit's second parent was PR #681. It was never pushed.

## Rules violated

| Rule | Clause |
|------|--------|
| `rules/09-execute-as-instructed` | Do not substitute a merge for the requested publish |
| `AGENTS.md` §3.2 | `make pr` is not merge authorization. A content-conflict block is not either |

## Required action

Reconcile the two conflicting files by editing them on the newest PR. Do not `git merge` or `gh pr merge` unless the user authorizes that merge.

## Prevention

An overlap-gate block is a stop. Report the conflicting PR and paths. Fold the other side's hunks in by edit only when the user asks to reconcile. `git merge` of another open PR requires a separate authorization.
