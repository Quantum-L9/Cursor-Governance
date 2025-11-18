---
title: N8N Execution Protocol
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: action-prompt + memory governance
tags: [n8n, automation, execution, cursor, mcp]
domain: workflow-orchestration
type: protocol
production_ready: true

---

## 🎯 Purpose
Defines how to execute automation tasks in n8n with full memory, schema, and research context.

---

## ✅ Required Context

- `.env.template`, `supabase-schema.sql`
- `memory_log.json`, `session_status.md`
- Governance: `reasoning_n8n.md`, `repeated-mistakes.md`, `quick-fixes.md`
- Node research from: `@.GlobalCommands/n8n research/`

---

## 🛠️ Tooling

- Use `n8n-mcp` to access node specs and config
- Use `Context7` to pull up documentation
- Save findings per node to `n8n research` for reuse

---

## 🔁 Task Execution Loop

1. Load and validate schema + variables
2. Confirm correct node selection
3. Comment every logic block
4. Validate inputs + outputs
5. Run recursive self-check
6. Log output to:
   - `memory_log.json`
   - `session_status.md`

---

## ⚠️ Rules

- Never invent fields
- No duplicate logic
- Respect locked tech stack
- Must reference schema
````
