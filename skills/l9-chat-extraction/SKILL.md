---
name: l9-chat-extraction
description: extract learnings and specific content from chat conversations to memory or structured output. use when closing sessions, capturing lessons, patterns, errors, preferences, code blocks, decisions, requirements, or action items from conversation.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, memory, extraction, chat, lessons, patterns]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
disable-model-invocation: true
---

# Chat Extraction

## Purpose

Extract durable value from conversation — lessons, patterns, errors, preferences, and structured content (code, decisions, requirements, action items) — into L9 memory or formatted output.

## Core Contract

`SCAN → CLASSIFY → WRITE (canonical path) → REPORT`

1. **Scan** conversation for extractable items (lessons, patterns, errors, preferences, decisions, code, requirements, actions).
2. **Classify** each item by type and scope; one atomic fact per memory write.
3. **Write** through the canonical memory client — never bypass governance pipeline.
4. **Report** extraction summary with counts and status.

## Authority Order

1. `docs/MEMORY_PIPELINE_MAP.md` — canonical write path
2. `.cursor/rules/87-cursor-memory-kernel.mdc` — memory write format
3. [`references/extract-chat.md`](references/extract-chat.md) — learnings → memory workflow
4. [`references/extract-from-chat.md`](references/extract-from-chat.md) — structured content extraction
5. `agents/cursor/cursor_memory_client.py` — CLI entry point

## Compact Workflow

### Memory extraction (learnings)

1. Scan for lessons, patterns, errors, preferences, decisions.
2. Write one fact per call with `--kind` and `--scope cursor`.
3. Output extraction table.

See [`references/extract-chat.md`](references/extract-chat.md).

### Content extraction (structured)

1. Identify extraction type: code, decisions, requirements, actions, files.
2. Pull matching blocks from conversation.
3. Format per type template.

See [`references/extract-from-chat.md`](references/extract-from-chat.md).

## Resource Map

- [`references/extract-chat.md`](references/extract-chat.md) — lessons/patterns/errors → memory writes
- [`references/extract-from-chat.md`](references/extract-from-chat.md) — code/decisions/requirements/actions extraction
- `agents/cursor/cursor_memory_client.py` — memory CLI
- `docs/MEMORY_PIPELINE_MAP.md` — pipeline routing

## Validation

- Each memory write uses `--kind` and atomic single-fact content.
- Extraction report lists type, summary, and status per item.
- No bulk blob writes; no bypass of canonical pipeline.

## Failure Handling

| Symptom | Action |
|---------|--------|
| Memory client unavailable | Report blocker; save structured handoff locally; retry on next session |
| Ambiguous extraction type | Ask one focused question or default to `insight` with scope note |
| Duplicate fact already in memory | Skip write; note in report as `skipped-duplicate` |
| No extractable content | Report `0 items`; do not invent learnings |

When blocked: state exact gap, label `Unknown`, give smallest next action (usually: run memory client health check or defer to `/end-session`).
