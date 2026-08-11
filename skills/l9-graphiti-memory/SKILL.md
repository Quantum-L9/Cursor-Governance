---
name: l9-graphiti-memory
description: Graphiti VPS memory — prefetch, group resolution, episode writes, GMP Phase 0 MEMORY_PREFETCH, /end-session PICKUP. Use when wiring memory, debugging prefetch, bootstrap, Graphiti health, or closing a session.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, graphiti, memory, prefetch, gmp, end-session]
owner: igor_beylin
status: active
version: 1.4.0
updated: 2026-08-07
disable-model-invocation: false
---

# Graphiti Global Memory

## Purpose

Operate the Graphiti VPS memory layer (T1/T2). **Resume SSOT** is Graphiti
`inject` / PICKUP episodes. Local `memory-bank/` (former T0) is **deprecated**
— hooks and `/end-session` do not read or write it. C1 MCP is **read-only legacy**.

**One agent memory (ADR-0005):** CLI (`graphiti_memory_client.py`) and MCP
(`l9-graphite-memory` / `memory.*`) are **transports to the same store**. Do not
treat them as two SSOTs. Consumer product graphs (Odoo / PlasticOS Neo4j / Gate)
are **out of band** — never use them as Cursor agent episodic memory.

**Required by:** `/end-session` / skill `l9-end-session` for PICKUP + learning writes. Load this skill (or follow its CLI block) before invoking `graphiti_memory_client.py`.

## Interpreter (fail-closed)

**Never** call the client with bare `python3` from PATH — system Python often lacks PyYAML (`ModuleNotFoundError: No module named 'yaml'`).

Always use the governance locked venv:

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
CLIENT="${GOV}/ops/graphiti/graphiti_memory_client.py"
# If the clone lives only under ~/Cursor-Governance:
[ -x "$GRAPHITI_PY" ] || GRAPHITI_PY="${HOME}/Cursor-Governance/.venv/bin/python"
[ -f "$CLIENT" ] || CLIENT="${HOME}/Cursor-Governance/ops/graphiti/graphiti_memory_client.py"
# Or via symlink: CLIENT="$(pwd)/.cursor-commands/ops/graphiti/graphiti_memory_client.py"
# still run it with GRAPHITI_PY, not system python3.
```

If `.venv` is missing: `make -C "$GOV" venv` (or `uv sync --locked --extra dev` in the governance clone).

## Feature flags

| Env | Default | Meaning |
|-----|---------|---------|
| `GRAPHITI_MEMORY_ENABLED` | `0` | Master switch for prefetch + writes |
| `GRAPHITI_WRITE_GATES` | `0` | Fail-closed edit/shell/subagent gates (GATES-002) |

Config: `~/.cursor/graphiti.env` (copy from `ops/graphiti/graphiti.env.example`).

## CLI

```bash
"$GRAPHITI_PY" "$CLIENT" health
"$GRAPHITI_PY" "$CLIENT" resolve
"$GRAPHITI_PY" "$CLIENT" search "query" --limit 5
"$GRAPHITI_PY" "$CLIENT" conflicts
"$GRAPHITI_PY" "$CLIENT" phase-lock
"$GRAPHITI_PY" "$CLIENT" inject "current task"
"$GRAPHITI_PY" "$CLIENT" write "durable fact…" --kind lesson
"$GRAPHITI_PY" "$CLIENT" write "PICKUP|date=…|task=…|files=…|next=…|blocker=…|gmps=…|outcome=…" --kind pickup_context
"$GRAPHITI_PY" "$CLIENT" bootstrap --dry-run
"$GRAPHITI_PY" "$CLIENT" stats
```

### `write` flags (authoritative)

| Allowed | Not a CLI flag |
|---------|----------------|
| `--kind KIND` | **`--scope`** — does not exist; do not pass `--scope cursor` |
| `--group-id GROUP_ID` | (optional; omit to use registry resolve) |
| `--dry-run` | |

Semantic “cursor scope” from older memory-kernel docs means tags/kind discipline, **not** a `write` argument.

## Session lifecycle

1. **sessionStart** — `session_start_memory_orchestrator.sh` runs code-graph health + Graphiti `inject` (when enabled).
2. **Resume** — cite prefetch / `inject` results and search PICKUP episodes; do not read `memory-bank/` as SSOT.
3. **sessionEnd hook** — `graphiti-session-end.sh` writes Graphiti `--kind session_summary` only; on failure, WARN and skip (no memory-bank).
4. **`/end-session` / `l9-end-session`** — agent **must** use this skill’s `GRAPHITI_PY` + `CLIENT` for T1 PICKUP + one `--kind` write per learning. See `skills/l9-end-session/SKILL.md` and `commands/end-session.md`.

## Proactive writes (T2)

When a durable doctrine, lesson, or ADR delta lands in-repo, write it to Graphiti **without waiting to be asked**:

```bash
"$GRAPHITI_PY" "$CLIENT" resolve   # expect repo group, e.g. cursor-governance
"$GRAPHITI_PY" "$CLIENT" write "…" --kind lesson
```

**MUST NOT** hardcode `igor-workspace` (or any prefetch/read fan-in group) as the write target — `cmd_write` blocks the shared workspace group on purpose. Prefer the CLI over raw MCP `add_memory`.

## GMP Phase 0

Run `conflicts` then `phase-lock` before GMP file edits when gates on:

```bash
"$GRAPHITI_PY" "$CLIENT" conflicts
"$GRAPHITI_PY" "$CLIENT" phase-lock
```

## GATES-002 activation

See `ops/graphiti/GATES-002-ACTIVATION.md`. Flip `GRAPHITI_WRITE_GATES=1` only after soak checklist passes.

## Wiring verify

```bash
bash .cursor-commands/ops/scripts/check_governance_wiring.sh "$(pwd)"
bash .cursor-commands/ops/graphiti/test_gate_e2e_full.sh
```

## Authority

1. `rules/03-graphiti-memory.mdc`
2. `ops/graphiti/MEMORY_BANK_POLICY.md` (deprecated — archival note only)
3. `ops/graphiti/group_registry.yaml`
4. `rules/97-graph-layer-boundary.mdc`, `98-graphiti-memory-gate.mdc`, `99-graphiti-temporal.mdc`
5. `skills/l9-end-session/SKILL.md` — session-close write path
6. `docs/decisions/ADR-0005-one-agent-memory-domain-out-of-band.md`

## VPS deploy (human gate)

See `ops/graphiti/DEPLOY.md` (C1 `46.62.243.82`, SSH tunnel). Health/bootstrap require `OPENAI_API_KEY` on VPS + running `docker compose up`.
