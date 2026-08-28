---
name: ynp
version: "8.2.0"
description: "Your Next Play — synthesize highest-leverage next action"
auto_chain: null
scope: "local_cursor_only"
---

# /ynp — Your Next Play

Delegates to skill **`l9-ynp`**.

Synthesizes the **single highest-leverage next action** from current context.

**Rules:**
- Recommend only. Do not auto-execute unless the user explicitly asks to run the play.
- `action:` is required. A bare percent is uncalibrated and must not select the play.
- Batch related TODOs (3 in one GMP > 3 separate runs)
- Harvest context first (check what's already in chat)

---

## EXECUTION

Read `skills/l9-ynp/SKILL.md` and [references/ynp-workflow.md](../skills/l9-ynp/references/ynp-workflow.md).

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
| GOVERNANCE | `/governance` |

### 4. STANCE

Emit:

```yaml
evidence_quality: high | medium | low | unknown
decision_risk: reversible | guarded | irreversible
action: proceed | proceed_with_validation | bounded_probe | block
calibration_status: none
```

---

## OUTPUT FORMAT

```markdown
## YNP: {action_title}

**action:** {proceed | proceed_with_validation | bounded_probe | block}
**evidence_quality:** {high | medium | low | unknown}
**decision_risk:** {reversible | guarded | irreversible}
**calibration_status:** none
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

| IN SCOPE | OUT OF SCOPE |
|----------|--------------|
| Local file ops | VPS/SSH |
| Local tests | Docker management |
| GMP execution | Production deploys |
| Slash commands | Remote env changes |

---

## STOP CONDITIONS

- Ambiguous context → Ask clarifying question
- Multiple equal-priority items → Present options
- Protected file without approval → Route to KERNEL GMP
- `action: block` → Gather more info first
