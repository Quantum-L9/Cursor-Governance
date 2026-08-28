# Durable deferral — `agent/claude/ff-novelty-reland` (foreign session work)

**Recorded:** 2026-08-27, by the session that planned PE adapter reliability.
**Why this file exists:** Stop-hook rule 42 (no abandoned work). The hook is correct:
this work is unpushed and un-merged. It is **not owned by this session** — it belongs to
a parallel session working the `/ff` novelty-reland (the same one that produced the
`ssot_machine_local_keep.sh` changes observed earlier today). This record discharges the
deferral durably without a foreign push and without touching another session's worktree.

## What exists

| Field | Value |
| --- | --- |
| Worktree | `/Users/macm2/.l9/gov-worktrees/claude__ff-novelty-reland` (registered) |
| Branch | `agent/claude/ff-novelty-reland` |
| HEAD | `a45970a` — **not on origin** (origin has no such branch) |
| Unpushed commits | 5+ ahead of `origin/main` (`af33b4d`, `a8c2e98`, … incl. the #331 merge) |
| Dirty (unstaged) | ~10 files, all under `skills/l9-git-work-preserve/` (SKILL.md, references/*, scripts/*; 2 added files: `triage-handoff.md`, `git_fetch.py`) |

## Deferral terms

- **Owner:** the parallel session that created the branch (or the operator).
- **Decision (operator, 2026-08-27):** the owner session will push. This session holds and
  does not publish foreign work. Asked and answered via explicit operator choice.
- **Completion path:** from that worktree — `PR_REMEDIATE=0 l9 pr`, then
  `/l9-pr-remediation` for merge.
- **Blocker for this session:** none for the PE adapter reliability plan — that work lives
  in the primary checkout and does not touch `skills/l9-git-work-preserve/`.
- **Gate note:** `session_debt.py` treats `publish` debt as undeferrable by design ("Only a
  push does"). The Stop gate will keep firing on this session's turns until the owner
  pushes or the branch publishes — that is the gate working as specified, not a defect.
- **Review trigger:** when the owner session publishes, this file should be superseded
  (deleted) so stale deferrals do not accumulate.

## Non-goals (why this is a deferral, not a rescue)

- Not pushing: push requires explicit user authorization and ownership of the change.
- Not committing or merging another session's dirty tree: shared-worktree isolation law.
- Not deleting or quarantining the worktree: it is registered and in use.

## Interlock

Do not let the `l9-git-work-preserve` changes in that worktree drift into conflict with
any `l9-repo-sync`/`/ff` work in this checkout — both touch the same skill. Re-sync before
either lands.
