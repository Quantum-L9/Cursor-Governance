# TODO - agent-owned task queue

Agent maintains this file. Humans use `WIP/` instead.

Format: one task per line. Status prefix required. Linear identifier required
when work spans sessions.

- `[ ]` open
- `[~]` in progress
- `[x]` done - remove on next sweep
- `[!]` blocked - must state the blocker

## Active

- [ ] ENG-000 example open task, one line, imperative
- [~] ENG-000 example in-progress task
- [!] ENG-000 example blocked task - blocker: waiting on ruleset admin access

## Rules

1. Never write to `WIP/`. It is human-owned and cursorignored.
2. One task per line. No nested bullets.
3. Anything spanning sessions gets a Linear issue and its identifier here.
4. Sweep `[x]` entries when the count exceeds ten.
5. `current_work/` is retired. Do not recreate it.
