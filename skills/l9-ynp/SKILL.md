---
name: l9-ynp
description: Synthesize the single highest-leverage next action from current context. Use after completing work, when priorities are unclear, or when the user asks what to do next.
---

---
name: ynp
version: "8.1.0"
description: "Your Next Play — synthesize highest-leverage next action"
auto_chain: null
scope: "local_cursor_only"
---

# /ynp — Your Next Play

## WHAT IT DOES

Synthesizes the **single highest-leverage next action** from current context.

**Rules:**
- Recommend the next play; do not auto-execute unless the user explicitly asks to run it
- Batch related TODOs (3 in one GMP > 3 separate runs)
- Harvest context first (check what's already in chat)

---

## EXECUTION

### 1. CONTEXT HARVEST

```
SCAN:
├── Chat context (files provided, referenced, pasted)
├── workflow_state.md (PHASE, TODOs, blockers)
├── Recent GMP outputs
└── Reusable assets
```

### 2. REASONING SYNTHESIS

Apply multi-modal reasoning:
- **Abductive:** What patterns suggest the best path?
- **Deductive:** What rules/constraints apply?
- **Inductive:** What worked before in similar situations?

### 3. CANDIDATE GENERATION

| Tier | Commands |
|------|----------|
| KERNEL | `/gmp` (protected files) |
| RUNTIME | `/gmp`, `/wire`, `/refactor-sweep` |
| INFRA | `/gmp` (docker, deploy) |
| UX | `/gmp`, quick edits |
| GOVERNANCE | `/rules`, `/governance` |

### 4. CONFIDENCE SCORING

| Score | Action |
|-------|--------|
| ≥90% | Strong recommendation |
| 80-89% | Recommend, ask confirmation |
| 70-79% | Recommend with caveats |
| <70% | Need more info, ask questions |

---

## OUTPUT FORMAT

```markdown
## 🎯 YNP: {action_title}

**Confidence:** {score}%
**Time:** {estimate}
**Tier:** KERNEL | RUNTIME | INFRA | UX

### Primary
{command} — {why this is highest leverage}

### Scope
- Files: {list}
- TODOs: {batched items}

### Alternates (if blocked)
1. {alt1}
2. {alt2}
```

---

## SCOPE BOUNDARY

| ✅ IN SCOPE | ❌ OUT OF SCOPE |
|-------------|-----------------|
| Local file ops | VPS/SSH |
| Local tests | Docker management |
| GMP execution | Production deploys |
| Slash commands | Remote env changes |

---

## STOP CONDITIONS

- Ambiguous context → Ask clarifying question
- Multiple equal-priority items → Present options
- Protected file without approval → Route to KERNEL GMP
- Confidence <70% → Gather more info first

--- End Command ---
