# Copy-paste prompt for Cursor Agent

Phase 0 is manual - it needs GitHub UI admin access and the agent cannot do it.
Do Phase 0 yourself first, then paste this.

---

```
Read ./housekeeping-pack/RUNBOOK.md and ./housekeeping-pack/AGENT_TASK.md.

Execute PHASE 2 and PHASE 3 only.

I have already completed Phase 0 (branch protection) manually.
Do NOT attempt Phase 1 (branch deletion) - I run that myself with the script.

Hard constraints:
- Do NOT delete any branch. Do not run git push --delete.
- Do NOT delete `commands/harvest copy.md`. Rename it to
  `commands/_harvest-copy-REVIEW.md` and leave it for me.
- Before untracking `.governance-build-lock`, grep Makefile and
  .github/workflows for readers. If anything reads it, STOP and report
  instead of untracking.
- Do not touch CANONICAL_LAW.md, ORG_INVARIANTS.yaml, CODEOWNERS,
  SECURITY.md, .claude/settings.json, or .claude/hooks/**.
- Branch: chore/housekeeping-rb-hk-001. Do not commit or push.
- Add `WIP/` to .cursorignore. WIP/ is mine; you never read or write it.
  TODO.md is yours to maintain.

After Phase 3, report the exact job names of each new workflow so I can add
them as required status checks, and confirm whether current_work/ still has
contents I need to migrate.
```

---

Run `./scripts/check_repo_hygiene.py` yourself afterward to verify.
