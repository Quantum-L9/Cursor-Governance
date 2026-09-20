---
name: l9-chat-extraction
description: extract learnings and specific content from chat conversations to memory or structured output. use when closing sessions, capturing lessons, patterns, errors, preferences, code blocks, decisions, requirements, or action items from conversation.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, memory, extraction, chat, lessons, patterns]
  owner: igor_beylin
  status: active
  version: 1.2.0
  updated: 2026-09-15
---

# Chat Extraction

## Purpose

Extract durable value from conversation — lessons, patterns, errors, preferences, and structured content (code, decisions, requirements, action items) — into canonical L9 memory (`MemoryService`, ADR-0030) or formatted output.

## Core Contract

`SCAN → CLASSIFY → WRITE (agent lane) → REPORT`

1. **Scan** conversation for extractable items (lessons, patterns, errors, preferences, decisions, code, requirements, actions).
2. **Classify** each item by type and scope; one atomic fact per memory write.
3. **Write** on the agent lane — one `memory.write_agent` per fact on the `l9-graphite-memory` MCP server (ADR-0033). The optional `memory.phase_lock` → `memory.write_governed` pair is for a fact that must be checked against contradictions first. Never through generic `memory.ingest`, never through the operator CLI `write` as a bypass, never to a provider, and never waiting on a phase, receipt, session close or PR gate.
4. **Report** extraction summary with counts and the canonical receipt status per item.

## Authority Order

1. `CANONICAL_LAW.md` §8.2 / §8.3 as amended by `docs/decisions/ADR-0033-two-lanes-one-memoryservice.md` (agent lane; ADR-0030 items 7–9 for the optional governed pair) — agent write contract
2. `docs/MEMORY_PIPELINE_MAP.md` — canonical write path
3. `.cursor/rules/03-graphiti-memory.mdc`, `.cursor/rules/87-cursor-memory-kernel.mdc` — write tiers and memory write format
4. [`references/extract-chat.md`](references/extract-chat.md) — learnings → agent-lane memory workflow
5. [`references/extract-from-chat.md`](references/extract-from-chat.md) — structured content extraction
6. `skills/l9-graphiti-memory/SKILL.md` — adapters, namespace resolution, operator CLI

## Compact Workflow

### Memory extraction (learnings)

1. Scan for lessons, patterns, errors, preferences, decisions.
2. Resolve the namespace (`python -m ops.memory.cli resolve`), then one `memory.write_agent` per fact with `memory_class` (no `--scope`). For a fact that must not contradict prior state, take one `memory.phase_lock` for the task signature and use `memory.write_governed` instead; the phase-lock is a memory-write precondition only, never edit/commit/push authority.
3. Output extraction table with each canonical receipt status.

See [`references/extract-chat.md`](references/extract-chat.md).

### Content extraction (structured)

1. Identify extraction type: code, decisions, requirements, actions, files.
2. Pull matching blocks from conversation.
3. Format per type template.

See [`references/extract-from-chat.md`](references/extract-from-chat.md).

## Resource Map

- [`references/extract-chat.md`](references/extract-chat.md) — lessons/patterns/errors → agent-lane memory writes
- [`references/extract-from-chat.md`](references/extract-from-chat.md) — code/decisions/requirements/actions extraction
- `l9-graphite-memory` MCP server (`memory.write_agent`; optional `memory.phase_lock` + `memory.write_governed`) — the model's write surface
- `ops/memory/cli.py` (`python -m ops.memory.cli`) — operator / adapter CLI (`resolve`, `readiness`, operator `write`)
- `docs/MEMORY_PIPELINE_MAP.md` — pipeline routing

## Validation

- Each memory write is one `memory.write_agent` (or, when conflict checking is wanted, one `memory.write_governed` under a held `memory.phase_lock`), with `memory_class` and atomic single-fact content.
- Extraction report lists type, summary, and canonical receipt status per item.
- No bulk blob writes; no generic ingest or operator-CLI bypass of the agent write; no provider call; no Cursor-Governance ceremony before the write.

## Failure Handling

| Symptom | Action |
|---------|--------|
| MCP memory server unbound / `BINDING_FAILED` | Report blocker (`python -m ops.memory.cli readiness`); save structured handoff locally; retry on next session — do not reroute through another door |
| `memory.phase_lock` refused (conflicts) | Read the conflicts as evidence, refine the fact, retry; a refused lock blocks only this memory write |
| Ambiguous extraction type | Ask one focused question or default to `insight` with scope note |
| Duplicate fact already in memory | Skip write; note in report as `skipped-duplicate` |
| No extractable content | Report `0 items`; do not invent learnings |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: run memory client health check or defer to `/end-session`).
