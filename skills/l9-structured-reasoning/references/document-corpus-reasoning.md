<!-- L9_META
l9_schema: 1
parent: l9-structured-reasoning
origin: migrated-from profiles/reasoning_docs.md (Strategic Intelligence Layer)
tags: [reasoning, document-corpus, gap-analysis, coherence, dependency-map]
status: active
/L9_META -->

# Document-Corpus Reasoning — Strategic Intelligence Layer

Multi-document analysis: reasoning across a **corpus** rather than a single file. Use when the
subject is a set of documents (specs, ADRs, policies, plans) and the question is about their
relationships, contradictions, or gaps — not about code behavior.

Complements [reasoning-modes.md](reasoning-modes.md) (depth tiers for a single problem) and
[analysis-modes.md](analysis-modes.md) (code analysis). Those route by complexity; this routes by
corpus-level question type.

## Mode selection

| Question | Mode |
|---|---|
| How does X connect to Y across docs? | Chain-of-thought |
| What repeats / what is anomalous? | Pattern recognition |
| Has this been solved elsewhere? | Analogical |
| Is my own conclusion sound? | Reflective |
| What does the whole corpus say? | Meta-analysis |

## Mode 1 — Chain-of-thought

Trace dependencies through document references.

1. Identify starting point (document, concept, requirement).
2. Trace dependencies through references.
3. Map logical flow of information and decisions.
4. Record the chain explicitly for transparency.
5. Identify gaps or breaks in the flow.

Output: dependency chain with the break named.

## Mode 2 — Pattern recognition

1. Scan corpus for repeated patterns.
2. Classify by type.
3. Measure frequency and significance.
4. Identify anomalies — deviations from the established pattern.
5. Report patterns with recommendations.

Pattern types: **structural** (organization, section format), **conceptual** (recurring themes),
**procedural** (repeated processes), **relational** (common doc relationships), **temporal**
(timeline patterns, milestones).

The anomaly is usually the finding. "14 of 15 modules have a test file" locates the gap faster than
reading all 15.

## Mode 3 — Analogical

1. Identify the problem domain.
2. Find analogous solved problems in the corpus.
3. Map structural similarities.
4. Adapt the solution to the new domain.
5. **Validate applicability and state limitations** — the adaptation is a hypothesis until checked.

Output: adapted solution with validation notes. Never present an analogy as a proven solution.

## Mode 4 — Reflective

Self-assessment applied to your own completed analysis.

1. Review the conclusion.
2. Question assumptions made.
3. Identify potential biases or blind spots.
4. Consider alternative interpretations.
5. Refine the conclusion.

Reflection questions:

- What assumptions did I make?
- What evidence contradicts the conclusion?
- Which perspectives are missing?
- How confident am I, and on what basis?

Typical correction shape: `"All stakeholders aligned"` → evidence is written docs only, no interview
data → `"Documented alignment exists; validation needed"` at medium confidence. Reflective mode
converts overclaims into scoped claims.

## Mode 5 — Meta-analysis

1. Aggregate insights from multiple analyses.
2. Identify meta-patterns across analysis types.
3. Assess overall corpus health and coherence.
4. Generate strategic recommendations.
5. Prioritize by impact and feasibility.

Meta-metrics:

| Metric | Scale | Meaning |
|---|---|---|
| Coherence | 0–100 | How well documents align |
| Completeness | 0–100 | Coverage of required topics |
| Redundancy index | % | Duplicate content |
| Gap severity | Critical / Major / Minor | Worst outstanding gap |
| Readiness | Yes / No / Partial | Ready for next phase |

Report `Partial` with the blocking count rather than rounding up to `Yes`.

## Operation 1 — Dependency mapping

1. Parse documents for references (links, citations, mentions).
2. Build a directed graph.
3. Identify critical-path documents.
4. Detect circular dependencies.
5. Emit a text tree grouped by level (foundation → requirements → implementation).

Always report two things explicitly: **circular dependencies** and **missing dependencies**
(referenced but not found). A referenced-but-absent document is a finding, not an omission.

## Operation 2 — Gap analysis

1. Identify all referenced topics/documents.
2. Verify existence and completeness.
3. Classify by severity.
4. Assess impact on readiness.
5. Emit a prioritized gap-closing plan.

| Severity | Definition | Action |
|---|---|---|
| Critical | Blocks progress | Immediate |
| Major | Significant impact | Address soon |
| Minor | Nice-to-have | Deferrable |
| Informational | No action needed | Awareness only |

Each gap states **impact** and **action**, not just absence. "Vendor financing terms undocumented"
is inert; "…so equipment procurement cannot proceed → create term sheet" is actionable.

## Operation 3 — Coherence check

1. Extract key claims from each document.
2. Check for contradictions across documents.
3. Verify data consistency (dates, numbers, names).
4. Identify conflicting recommendations.
5. Report conflicts with a proposed resolution each.

Contradictions are reported as pairs with both sources cited and a resolution owner. Two documents
stating different timelines is a decision to be made, not a typo to be silently picked.

## Operation 4 — Insight generation

1. Apply the relevant modes to the focus area.
2. Synthesize findings into actionable insights.
3. Prioritize by strategic value.
4. Summarize for the decision-maker.
5. Attach recommended actions.

Insight types: **opportunity** (unidentified value path), **risk** (failure point), **efficiency**
(more with less), **innovation** (novel combination), **quick win** (high value, low effort).

Each insight carries: the finding, its quantified consequence where available, and one action.

## Quality standards

Analysis MUST be:

- **Evidence-based** — every insight tied to a specific document or path.
- **Traceable** — reasoning chain from evidence to conclusion is visible.
- **Validated** — cross-checked against more than one source.
- **Transparent** — confidence level and assumptions stated.
- **Actionable** — leads to a specific next action.

Output MUST be: clear, concise (high-value insights, not data dumps), structured, prioritized, and
complete on context.

## Invocation

No dedicated command. Invoke via `/reasoning` or by naming the operation directly — for example
"map dependencies across `docs/contracts/`" or "coherence-check the ADR set". Automatic triggers
(on-save dependency refresh, scheduled insight generation) are **not wired**; treat every operation
as explicitly invoked.
