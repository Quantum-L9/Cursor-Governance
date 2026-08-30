<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: human_blocker_mcq
tags: [issues, autonomy, blocker, multiple-choice, architecture]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-29
/L9_META -->

# Human blocker questions (max autonomy)

Converge does **not** pause between automatable issues. Drain the
leverage-ranked queue until the next step is impossible without a human.
Then stop, ask, and **resume the same queue** after the answer.

## When you may stop

Only these force a human turn:

- **ARCHITECTURE** — new module boundary, SSOT move, public API, or a
  second competing design. The human keeps architecture approval.
- **HUMAN** product fork (ship / don't ship / which UX)
- **EXTERNAL** secrets, vendor, or org policy the agent cannot operate
- **Unknown owning repo** after ownership-boundary (do not guess a write)

Do **not** stop to ask which cluster to do next, whether to verify, whether
to stack, or which option the codebase already answers. Those are agent work.
Put the recommended call in **A**.

## Question shape (required)

Keep it oral-exam simple. **A is always the recommended path** — mark it
`[RECOMMENDED]` and state why in one line from repo evidence. Other options
are quieter. Two or three choices. No essays.

```markdown
### Human blocker — {owner}/{repo}#{n}

Cannot proceed without you. I will resume the remediator queue after your letter.

**A) [RECOMMENDED]** {action}
Why: {one codebase fact — path, test, or invariant}

**B)** {alternative}
**C)** Hold — leave OPEN; continue other clusters

Reply `A`, `B`, or `C` (or one short correction).
```

If only two real options exist, omit C or make C = hold.

## After the answer

1. Apply the chosen letter (A if they say "go" / "yes" / silence-is-not-yes —
   wait for a letter; do not invent consent).
2. Resume Converge at the next unverified cluster. Do not restart fleet
   discover from zero unless ingest is stale.
3. If they pick C / hold, breadcrumb and continue **other** automatable
   clusters. Do not idle the whole invoke.

## Architecture

Recommend the optimal path from the live tree (A). Do not implement a new
architecture until they pick A (or an explicit B you then follow). Codebase
bugfixes inside an existing contract are not architecture — keep going.
