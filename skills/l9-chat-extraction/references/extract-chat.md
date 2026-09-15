<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-chat-extraction
layer: reference
role: memory_extraction_protocol
tags: [l9, memory, lessons, patterns, errors]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-07
--- /SKILL_META ---
-->

# /extract-chat — Memory Extraction

## WHAT IT DOES

Extract learnings from conversation → canonical L9 memory (one `MemoryService`,
ADR-0030):

- Lessons learned
- Patterns discovered
- Errors and fixes
- User preferences

---

## EXECUTION

### 1. SCAN CONVERSATION

```
EXTRACT:
├── Lessons (mistakes → corrections)
├── Patterns (reusable approaches)
├── Errors (issue → fix)
├── Preferences (user corrections)
└── Decisions (architectural choices)
```

### 2. WRITE TO MEMORY (agent lane — model-authored facts)

Extracted facts are model-authored, so they take the agent lane on the
`l9-graphite-memory` MCP server (ADR-0033): one `memory.write_agent` per fact.
Each write is immediately visible to another agent's `hydrate` / `search` and
waits on no phase, receipt, session close or PR gate. Resolve the namespace
first (`python -m ops.memory.cli resolve` → `write_namespace_hint`); never
request the shared workspace namespace.

```text
memory.write_agent     {namespace: "{ns}", content: "LESSON: {content}",
                        memory_class: "lesson", tags: ["agent:cursor", "session:{session}"]}

memory.write_agent     {namespace: "{ns}", content: "PATTERN: {content}",
                        memory_class: "insight", tags: ["agent:cursor", "session:{session}"]}

memory.write_agent     {namespace: "{ns}", content: "ERROR: {issue} → FIX: {solution}",
                        memory_class: "lesson", tags: ["agent:cursor", "session:{session}"]}
```

For a fact that must not contradict prior state (a decision, a plan lock), the
optional conflict-sensitive pair is available on the same server:

```text
memory.phase_lock      {namespace: "{ns}", task_signature: "extract-chat:{session}"}
memory.write_governed  {namespace: "{ns}", task_signature: "extract-chat:{session}",
                        content: "DECISION: {content}", memory_class: "decision", tags: ["agent:cursor"]}
```

- The phase-lock is a memory-write precondition only (namespace snapshot
  consistency) and only for `write_governed`. It never authorizes an edit,
  commit, push or publish, and it is never required for `write_agent`.
- Do not route these facts through generic `memory.ingest` or the operator CLI
  `write` to skip the lock; an unbound MCP server is reported as a gap
  (`python -m ops.memory.cli readiness`), not rerouted.
- A human operator extracting by hand may use the operator CLI
  (`python -m ops.memory.cli write "…" --kind lesson --agent-id cursor`).

---

## OUTPUT

```markdown
## 📝 EXTRACTED TO MEMORY

| Type | Content | Status |
|------|---------|--------|
| lesson | {summary} | ✅ admitted (receipt id) |
| pattern | {summary} | ✅ admitted (receipt id) |
| error | {summary} | ⚠️ duplicate / rejected (receipt reason) |

**Items:** N extracted · lock: {task_signature} · namespace: {ns}
```
