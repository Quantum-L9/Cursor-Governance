---
name: reasoning
version: "6.0.0"
description: "Multi-modal reasoning — abductive, deductive, inductive"
auto_chain: ynp
---

# /reasoning — Multi-Modal Reasoning

## WHAT IT DOES

Apply structured reasoning with confidence scoring:

| Mode | Purpose | When |
|------|---------|------|
| Abductive | Pattern discovery, hypothesis | Diagnosis, root cause |
| Deductive | Logical validation | Verification, compliance |
| Inductive | Generalization | Trends, predictions |

---

## EXECUTION

### 1. DEFINE OBJECTIVE

- What's the question/decision?
- What does success look like?
- What constraints apply?

### 2. APPLY REASONING MODES

**Abductive (Discovery):**
- Observe symptoms
- Generate explanations
- Rank by likelihood

**Deductive (Validation):**
- State premises
- Apply logic
- Derive conclusions

**Inductive (Generalization):**
- Collect observations
- Identify patterns
- Generalize principle

### 3. SYNTHESIZE

Combine insights → confidence score → recommendation

---

## CONFIDENCE SCORING

| Score | Meaning | Action |
|-------|---------|--------|
| ≥90% | Very High | Execute |
| 80-89% | High | Proceed with monitoring |
| 70-79% | Moderate | Validate first |
| <70% | Low | Investigate more |

---

## OUTPUT FORMAT

```markdown
## 🧠 REASONING: {topic}

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

→ **Auto-chains to /ynp**

--- End Command ---
