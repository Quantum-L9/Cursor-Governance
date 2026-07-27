<!-- L9_META
l9_schema: 1
parent: l9-forge
origin: migrated-from profiles/advanced-features.md sections B and C
sources: [profiles/advanced-features.md]
tags: [forge, parallel, batching, subagents, preference-learning]
status: active
/L9_META -->

# Parallel Batch Execution and Evolution

Two bulk mechanisms: fanning work out across subagents, and folding recurring feedback back into
governance.

## Parallel batch execution

**Trigger:** a list of 5 or more independent items.

**Configuration**

| Setting | Value |
|---|---|
| Batch size | up to 10 items per subagent |
| Concurrency | no hard cap — optimize for wall-clock |
| Strategy | split → process in parallel → consolidate |

**Announce the split before running it** so the user can see the shape:

```text
[Parallel processing: 25 items detected]

Batch 1: items 1–10   (subagent A)
Batch 2: items 11–20  (subagent B)
Batch 3: items 21–25  (subagent C)
```

Then consolidate into a single result. Report the actual speedup only if measured; do not assert a
multiplier you did not observe.

### Use it for

Independent per-item analysis: file-by-file review (5+ files), record transformation, validation
sweeps, independent match/scoring runs.

### Do not use it for

- **Sequential operations** — order matters.
- **Items with dependencies** — batch 2 needs batch 1's output.
- **A single complex task** — splitting adds coordination cost without parallelism.
- **Real-time operations** — subagent latency dominates.

The failure mode is silent: parallelizing dependent work produces plausible output computed from
missing context. Check for dependencies **before** splitting, not after results disagree.

## Continuous evolution

Fold recurring signal into durable governance instead of re-learning it every session.

### Triggers

1. **Explicit preference stated** — user declares a standard.
2. **Repeated correction** — user fixes the same thing more than once.
3. **Contradiction or gap** — existing rules conflict or do not cover the case.
4. **Domain pattern emerges** — user establishes a domain-specific convention.
5. **Better approach found** — a measured improvement over current guidance.

Trigger 2 is the highest-value one and the easiest to miss. A second identical correction is a
signal, not a coincidence.

### Update protocol

1. **Capture** — note the signal during the session.
2. **Assess** — relevance and blast radius. One-off, or a standing rule?
3. **Update** — edit the owning artifact: a `rules/*.mdc` for always-applied law, the relevant
   `SKILL.md` or reference for scoped practice, `learning/` for lessons.
4. **Version** — bump per [artifact-versioning-policy.md](../../l9-architecture-decision-records/references/artifact-versioning-policy.md).
5. **Notify** — state what changed and why, in one block:

```markdown
✅ **Updated:** rules/45-pre-action-verification.mdc

**Added:** evidence requirement before "fixed" claims
**Why:** third occurrence of unverified completion claim this week
**Confidence:** 0.92
```

### Constraint

Governance edits are edits. They are subject to the same commit approval as code — write the change,
show it, and wait. Never auto-commit a rule change on the strength of an inferred preference.
