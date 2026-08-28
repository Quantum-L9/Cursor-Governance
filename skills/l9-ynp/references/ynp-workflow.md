<!-- L9_META
l9_schema: 1
parent: l9-ynp
origin: migrated-from ynp command v8.2.0
sources: [profiles/ynp_mode.md]
tags: [ynp, next-action, action-enum, batching, packet-completeness]
status: active
/L9_META -->

# YNP Workflow — Your Next Play

## Rules

- Recommend the next play; do not auto-execute unless the user explicitly asks.
- Batch related TODOs (3 in one GMP > 3 separate runs).
- Harvest context first (check what's already in chat).
- `action:` is required. A bare percent is `uncalibrated` and must not select the play.

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

## Step 4 — Stance (not a percent)

| evidence_quality × decision_risk | Typical action |
|----------------------------------|----------------|
| high × reversible | proceed |
| high × guarded | proceed_with_validation |
| medium × reversible | proceed_with_validation |
| low or unknown × reversible | bounded_probe |
| unknown or low × irreversible | block |

A leftover `Confidence: N%` line, if present, is `calibration_status: uncalibrated` and must not choose `action`.

## Output format

```markdown
## YNP: {action_title}

**action:** proceed | proceed_with_validation | bounded_probe | block
**evidence_quality:** high | medium | low | unknown
**decision_risk:** reversible | guarded | irreversible
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

## Closing block

When operating in YNP mode, end the response with a next-prompt block the user can accept verbatim:

```markdown
## Your Next Prompt

{next prompt, batching the related steps into one runnable instruction}

Reply Y to use this as your next prompt!
```

The prompt batches related steps into a single instruction — that is the same batching rule as
above (3 TODOs in one GMP beats 3 runs), expressed as a prompt rather than a plan. It MUST reference
the specific files or deliverables it acts on.

### Reply interpretation

| Reply | Meaning |
|---|---|
| `Y` | User accepted the next prompt — proceed with it |
| `Y + edit` | Parse the edit, regenerate the modified prompt, proceed |
| `N` | Rejected — use the stated reason to produce a better prompt |

`Y` authorizes the *prompt*, not the operations inside it. Destructive actions, commits, and pushes
still require their own explicit approval.

## Do not re-ask confirmed inputs

Once the user has confirmed a value, decision, or constraint, do not ask again unless they reset it.
No revalidation, no "just to confirm", no duplicate questions.

**Boundary:** this eliminates redundant *questions*, not approval *gates*. Commit, push, delete, and
protected-file approvals are required every time regardless of prior confirmations.

## Packet completeness

When the deliverable is structured content, deliver the whole packet rather than a fragment:

- the code or config file(s)
- `README.md` — what it is and how to run it
- a summary or explanation of decisions
- schema outline, where a schema exists
- sample or test data, where applicable

Ship complete packages, not fragments. Note which packet elements were intentionally omitted.

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
- `action: block` or unnamed missing evidence → Gather more info first
