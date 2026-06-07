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

`PICKUP → MEMORY → REDIS → HOOKS → GOVERNANCE BACKUP → HANDOFF`

1. **PICKUP** — write structured handoff packet to C1 memory.
2. **MEMORY** — atomic learnings via canonical pipeline (one fact per write).
3. **REDIS** — `cache_set_session_context` for next-window resume (mandatory).
4. **HOOKS** — teardown session hooks if activated at start.
5. **GOVERNANCE** — backup GlobalCommands to GitHub.
6. **HANDOFF** — emit completed/in-progress/next-steps summary.

## Authority Order

1. `end-session.yaml` (v2.1) — protocol spec
2. `docs/MEMORY_PIPELINE_MAP.md` — canonical memory path
3. `.cursor/rules/87-cursor-memory-kernel.mdc` — memory write format
4. [`references/end-session-protocol.md`](references/end-session-protocol.md) — step-by-step execution
5. `agents/cursor/cursor_memory_client.py` — memory CLI
6. `.cursor-commands/ops/scripts/backup_to_github.sh` — governance backup

## Compact Workflow

1. Write PICKUP context with structured fields (task, files, next, blocker, gmps, outcome).
2. Extract learnings — one atomic write per fact with `--kind` and `--scope cursor`.
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
- `agents/cursor/cursor_memory_client.py` — memory writes
- `agents/cursor/cursor_session_hooks.py` — session hook teardown
- `.cursor-commands/ops/scripts/backup_to_github.sh` — governance backup

## Validation

- PICKUP context written with all required fields.
- Redis session context saved (mandatory — next window depends on it).
- Governance backup script executed or `make governance-backup` run.
- Handoff lists completed, in-progress, and next steps.

## Failure Handling

| Symptom | Action |
|---------|--------|
| Memory client fails | Complete Redis handoff anyway; note memory gap in report |
| Redis MCP unavailable | Write full handoff to PICKUP; warn next window to read C1 |
| Governance backup fails | Report failure; retry `backup_to_github.sh`; do not skip silently |
| Session hooks not active | Skip teardown; note in report |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: save Redis context first, defer memory retry).
