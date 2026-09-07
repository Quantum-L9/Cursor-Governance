<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-end-session
layer: reference
role: session_close_protocol
tags: [l9, session, handoff, memory, governance]
owner: igor_beylin
status: active
version: 1.4.0
updated: 2026-09-07
auto_chain: extract-chat
--- /SKILL_META ---
-->

# /end-session — Session Close

## WHAT IT DOES

Clean session close (force-retry / offline recovery — normal closes are the
automatic `sessionEnd` hook, ADR-0028):

1. Repair-write the canonical continuation record (`ContinuationCapsuleV2`)
   through `ops/memory` and stamp the close receipt
2. Extract learnings as governed memory writes (`memory.phase_lock` →
   `memory.write_governed`; see `docs/MEMORY_PIPELINE_MAP.md`)
3. Save Redis session context for cross-window resume
4. Create handoff summary
5. **Backup GlobalCommands to GitHub** (`Quantum-L9/Cursor-Governance`)

Protocol spec: `end-session.yaml` (v2.1). Authority: CANONICAL_LAW §8.2/§8.3,
ADR-0030 (items 7–9), ADR-0028 as amended 2026-09-07.

---

## EXECUTION

### 1. MEMORY REPAIR — canonical continuation record (REQUIRED)

Health-check first, then `repair-write` the continuation record for the
session that did not land. This is a **deterministic adapter** over the same
`MemoryService` the hook closer uses; it is the only close-gap repair. A bare
`ops.memory.cli write` does not stamp the close receipt and is not this step.

If health fails or the write is refused: **warn and skip** memory persistence
for this close — do **not** fall back to `memory-bank/` (deprecated; see
`MEMORY_BANK_POLICY.md`) and do **not** write a provider. Continue with
Redis/handoff.

Use governance **venv Python** (see `skills/l9-graphiti-memory/SKILL.md`). Bare `python3` often fails with `No module named 'yaml'`. Do **not** pass `--scope` / `--scope cursor` (not a CLI flag).

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
[ -x "$GRAPHITI_PY" ] || GRAPHITI_PY="${HOME}/Cursor-Governance/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-$(pwd)}"
memcli() { (cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.memory.cli "$@" --workspace "${WS:-$PWD}"); }  # canonical control plane (C11)
PRIOR_FILE="$WS/.l9/memory/previous_opened.json"
REPAIR_SID="$("$GRAPHITI_PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("session_id") or "")' "$PRIOR_FILE" 2>/dev/null || true)"
REPAIR_SID="${REPAIR_SID:-${CURSOR_CONVERSATION_ID:-manual}}"
export L9_MEMORY_AGENT_ID=cursor USER_ID=cursor_agent

memcli health
# If healthy:
cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.graphiti.hydration.cli repair-write \
  --project-dir "$WS" --session-id "$REPAIR_SID" \
  --objective "{TASK}" --next "{NEXT}" --files "{FILES}" --blocker "{BLOCKER}" \
  --agent-id cursor
```

`ops/hooks/graphiti-session-end.sh` on automatic `sessionEnd` performs the
canonical close only (`close_session.py`: capsule → governed candidate →
`memory.close`, idempotent); on failure it writes a fail receipt, WARNs on
stderr and exits without writing `memory-bank/` or a provider.

### 2. EXTRACT LEARNINGS (governed writes — part of step 1)

Only runs when step 1's health check passed. If it did not, skip learnings
writes and note the gap in the handoff report.

Session learnings are **model-authored durable facts**, so they take the
interactive write contract: `memory.phase_lock` then `memory.write_governed`
on the `l9-graphite-memory` MCP server (ADR-0030 item 7). They get the same
admission, audit, supersession and projection as every other canonical record.
See `docs/MEMORY_PIPELINE_MAP.md`.

- **Path:** MCP `l9-graphite-memory` → `MemoryService.write_governed` →
  canonical store → outbox → projection. The retired provider path
  (`graphiti_memory_client.py`, `add_memory`-class episodes) and the legacy C1
  path (`cursor_memory_client.py` → `save_memory`) are gone — do not use them.
- The memory phase-lock is a memory-write precondition only; it authorizes no
  file edit, commit or push.

**Write atomic memories — one fact per write, not one big blob.**
See `.cursor/rules/87-cursor-memory-kernel.mdc` → "Memory Write Format" for the full spec.

```text
memory.phase_lock      {namespace: "{resolved namespace}", task_signature: "end-session:{REPAIR_SID}"}

memory.write_governed  {namespace: "{resolved namespace}", task_signature: "end-session:{REPAIR_SID}",
                        content: "{terse fact 1}", memory_class: "lesson", tags: ["agent:cursor"]}

memory.write_governed  {namespace: "{resolved namespace}", task_signature: "end-session:{REPAIR_SID}",
                        content: "{terse fact 2}", memory_class: "insight", tags: ["agent:cursor"]}
```

A human operator running the close by hand may use the operator CLI
(`memcli write "{fact}" --kind lesson --agent-id cursor`); the model does not
substitute it for the governed write.

### 3. REDIS SESSION CONTEXT (cache_set_session_context)

**Call MCP tool `cache_set_session_context`** so the next window can resume from this handoff. Use the same structure as the handoff below.

- **context** (required): JSON object with:
  - `summary`: 1–2 sentence summary of session work
  - `completed`: list of tasks completed
  - `in_progress`: list with status if any
  - `next_steps`: 2–5 concrete next steps
  - `open_questions`: list if any
  - `files_touched`: list of paths modified (optional but useful)
- **session_id**: omit (daily session)
- **ttl**: omit (default 86400)

This step is mandatory: without it, the next window will not have this handoff in Redis.

### 3b. SESSION HOOKS (canonical sessionEnd close)

Rely on the installed Cursor hook `ops/hooks/graphiti-session-end.sh` (wired via `~/.cursor/hooks.json` after `setup_workspace_symlinks.sh`).

- On automatic `sessionEnd`, that script runs the canonical close
  (`ContinuationCapsuleV2` → governed candidate → `memory.close`) when a
  summary payload is present and memory is enabled.
- If no summary was available, memory is disabled, or the close fails: **skip** — warn in the close report; do not fall back to memory-bank, a provider write, or CEG working-memory promotion.
- **Do not** invoke CEG working-memory session hooks (not part of Cursor-Governance). Agent-side close persistence is the canonical continuation record + governed lesson writes (steps 1–2).

### 4. GOVERNANCE GITHUB BACKUP (mandatory)

Push the GitHub-backed governance SSOT (everything under `@.cursor-commands/` → `$HOME/.cursor-governance`) to the governance repo:

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh "chore(governance): end-session $(date +%Y-%m-%d)"
```

Or: `/governance-backup` / `make governance-backup` (PlasticOS).

Also runs automatically on **sessionEnd** after `setup_workspace_symlinks.sh` (see `~/.cursor/hooks.json`).

### 5. HANDOFF

```markdown
## Session Handoff

### Completed
- {task 1}
- {task 2}

### In Progress
- {task} — {status}

### Next Steps
1. {action}
2. {action}

### Open Questions
- {question}
```

---

## OUTPUT

```markdown
## 👋 SESSION CLOSED

### Summary
**Work completed:** {count} items
**Reports generated:** {list}

### Handoff
- Continuation record repaired + governed learnings written through the memory control plane (or warned if memory unbound) ✅
- Redis session context saved (cache_set_session_context) ✅
- Next steps defined ✅
- GlobalCommands pushed to Cursor-Governance ✅

### When you open a new window
→ Use **/start-session** to load Redis context + the canonical hydrate (`ContinuationCapsuleV2`) and resume.
```

→ **Auto-chains to /extract-chat**
