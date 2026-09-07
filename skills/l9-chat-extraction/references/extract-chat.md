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

### 2. WRITE TO MEMORY (governed — model-authored facts)

Extracted facts are model-authored, so they take the interactive write
contract on the `l9-graphite-memory` MCP server: one `memory.phase_lock` per
task signature, then one `memory.write_governed` per fact. Resolve the
namespace first (`python -m ops.memory.cli resolve` → `write_namespace_hint`);
never request the shared workspace namespace.

```text
memory.phase_lock      {namespace: "{ns}", task_signature: "extract-chat:{session}"}

memory.write_governed  {namespace: "{ns}", task_signature: "extract-chat:{session}",
                        content: "LESSON: {content}", memory_class: "lesson", tags: ["agent:cursor"]}

memory.write_governed  {namespace: "{ns}", task_signature: "extract-chat:{session}",
                        content: "PATTERN: {content}", memory_class: "insight", tags: ["agent:cursor"]}

memory.write_governed  {namespace: "{ns}", task_signature: "extract-chat:{session}",
                        content: "ERROR: {issue} → FIX: {solution}", memory_class: "lesson", tags: ["agent:cursor"]}
```

- The phase-lock is a memory-write precondition only (namespace snapshot
  consistency). It never authorizes an edit, commit, push or publish.
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
