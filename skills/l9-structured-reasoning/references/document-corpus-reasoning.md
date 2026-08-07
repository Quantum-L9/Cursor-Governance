# Document-Corpus Reasoning

Use when the subject is a **set of documents** (specs, ADRs, policies, plans) and the question is about relationships, contradictions, gaps, or corpus health — not code behavior.

Load only for `task_kind: corpus` or an explicit corpus operation. Prefer primary reads of the named corpus over broad exploration.

## Mode selection

| Question | Mode |
|---|---|
| How does X connect to Y across docs? | Chain-of-thought |
| What repeats / what is anomalous? | Pattern recognition |
| Has this been solved elsewhere? | Analogical |
| Is my own conclusion sound? | Reflective |
| What does the whole corpus say? | Meta-analysis |

## Modes

### Chain-of-thought

Trace dependencies through document references. Name the starting point, map the chain, and report breaks explicitly.

Output: dependency chain with the break named.

### Pattern recognition

Scan for repeated structural, conceptual, procedural, relational, or temporal patterns. Classify, measure significance, and surface anomalies.

The anomaly is usually the finding. Prefer "14 of 15 modules have X" over reading all 15 as equals.

### Analogical

Find an analogous solved problem in the corpus, map structural similarities, adapt, then validate applicability. Treat the adaptation as a hypothesis until checked. Never present analogy as proof.

### Reflective

After a draft conclusion: challenge assumptions, name disconfirming evidence, note missing perspectives, and tighten overclaims into scoped claims with evidence grades.

### Meta-analysis

Aggregate prior mode outputs. Score coherence, completeness, redundancy, worst gap severity, and readiness (`Yes` / `No` / `Partial`). Prefer `Partial` with a blocking count over rounding up to `Yes`.

## Operations

### Dependency mapping

Build a directed reference graph. Report critical-path docs, circular dependencies, and missing dependencies (referenced but absent). Emit a foundation → requirements → implementation tree when useful.

### Gap analysis

Classify missing or incomplete topics by severity:

| Severity | Action |
|---|---|
| Critical | Blocks progress — immediate |
| Major | Significant impact — soon |
| Minor | Deferrable |
| Informational | Awareness only |

Each gap states impact and a concrete closing action.

### Coherence check

Extract material claims. Report contradictions as source pairs with a proposed resolution owner. Do not silently pick a winner when timelines, numbers, or recommendations conflict.

### Insight generation

Synthesize actionable insights (opportunity, risk, efficiency, innovation, quick win). Each insight carries the finding, consequence when available, and one next action.

## Quality bar

- Every insight cites a document or path.
- Evidence grade or `Unknown` on material claims.
- Cross-check across more than one source when stakes are guarded+.
- Output is structured, prioritized, and action-bearing — not a corpus dump.

## Invocation

Explicit corpus asks ("map dependencies across `docs/contracts/`", "coherence-check the ADR set") or router `task_kind: corpus`. No background/on-save corpus jobs.
