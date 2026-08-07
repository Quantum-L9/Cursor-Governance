<!-- L9_META
l9_schema: 1
parent: l9-structured-reasoning
origin: migrated-from reasoning command v6.0.0
tags: [reasoning, abductive, deductive, inductive, confidence]
status: active
/L9_META -->

# Reasoning Command Workflow — Multi-Modal Synthesis

Apply structured reasoning with confidence scoring.

| Mode | Purpose | When |
|------|---------|------|
| Abductive | Pattern discovery, hypothesis | Diagnosis, root cause |
| Deductive | Logical validation | Verification, compliance |
| Inductive | Generalization | Trends, predictions |

## Execution

### 1. Define objective

- What's the question/decision?
- What does success look like?
- What constraints apply?

### 2. Apply reasoning modes

**Abductive:** observe symptoms → generate explanations → rank by likelihood.

**Deductive:** state premises → apply logic → derive conclusions.

**Inductive:** collect observations → identify patterns → generalize principle.

### 3. Synthesize

Combine insights → confidence score → recommendation.

## Confidence scoring

| Score | Meaning | Action |
|-------|---------|--------|
| ≥90% | Very High | Execute |
| 80–89% | High | Proceed with monitoring |
| 70–79% | Moderate | Validate first |
| <70% | Low | Investigate more |

## Output format

```markdown
## REASONING: {topic}

### Analysis
**Abductive:** {findings}
**Deductive:** {validation}
**Inductive:** {patterns}

### Synthesis
{combined insight}

### Confidence: {score}%
**Evidence:** {quality}

### Recommendation
{action with rationale}
```

Auto-chain recommendation: load `l9-ynp` for next action.
