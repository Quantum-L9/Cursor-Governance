---
name: l9-end-session
description: close agent session — save pickup context, extract learnings, redis handoff, governance backup. use when ending a work session, creating handoff for next window, or running session teardown hooks.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, session, handoff, memory, governance]
owner: igor_beylin
status: active
version: 1.1.1
updated: 2026-06-06
disable-model-invocation: true
---

# End Session

## Purpose

Clean session close: structured PICKUP context, canonical memory extraction, Redis cross-window resume, governance GitHub backup, and handoff summary.

## Core Contract

`GRAPHITI (T1, primary) → MEMORY-BANK (T0, fallback only) → REDIS → HOOKS → GOVERNANCE BACKUP → HANDOFF`

1. **MEMORY (primary)** — health-check `graphiti_memory_client.py`, then write PICKUP context + one atomic write per learning (`--kind`, `--scope cursor`). This is the canonical store. When it succeeds, this is the **only** memory write for the session — do not also write the same summary into memory-bank.
2. **MEMORY-BANK (fallback only)** — ONLY when the Graphiti health check fails or a write errors: append a dated PICKUP section to `$CURSOR_PROJECT_DIR/memory-bank/activeContext.md` (T0, target repo — never `$GLOBAL_COMMANDS`) instead of Graphiti, not in addition to it. Never truncate/overwrite the file. If `memory-bank/` is gitignored in the target repo (commonly this machine's global `~/.gitignore_global`), add a repo-local negation before relying on it being trackable.
3. **REDIS** — `cache_set_session_context` for next-window resume (mandatory).
4. **HOOKS** — teardown session hooks if activated at start.
5. **GOVERNANCE** — backup GlobalCommands to GitHub.
6. **HANDOFF** — emit completed/in-progress/next-steps summary.

## Authority Order

1. `end-session.yaml` (v2.1) — protocol spec
2. `docs/MEMORY_PIPELINE_MAP.md` — canonical memory path
3. `.cursor/rules/87-cursor-memory-kernel.mdc` — memory write format
4. [`references/end-session-protocol.md`](references/end-session-protocol.md) — step-by-step execution
5. `.cursor-commands/ops/graphiti/graphiti_memory_client.py` — memory CLI (primary); `agents/cursor/cursor_memory_client.py` (C1, deprecated, fallback path only)
6. `.cursor-commands/ops/scripts/backup_to_github.sh` — governance backup

## Compact Workflow

1. Check Graphiti health. If healthy: write PICKUP context (structured fields — task, files, next, blocker, gmps, outcome) and one atomic write per learning fact with `--kind` and `--scope cursor`, all to Graphiti. This is the only memory write.
2. Only if Graphiti is unreachable or a write errors: fall back to memory-bank instead — append the same PICKUP fields + learnings to `activeContext.md`/`tasks.md`/`progress.md`/`tech-debt.md`. Never write both for the same session.
3. Call MCP `cache_set_session_context` with summary, completed, in_progress, next_steps.
4. Run session hooks teardown if `/start-session` activated hooks.
5. Run governance backup script.
6. Output session-closed report.

See [`references/end-session-protocol.md`](references/end-session-protocol.md).

Auto-chains to `/extract-chat` for learnings pass.

## Resource Map

- [`references/end-session-protocol.md`](references/end-session-protocol.md) — full execution steps and output templates
- `end-session.yaml` — protocol spec (v2.1)
- `docs/MEMORY_PIPELINE_MAP.md` — memory pipeline routing
- `.cursor-commands/ops/graphiti/graphiti_memory_client.py` — memory writes (primary)
- `agents/cursor/cursor_session_hooks.py` — session hook teardown
- `.cursor-commands/ops/scripts/backup_to_github.sh` — governance backup

## Validation

- PICKUP context + learnings written to Graphiti (primary), OR to memory-bank if and only if Graphiti was unavailable — never both for the same session.
- Redis session context saved (mandatory — next window depends on it).
- Governance backup script executed or `make governance-backup` run.
- Handoff lists completed, in-progress, and next steps.

## Failure Handling

| Symptom | Action |
|---------|--------|
| Graphiti health check fails, or a Graphiti write errors | Fall back to `$CURSOR_PROJECT_DIR/memory-bank/` directly (and only then): append (not overwrite) dated sections to `activeContext.md`/`tasks.md`/`progress.md`/`tech-debt.md` with the same PICKUP fields + learnings; run the gitignore check below before assuming it's trackable |
| Redis MCP unavailable | Write full handoff to whichever memory store was used (Graphiti or memory-bank); warn next window to read it there |
| Governance backup fails | Report failure; retry `backup_to_github.sh`; do not skip silently |
| Session hooks not active | Skip teardown; note in report |
| `memory-bank/` gitignored in target repo | Run `git -C "$CURSOR_PROJECT_DIR" check-ignore -q memory-bank/activeContext.md`; if ignored, append `!/memory-bank/` + `!/memory-bank/**` to that repo's `.gitignore` (after any blanket ignore rule) — never edit the global `~/.gitignore_global` |
| Target repo's current branch has unrelated uncommitted diff | Do not commit memory-bank changes on top of it; use an isolated `git worktree` off a fresh copy of the default branch, commit + push from there, open a PR |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: save Redis context first, defer memory retry).
