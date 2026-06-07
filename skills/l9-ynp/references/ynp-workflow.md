<!-- L9_META
l9_schema: 1
parent: l9-ynp
origin: migrated-from ynp command v8.1.0
tags: [ynp, next-action, confidence, batching]
status: active
/L9_META -->

# YNP Workflow — Your Next Play

## Rules

- Recommend the next play; do not auto-execute unless the user explicitly asks.
- Batch related TODOs (3 in one GMP > 3 separate runs).
- Harvest context first (check what's already in chat).

## Step 1 — Context harvest

```text
SCAN:
├── Chat context (files provided, referenced, pasted)
├── workflow_state.md (PHASE, TODOs, blockers)
├── Recent GMP outputs
└── Reusable assets
```

## Step 2 — Reasoning synthesis

- **Abductive:** What patterns suggest the best path?
- **Deductive:** What rules/constraints apply?
- **Inductive:** What worked before in similar situations?

## Step 3 — Candidate generation

| Tier | Commands |
|------|----------|
| KERNEL | gmp (protected files) |
| RUNTIME | gmp, wire, refactor-sweep |
| INFRA | gmp (docker, deploy) |
| UX | gmp, quick edits |
| GOVERNANCE | rules, governance |

## Step 4 — Confidence scoring

| Score | Action |
|-------|--------|
| ≥90% | Strong recommendation |
| 80–89% | Recommend, ask confirmation |
| 70–79% | Recommend with caveats |
| <70% | Need more info, ask questions |

## Output format

```markdown
## YNP: {action_title}

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

## Scope boundary

| In scope | Out of scope |
|----------|--------------|
| Local file ops | VPS/SSH |
| Local tests | Docker management |
| GMP execution | Production deploys |
| Slash commands | Remote env changes |

## Stop conditions

- Ambiguous context → Ask clarifying question
- Multiple equal-priority items → Present options
- Protected file without approval → Route to KERNEL GMP
- Confidence <70% → Gather more info first
