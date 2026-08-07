---
name: l9-end-session
description: close agent session — save pickup context, extract learnings, redis handoff, governance backup. use when ending a work session, creating handoff for next window, or running session teardown hooks.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, session, handoff, memory, governance, graphiti]
owner: igor_beylin
status: active
version: 1.4.0
updated: 2026-08-06
disable-model-invocation: true
---

# End Session

## Purpose

Clean session close: structured PICKUP context, canonical memory extraction, Redis cross-window resume, governance GitHub backup, and handoff summary.

## Mandatory preload

Before any Graphiti CLI call, **load and follow** [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md) interpreter rules:

- Use governance **`.venv` Python** (`GRAPHITI_PY`), never bare `python3` (avoids `No module named 'yaml'`).
- `write` accepts only `--kind`, `--group-id`, `--dry-run` — **never** `--scope` / `--scope cursor`.

Slash command entry: [`commands/end-session.md`](../../commands/end-session.md) (`/end-session`).

## Core Contract

`GRAPHITI (T1) → REDIS → HOOKS → GOVERNANCE BACKUP → HANDOFF`

1. **MEMORY** — health-check via `GRAPHITI_PY` + `graphiti_memory_client.py`, then write PICKUP (`--kind pickup_context`) + one atomic write per learning (`--kind` only). This is the canonical store. **Do not** write `memory-bank/` (deprecated).
2. **Graphiti failure** — if health check fails or a write errors: warn explicitly, skip memory persistence for this close, and continue Redis/handoff. No memory-bank fallback.
3. **REDIS** — `cache_set_session_context` for next-window resume when the MCP tool exists; if unavailable, keep full handoff in Graphiti/PICKUP and warn.
4. **HOOKS** — teardown session hooks if activated at start.
5. **GOVERNANCE** — backup GlobalCommands to GitHub.
6. **HANDOFF** — emit completed/in-progress/next-steps summary. If a bounded
   autonomy campaign was active, include PICKUP fields from
   `l9-bounded-autonomy/references/campaign-handoff.md` (`packet_id`, declared
   PRs, lock owners, join/merge_gate status, next_actions, blockers).

## Authority Order

1. `end-session.yaml` (v2.1) — protocol spec
2. `docs/MEMORY_PIPELINE_MAP.md` — canonical memory path
3. `.cursor/rules/87-cursor-memory-kernel.mdc` — memory write format (kinds; **not** a `--scope` CLI flag)
4. [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md) — **venv + CLI flags**
5. [`references/end-session-protocol.md`](references/end-session-protocol.md) — step-by-step execution
6. `ops/graphiti/graphiti_memory_client.py` — memory CLI (primary); `agents/cursor/cursor_memory_client.py` (C1, deprecated, fallback path only)
7. `ops/scripts/backup_to_github.sh` — governance backup

## Compact Workflow

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
CLIENT="${GOV}/ops/graphiti/graphiti_memory_client.py"
[ -x "$GRAPHITI_PY" ] || GRAPHITI_PY="${HOME}/Cursor-Governance/.venv/bin/python"
[ -f "$CLIENT" ] || CLIENT="${HOME}/Cursor-Governance/ops/graphiti/graphiti_memory_client.py"

"$GRAPHITI_PY" "$CLIENT" health
# If healthy:
"$GRAPHITI_PY" "$CLIENT" write \
  "PICKUP|date=$(date +%Y-%m-%d)|task={TASK}|files={FILES}|next={NEXT}|blocker={BLOCKER}|gmps={GMPS}|outcome={OUTCOME}" \
  --kind pickup_context
"$GRAPHITI_PY" "$CLIENT" write "{terse fact}" --kind lesson
```

1. Check Graphiti health with `GRAPHITI_PY`. If healthy: write PICKUP + one learning write per fact with `--kind` only (no `--scope`).
2. If Graphiti is unreachable or a write errors: warn and continue — do not write memory-bank.
3. Call MCP `cache_set_session_context` when available; else note Redis unavailable.
4. Run session hooks teardown if `/start-session` activated hooks.
5. Run governance backup script.
6. Output session-closed report.

See [`references/end-session-protocol.md`](references/end-session-protocol.md).

Auto-chains to `/extract-chat` for learnings pass.

## Resource Map

- [`../l9-graphiti-memory/SKILL.md`](../l9-graphiti-memory/SKILL.md) — interpreter + CLI contract
- [`references/end-session-protocol.md`](references/end-session-protocol.md) — full execution steps and output templates
- [`../../commands/end-session.md`](../../commands/end-session.md) — slash command
- `end-session.yaml` — protocol spec (v2.1)
- `docs/MEMORY_PIPELINE_MAP.md` — memory pipeline routing
- `ops/graphiti/graphiti_memory_client.py` — memory writes (primary)
- `agents/cursor/cursor_session_hooks.py` — session hook teardown
- `ops/scripts/backup_to_github.sh` — governance backup

## Validation

- PICKUP context + learnings written to Graphiti when healthy; otherwise explicit warn (no memory-bank).
- Redis session context saved when MCP exists; otherwise Graphiti PICKUP is the resume source (warn explicitly).
- Governance backup script executed or `make governance-backup` / `backup_to_github.sh` run.
- Handoff lists completed, in-progress, and next steps.
- No `ModuleNotFoundError: yaml` (venv used); no `unrecognized arguments: --scope`.

## Failure Handling

| Symptom | Action |
|---------|--------|
| `No module named 'yaml'` | Wrong interpreter — switch to `$GOV/.venv/bin/python`; run `make -C "$GOV" venv` if missing |
| `unrecognized arguments: --scope` | Drop `--scope` / `--scope cursor`; use `--kind` only |
| Graphiti health check fails, or a Graphiti write errors | Warn; skip memory persistence; continue Redis/handoff — **no** memory-bank |
| Redis MCP unavailable | Write full handoff to Graphiti when healthy; warn next window |
| Governance backup fails | Report failure; retry `backup_to_github.sh`; do not skip silently |
| Session hooks not active | Skip teardown; note in report |

When blocked: state exact gap, label `Unknown`, give smallest next action.
